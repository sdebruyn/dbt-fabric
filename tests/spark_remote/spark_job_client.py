from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
from typing import Callable

import requests

FABRIC_API_BASE = "https://api.fabric.microsoft.com"
FABRIC_CREDENTIAL_SCOPE = "https://analysis.windows.net/powerbi/api/.default"


@dataclass
class SparkJobResult:
    status: str
    start_time: str | None
    end_time: str | None
    job_url: str
    error_message: str | None


class SparkJobClient:
    def __init__(self, workspace_id: str, token_provider_fn: Callable[[], str]):
        self._workspace_id = workspace_id
        self._token_provider_fn = token_provider_fn

    def _headers(self) -> dict[str, str]:
        token = self._token_provider_fn()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def _get(self, path: str, **kwargs) -> requests.Response:
        url = f"{FABRIC_API_BASE}{path}"
        resp = requests.get(url, headers=self._headers(), **kwargs)
        resp.raise_for_status()
        return resp

    def _post(self, path: str, json_data: dict | None = None, **kwargs) -> requests.Response:
        url = f"{FABRIC_API_BASE}{path}"
        resp = requests.post(url, headers=self._headers(), json=json_data, **kwargs)
        resp.raise_for_status()
        return resp

    def list_spark_job_definitions(self) -> list[dict]:
        items = []
        path = f"/v1/workspaces/{self._workspace_id}/sparkJobDefinitions"
        while path:
            resp = self._get(path)
            data = resp.json()
            items.extend(data.get("value", []))
            path = data.get("continuationUri")
        return items

    def find_by_name(self, name: str) -> dict | None:
        for item in self.list_spark_job_definitions():
            if item.get("displayName") == name:
                return item
        return None

    def create_spark_job_definition(
        self, name: str, lakehouse_id: str, executable_path: str
    ) -> str:
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

        path = f"/v1/workspaces/{self._workspace_id}/sparkJobDefinitions"
        resp = self._post(path, json_data=body)
        return resp.json()["id"]

    def run_on_demand(self, item_id: str, command_line_args: list[str]) -> tuple[str, str]:
        path = (
            f"/v1/workspaces/{self._workspace_id}/items/{item_id}/jobs/instances?jobType=sparkjob"
        )
        body = {"executionData": {"commandLineArguments": " ".join(command_line_args)}}
        resp = self._post(path, json_data=body)

        location = resp.headers.get("Location", "")
        # Location header format: .../items/{item_id}/jobs/instances/{job_instance_id}
        parts = location.rstrip("/").split("/")
        job_instance_id = parts[-1] if parts else ""
        return item_id, job_instance_id

    def get_job_instance(self, item_id: str, job_instance_id: str) -> dict:
        path = (
            f"/v1/workspaces/{self._workspace_id}/items/{item_id}/jobs/instances/{job_instance_id}"
        )
        return self._get(path).json()

    def poll_until_done(
        self, item_id: str, job_instance_id: str, interval: int = 10, timeout: int = 1800
    ) -> SparkJobResult:
        job_url = (
            f"https://app.fabric.microsoft.com/groups/{self._workspace_id}"
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
        path = (
            f"/v1/workspaces/{self._workspace_id}/items/{item_id}/jobs/instances/{job_instance_id}"
        )
        for attempt in range(max_retries):
            try:
                return self._get(path).json()
            except requests.exceptions.RequestException:
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 ** (attempt + 1))
        return {}
