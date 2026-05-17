from pathlib import Path

import pytest

from dbt.tests.util import run_dbt
from tests.packages.base_package_test import BaseDbtPackageTests

# T-SQL fix for dbt_expectations.expect_column_to_exist which renders Jinja True/False
# directly in SQL (invalid in T-SQL). We patch the installed package file after dbt deps.
# Upstream: https://github.com/metaplane/dbt-expectations/issues/43
_EXPECT_COLUMN_TO_EXIST_SQL = """\
{%- test expect_column_to_exist(model, column_name, column_index=None, transform="upper") -%}
{%- if execute -%}
    {%- set column_name = column_name | map(transform) | join -%}
    {%- set relation_column_names = dbt_expectations._get_column_list(model, transform) -%}
    {%- set matching_column_index = relation_column_names.index(column_name)
        if column_name in relation_column_names else -1 %}
    {%- if column_index -%}
        {%- set column_index_0 = column_index - 1 if column_index > 0 else 0 -%}
        {%- set column_index_matches = 1 if matching_column_index == column_index_0 else 0 %}
    {%- else -%}
        {%- set column_index_matches = 1 -%}
    {%- endif %}
    with test_data as (
        select
            cast('{{ column_name }}' as {{ dbt.type_string() }}) as column_name,
            {{ matching_column_index }} as matching_column_index,
            {{ column_index_matches }} as column_index_matches
    )
    select *
    from test_data
    where
        not(matching_column_index >= 0 and column_index_matches = 1)
{%- endif -%}
{%- endtest -%}
"""


class TestDbtProfiler(BaseDbtPackageTests):
    @pytest.fixture(scope="class")
    def package_name(self) -> str:
        return "dbt_profiler"

    @pytest.fixture(scope="class")
    def package_repo(self) -> str:
        return "https://github.com/data-mie/dbt-profiler"

    @pytest.fixture(scope="class")
    def package_revision(self) -> str:
        return "1.0.0"

    @pytest.fixture(scope="class")
    def extra_dispatches(self):
        return [
            {
                "macro_namespace": "dbt_expectations",
                "search_order": [
                    "test_dbt_package",
                    "dbt",
                    "dbt_expectations",
                ],
            }
        ]

    @pytest.fixture(scope="class")
    def models_config(self):
        return {
            "dbt_profiler_integration_tests": {
                # STRUCT type does not exist in T-SQL (BigQuery-only)
                "profile_struct": {"+enabled": False},
            }
        }

    @pytest.fixture(scope="class")
    def seeds_config(self):
        return {
            "dbt_profiler_integration_tests": {"+column_types": {"date_nullable": "datetime2(6)"}}
        }

    def test_package(self, project, dbt_core_bug_workaround):
        run_dbt(["deps"])

        # Patch expect_column_to_exist in the installed package (uses True/False literals)
        expect_col_path = (
            Path(project.project_root)
            / "dbt_packages"
            / "dbt_expectations"
            / "macros"
            / "schema_tests"
            / "table_shape"
            / "expect_column_to_exist.sql"
        )
        expect_col_path.write_text(_EXPECT_COLUMN_TO_EXIST_SQL)

        run_dbt(["build"])

        # Run the incremental model a second time to test the merge/insert path
        run_dbt(["run", "--select", "profile_over_time"])
