from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from _pytest.reports import TestReport

from tests.spark_remote.spark_job_client import SparkJobResult


@dataclass
class JunitTestResult:
    nodeid: str
    outcome: str
    duration: float
    failure_message: str | None = None
    skip_reason: str | None = None
    sections: list[tuple[str, str]] = field(default_factory=list)


def report_remote_results(
    session: pytest.Session, results_path: Path | None, job_result: SparkJobResult
) -> None:
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
            _report_item_as_error(item, "Test not found in remote execution results")
        else:
            _report_item_result(item, result)

        ihook.pytest_runtest_logfinish(nodeid=item.nodeid, location=item.location)


def _report_all_as_error(session: pytest.Session, message: str) -> None:
    for item in session.items:
        ihook = item.ihook
        ihook.pytest_runtest_logstart(nodeid=item.nodeid, location=item.location)
        _report_item_as_error(item, message)
        ihook.pytest_runtest_logfinish(nodeid=item.nodeid, location=item.location)


def _report_item_as_error(item: pytest.Item, message: str) -> None:
    ihook = item.ihook
    for when in ("setup", "call", "teardown"):
        report = TestReport(
            nodeid=item.nodeid,
            location=item.location,
            keywords={x: 1 for x in item.keywords},
            outcome="failed" if when == "call" else "passed",
            longrepr=message if when == "call" else None,
            when=when,
            duration=0,
        )
        ihook.pytest_runtest_logreport(report=report)


def _report_item_result(item: pytest.Item, result: JunitTestResult) -> None:
    ihook = item.ihook

    setup_report = TestReport(
        nodeid=item.nodeid,
        location=item.location,
        keywords={x: 1 for x in item.keywords},
        outcome="passed",
        longrepr=None,
        when="setup",
        duration=0,
    )
    ihook.pytest_runtest_logreport(report=setup_report)

    if result.outcome == "passed":
        call_report = TestReport(
            nodeid=item.nodeid,
            location=item.location,
            keywords={x: 1 for x in item.keywords},
            outcome="passed",
            longrepr=None,
            when="call",
            duration=result.duration,
            sections=result.sections,
        )
    elif result.outcome == "failed":
        call_report = TestReport(
            nodeid=item.nodeid,
            location=item.location,
            keywords={x: 1 for x in item.keywords},
            outcome="failed",
            longrepr=result.failure_message,
            when="call",
            duration=result.duration,
            sections=result.sections,
        )
    elif result.outcome == "skipped":
        call_report = TestReport(
            nodeid=item.nodeid,
            location=item.location,
            keywords={x: 1 for x in item.keywords},
            outcome="skipped",
            longrepr=("", 0, result.skip_reason or "Skipped"),
            when="call",
            duration=result.duration,
            sections=result.sections,
        )
    else:
        call_report = TestReport(
            nodeid=item.nodeid,
            location=item.location,
            keywords={x: 1 for x in item.keywords},
            outcome="failed",
            longrepr=f"Unknown outcome: {result.outcome}",
            when="call",
            duration=result.duration,
            sections=result.sections,
        )
    ihook.pytest_runtest_logreport(report=call_report)

    teardown_report = TestReport(
        nodeid=item.nodeid,
        location=item.location,
        keywords={x: 1 for x in item.keywords},
        outcome="passed",
        longrepr=None,
        when="teardown",
        duration=0,
    )
    ihook.pytest_runtest_logreport(report=teardown_report)


def _parse_junitxml(path: Path) -> list[JunitTestResult]:
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
    file_attr = testcase.get("file")
    classname = testcase.get("classname", "")
    name = testcase.get("name", "")

    if file_attr:
        file_module = file_attr.replace("/", ".").removesuffix(".py")
        remaining = classname.removeprefix(file_module + ".")
        if remaining and remaining != classname:
            return f"{file_attr}::{remaining.replace('.', '::')}::{name}"
        return f"{file_attr}::{name}"

    # Fallback: split classname on first uppercase component (class name boundary)
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
