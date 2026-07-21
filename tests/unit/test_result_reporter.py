from __future__ import annotations

import textwrap
from pathlib import Path

from junitparser import TestCase

from tests.spark_remote.result_reporter import _parse_junitxml, _reconstruct_nodeid


def _make_testcase(**attrs) -> TestCase:
    case = TestCase()
    case.name = attrs.get("name", "")
    case.classname = attrs.get("classname", "")
    if "file" in attrs:
        case._elem.set("file", attrs["file"])
    return case


class TestReconstructNodeid:
    def test_simple_file_and_name(self):
        case = _make_testcase(
            file="tests/unit/test_foo.py",
            classname="tests.unit.test_foo.TestFoo",
            name="test_bar",
        )
        assert _reconstruct_nodeid(case) == "tests/unit/test_foo.py::TestFoo::test_bar"

    def test_no_class_in_classname(self):
        case = _make_testcase(
            file="tests/unit/test_foo.py",
            classname="tests.unit.test_foo",
            name="test_standalone",
        )
        assert _reconstruct_nodeid(case) == "tests/unit/test_foo.py::test_standalone"

    def test_parametrized_name(self):
        case = _make_testcase(
            file="tests/unit/test_foo.py",
            classname="tests.unit.test_foo.TestParams",
            name="test_add[1-2-3]",
        )
        assert _reconstruct_nodeid(case) == "tests/unit/test_foo.py::TestParams::test_add[1-2-3]"

    def test_nested_class(self):
        case = _make_testcase(
            file="tests/unit/test_foo.py",
            classname="tests.unit.test_foo.TestOuter.TestInner",
            name="test_deep",
        )
        assert (
            _reconstruct_nodeid(case) == "tests/unit/test_foo.py::TestOuter::TestInner::test_deep"
        )

    def test_fallback_no_file_attr(self):
        case = _make_testcase(
            classname="tests.unit.test_foo.TestClass",
            name="test_method",
        )
        assert _reconstruct_nodeid(case) == "tests/unit/test_foo.py::TestClass::test_method"


class TestParseJunitxml:
    def test_passed(self, tmp_path: Path):
        xml_content = textwrap.dedent("""\
            <?xml version="1.0" encoding="utf-8"?>
            <testsuite>
              <testcase file="tests/test_a.py" classname="tests.test_a.TestA"
                        name="test_one" time="0.5"/>
            </testsuite>
        """)
        xml_file = tmp_path / "results.xml"
        xml_file.write_text(xml_content)

        results = _parse_junitxml(xml_file)
        assert len(results) == 1
        assert results[0].nodeid == "tests/test_a.py::TestA::test_one"
        assert results[0].outcome == "passed"
        assert results[0].duration == 0.5

    def test_failed(self, tmp_path: Path):
        xml_content = textwrap.dedent("""\
            <?xml version="1.0" encoding="utf-8"?>
            <testsuite>
              <testcase file="tests/test_a.py" classname="tests.test_a.TestA"
                        name="test_fail" time="1.2">
                <failure message="assert False">Traceback here</failure>
              </testcase>
            </testsuite>
        """)
        xml_file = tmp_path / "results.xml"
        xml_file.write_text(xml_content)

        results = _parse_junitxml(xml_file)
        assert len(results) == 1
        assert results[0].outcome == "failed"
        assert results[0].failure_message == "Traceback here"

    def test_skipped(self, tmp_path: Path):
        xml_content = textwrap.dedent("""\
            <?xml version="1.0" encoding="utf-8"?>
            <testsuite>
              <testcase file="tests/test_a.py" classname="tests.test_a.TestA"
                        name="test_skip" time="0.0">
                <skipped message="not supported"/>
              </testcase>
            </testsuite>
        """)
        xml_file = tmp_path / "results.xml"
        xml_file.write_text(xml_content)

        results = _parse_junitxml(xml_file)
        assert len(results) == 1
        assert results[0].outcome == "skipped"
        assert results[0].skip_reason == "not supported"

    def test_error(self, tmp_path: Path):
        xml_content = textwrap.dedent("""\
            <?xml version="1.0" encoding="utf-8"?>
            <testsuite>
              <testcase file="tests/test_a.py" classname="tests.test_a.TestA"
                        name="test_err" time="0.1">
                <error message="setup failed">Error details</error>
              </testcase>
            </testsuite>
        """)
        xml_file = tmp_path / "results.xml"
        xml_file.write_text(xml_content)

        results = _parse_junitxml(xml_file)
        assert len(results) == 1
        assert results[0].outcome == "failed"
        assert results[0].failure_message == "Error details"

    def test_captures_stdout_stderr(self, tmp_path: Path):
        xml_content = textwrap.dedent("""\
            <?xml version="1.0" encoding="utf-8"?>
            <testsuite>
              <testcase file="tests/test_a.py" classname="tests.test_a.TestA"
                        name="test_output" time="0.3">
                <system-out>hello stdout</system-out>
                <system-err>hello stderr</system-err>
              </testcase>
            </testsuite>
        """)
        xml_file = tmp_path / "results.xml"
        xml_file.write_text(xml_content)

        results = _parse_junitxml(xml_file)
        assert len(results) == 1
        assert ("Captured stdout (remote)", "hello stdout") in results[0].sections
        assert ("Captured stderr (remote)", "hello stderr") in results[0].sections

    def test_multiple_testcases(self, tmp_path: Path):
        xml_content = textwrap.dedent("""\
            <?xml version="1.0" encoding="utf-8"?>
            <testsuite>
              <testcase file="tests/test_a.py" classname="tests.test_a" name="test_one" time="0.1"/>
              <testcase file="tests/test_a.py" classname="tests.test_a" name="test_two" time="0.2"/>
            </testsuite>
        """)
        xml_file = tmp_path / "results.xml"
        xml_file.write_text(xml_content)

        results = _parse_junitxml(xml_file)
        assert len(results) == 2
        assert results[0].nodeid == "tests/test_a.py::test_one"
        assert results[1].nodeid == "tests/test_a.py::test_two"
