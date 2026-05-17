from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

from dbt.adapters.fabric.fabric_api_client import FabricApiClient
from dbt.adapters.fabric.fabric_token_provider import FabricTokenProvider
from dbt.adapters.fabricspark.fabricspark_credentials import FabricSparkCredentials
from tests.conftest import _auth_kwargs_from_env
from tests.spark_remote.spark_job_client import SparkJobClient, SparkJobResult
from tests.spark_remote.sync import ProjectSync, check_prerequisites


def _worktree_key(project_root: Path) -> str:
    """Derive a stable short key from the worktree's absolute path.

    Args:
        project_root: Absolute path to the project root.

    Returns:
        8-character hex digest, stable across runs from the same directory.
    """
    return hashlib.md5(str(project_root).encode()).hexdigest()[:8]


class RemoteTestOrchestrator:
    """Coordinates remote test execution: sync, job submission, and result retrieval.

    Uses a two-level namespace on OneLake:

    - **worktree_key** (hash of project root path) — determines the project
      upload path. Stable across runs from the same worktree, enabling
      incremental sync. Also used to name and reuse the Spark Job Definition.
    - **run_id** (random UUID fragment) — determines the artifacts path.
      Unique per invocation, preventing concurrent runs from overwriting
      each other's results.

    Args:
        api_client: Authenticated FabricApiClient for API communication.
        project_root: Local path to the dbt-fabric project root.
        run_id: Unique identifier for this test run.
        job_name: Base display name of the Spark Job Definition.
    """

    def __init__(
        self,
        api_client: FabricApiClient,
        project_root: Path,
        run_id: str,
        job_name: str = "dbt-fabric-tests",
    ):
        self._api_client = api_client
        self._project_root = project_root
        self._run_id = run_id
        self._worktree_key = _worktree_key(project_root)
        self._job_name = job_name
        self._local_results_dir = project_root / "remote-test-results" / run_id

    @classmethod
    def from_env(cls, run_id: str) -> RemoteTestOrchestrator:
        """Create an orchestrator from environment variables.

        Uses FABRIC_TEST_* env vars to build credentials and resolve workspace/lakehouse.

        Args:
            run_id: Unique identifier for this test run.

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
            run_id=run_id,
            job_name=job_name,
        )

    def _make_sync(self) -> ProjectSync:
        """Create a ProjectSync configured for this worktree and run."""
        return ProjectSync(
            self._api_client.get_workspace_id(),
            self._api_client.get_lakehouse_id(),
            self._project_root,
            self._worktree_key,
            self._run_id,
        )

    def sync_project(self) -> None:
        """Upload the project to a per-worktree lakehouse directory via azcopy.

        Uses incremental sync — only files that changed since the last upload
        from this worktree are transferred.

        Raises:
            RuntimeError: If azcopy sync fails.
        """
        self._make_sync().upload()

    def run_spark_job(self, pytest_args: list[str]) -> SparkJobResult:
        """Submit a Spark job to run pytest remotely and wait for completion.

        Reuses the Spark Job Definition for this worktree if one exists,
        otherwise creates a new one. Passes both the worktree key and run ID
        to the entry point so it can locate the project and artifacts directories.

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

        job_definition_name = f"{self._job_name}-{self._worktree_key}"
        existing = job_client.find_by_name(job_definition_name)
        if existing:
            item_id = existing["id"]
            print(f"  Reusing Spark Job Definition: {job_definition_name} ({item_id})")
        else:
            executable_path = (
                f"abfss://{workspace_id}@onelake.dfs.fabric.microsoft.com"
                f"/{lakehouse_id}/Files/dbt-remote-runs/projects/{self._worktree_key}"
                f"/tests/spark_remote/spark_entry_point.py"
            )
            item_id = job_client.create_spark_job_definition(
                name=job_definition_name,
                lakehouse_id=lakehouse_id,
                executable_path=executable_path,
            )
            print(f"  Created Spark Job Definition: {job_definition_name} ({item_id})")

        full_args = [self._worktree_key, self._run_id, *pytest_args]
        print(f"  Remote pytest args: {' '.join(pytest_args)}")
        item_id, job_instance_id = job_client.run_on_demand(item_id, full_args)

        job_url = (
            f"https://app.fabric.microsoft.com/groups/{workspace_id}"
            f"/sparkJobDefinitions/{item_id}/runs/{job_instance_id}"
        )
        print(f"  Job URL: {job_url}")
        print("\nWaiting for Spark job...")

        return job_client.poll_until_done(item_id, job_instance_id)

    def download_results(self) -> Path | None:
        """Download test result artifacts from the per-run artifacts directory.

        Returns:
            Path to the results.xml file, or None if it was not produced.

        Raises:
            RuntimeError: If azcopy download fails.
        """
        return self._make_sync().download_artifacts(self._local_results_dir)
