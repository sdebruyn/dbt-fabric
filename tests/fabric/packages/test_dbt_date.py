import pytest

from dbt.tests.util import run_dbt
from tests.fabric.packages.base_package_test import BaseDbtPackageTests


class TestDbtDate(BaseDbtPackageTests):
    @pytest.fixture(scope="class")
    def package_name(self) -> str:
        return "dbt_date"

    @pytest.fixture(scope="class")
    def package_repo(self) -> str:
        return "https://github.com/godatadriven/dbt-date"

    @pytest.fixture(scope="class")
    def package_revision(self) -> str:
        return "0.17.2"

    @pytest.fixture(scope="class")
    def macros(self):
        return {
            "fabric_test_helpers.sql": """
{% macro fabric__get_test_week_of_year() -%}
    {{ return([49, 49]) }}
{%- endmacro %}

{% macro fabric__get_test_timestamps() -%}
    {{ return(['2021-06-07 14:35:20.000000',
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
        results = run_dbt(["test"], expect_pass=False)
        failures = [r for r in results if r.status == "fail"]
        for f in failures:
            assert "rounded_timestamp" in f.node.name, f"Unexpected test failure: {f.node.name}"
