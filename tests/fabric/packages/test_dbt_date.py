from pathlib import Path

import pytest

from dbt.tests.util import run_dbt
from tests.fabric.packages.base_package_test import BaseDbtPackageTests

_FISCAL_PERIODS_MACRO = (
    Path(__file__).resolve().parents[3]
    / "src/dbt/include/fabric/macros/dbt_package_support/dbt_date/fiscal_date"
    / "get_fiscal_periods.sql"
).read_text()

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
            "get_fiscal_periods.sql": _FISCAL_PERIODS_MACRO,
            "fabric_test_helpers.sql": """
{% macro fabric__get_test_week_of_year() -%}
    {{ return([49, 49]) }}
{%- endmacro %}

{% macro fabric__get_test_timestamps() -%}
    {{ return(['2021-06-07 14:35:20.000000',
                '2021-06-07 14:35:20.000000']) }}
{%- endmacro %}

{% macro get_test_dates() -%}
{#- Override of dbt_date_integration_tests.get_test_dates:
    - rounded_timestamp changed from '2021-06-07' to '2021-06-08' because with
      dbt_date:time_zone=UTC, time_stamp=time_stamp_utc (convert_timezone is a
      no-op) and both round to the same day (14:35 + 12h = next day).
    - All helper macro calls inlined to avoid cross-package resolution issues.
-#}
    select
        cast('2020-11-29' as date) as date_day,
        cast('2020-11-28' as date) as prior_date_day,
        cast('2020-11-30' as date) as next_date_day,
        'Sunday' as day_name,
        'Sun' as day_name_short,
        'zondag' as day_name_long_dutch,
        'So' as day_name_short_german,
        29 as day_of_month,
        1 as day_of_week,
        7 as iso_day_of_week,
        334 as day_of_year,
        cast('2020-11-29' as date) as week_start_date,
        cast('2020-12-05' as date) as week_end_date,
        49 as week_of_year,
        cast('2020-11-23' as date) as iso_week_start_date,
        cast('2020-11-29' as date) as iso_week_end_date,
        48 as iso_week_of_year,
        '2020-W48' as iso_year_week,
        11 as month_number,
        'November' as month_name,
        'Nov' as month_name_short,
        'november' as month_name_dutch,
        'Nov' as month_name_short_german,
        1623076520 as unix_epoch,
        cast('2021-06-07 14:35:20.000000' as {{ dbt.type_timestamp() }}) as time_stamp,
        cast('2021-06-07 14:35:20.000000' as {{ dbt.type_timestamp() }}) as time_stamp_utc,
        cast('2021-06-08' as {{ dbt.type_timestamp() }}) as rounded_timestamp,
        cast('2021-06-08' as {{ dbt.type_timestamp() }}) as rounded_timestamp_utc,
        {{ dbt_date.last_month_number() }} as last_month_number,
        {{ dbt_date.last_month_name(short=False) }} as last_month_name,
        {{ dbt_date.last_month_name(short=True) }} as last_month_name_short,
        {{ dbt_date.next_month_number() }} as next_month_number,
        {{ dbt_date.next_month_name(short=False) }} as next_month_name,
        {{ dbt_date.next_month_name(short=True) }} as next_month_name_short,
        cast('{{ modules.datetime.date(1997, 9, 29) }}' as date) as datetime_date,
        cast(
            '{{ modules.datetime.datetime(1997, 9, 29, 6, 14, 0, tzinfo=modules.pytz.timezone(var("dbt_date:time_zone"))) }}'
            as {{ dbt.type_timestamp() }}
        ) as datetime_datetime

    union all

    select
        cast('2020-12-01' as date) as date_day,
        cast('2020-11-30' as date) as prior_date_day,
        cast('2020-12-02' as date) as next_date_day,
        'Tuesday' as day_name,
        'Tue' as day_name_short,
        'dinsdag' as day_name_long_dutch,
        'Di' as day_name_short_german,
        1 as day_of_month,
        3 as day_of_week,
        2 as iso_day_of_week,
        336 as day_of_year,
        cast('2020-11-29' as date) as week_start_date,
        cast('2020-12-05' as date) as week_end_date,
        49 as week_of_year,
        cast('2020-11-30' as date) as iso_week_start_date,
        cast('2020-12-06' as date) as iso_week_end_date,
        49 as iso_week_of_year,
        '2020-W49' as iso_year_week,
        12 as month_number,
        'December' as month_name,
        'Dec' as month_name_short,
        'december' as month_name_dutch,
        'Dez' as month_name_short_german,
        1623076520 as unix_epoch,
        cast('2021-06-07 14:35:20.000000' as {{ dbt.type_timestamp() }}) as time_stamp,
        cast('2021-06-07 14:35:20.000000' as {{ dbt.type_timestamp() }}) as time_stamp_utc,
        cast('2021-06-08' as {{ dbt.type_timestamp() }}) as rounded_timestamp,
        cast('2021-06-08' as {{ dbt.type_timestamp() }}) as rounded_timestamp_utc,
        {{ dbt_date.last_month_number() }} as last_month_number,
        {{ dbt_date.last_month_name(short=False) }} as last_month_name,
        {{ dbt_date.last_month_name(short=True) }} as last_month_name_short,
        {{ dbt_date.next_month_number() }} as next_month_number,
        {{ dbt_date.next_month_name(short=False) }} as next_month_name,
        {{ dbt_date.next_month_name(short=True) }} as next_month_name_short,
        cast('{{ modules.datetime.date(1997, 9, 29) }}' as date) as datetime_date,
        cast(
            '{{ modules.datetime.datetime(1997, 9, 29, 6, 14, 0, tzinfo=modules.pytz.timezone(var("dbt_date:time_zone"))) }}'
            as {{ dbt.type_timestamp() }}
        ) as datetime_datetime
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
