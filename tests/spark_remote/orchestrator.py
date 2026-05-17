from __future__ import annotations

import os
import sys
from pathlib import Path

from dbt.adapters.fabric.fabric_api_client import FabricApiClient
from dbt.adapters.fabric.fabric_token_provider import FabricTokenProvider
from dbt.adapters.fabricspark.fabricspark_credentials import FabricSparkCredentials
from tests.conftest import _auth_kwargs_from_env
from tests.spark_remote.spark_job_client import SparkJobClient, SparkJobResult
from tests.spark_remote.sync import ProjectSync, check_prerequisites


class RemoteTestOrchestrator:
    """Coordinates remote test execution: sync, job submission, and result retrieval.

    Args:
        api_client: Authenticated FabricApiClient for API communication.
        project_root: Local path to the dbt-fabric project root.
        job_name: Display name of the Spark Job Definition to use or create.
    """

    def __init__(
        self,
        api_client: FabricApiClient,
        project_root: Path,
        job_name: str = "dbt-fabric-tests",
    ):
        self._api_client = api_client
        self._project_root = project_root
        self._job_name = job_name
        self._local_results_dir = project_root / "remote-test-results"

    @classmethod
    def from_env(cls) -> RemoteTestOrchestrator:
        """Create an orchestrator from environment variables.

        Uses FABRIC_TEST_* env vars to build credentials and resolve workspace/lakehouse.

        Raises:
            SystemExit: If prerequisites (azcopy, Azure CLI) are not met.
        """
        errors = check_prerequisites()
        if errors:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            raise SystemExit(1)

        job_name = os.environ.get("FABRIC_TEST_SPARK_JOB_NAME", "dbt-fabric-tests")

        creds = FabricSparkCredentials(
            database=os.getenv("FABRIC_TEST_LAKEHOUSE_NAME", ""),
            schema="dbo",
            workspace_name=os.getenv("FABRIC_TEST_WORKSPACE_NAME"),
            workspace_id=os.getenv("FABRIC_TEST_WORKSPACE_ID"),
            **_auth_kwargs_from_env(),
        )
        token_provider = FabricTokenProvider(creds)
        api_client = FabricApiClient(creds, token_provider)

        project_root = Path(__file__).resolve().parent.parent.parent
        return cls(
            api_client=api_client,
            project_root=project_root,
            job_name=job_name,
        )

    def sync_project(self) -> None:
        """Upload the project to the lakehouse via azcopy.

        Raises:
            RuntimeError: If azcopy sync fails.
        """
        workspace_id = self._api_client.get_workspace_id()
        lakehouse_id = self._api_client.get_lakehouse_id()
        sync = ProjectSync(workspace_id, lakehouse_id, self._project_root)
        sync.upload()

    def run_spark_job(self, pytest_args: list[str]) -> SparkJobResult:
        """Submit a Spark job to run pytest remotely and wait for completion.

        Creates a Spark Job Definition if one doesn't exist with the configured name.

        Args:
            pytest_args: Command-line arguments to forward to the remote pytest invocation.

        Returns:
            SparkJobResult with final job status and metadata.

        Raises:
            FabricApiError: If any Fabric API call fails.
        """
        workspace_id = self._api_client.get_workspace_id()
        lakehouse_id = self._api_client.get_lakehouse_id()

        job_client = SparkJobClient(self._api_client)

        existing = job_client.find_by_name(self._job_name)
        if existing:
            item_id = existing["id"]
            print(f"  Reusing Spark Job Definition: {self._job_name} ({item_id})")
        else:
            executable_path = (
                f"abfss://{workspace_id}@onelake.dfs.fabric.microsoft.com"
                f"/{lakehouse_id}/Files/dbt-fabric-tests"
                f"/tests/spark_remote/spark_entry_point.py"
            )
            item_id = job_client.create_spark_job_definition(
                name=self._job_name,
                lakehouse_id=lakehouse_id,
                executable_path=executable_path,
            )
            print(f"  Created Spark Job Definition: {self._job_name} ({item_id})")

        print(f"  Remote pytest args: {' '.join(pytest_args)}")
        item_id, job_instance_id = job_client.run_on_demand(item_id, pytest_args)

        job_url = (
            f"https://app.fabric.microsoft.com/groups/{workspace_id}"
            f"/sparkJobDefinitions/{item_id}/runs/{job_instance_id}"
        )
        print(f"  Job URL: {job_url}")
        print("\nWaiting for Spark job...")

        return job_client.poll_until_done(item_id, job_instance_id)

    def download_results(self) -> Path | None:
        """Download test result artifacts from the lakehouse.

        Returns:
            Path to the results.xml file, or None if it was not produced.

        Raises:
            RuntimeError: If azcopy download fails.
        """
        workspace_id = self._api_client.get_workspace_id()
        lakehouse_id = self._api_client.get_lakehouse_id()
        sync = ProjectSync(workspace_id, lakehouse_id, self._project_root)
        return sync.download_artifacts(self._local_results_dir)
