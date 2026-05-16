import pytest

from dbt.tests.util import run_dbt
from tests.fabric.packages.base_package_test import BaseDbtPackageTests


class TestDbtCodegen(BaseDbtPackageTests):
    @pytest.fixture(scope="class")
    def package_name(self) -> str:
        return "dbt_codegen"

    @pytest.fixture(scope="class")
    def package_repo(self) -> str:
        return "https://github.com/dbt-labs/dbt-codegen"

    @pytest.fixture(scope="class")
    def package_revision(self) -> str:
        return "0.14.1"

    @pytest.fixture(scope="class")
    def macros(self):
        return {
            "create_source_table.sql": _CREATE_SOURCE_TABLE_SQL,
            "assert_equal.sql": _ASSERT_EQUAL_SQL,
            "integer_type_value.sql": _INTEGER_TYPE_VALUE_SQL,
            "text_type_value.sql": _TEXT_TYPE_VALUE_SQL,
        }

    @pytest.fixture(scope="class")
    def extra_dispatches(self):
        return [
            {
                "macro_namespace": "codegen_integration_tests",
                "search_order": [
                    "test_dbt_package",
                    "dbt",
                    "codegen_integration_tests",
                ],
            }
        ]

    def test_package(self, project, dbt_core_bug_workaround):
        run_dbt(["deps"])
        run_dbt(["seed"])
        run_dbt(["run-operation", "create_source_table"])
        run_dbt(["run"])
        run_dbt(["test"])


_CREATE_SOURCE_TABLE_SQL = """
{% macro create_source_table() %}

{% set target_schema=api.Relation.create(
    database=target.database,
    schema=target.schema ~ "__data_source_schema"
) %}

{% do adapter.create_schema(target_schema) %}

{% set drop_table_sql %}
drop table if exists {{ target_schema }}.codegen_integration_tests__data_source_table
{% endset %}

{{ run_query(drop_table_sql) }}

{% set create_table_sql %}
create table {{ target_schema }}.codegen_integration_tests__data_source_table
as select
    1 as my_integer_col,
    cast(1 as bit) as my_bool_col
{% endset %}

{{ run_query(create_table_sql) }}

{% set drop_table_sql_case_sensitive %}
drop table if exists {{ target_schema }}.codegen_integration_tests__data_source_table_case_sensitive
{% endset %}

{{ run_query(drop_table_sql_case_sensitive) }}

{% set create_table_sql_case_sensitive %}
create table {{ target_schema }}.codegen_integration_tests__data_source_table_case_sensitive
as select
    1 as {{ adapter.quote("My_Integer_Col") }},
    cast(1 as bit) as {{ adapter.quote("My_Bool_Col") }}
{% endset %}

{{ run_query(create_table_sql_case_sensitive) }}

{% endmacro %}
""".strip()

_ASSERT_EQUAL_SQL = """
{% macro assert_equal(actual_object, expected_object) %}
{% if not execute %}

    {# pass #}

{% elif actual_object != expected_object %}

    {% set msg %}
    Expected did not match actual

    -----------
    Actual:
    -----------
    --->{{ actual_object }}<---

    -----------
    Expected:
    -----------
    --->{{ expected_object }}<---

    {% endset %}

    {{ log(msg, info=True) }}

    select 'fail'

{% else %}

    select top 0 'ok'

{% endif %}
{% endmacro %}
""".strip()

_INTEGER_TYPE_VALUE_SQL = """
{%- macro integer_type_value() -%}
bigint
{%- endmacro -%}
""".strip()

_TEXT_TYPE_VALUE_SQL = """
{%- macro text_type_value() -%}
varchar
{%- endmacro -%}
""".strip()
