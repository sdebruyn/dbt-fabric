{% macro fabric__insert_into_metadata_table(relation, fields, content) -%}

    {% set insert_into_table_query %}
    insert into {{ relation }} {{ fields }}
    {{ content }}
    {% endset %}

    {% do run_query(insert_into_table_query) %}

{%- endmacro %}
