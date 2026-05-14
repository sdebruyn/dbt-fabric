import pytest

from dbt.tests.util import run_dbt

macro_build_openrowset_parquet = """
{% macro test_build_openrowset_parquet() %}
    {% set location = 'https://storage.blob.core.windows.net/container/data.parquet' %}
    {% set result = fabric__build_openrowset(location, 'PARQUET', {}, []) %}
    {{ log("OPENROWSET_RESULT: " ~ result | replace("\\n", " "), info=True) }}
{% endmacro %}
"""

macro_build_openrowset_csv_with_options = """
{% macro test_build_openrowset_csv() %}
    {% set location = 'https://storage.blob.core.windows.net/container/data.csv' %}
    {% set options = {'header_row': 'true', 'fieldterminator': ','} %}
    {% set result = fabric__build_openrowset(location, 'CSV', options, []) %}
    {{ log("OPENROWSET_CSV_RESULT: " ~ result | replace("\\n", " "), info=True) }}
{% endmacro %}
"""

macro_build_openrowset_jsonl = """
{% macro test_build_openrowset_jsonl() %}
    {% set location = 'https://storage.blob.core.windows.net/container/data.jsonl' %}
    {% set result = fabric__build_openrowset(location, 'JSONL', {}, []) %}
    {{ log("OPENROWSET_JSONL_RESULT: " ~ result | replace("\\n", " "), info=True) }}
{% endmacro %}
"""

macro_resolve_file_format_from_extension = """
{% macro test_resolve_format_parquet() %}
    {% set external = {'location': 'https://storage.blob.core.windows.net/c/data.parquet'} %}
    {% set result = fabric__resolve_file_format(external) %}
    {{ log("FORMAT_PARQUET: " ~ result, info=True) }}
{% endmacro %}
"""

macro_resolve_file_format_csv = """
{% macro test_resolve_format_csv() %}
    {% set external = {'location': 'https://storage.blob.core.windows.net/c/data.csv'} %}
    {% set result = fabric__resolve_file_format(external) %}
    {{ log("FORMAT_CSV: " ~ result, info=True) }}
{% endmacro %}
"""

macro_resolve_file_format_jsonl = """
{% macro test_resolve_format_jsonl() %}
    {% set external = {'location': 'https://storage.blob.core.windows.net/c/data.jsonl'} %}
    {% set result = fabric__resolve_file_format(external) %}
    {{ log("FORMAT_JSONL: " ~ result, info=True) }}
{% endmacro %}
"""

macro_resolve_file_format_explicit = """
{% macro test_resolve_format_explicit() %}
    {% set external = {'location': 'https://storage.blob.core.windows.net/c/myfile.dat', 'file_format': 'parquet'} %}
    {% set result = fabric__resolve_file_format(external) %}
    {{ log("FORMAT_EXPLICIT: " ~ result, info=True) }}
{% endmacro %}
"""

macro_build_openrowset_csv_all_options = """
{% macro test_build_openrowset_csv_all_options() %}
    {% set location = 'https://storage.blob.core.windows.net/c/data.csv' %}
    {% set options = {
        'header_row': 'true',
        'fieldterminator': ',',
        'rowterminator': '0x0a',
        'parser_version': '2.0',
        'firstrow': '2',
        'data_source': 'my_source'
    } %}
    {% set result = fabric__build_openrowset(location, 'CSV', options, []) %}
    {{ log("OPENROWSET_CSV_ALL: " ~ result | replace("\\n", " "), info=True) }}
{% endmacro %}
"""

macro_build_openrowset_escaping = """
{% macro test_build_openrowset_escaping() %}
    {% set location = "https://storage.blob.core.windows.net/container/it's data.parquet" %}
    {% set options = {'fieldterminator': "it's a delimiter"} %}
    {% set result = fabric__build_openrowset(location, 'CSV', options, []) %}
    {{ log("OPENROWSET_ESCAPE: " ~ result | replace("\\n", " "), info=True) }}
{% endmacro %}
"""


def _find_log_output(capsys, prefix):
    """Find a log line in captured stdout by prefix and return the rest of the line."""
    captured = capsys.readouterr()
    for line in captured.out.splitlines():
        if prefix in line:
            return line[line.index(prefix) + len(prefix) :].strip()
    return None


