import pytest

from dbt.tests.util import relation_from_name, run_dbt

PANDEMIC_PARQUET_URL = "https://pandemicdatalake.blob.core.windows.net/public/curated/covid-19/bing_covid-19_data/latest/bing_covid-19_data.parquet"
PANDEMIC_CSV_URL = "https://pandemicdatalake.blob.core.windows.net/public/curated/covid-19/bing_covid-19_data/latest/bing_covid-19_data.csv"
PANDEMIC_JSONL_URL = "https://pandemicdatalake.blob.core.windows.net/public/curated/covid-19/bing_covid-19_data/latest/bing_covid-19_data.jsonl"

macro_build_openrowset_parquet = (
    """
{% macro test_build_openrowset_parquet() %}
    {% set location = '"""
    + PANDEMIC_PARQUET_URL
    + """' %}
    {% set result = fabric__build_openrowset(location, 'PARQUET', {}, []) %}
    {{ log("OPENROWSET_RESULT: " ~ result | replace("\\n", " "), info=True) }}
{% endmacro %}
"""
)

macro_build_openrowset_csv_with_options = (
    """
{% macro test_build_openrowset_csv() %}
    {% set location = '"""
    + PANDEMIC_CSV_URL
    + """' %}
    {% set options = {'header_row': 'true', 'fieldterminator': ','} %}
    {% set result = fabric__build_openrowset(location, 'CSV', options, []) %}
    {{ log("OPENROWSET_CSV_RESULT: " ~ result | replace("\\n", " "), info=True) }}
{% endmacro %}
"""
)

macro_build_openrowset_jsonl = (
    """
{% macro test_build_openrowset_jsonl() %}
    {% set location = '"""
    + PANDEMIC_JSONL_URL
    + """' %}
    {% set result = fabric__build_openrowset(location, 'JSONL', {}, []) %}
    {{ log("OPENROWSET_JSONL_RESULT: " ~ result | replace("\\n", " "), info=True) }}
{% endmacro %}
"""
)

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


def _find_in_output(text, prefix):
    """Find a log line in captured text by prefix and return the rest of the line."""
    for line in text.splitlines():
        if prefix in line:
            return line[line.index(prefix) + len(prefix) :].strip()
    return None


def _find_log_output(capsys, prefix):
    """Find a log line in captured stdout by prefix and return the rest of the line."""
    captured = capsys.readouterr()
    return _find_in_output(captured.out, prefix)


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
        assert f"BULK '{PANDEMIC_PARQUET_URL}'" in output
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


openrowset_inline_model = (
    """
{{ config(materialized='table') }}
select top 10
    id,
    updated,
    confirmed,
    deaths,
    country_region
from openrowset(
    bulk '"""
    + PANDEMIC_PARQUET_URL
    + """',
    format = 'parquet'
) as covid_data
where country_region = 'Belgium'
"""
)


class TestOpenrowsetInlineModel:
    """Integration test: materializes data from an inline OPENROWSET query."""

    @pytest.fixture(scope="class")
    def models(self):
        return {"covid_belgium.sql": openrowset_inline_model}

    @pytest.fixture(scope="class")
    def project_config_update(self):
        return {
            "name": "test_openrowset_inline",
            "models": {"+materialized": "table"},
        }

    def test_openrowset_inline_creates_table_with_rows(self, project):
        results = run_dbt(["run"])
        assert len(results) == 1
        assert results[0].status == "success"

        relation = relation_from_name(project.adapter, "covid_belgium")
        result = project.run_sql(f"select count(*) from {relation}", fetch="one")
        row_count = result[0]
        assert row_count > 0, f"Expected rows in table, got {row_count}"


macro_execute_openrowset = (
    """
{% macro test_execute_openrowset() %}
    {% set openrowset_sql = fabric__build_openrowset(
        '"""
    + PANDEMIC_PARQUET_URL
    + """',
        'PARQUET',
        {},
        []
    ) %}
    {% set query = "select top 5 id, country_region from " ~ openrowset_sql %}
    {% set results = run_query(query) %}
    {{ log("EXEC_ROWCOUNT: " ~ results | length, info=True) }}
    {% if results | length > 0 %}
        {{ log("EXEC_FIRST_ROW: " ~ results.columns['country_region'].values()[0], info=True) }}
    {% endif %}
{% endmacro %}
"""
)


class TestOpenrowsetMacroExecution:
    """Integration test: executes the build_openrowset macro output as a real query."""

    @pytest.fixture(scope="class")
    def models(self):
        return {"placeholder.sql": "select 1 as id"}

    @pytest.fixture(scope="class")
    def macros(self):
        return {"test_execute_openrowset.sql": macro_execute_openrowset}

    def test_build_openrowset_produces_executable_sql(self, project, capsys):
        run_dbt(["run-operation", "test_execute_openrowset"])
        captured = capsys.readouterr().out

        output = _find_in_output(captured, "EXEC_ROWCOUNT: ")
        assert output is not None, "Expected EXEC_ROWCOUNT in log output"
        row_count = int(output.strip())
        assert row_count == 5, f"Expected 5 rows, got {row_count}"

        country = _find_in_output(captured, "EXEC_FIRST_ROW: ")
        assert country is not None, "Expected EXEC_FIRST_ROW in log output"
        assert len(country.strip()) > 0, "Expected a non-empty country_region value"
