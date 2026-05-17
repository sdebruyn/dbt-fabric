from __future__ import annotations

import base64
import json
import shlex
import time
from dataclasses import dataclass

from dbt.adapters.fabric.fabric_api_client import FabricApiClient, FabricApiError


@dataclass
class SparkJobResult:
    """Result of a Spark Job Definition execution."""

    status: str
    start_time: str | None
    end_time: str | None
    job_url: str
    error_message: str | None


class SparkJobClient:
    """Client for managing and running Spark Job Definitions via the Fabric REST API.

    Args:
        api_client: Authenticated FabricApiClient for HTTP communication.
    """

    def __init__(self, api_client: FabricApiClient):
        self._api_client = api_client

    @property
    def _base_url(self) -> str:
        return self._api_client._credentials.fabric_base_api_uri

    @property
    def _workspace_id(self) -> str:
        return self._api_client.get_workspace_id()

    def list_spark_job_definitions(self) -> list[dict]:
        """List all Spark Job Definitions in the workspace, following pagination.

        Returns:
            List of Spark Job Definition metadata dicts.

        Raises:
            FabricApiError: If the API request fails.
        """
        items = []
        url: str | None = f"{self._base_url}/workspaces/{self._workspace_id}/sparkJobDefinitions"
        while url:
            resp = self._api_client._api_get(url)
            data = resp.json()
            items.extend(data.get("value", []))
            url = data.get("continuationUri")
        return items

    def find_by_name(self, name: str) -> dict | None:
        """Find a Spark Job Definition by its display name.

        Args:
            name: The display name to search for.

        Returns:
            The matching item dict, or None if not found.

        Raises:
            FabricApiError: If the API request fails.
        """
        for item in self.list_spark_job_definitions():
            if item.get("displayName") == name:
                return item
        return None

    def create_spark_job_definition(
        self, name: str, lakehouse_id: str, executable_path: str
    ) -> str:
        """Create a new Spark Job Definition in the workspace.

        Args:
            name: Display name for the new job definition.
            lakehouse_id: ID of the default lakehouse to attach.
            executable_path: abfss:// path to the Python entry point script.

        Returns:
            The ID of the newly created Spark Job Definition.

        Raises:
            FabricApiError: If the API request fails.
        """
        payload_json = json.dumps(
            {
                "executableFile": executable_path,
                "defaultLakehouseArtifactId": lakehouse_id,
                "language": "Python",
                "environmentArtifactId": None,
            }
        )
        payload_b64 = base64.b64encode(payload_json.encode()).decode()

        body = {
            "displayName": name,
            "definition": {
                "parts": [
                    {
                        "path": "SparkJobDefinitionV1.json",
                        "payload": payload_b64,
                        "payloadType": "InlineBase64",
                    }
                ]
            },
        }

        url = f"{self._base_url}/workspaces/{self._workspace_id}/sparkJobDefinitions"
        resp = self._api_client._api_post(url, body)
        return resp.json()["id"]

    def run_on_demand(self, item_id: str, command_line_args: list[str]) -> tuple[str, str]:
        """Submit an on-demand run of a Spark Job Definition.

        Args:
            item_id: ID of the Spark Job Definition to run.
            command_line_args: Command-line arguments to pass to the job.

        Returns:
            Tuple of (item_id, job_instance_id) for tracking the run.

        Raises:
            FabricApiError: If the API request fails.
        """
        url = (
            f"{self._base_url}/workspaces/{self._workspace_id}"
            f"/items/{item_id}/jobs/instances?jobType=sparkjob"
        )
        body = {"executionData": {"commandLineArguments": shlex.join(command_line_args)}}
        resp = self._api_client._api_post(url, body)

        location = resp.headers.get("Location", "")
        parts = location.rstrip("/").split("/")
        job_instance_id = parts[-1] if parts else ""
        return item_id, job_instance_id

    def delete_spark_job_definition(self, item_id: str) -> None:
        """Delete a Spark Job Definition by ID.

        Args:
            item_id: ID of the Spark Job Definition to delete.

        Raises:
            FabricApiError: If the API request fails.
        """
        url = f"{self._base_url}/workspaces/{self._workspace_id}/sparkJobDefinitions/{item_id}"
        self._api_client._api_delete(url)

    def get_job_instance(self, item_id: str, job_instance_id: str) -> dict:
        """Get the current state of a job instance.

        Args:
            item_id: ID of the Spark Job Definition.
            job_instance_id: ID of the specific job run instance.

        Returns:
            Job instance metadata dict including status, timestamps, and failure info.

        Raises:
            FabricApiError: If the API request fails.
        """
        url = (
            f"{self._base_url}/workspaces/{self._workspace_id}"
            f"/items/{item_id}/jobs/instances/{job_instance_id}"
        )
        return self._api_client._api_get(url).json()

    def poll_until_done(
        self, item_id: str, job_instance_id: str, interval: int = 10, timeout: int = 1800
    ) -> SparkJobResult:
        """Poll a job instance until it reaches a terminal state.

        Prints status updates to stdout when the status changes.

        Args:
            item_id: ID of the Spark Job Definition.
            job_instance_id: ID of the specific job run instance.
            interval: Seconds between polling attempts.
            timeout: Maximum seconds to wait before returning a Timeout result.

        Returns:
            SparkJobResult with final status, timestamps, and any error message.
        """
        workspace_id = self._workspace_id
        job_url = (
            f"https://app.fabric.microsoft.com/groups/{workspace_id}"
            f"/sparkJobDefinitions/{item_id}/runs/{job_instance_id}"
        )
        start = time.time()
        last_status = ""

        while True:
            elapsed = time.time() - start
            if elapsed > timeout:
                return SparkJobResult(
                    status="Timeout",
                    start_time=None,
                    end_time=None,
                    job_url=job_url,
                    error_message=f"Job timed out after {timeout}s. Check: {job_url}",
                )

            instance = self._get_with_retry(item_id, job_instance_id)
            status = instance.get("status", "Unknown")

            if status != last_status:
                minutes = int(elapsed) // 60
                seconds = int(elapsed) % 60
                print(f"  [{minutes}:{seconds:02d}] {status}...")
                last_status = status

            if status in ("Completed", "Failed", "Cancelled", "Deduped"):
                return SparkJobResult(
                    status=status,
                    start_time=instance.get("startTimeUtc"),
                    end_time=instance.get("endTimeUtc"),
                    job_url=job_url,
                    error_message=instance.get("failureReason", {}).get("message"),
                )

            time.sleep(interval)

    def _get_with_retry(self, item_id: str, job_instance_id: str, max_retries: int = 3) -> dict:
        """Fetch job instance state with retry on transient API errors.

        Args:
            item_id: ID of the Spark Job Definition.
            job_instance_id: ID of the specific job run instance.
            max_retries: Maximum number of attempts before raising.

        Returns:
            Job instance metadata dict.

        Raises:
            FabricApiError: If all retry attempts fail.
        """
        url = (
            f"{self._base_url}/workspaces/{self._workspace_id}"
            f"/items/{item_id}/jobs/instances/{job_instance_id}"
        )
        for attempt in range(max_retries):
            try:
                return self._api_client._api_get(url).json()
            except FabricApiError:
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 ** (attempt + 1))
        return {}
