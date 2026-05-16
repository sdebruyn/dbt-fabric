{%- macro fabric__date(year, month, day) -%}
    {{- return(modules.datetime.date(year, month, day)) -}}
{%- endmacro -%}
