{%- macro fabric__month_name(date, short, language="default") -%}
{%- if language == "default" -%}
    {%- set f = 'MMM' if short else 'MMMM' -%}
    cast(format({{ date }}, '{{ f }}') as varchar(4000))
{%- else -%}
    {{ dbt_date.month_name_localized(date, short, language) }}
{%- endif -%}
{%- endmacro %}
