from __future__ import annotations

import pytest

from tests.spark_remote.orchestrator import RemoteTestOrchestrator
from tests.spark_remote.result_reporter import report_remote_results


def remote_runtestloop(session: pytest.Session) -> bool:
    if session.config.option.collectonly:
        return True

    if not session.items:
        return True

    remote_args = _build_remote_args(session)

    print("\nRemote execution: syncing project to lakehouse...")
    orchestrator = RemoteTestOrchestrator.from_env()
    orchestrator.sync_project()

    print("\nRemote execution: submitting Spark job...")
    job_result = orchestrator.run_spark_job(remote_args)

    print(f"\n  {job_result.status} — downloading results...")
    results_path = orchestrator.download_results()
    report_remote_results(session, results_path, job_result)

    return True


def _build_remote_args(session: pytest.Session) -> list[str]:
    args: list[str] = []
    config = session.config

    if config.getoption("-k"):
        args.extend(["-k", config.getoption("-k")])

    if config.getoption("verbose", 0) > 0:
        args.append("-" + "v" * config.getoption("verbose"))

    if config.getoption("--de", default=False):
        args.append("--de")

    if config.getoption("-x", default=False):
        args.append("-x")

    args.append("--junitxml=/lakehouse/default/Files/dbt-test-artifacts/results.xml")

    return args
