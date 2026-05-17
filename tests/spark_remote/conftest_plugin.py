from __future__ import annotations

from uuid import uuid4

import pytest

from tests.spark_remote.orchestrator import RemoteTestOrchestrator
from tests.spark_remote.result_reporter import report_remote_results


def remote_runtestloop(session: pytest.Session) -> bool:
    """Replace pytest's default test loop with remote Spark execution.

    Generates a unique run ID to isolate concurrent runs, syncs the project
    to a per-run lakehouse directory, submits a Spark job, downloads junitxml
    results, and reports them back into the local session.

    Args:
        session: The pytest Session (already collected).

    Returns:
        True to signal that the test loop has been handled.
    """
    if session.config.option.collectonly:
        return True

    if not session.items:
        return True

    run_id = uuid4().hex[:8]
    remote_args = _build_remote_args(session)

    print(f"\nRemote execution [{run_id}]: syncing project to lakehouse...")
    orchestrator = RemoteTestOrchestrator.from_env(run_id)
    orchestrator.sync_project()

    print(f"\nRemote execution [{run_id}]: submitting Spark job...")
    job_result = orchestrator.run_spark_job(remote_args)

    print(f"\n  {job_result.status} — downloading results...")
    results_path = orchestrator.download_results()
    report_remote_results(session, results_path, job_result)

    return True


def _build_remote_args(session: pytest.Session) -> list[str]:
    """Extract relevant pytest options from the local session for remote forwarding.

    Forwards -k, -v, --de, -x, and positional test paths. The --junitxml path
    is set by the remote entry point based on the run ID.

    Args:
        session: The local pytest Session to extract options from.

    Returns:
        List of CLI arguments to pass to the remote pytest invocation.
    """
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

    positional = config.args
    if positional:
        args.extend(positional)

    return args
