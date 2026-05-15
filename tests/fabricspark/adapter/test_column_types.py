import pytest

from dbt.tests.adapter.column_types.fixtures import schema_yml
from dbt.tests.adapter.column_types.test_column_types import BasePostgresColumnTypes

# Spark SQL-compatible model using CAST instead of PostgreSQL :: syntax.
# Types are chosen so that Spark reports them as names recognized by the
# base Column.is_*() helpers (smallint, bigint, float, double) or by the
# custom macro below (int, string, decimal).
model_sql = """
{{ config(materialized="materialized_view") }}
select
    CAST(1 AS smallint) as smallint_col,
    CAST(2 AS int) as int_col,
    CAST(3 AS bigint) as bigint_col,
    CAST(4.0 AS float) as real_col,
    CAST(5.0 AS double) as double_col,
    CAST(6.0 AS decimal(10,2)) as numeric_col,
    CAST('7' AS string) as text_col,
    CAST('8' AS string) as varchar_col
"""

# Custom is_type macro for Spark.  The base Column.is_*() methods do not
# recognise Spark's "int", "string", or "decimal(p,s)" type names, so
# this macro extends the checks with dtype-string comparisons.
macro_test_is_type_sql = """
{% macro simple_type_check_column(column, check) %}
    {% if check == 'string' %}
        {{ return(column.is_string() or column.dtype.lower() == 'string') }}
    {% elif check == 'float' %}
        {{ return(column.is_float()) }}
    {% elif check == 'number' %}
        {{ return(column.is_number()
                  or column.dtype.lower() == 'int'
                  or column.dtype.lower().startswith('decimal')) }}
    {% elif check == 'numeric' %}
        {{ return(column.is_numeric() or column.dtype.lower().startswith('decimal')) }}
    {% elif check == 'integer' %}
        {{ return(column.is_integer() or column.dtype.lower() == 'int') }}
    {% else %}
        {% do exceptions.raise_compiler_error('invalid type check value: ' ~ check) %}
    {% endif %}
{% endmacro %}

{% macro type_check_column(column, type_checks) %}
    {% set failures = [] %}
    {% for type_check in type_checks %}
        {% if type_check.startswith('not ') %}
            {% if simple_type_check_column(column, type_check[4:]) %}
                {% do log('simple_type_check_column got ', True) %}
                {% do failures.append(type_check) %}
            {% endif %}
        {% else %}
            {% if not simple_type_check_column(column, type_check) %}
                {% do failures.append(type_check) %}
            {% endif %}
        {% endif %}
    {% endfor %}
    {% if (failures | length) > 0 %}
        {% do log('column ' ~ column.name ~ ' had failures: ' ~ failures, info=True) %}
    {% endif %}
    {% do return((failures | length) == 0) %}
{% endmacro %}

{% test is_type(model, column_map) %}
    {% if not execute %}
        {{ return(None) }}
    {% endif %}
    {% if not column_map %}
        {% do exceptions.raise_compiler_error('test_is_type must have a column name') %}
    {% endif %}
    {% set columns = adapter.get_columns_in_relation(model) %}
    {% if (column_map | length) != (columns | length) %}
        {% set column_map_keys = (column_map | list | string) %}
        {% set column_names = (columns | map(attribute='name') | list | string) %}
        {% do exceptions.raise_compiler_error('did not get all the columns/all columns not specified:\\n' ~ column_map_keys ~ '\\nvs\\n' ~ column_names) %}
    {% endif %}
    {% set bad_columns = [] %}
    {% for column in columns %}
        {% set column_key = (column.name | lower) %}
        {% if column_key in column_map %}
            {% set type_checks = column_map[column_key] %}
            {% if not type_checks %}
                {% do exceptions.raise_compiler_error('no type checks?') %}
            {% endif %}
            {% if not type_check_column(column, type_checks) %}
                {% do bad_columns.append(column.name) %}
            {% endif %}
        {% else %}
            {% do exceptions.raise_compiler_error('column key ' ~ column_key ~ ' not found in ' ~ (column_map | list | string)) %}
        {% endif %}
    {% endfor %}
    {% do log('bad columns: ' ~ bad_columns, info=True) %}
    {% for bad_column in bad_columns %}
      select '{{ bad_column }}' as bad_column
      {{ 'union all' }}
    {% endfor %}
    select * from (select 1 as c where 1 = 0) as nothing
{% endtest %}
"""


class TestFabricSparkColumnTypes(BasePostgresColumnTypes):
    @pytest.fixture(scope="class")
    def macros(self):
        return {"test_is_type.sql": macro_test_is_type_sql}

    @pytest.fixture(scope="class")
    def models(self):
        return {"model.sql": model_sql, "schema.yml": schema_yml}
