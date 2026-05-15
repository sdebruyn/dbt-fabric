import os
import urllib.parse

import pytest
import requests
from azure.identity import AzureCliCredential

from dbt.tests.util import relation_from_name, run_dbt

TEST_CSV_CONTENT = (
    "id,name,amount,sale_date\n"
    "1,Widget A,19.99,2024-01-15\n"
    "2,Widget B,29.99,2024-02-20\n"
    "3,Gadget C,49.50,2024-03-10\n"
    "4,Gadget D,99.00,2024-04-05\n"
    "5,Widget E,14.75,2024-05-12"
)

_onelake_info_cache = None


def _get_onelake_info():
    """Resolve workspace ID and lakehouse ID, then upload a test CSV to OneLake."""
    global _onelake_info_cache
    if _onelake_info_cache is not None:
        return _onelake_info_cache

    workspace_name = os.getenv("FABRIC_TEST_WORKSPACE_NAME")
    lakehouse_name = os.getenv("FABRIC_TEST_LAKEHOUSE_NAME")
    if not workspace_name or not lakehouse_name:
        return None

    try:
        credential = AzureCliCredential()
        pbi_token = credential.get_token("https://analysis.windows.net/powerbi/api/.default").token
        pbi_headers = {
            "Authorization": f"Bearer {pbi_token}",
            "Accept": "application/json",
        }

        query = urllib.parse.quote_plus(f"name eq '{workspace_name}'")
        resp = requests.get(
            f"https://api.powerbi.com/v1.0/myorg/groups?$filter={query}",
            headers=pbi_headers,
        )
        resp.raise_for_status()
        workspaces = resp.json().get("value", [])
        if not workspaces:
            return None
        workspace_id = workspaces[0]["id"]

        resp = requests.get(
            f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/lakehouses",
            headers=pbi_headers,
        )
        resp.raise_for_status()
        lakehouses = resp.json().get("value", [])
        lh = next((l for l in lakehouses if l["displayName"] == lakehouse_name), None)
        if not lh:
            return None
        lakehouse_id = lh["id"]

        _upload_test_csv(credential, workspace_id, lakehouse_id)

        csv_url = (
            f"https://onelake.dfs.fabric.microsoft.com"
            f"/{workspace_id}/{lakehouse_id}/Files/dbt-test/sample.csv"
        )
        _onelake_info_cache = csv_url
        return csv_url
    except Exception:
        return None


def _upload_test_csv(credential, workspace_id, lakehouse_id):
    """Upload a small test CSV to OneLake via the DFS REST API."""
    storage_token = credential.get_token("https://storage.azure.com/.default").token
    headers = {"Authorization": f"Bearer {storage_token}"}
    base = (
        f"https://onelake.dfs.fabric.microsoft.com"
        f"/{workspace_id}/{lakehouse_id}/Files/dbt-test/sample.csv"
    )
    data = TEST_CSV_CONTENT.encode()

    requests.put(f"{base}?resource=file", headers=headers)
    requests.patch(
        f"{base}?action=append&position=0",
        headers={**headers, "Content-Type": "text/csv"},
        data=data,
    )
    requests.patch(f"{base}?action=flush&position={len(data)}", headers=headers)


macro_build_openrowset_parquet = """
{% macro test_build_openrowset_parquet() %}
    {% set location = 'https://storage.blob.core.windows.net/c/data.parquet' %}
    {% set result = fabric__build_openrowset(location, 'PARQUET', {}, []) %}
    {{ log("OPENROWSET_RESULT: " ~ result | replace("\\n", " "), info=True) }}
{% endmacro %}
"""

macro_build_openrowset_csv_with_options = """
{% macro test_build_openrowset_csv() %}
    {% set location = 'https://storage.blob.core.windows.net/c/data.csv' %}
    {% set options = {'header_row': 'true', 'fieldterminator': ','} %}
    {% set result = fabric__build_openrowset(location, 'CSV', options, []) %}
    {{ log("OPENROWSET_CSV_RESULT: " ~ result | replace("\\n", " "), info=True) }}
{% endmacro %}
"""

macro_build_openrowset_jsonl = """
{% macro test_build_openrowset_jsonl() %}
    {% set location = 'https://storage.blob.core.windows.net/c/data.jsonl' %}
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


def _find_in_output(text, prefix):
    for line in text.splitlines():
        if prefix in line:
            return line[line.index(prefix) + len(prefix) :].strip()
    return None


def _find_log_output(capsys, prefix):
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
        assert "BULK 'https://storage.blob.core.windows.net/c/data.parquet'" in output
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


external_table_model_sql = """
{{ config(materialized='table') }}
select
    id,
    name,
    amount,
    sale_date
from {{ source('test_external', 'sample_csv') }}
"""


def _build_sources_yml(csv_url):
    return """
version: 2
sources:
  - name: test_external
    schema: dbo
    tables:
      - name: sample_csv
        external:
          location: "{csv_url}"
          file_format: csv
          options:
            header_row: "true"
            fieldterminator: ","
            parser_version: "2.0"
        columns:
          - name: id
            data_type: int
          - name: name
            data_type: "varchar(100)"
          - name: amount
            data_type: "decimal(10,2)"
          - name: sale_date
            data_type: date
""".format(csv_url=csv_url)


class TestExternalTablesEndToEnd:
    @pytest.fixture(scope="class")
    def packages(self):
        return {"packages": [{"package": "dbt-labs/dbt_external_tables", "version": "0.11.0"}]}

    @pytest.fixture(scope="class")
    def models(self):
        csv_url = _get_onelake_info()
        if not csv_url:
            pytest.skip("No lakehouse available for OPENROWSET end-to-end test")
        return {
            "sources.yml": _build_sources_yml(csv_url),
            "external_data.sql": external_table_model_sql,
        }

    @pytest.fixture(scope="class")
    def project_config_update(self):
        return {
            "dispatch": [
                {
                    "macro_namespace": "dbt_external_tables",
                    "search_order": ["dbt", "dbt_external_tables"],
                }
            ],
        }

    def test_stage_and_materialize(self, project):
        run_dbt(["deps"])
        run_dbt(["run-operation", "stage_external_sources"])

        results = run_dbt(["run"])
        assert len(results) == 1
        assert results[0].status == "success"

        relation = relation_from_name(project.adapter, "external_data")
        result = project.run_sql(f"select count(*) from {relation}", fetch="one")
        row_count = result[0]
        assert row_count == 5, f"Expected 5 rows, got {row_count}"
