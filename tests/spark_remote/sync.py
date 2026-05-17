from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

EXCLUDE_PATHS = (
    ".venv;.git;__pycache__;.cache;.claude;logs;.ruff_cache;"
    ".pytest_cache;.eggs;dist;build;site;.vscode;node_modules;"
    "remote-test-results;dbt-test-artifacts"
)
EXCLUDE_PATTERNS = "*.pyc;*.pyo;*.egg-info"


class ProjectSync:
    """Syncs the local project to/from a lakehouse on OneLake via azcopy.

    Args:
        workspace_id: Fabric workspace GUID.
        lakehouse_id: Lakehouse item GUID.
        project_root: Local path to the dbt-fabric project root.
    """

    def __init__(self, workspace_id: str, lakehouse_id: str, project_root: Path):
        self._project_root = project_root
        self._onelake_base = (
            f"https://onelake.dfs.fabric.microsoft.com/{workspace_id}/{lakehouse_id}/Files"
        )

    def upload(self) -> None:
        """Upload the project directory to the lakehouse, excluding build artifacts.

        Generates a requirements file and sanitized test.env before syncing.

        Raises:
            RuntimeError: If azcopy sync or uv export fails.
        """
        self._generate_requirements()
        self._generate_test_env_remote()

        target = f"{self._onelake_base}/dbt-fabric-tests"
        print(f"  Syncing: {self._project_root} -> {target}")

        cmd = [
            "azcopy",
            "sync",
            str(self._project_root),
            target,
            "--login-type=azcli",
            f"--exclude-path={EXCLUDE_PATHS}",
            f"--exclude-pattern={EXCLUDE_PATTERNS}",
            "--delete-destination=true",
            "--put-md5",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"azcopy sync failed:\n{result.stderr}")
        print("  Sync complete.")

    def download_artifacts(self, local_dir: Path) -> Path | None:
        """Download test artifacts (junitxml) from the lakehouse.

        Args:
            local_dir: Local directory to sync artifacts into.

        Returns:
            Path to results.xml if it exists after download, otherwise None.

        Raises:
            RuntimeError: If azcopy sync fails.
        """
        source = f"{self._onelake_base}/dbt-test-artifacts"
        local_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            "azcopy",
            "sync",
            source,
            str(local_dir),
            "--login-type=azcli",
            "--delete-destination=true",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"azcopy artifact download failed:\n{result.stderr}")

        results_xml = local_dir / "results.xml"
        return results_xml if results_xml.exists() else None

    def _generate_requirements(self) -> None:
        """Export pinned requirements via uv for remote pip install.

        Raises:
            RuntimeError: If uv export fails.
        """
        result = subprocess.run(
            ["uv", "export", "--format", "requirements.txt", "--all-extras", "--group", "dev"],
            capture_output=True,
            text=True,
            cwd=self._project_root,
        )
        if result.returncode != 0:
            raise RuntimeError(f"uv export failed:\n{result.stderr}")

        reqs_path = self._project_root / "requirements-remote.txt"
        reqs_path.write_text(result.stdout)

    def _generate_test_env_remote(self) -> None:
        """Create a sanitized test.env.remote with secrets stripped and auth overridden.

        Reads the local test.env, removes sensitive variables (client secrets,
        federated tokens), and overrides authentication to use notebookutils.
        """
        test_env_path = self._project_root / "test.env"
        remote_env_path = self._project_root / "test.env.remote"

        overrides = {
            "FABRIC_TEST_AUTH": "notebookutils",
            "FABRIC_TEST_SPARK_EXEC_MODE": "remote",
        }

        secret_prefixes = (
            "FABRIC_TEST_CLIENT_SECRET",
            "FABRIC_TEST_FEDERATED_TOKEN",
            "FABRIC_TEST_TENANT_ID",
            "FABRIC_TEST_CLIENT_ID",
        )

        lines = []
        if test_env_path.exists():
            for line in test_env_path.read_text().splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    lines.append(line)
                    continue
                key = stripped.split("=", 1)[0]
                if key in overrides:
                    continue
                if key.startswith(secret_prefixes):
                    continue
                lines.append(line)

        for key, value in overrides.items():
            lines.append(f"{key}={value}")

        remote_env_path.write_text("\n".join(lines) + "\n")


def check_prerequisites() -> list[str]:
    """Verify that required CLI tools (azcopy, az) are available and authenticated.

    Returns:
        List of human-readable error messages. Empty if all prerequisites are met.
    """
    errors = []

    if not shutil.which("azcopy"):
        errors.append(
            "azcopy not found on PATH. Install from: "
            "https://learn.microsoft.com/en-us/azure/storage/common/storage-use-azcopy-v10"
            "?WT.mc_id=MVP_310840"
        )

    try:
        result = subprocess.run(["az", "account", "show"], capture_output=True, text=True)
        if result.returncode != 0:
            errors.append("Azure CLI not logged in. Run: az login")
    except FileNotFoundError:
        errors.append(
            "Azure CLI (az) not found on PATH. Install from: "
            "https://learn.microsoft.com/en-us/cli/azure/install-azure-cli"
            "?WT.mc_id=MVP_310840"
        )

    return errors