class TestBuildOpenrowsetMacros:
    @pytest.fixture(scope="class")
    def models(self):
        return {"placeholder.sql": "select 1 as id"}

    @pytest.fixture(scope="class")
    def macros(self):
        return {
            "test_build_openrowset_parquet.sql": macro_build_openrowset_parquet,
            "test_build_openrowset_csv.sql": macro_build_openrowset_csv_with_options,
            "test_build_openrowset_jsonl.sql": macro_build_openrowset_jsonl,
            "test_build_openrowset_csv_all_options.sql": macro_build_openrowset_csv_all_options,
            "test_build_openrowset_escaping.sql": macro_build_openrowset_escaping,
        }

    def test_build_openrowset_parquet(self, project, capsys):
        run_dbt(["run-operation", "test_build_openrowset_parquet"])
        output = _find_log_output(capsys, "OPENROWSET_RESULT: ")
        assert output is not None, "Expected OPENROWSET_RESULT in log output"
        assert "OPENROWSET(" in output
        assert "BULK 'https://storage.blob.core.windows.net/container/data.parquet'" in output
        assert "FORMAT = 'PARQUET'" in output

    def test_build_openrowset_csv(self, project, capsys):
        run_dbt(["run-operation", "test_build_openrowset_csv"])
        output = _find_log_output(capsys, "OPENROWSET_CSV_RESULT: ")
        assert output is not None, "Expected OPENROWSET_CSV_RESULT in log output"
        assert "OPENROWSET(" in output
        assert "FORMAT = 'CSV'" in output
        assert "HEADER_ROW = true" in output
        assert "FIELDTERMINATOR = ','" in output

    def test_build_openrowset_jsonl(self, project, capsys):
        run_dbt(["run-operation", "test_build_openrowset_jsonl"])
        output = _find_log_output(capsys, "OPENROWSET_JSONL_RESULT: ")
        assert output is not None, "Expected OPENROWSET_JSONL_RESULT in log output"
        assert "OPENROWSET(" in output
        assert "FORMAT = 'JSONL'" in output

    def test_build_openrowset_csv_all_options(self, project, capsys):
        run_dbt(["run-operation", "test_build_openrowset_csv_all_options"])
        output = _find_log_output(capsys, "OPENROWSET_CSV_ALL: ")
        assert output is not None, "Expected OPENROWSET_CSV_ALL in log output"
        assert "OPENROWSET(" in output
        assert "HEADER_ROW = true" in output
        assert "FIELDTERMINATOR = ','" in output
        assert "ROWTERMINATOR = '0x0a'" in output
        assert "PARSER_VERSION = '2.0'" in output
        assert "FIRSTROW = 2" in output
        assert "DATA_SOURCE = 'my_source'" in output

    def test_build_openrowset_escaping(self, project, capsys):
        run_dbt(["run-operation", "test_build_openrowset_escaping"])
        output = _find_log_output(capsys, "OPENROWSET_ESCAPE: ")
        assert output is not None, "Expected OPENROWSET_ESCAPE in log output"
        assert "OPENROWSET(" in output
        assert "it''s data.parquet'" in output
        assert "FIELDTERMINATOR = 'it''s a delimiter'" in output


class TestResolveFileFormatMacro:
    @pytest.fixture(scope="class")
    def models(self):
        return {"placeholder.sql": "select 1 as id"}

    @pytest.fixture(scope="class")
    def macros(self):
        return {
            "test_resolve_format_parquet.sql": macro_resolve_file_format_from_extension,
            "test_resolve_format_csv.sql": macro_resolve_file_format_csv,
            "test_resolve_format_jsonl.sql": macro_resolve_file_format_jsonl,
            "test_resolve_format_explicit.sql": macro_resolve_file_format_explicit,
        }

    def test_resolve_format_parquet(self, project, capsys):
        run_dbt(["run-operation", "test_resolve_format_parquet"])
        output = _find_log_output(capsys, "FORMAT_PARQUET: ")
        assert output is not None, "Expected FORMAT_PARQUET in log output"
        assert output.strip() == "PARQUET"

    def test_resolve_format_csv(self, project, capsys):
        run_dbt(["run-operation", "test_resolve_format_csv"])
        output = _find_log_output(capsys, "FORMAT_CSV: ")
        assert output is not None, "Expected FORMAT_CSV in log output"
        assert output.strip() == "CSV"

    def test_resolve_format_jsonl(self, project, capsys):
        run_dbt(["run-operation", "test_resolve_format_jsonl"])
        output = _find_log_output(capsys, "FORMAT_JSONL: ")
        assert output is not None, "Expected FORMAT_JSONL in log output"
        assert output.strip() == "JSONL"

    def test_resolve_format_explicit(self, project, capsys):
        run_dbt(["run-operation", "test_resolve_format_explicit"])
        output = _find_log_output(capsys, "FORMAT_EXPLICIT: ")
        assert output is not None, "Expected FORMAT_EXPLICIT in log output"
        assert output.strip() == "PARQUET"
