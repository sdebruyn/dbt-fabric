from __future__ import annotations

import os
import sys
from pathlib import Path

from dbt.adapters.fabric.fabric_credentials import FabricCredentials
from dbt.adapters.fabric.fabric_token_provider import FabricTokenProvider
from tests.spark_remote.spark_job_client import SparkJobClient, SparkJobResult
from tests.spark_remote.sync import ProjectSync, check_prerequisites


class RemoteTestOrchestrator:
    def __init__(
        self,
        workspace_id: str,
        lakehouse_id: str,
        project_root: Path,
        token_provider: FabricTokenProvider,
        job_name: str = "dbt-fabric-tests",
    ):
        self._workspace_id = workspace_id
        self._lakehouse_id = lakehouse_id
        self._project_root = project_root
        self._job_name = job_name

        self._sync = ProjectSync(workspace_id, lakehouse_id, project_root)
        self._token_provider = token_provider
        self._job_client = SparkJobClient(workspace_id, self._get_token)
        self._local_results_dir = project_root / "remote-test-results"

    @classmethod
    def from_env(cls) -> RemoteTestOrchestrator:
        errors = check_prerequisites()
        if errors:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            raise SystemExit(1)

        workspace_id = os.environ.get("FABRIC_TEST_WORKSPACE_ID", "")
        lakehouse_id = os.environ.get("FABRIC_TEST_REMOTE_LAKEHOUSE_ID", "")
        job_name = os.environ.get("FABRIC_TEST_SPARK_JOB_NAME", "dbt-fabric-tests")

        missing = []
        if not workspace_id:
            missing.append("FABRIC_TEST_WORKSPACE_ID")
        if not lakehouse_id:
            missing.append("FABRIC_TEST_REMOTE_LAKEHOUSE_ID")
        if missing:
            raise ValueError(f"Required env vars not set: {', '.join(missing)}")

        auth_kwargs: dict[str, str] = {}
        auth = os.getenv("FABRIC_TEST_AUTH")
        if auth:
            auth_kwargs["authentication"] = auth
        for key in ("tenant_id", "client_id", "federated_token_url", "federated_token_file"):
            val = os.getenv(f"FABRIC_TEST_{key.upper()}")
            if val:
                auth_kwargs[key] = val
        federated_header = os.getenv("FABRIC_TEST_FEDERATED_TOKEN_HEADER")
        if federated_header:
            auth_kwargs["federated_token_header"] = federated_header

        creds = FabricCredentials(
            database="",
            schema="dbo",
            workspace_id=workspace_id,
            **auth_kwargs,
        )
        token_provider = FabricTokenProvider(creds)

        project_root = Path(__file__).resolve().parent.parent.parent
        return cls(
            workspace_id=workspace_id,
            lakehouse_id=lakehouse_id,
            project_root=project_root,
            token_provider=token_provider,
            job_name=job_name,
        )

    def sync_project(self) -> None:
        self._sync.upload()

    def run_spark_job(self, pytest_args: list[str]) -> SparkJobResult:
        existing = self._job_client.find_by_name(self._job_name)
        if existing:
            item_id = existing["id"]
            print(f"  Reusing Spark Job Definition: {self._job_name} ({item_id})")
        else:
            executable_path = (
                f"abfss://{self._workspace_id}@onelake.dfs.fabric.microsoft.com"
                f"/{self._lakehouse_id}/Files/dbt-fabric-tests"
                f"/tests/spark_remote/spark_entry_point.py"
            )
            item_id = self._job_client.create_spark_job_definition(
                name=self._job_name,
                lakehouse_id=self._lakehouse_id,
                executable_path=executable_path,
            )
            print(f"  Created Spark Job Definition: {self._job_name} ({item_id})")

        print(f"  Remote pytest args: {' '.join(pytest_args)}")
        item_id, job_instance_id = self._job_client.run_on_demand(item_id, pytest_args)

        job_url = (
            f"https://app.fabric.microsoft.com/groups/{self._workspace_id}"
            f"/sparkJobDefinitions/{item_id}/runs/{job_instance_id}"
        )
        print(f"  Job URL: {job_url}")
        print("\nWaiting for Spark job...")

        return self._job_client.poll_until_done(item_id, job_instance_id)

    def download_results(self) -> Path | None:
        return self._sync.download_artifacts(self._local_results_dir)

    def _get_token(self) -> str:
        return self._token_provider.get_access_token()
