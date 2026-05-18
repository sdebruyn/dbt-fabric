import pytest

from tests.packages.base_package_test import BaseDbtPackageTests

_TEST_DATES_SQL = "{{ get_test_dates() }}"


class TestDbtDate(BaseDbtPackageTests):
    @pytest.fixture(scope="class")
    def package_name(self) -> str:
        return "dbt_date"

    @pytest.fixture(scope="class")
    def package_repo(self, dbt_date_repo) -> str:
        return dbt_date_repo

    @pytest.fixture(scope="class")
    def package_revision(self, dbt_date_revision) -> str:
        return dbt_date_revision

    @pytest.fixture(scope="class")
    def models(self):
        return {
            "test_dates.sql": _TEST_DATES_SQL,
        }

    @pytest.fixture(scope="class")
    def models_config(self):
        return {
            "dbt_date_integration_tests": {
                "test_dates": {"+enabled": False},
            }
        }

    @pytest.fixture(scope="class")
    def macros(self):
        return {
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
{{ dbt_date_integration_tests.get_test_dates() | replace("'2021-06-07' as datetime2(6)) as rounded_timestamp,", "'2021-06-08' as datetime2(6)) as rounded_timestamp,") }}
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
