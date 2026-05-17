from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest
from _pytest.reports import TestReport
from junitparser import Error, Failure, JUnitXml, Skipped, TestCase

from tests.spark_remote.spark_job_client import SparkJobResult


@dataclass
class JunitTestResult:
    """Parsed result of a single test case from junitxml."""

    nodeid: str
    outcome: str
    duration: float
    failure_message: str | None = None
    skip_reason: str | None = None
    sections: list[tuple[str, str]] = field(default_factory=list)


def report_remote_results(
    session: pytest.Session, results_path: Path | None, job_result: SparkJobResult
) -> None:
    """Report remote test results back into the local pytest session.

    Parses the junitxml from the remote run and replays each result as a
    pytest TestReport so the local session shows correct pass/fail/skip counts.

    Args:
        session: The local pytest Session with collected items.
        results_path: Path to the downloaded results.xml, or None if unavailable.
        job_result: The SparkJobResult with job status and error info.
    """
    if results_path is None:
        msg = f"Remote job {job_result.status}"
        if job_result.error_message:
            msg += f": {job_result.error_message}"
        msg += f"\nJob URL: {job_result.job_url}"
        _report_all_as_error(session, msg)
        return

    results = _parse_junitxml(results_path)
    result_map = {r.nodeid: r for r in results}

    for item in session.items:
        ihook = item.ihook
        ihook.pytest_runtest_logstart(nodeid=item.nodeid, location=item.location)

        result = result_map.get(item.nodeid)
        if result is None:
            not_run = JunitTestResult(
                nodeid=item.nodeid,
                outcome="skipped",
                duration=0,
                skip_reason="Not executed by remote run (possibly due to -x/maxfail)",
            )
            _report_item_result(item, not_run)
        else:
            _report_item_result(item, result)

        ihook.pytest_runtest_logfinish(nodeid=item.nodeid, location=item.location)


def _report_all_as_error(session: pytest.Session, message: str) -> None:
    """Report all collected items as failed with the given error message.

    Args:
        session: The pytest Session with collected items.
        message: Error message to attach to each test report.
    """
    for item in session.items:
        ihook = item.ihook
        ihook.pytest_runtest_logstart(nodeid=item.nodeid, location=item.location)
        _report_item_as_error(item, message)
        ihook.pytest_runtest_logfinish(nodeid=item.nodeid, location=item.location)


def _report_item_as_error(item: pytest.Item, message: str) -> None:
    """Emit setup/call/teardown reports for a single item, marking call as failed.

    Args:
        item: The pytest Item to report on.
        message: Error message for the call phase.
    """
    ihook = item.ihook
    for when in ("setup", "call", "teardown"):
        report = TestReport(
            nodeid=item.nodeid,
            location=item.location,
            keywords=dict.fromkeys(item.keywords, 1),
            outcome="failed" if when == "call" else "passed",
            longrepr=message if when == "call" else None,
            when=when,
            duration=0,
        )
        ihook.pytest_runtest_logreport(report=report)


def _report_item_result(item: pytest.Item, result: JunitTestResult) -> None:
    """Emit setup/call/teardown reports for a single item based on remote results.

    Args:
        item: The pytest Item to report on.
        result: Parsed JunitTestResult from the remote junitxml.
    """
    ihook = item.ihook
    keywords = dict.fromkeys(item.keywords, 1)

    if result.outcome == "skipped":
        longrepr = ("", 0, result.skip_reason or "Skipped")
    elif result.outcome == "failed":
        longrepr = result.failure_message
    elif result.outcome == "passed":
        longrepr = None
    else:
        longrepr = f"Unknown outcome: {result.outcome}"

    outcome = "failed" if result.outcome not in ("passed", "skipped") else result.outcome

    for when, phase_outcome, phase_longrepr, duration in (
        ("setup", "passed", None, 0),
        ("call", outcome, longrepr, result.duration),
        ("teardown", "passed", None, 0),
    ):
        report = TestReport(
            nodeid=item.nodeid,
            location=item.location,
            keywords=keywords,
            outcome=phase_outcome,
            longrepr=phase_longrepr,
            when=when,
            duration=duration,
            sections=result.sections if when == "call" else [],
        )
        ihook.pytest_runtest_logreport(report=report)


def _parse_junitxml(path: Path) -> list[JunitTestResult]:
    """Parse a junitxml file into a list of test results.

    Args:
        path: Path to the junitxml file.

    Returns:
        List of JunitTestResult, one per test case.
    """
    xml = JUnitXml.fromfile(str(path))

    results = []
    for suite in xml:
        for case in suite:
            if not isinstance(case, TestCase):
                continue
            nodeid = _reconstruct_nodeid(case)
            duration = case.time or 0.0

            sections: list[tuple[str, str]] = []
            if case.system_out:
                sections.append(("Captured stdout (remote)", case.system_out))
            if case.system_err:
                sections.append(("Captured stderr (remote)", case.system_err))

            failure_entry = None
            skip_entry = None
            for entry in case.result:
                if isinstance(entry, (Failure, Error)):
                    failure_entry = entry
                    break
                if isinstance(entry, Skipped):
                    skip_entry = entry

            if failure_entry is not None:
                results.append(
                    JunitTestResult(
                        nodeid=nodeid,
                        outcome="failed",
                        duration=duration,
                        failure_message=failure_entry.text or failure_entry.message or "",
                        sections=sections,
                    )
                )
            elif skip_entry is not None:
                results.append(
                    JunitTestResult(
                        nodeid=nodeid,
                        outcome="skipped",
                        duration=duration,
                        skip_reason=skip_entry.message or "Skipped",
                        sections=sections,
                    )
                )
            else:
                results.append(
                    JunitTestResult(
                        nodeid=nodeid,
                        outcome="passed",
                        duration=duration,
                        sections=sections,
                    )
                )

    return results


def _reconstruct_nodeid(case: TestCase) -> str:
    """Reconstruct a pytest node ID from a junitparser TestCase.

    Handles the mapping from junitxml's (file, classname, name) triple back to
    pytest's ``file::Class::method`` format.

    Args:
        case: A junitparser TestCase with classname and name attributes.

    Returns:
        A pytest-compatible node ID string (e.g. "tests/test_foo.py::TestBar::test_baz").
    """
    file_attr = case._elem.get("file")
    classname = case.classname or ""
    name = case.name or ""

    if file_attr:
        file_module = file_attr.replace("/", ".").removesuffix(".py")
        remaining = classname.removeprefix(file_module + ".")
        if remaining and remaining != classname:
            return f"{file_attr}::{remaining.replace('.', '::')}::{name}"
        return f"{file_attr}::{name}"

    parts = classname.split(".")
    file_parts = []
    class_parts = []
    for i, part in enumerate(parts):
        if part and part[0].isupper():
            class_parts = parts[i:]
            break
        file_parts.append(part)

    file_path = "/".join(file_parts) + ".py" if file_parts else ""
    node_parts = class_parts + [name]
    node_path = "::".join(node_parts)

    if file_path:
        return f"{file_path}::{node_path}"
    return node_path
