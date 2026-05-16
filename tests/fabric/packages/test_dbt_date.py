from pathlib import Path

import pytest

from dbt.tests.util import run_dbt
from tests.fabric.packages.base_package_test import BaseDbtPackageTests

_FISCAL_PERIODS_MACRO = (
    Path(__file__).resolve().parents[3]
    / "src/dbt/include/fabric/macros/dbt_package_support/dbt_date/fiscal_date"
    / "get_fiscal_periods.sql"
).read_text()

_DIM_DATE_FISCAL_SQL = "{{ get_fiscal_periods(ref('dates'), year_end_month=1, week_start_day=1) }}"

_DIM_DATE_SQL = """
select
    d.*,
    f.fiscal_week_of_year,
    f.fiscal_week_of_period,
    f.fiscal_period_number,
    f.fiscal_quarter_number,
    f.fiscal_period_of_quarter
from {{ ref("dates") }} d
left join {{ ref("dim_date_fiscal") }} f on d.date_day = f.date_day
""".strip()


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
    def models(self):
        return {
            "dim_date.sql": _DIM_DATE_SQL,
            "dim_date_fiscal.sql": _DIM_DATE_FISCAL_SQL,
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
    def macros(self):
        return {
            "get_fiscal_periods.sql": _FISCAL_PERIODS_MACRO,
            "fabric_test_helpers.sql": """
{% macro fabric__get_test_week_of_year() -%}
    {{ return([49, 49]) }}
{%- endmacro %}

{% macro fabric__get_test_timestamps() -%}
    {{ return(['2021-06-07 14:35:20.000000',
                '2021-06-07 14:35:20.000000']) }}
{%- endmacro %}
""",
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
