"""Entry point for remote pytest execution on Fabric Spark.

This script is submitted as a Spark Job Definition. It installs the project
and its dependencies, then runs pytest with the provided arguments. Results
are written to junitxml on the lakehouse filesystem for the local pytest
session to parse.
"""

from __future__ import annotations

import os
import subprocess
import sys

LAKEHOUSE_ROOT = "/lakehouse/default"
PROJECT_DIR = f"{LAKEHOUSE_ROOT}/Files/dbt-fabric-tests"
ARTIFACTS_DIR = f"{LAKEHOUSE_ROOT}/Files/dbt-test-artifacts"


def main() -> None:
    if os.path.isdir(ARTIFACTS_DIR):
        for f in os.listdir(ARTIFACTS_DIR):
            os.remove(os.path.join(ARTIFACTS_DIR, f))
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)

    requirements_file = f"{PROJECT_DIR}/requirements-remote.txt"
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-r", requirements_file, "--quiet"],
    )

    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-e", PROJECT_DIR, "--no-deps", "--quiet"],
    )

    env_file = f"{PROJECT_DIR}/test.env.remote"
    if os.path.exists(env_file):
        from dotenv import load_dotenv

        load_dotenv(env_file, override=True)

    os.environ["FABRIC_TEST_SPARK_EXEC_MODE"] = "remote"

    pytest_args = sys.argv[1:]

    has_junitxml = any(arg.startswith("--junitxml") for arg in pytest_args)
    if not has_junitxml:
        pytest_args.extend(["--junitxml", f"{ARTIFACTS_DIR}/results.xml"])

    exit_code = subprocess.call(
        [sys.executable, "-m", "pytest"] + pytest_args,
        cwd=PROJECT_DIR,
    )

    exit_code_file = f"{ARTIFACTS_DIR}/exit_code.txt"
    with open(exit_code_file, "w") as f:
        f.write(str(exit_code))

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
