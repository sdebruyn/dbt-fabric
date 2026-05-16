{% macro fabric__test_expression_is_true(model, expression, column_name, condition='1=1') %}

{% set column_list = '*' if should_store_failures() else "1 as col" %}

select
    {{ column_list }}
from {{ model }}
where {{ condition }}
and (
{% if column_name is none %}
    not({{ expression }})
{%- else %}
    not({{ column_name }} {{ expression }})
{%- endif %}
)

{% endmacro %}
