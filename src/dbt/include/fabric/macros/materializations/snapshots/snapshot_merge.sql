{# T-SQL requires MERGE to be terminated with a semicolon #}
{% macro fabric__snapshot_merge_sql(target, source, insert_cols) %}
    {{ default__snapshot_merge_sql(target, source, insert_cols) }};
{% endmacro %}
