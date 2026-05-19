{#- T-SQL does not support `COUNT(DISTINCT col1, col2) OVER (...)`: `COUNT(DISTINCT)`
    accepts a single column and is rejected in window functions. We use the
    distinct-free dense_rank trick that postgres and databricks ship under
    `_count_num_rows_in_status_without_distinct_window_func`. -#}
{% macro fabric___count_num_rows_in_status() %}
    dense_rank() over (partition by dbt_audit_row_status order by dbt_audit_surrogate_key, dbt_audit_pk_row_num)
    + dense_rank() over (partition by dbt_audit_row_status order by dbt_audit_surrogate_key desc, dbt_audit_pk_row_num desc)
    - 1
{% endmacro %}
