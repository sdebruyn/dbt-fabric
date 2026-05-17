{% macro fabricspark__string_literal(value) -%}
    '{{ value }}'
{%- endmacro %}

{# Fabric Lakehouse Spark has escapedStringLiterals=false (the default),
   so backslash is a literal character — use SQL-standard doubled quotes. #}
{% macro fabricspark__escape_single_quotes(expression) -%}
{{ expression | replace("'","''") }}
{%- endmacro %}
