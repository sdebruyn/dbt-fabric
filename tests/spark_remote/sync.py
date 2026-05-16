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
    def __init__(self, workspace_name: str, lakehouse_name: str, project_root: Path):
        self._workspace_name = workspace_name
        self._lakehouse_name = lakehouse_name
        self._project_root = project_root
        self._onelake_base = (
            f"https://onelake.dfs.fabric.microsoft.com"
            f"/{workspace_name}/{lakehouse_name}.Lakehouse/Files"
        )

    def upload(self) -> None:
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
        test_env_path = self._project_root / "test.env"
        remote_env_path = self._project_root / "test.env.remote"

        overrides = {
            "FABRIC_TEST_AUTH": "notebookutils",
            "FABRIC_TEST_SPARK_EXEC_MODE": "remote",
        }

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
                lines.append(line)

        for key, value in overrides.items():
            lines.append(f"{key}={value}")

        remote_env_path.write_text("\n".join(lines) + "\n")


def check_prerequisites() -> list[str]:
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
