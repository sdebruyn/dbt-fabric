import pytest

from dbt.tests.util import run_dbt
from tests.fabric.packages.base_package_test import BaseDbtPackageTests


class TestDbtDate(BaseDbtPackageTests):
    @pytest.fixture(scope="class")
    def package_name(self) -> str:
        return "dbt_date"

    @pytest.fixture(scope="class")
    def package_repo(self) -> str:
        return "https://github.com/calogica/dbt-date"

    @pytest.fixture(scope="class")
    def package_revision(self) -> str:
        return "0.10.1"

    @pytest.fixture(scope="class")
    def macros(self):
        return {
            "fabric_test_helpers.sql": """
{% macro fabric__get_test_week_of_year() -%}
    {# T-SQL datepart(week) counts from Jan 1, not ISO weeks #}
    {{ return([49, 49]) }}
{%- endmacro %}

{% macro fabric__get_test_timestamps() -%}
    {# T-SQL CAST does not support timezone suffixes in datetime literals #}
    {{ return(['2021-06-07 07:35:20.000000',
                '2021-06-07 14:35:20.000000']) }}
{%- endmacro %}
"""
        }

    @pytest.fixture(scope="class")
    def models_config(self):
        return {
            "dbt_date_integration_tests": {
                "dim_date": {"+enabled": False},
                "dim_date_fiscal": {"+enabled": False},
            }
        }

    @pytest.fixture(scope="class")
    def project_vars(self):
        return {"dbt_date:time_zone": "UTC"}

    @pytest.fixture(scope="class")
    def extra_dispatches(self):
        return [
            {
                "macro_namespace": "dbt_date_integration_tests",
                "search_order": [
                    "test_dbt_package",
                    "dbt",
                    "dbt_date_integration_tests",
                ],
            }
        ]

    def test_package(self, project, dbt_core_bug_workaround):
        run_dbt(["deps"])
        run_dbt(["seed"])
        run_dbt(["run"])
        run_dbt(["test"])
