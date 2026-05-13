import pytest

from dbt.tests.util import run_dbt

macro_build_openrowset_parquet = """
{% macro test_build_openrowset_parquet() %}
    {% set location = 'https://storage.blob.core.windows.net/container/data.parquet' %}
    {% set result = fabric__build_openrowset(location, 'PARQUET', {}, []) %}
    {{ log("OPENROWSET_RESULT: " ~ result, info=True) }}
{% endmacro %}
"""

macro_build_openrowset_csv_with_options = """
{% macro test_build_openrowset_csv() %}
    {% set location = 'https://storage.blob.core.windows.net/container/data.csv' %}
    {% set options = {'header_row': 'true', 'fieldterminator': ','} %}
    {% set result = fabric__build_openrowset(location, 'CSV', options, []) %}
    {{ log("OPENROWSET_CSV_RESULT: " ~ result, info=True) }}
{% endmacro %}
"""

macro_build_openrowset_jsonl = """
{% macro test_build_openrowset_jsonl() %}
    {% set location = 'https://storage.blob.core.windows.net/container/data.jsonl' %}
    {% set result = fabric__build_openrowset(location, 'JSONL', {}, []) %}
    {{ log("OPENROWSET_JSONL_RESULT: " ~ result, info=True) }}
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
        'firstrow': '2'
    } %}
    {% set result = fabric__build_openrowset(location, 'CSV', options, []) %}
    {{ log("OPENROWSET_CSV_ALL: " ~ result, info=True) }}
{% endmacro %}
"""


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
        }

    def test_build_openrowset_parquet(self, project):
        run_dbt(["run-operation", "test_build_openrowset_parquet"])

    def test_build_openrowset_csv(self, project):
        run_dbt(["run-operation", "test_build_openrowset_csv"])

    def test_build_openrowset_jsonl(self, project):
        run_dbt(["run-operation", "test_build_openrowset_jsonl"])

    def test_build_openrowset_csv_all_options(self, project):
        run_dbt(["run-operation", "test_build_openrowset_csv_all_options"])


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

    def test_resolve_format_parquet(self, project):
        run_dbt(["run-operation", "test_resolve_format_parquet"])

    def test_resolve_format_csv(self, project):
        run_dbt(["run-operation", "test_resolve_format_csv"])

    def test_resolve_format_jsonl(self, project):
        run_dbt(["run-operation", "test_resolve_format_jsonl"])

    def test_resolve_format_explicit(self, project):
        run_dbt(["run-operation", "test_resolve_format_explicit"])
