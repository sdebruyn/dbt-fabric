from pathlib import Path

import pytest

from dbt.tests.util import run_dbt
from tests.fabric.packages.base_package_test import BaseDbtPackageTests

_FISCAL_PERIODS_PATH = (
    Path(__file__).resolve().parents[3]
    / "src/dbt/include/fabric/macros/dbt_package_support/dbt_date/fiscal_date"
    / "get_fiscal_periods.sql"
)

_TEST_DATES_SQL = "{{ get_test_dates() }}"

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
            "test_dates.sql": _TEST_DATES_SQL,
            "dim_date.sql": _DIM_DATE_SQL,
            "dim_date_fiscal.sql": _DIM_DATE_FISCAL_SQL,
        }

    @pytest.fixture(scope="class")
    def models_config(self):
        return {
            "dbt_date_integration_tests": {
                "test_dates": {"+enabled": False},
                "dim_date": {"+enabled": False},
                "dim_date_fiscal": {"+enabled": False},
            }
        }

    @pytest.fixture(scope="class")
    def macros(self):
        return {
            "get_fiscal_periods.sql": _FISCAL_PERIODS_PATH.read_text(),
            "fabric_test_helpers.sql": """
{% macro get_test_week_of_year() -%}
    {{ return([49, 49]) }}
{%- endmacro %}

{% macro get_test_timestamps() -%}
    {{ return(['2021-06-07 14:35:20.000000',
                '2021-06-07 14:35:20.000000']) }}
{%- endmacro %}

{% macro get_test_week_start_date() -%}
    {{ return(["2020-11-29", "2020-11-29"]) }}
{%- endmacro %}

{% macro get_test_week_end_date() -%}
    {{ return(["2020-12-05", "2020-12-05"]) }}
{%- endmacro %}

{#- With dbt_date:time_zone=UTC, convert_timezone is a no-op so time_stamp =
    time_stamp_utc. round_timestamp adds 12h then truncates: 14:35+12h = next
    day. Upstream hardcodes '2021-06-07' assuming a non-UTC offset; we fix it. -#}
{% macro get_test_dates() -%}
{{ dbt_date_integration_tests.get_test_dates() | replace("'2021-06-07' as DATETIME2(6)) as rounded_timestamp,", "'2021-06-08' as DATETIME2(6)) as rounded_timestamp,") }}
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
        run_dbt(["test"])
