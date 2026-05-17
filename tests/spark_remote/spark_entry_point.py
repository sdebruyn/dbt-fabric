"""Entry point for remote pytest execution on Fabric Spark.

This script is submitted as a Spark Job Definition. It receives a run ID
as its first argument (used to locate the per-run project and artifacts
directories on the lakehouse), installs the project and its dependencies,
then runs pytest with the remaining arguments.
"""

from __future__ import annotations

import os
import subprocess
import sys

LAKEHOUSE_ROOT = "/lakehouse/default"


def main() -> None:
    """Install dependencies, configure env, run pytest, and write exit code.

    The first positional argument is the run ID, which determines the project
    and artifacts paths on the lakehouse. All remaining arguments are forwarded
    to pytest. Ensures --junitxml is set so results can be collected.

    Raises:
        subprocess.CalledProcessError: If pip install fails.
        SystemExit: Always exits with the pytest exit code.
    """
    run_id = sys.argv[1]
    pytest_args = sys.argv[2:]

    project_dir = f"{LAKEHOUSE_ROOT}/Files/dbt-remote-runs/{run_id}/project"
    artifacts_dir = f"{LAKEHOUSE_ROOT}/Files/dbt-remote-runs/{run_id}/artifacts"

    if os.path.isdir(artifacts_dir):
        for f in os.listdir(artifacts_dir):
            os.remove(os.path.join(artifacts_dir, f))
    os.makedirs(artifacts_dir, exist_ok=True)

    requirements_file = f"{project_dir}/requirements-remote.txt"
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-r", requirements_file, "--quiet"],
    )

    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-e", project_dir, "--no-deps", "--quiet"],
    )

    env_file = f"{project_dir}/test.env.remote"
    if os.path.exists(env_file):
        from dotenv import load_dotenv

        load_dotenv(env_file, override=True)

    os.environ["FABRIC_TEST_SPARK_EXEC_MODE"] = "remote"

    has_junitxml = any(arg.startswith("--junitxml") for arg in pytest_args)
    if not has_junitxml:
        pytest_args.extend(["--junitxml", f"{artifacts_dir}/results.xml"])

    exit_code = subprocess.call(
        [sys.executable, "-m", "pytest"] + pytest_args,
        cwd=project_dir,
    )

    exit_code_file = f"{artifacts_dir}/exit_code.txt"
    with open(exit_code_file, "w") as f:
        f.write(str(exit_code))

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
