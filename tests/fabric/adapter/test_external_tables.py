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


external_sources_yml = """
version: 2
sources:
  - name: pandemic_data
    schema: dbo
    tables:
      - name: covid_parquet
        external:
          location: "{parquet_url}"
          file_format: parquet
        columns:
          - name: id
            data_type: int
          - name: updated
            data_type: date
          - name: confirmed
            data_type: int
          - name: deaths
            data_type: int
          - name: country_region
            data_type: "varchar(8000)"
          - name: iso2
            data_type: "varchar(8000)"
          - name: iso3
            data_type: "varchar(8000)"
      - name: covid_csv
        external:
          location: "{csv_url}"
          file_format: csv
          options:
            header_row: "true"
        columns:
          - name: id
            data_type: int
          - name: updated
            data_type: date
          - name: confirmed
            data_type: int
          - name: deaths
            data_type: int
          - name: country_region
            data_type: "varchar(8000)"
""".format(
    parquet_url=PANDEMIC_PARQUET_URL,
    csv_url=PANDEMIC_CSV_URL,
)

external_table_model_sql = """
{{ config(materialized='table') }}
select top 100
    id,
    updated,
    confirmed,
    deaths,
    country_region
from {{ source('pandemic_data', 'covid_parquet') }}
where country_region = 'Belgium'
"""


class TestExternalTablesEndToEnd:
    """Integration test: full dbt-external-tables flow with source YAML, stage, and table model."""

    @pytest.fixture(scope="class")
    def packages(self):
        return {"packages": [{"package": "dbt-labs/dbt_external_tables", "version": "0.11.0"}]}

    @pytest.fixture(scope="class")
    def models(self):
        return {
            "sources.yml": external_sources_yml,
            "covid_belgium.sql": external_table_model_sql,
        }

    @pytest.fixture(scope="class")
    def project_config_update(self):
        return {
            "dispatch": [
                {
                    "macro_namespace": "dbt_external_tables",
                    "search_order": ["test", "dbt_fabric", "dbt_external_tables"],
                }
            ],
        }

    def test_stage_and_materialize(self, project):
        run_dbt(["deps"])
        run_dbt(["run-operation", "stage_external_sources"])

        results = run_dbt(["run"])
        assert len(results) == 1
        assert results[0].status == "success"

        relation = relation_from_name(project.adapter, "covid_belgium")
        result = project.run_sql(f"select count(*) from {relation}", fetch="one")
        row_count = result[0]
        assert row_count > 0, f"Expected rows in table, got {row_count}"
