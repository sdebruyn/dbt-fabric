from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from _pytest.reports import TestReport

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
        List of JunitTestResult, one per <testcase> element.

    Raises:
        ET.ParseError: If the XML is malformed.
    """
    tree = ET.parse(path)
    root = tree.getroot()

    results = []
    for testcase in root.iter("testcase"):
        nodeid = _reconstruct_nodeid(testcase)
        duration = float(testcase.get("time", "0"))

        failure_el = testcase.find("failure")
        error_el = testcase.find("error")
        skipped_el = testcase.find("skipped")

        sections: list[tuple[str, str]] = []
        stdout_el = testcase.find("system-out")
        if stdout_el is not None and stdout_el.text:
            sections.append(("Captured stdout (remote)", stdout_el.text))
        stderr_el = testcase.find("system-err")
        if stderr_el is not None and stderr_el.text:
            sections.append(("Captured stderr (remote)", stderr_el.text))

        if failure_el is not None:
            results.append(
                JunitTestResult(
                    nodeid=nodeid,
                    outcome="failed",
                    duration=duration,
                    failure_message=failure_el.text or failure_el.get("message", ""),
                    sections=sections,
                )
            )
        elif error_el is not None:
            results.append(
                JunitTestResult(
                    nodeid=nodeid,
                    outcome="failed",
                    duration=duration,
                    failure_message=error_el.text or error_el.get("message", ""),
                    sections=sections,
                )
            )
        elif skipped_el is not None:
            results.append(
                JunitTestResult(
                    nodeid=nodeid,
                    outcome="skipped",
                    duration=duration,
                    skip_reason=skipped_el.get("message", "Skipped"),
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


def _reconstruct_nodeid(testcase: ET.Element) -> str:
    """Reconstruct a pytest node ID from junitxml testcase attributes.

    Handles the mapping from junitxml's (file, classname, name) triple back to
    pytest's ``file::Class::method`` format.

    Args:
        testcase: An XML <testcase> element with file, classname, and name attributes.

    Returns:
        A pytest-compatible node ID string (e.g. "tests/test_foo.py::TestBar::test_baz").
    """
    file_attr = testcase.get("file")
    classname = testcase.get("classname", "")
    name = testcase.get("name", "")

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
