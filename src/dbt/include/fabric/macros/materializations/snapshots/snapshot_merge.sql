{% macro fabric__snapshot_merge_sql(target, source, insert_cols) %}

  {%- set insert_cols_csv = insert_cols | join(', ') -%}
  {%- set columns = config.get("snapshot_table_column_names") or get_snapshot_table_column_names() -%}
  {%- set target_table = target.include(database=False) -%}
  {%- set source_table = source.include(database=False) -%}
  {% set source_columns_list = [] %}
  {% for column in insert_cols %}
    {% set source_columns_list = source_columns_list.append("DBT_INTERNAL_SOURCE." + column) %}
  {% endfor %}
  {%- set source_columns_csv = source_columns_list | join(', ') -%}

  merge into {{ target_table }} as DBT_INTERNAL_DEST
  using {{ source_table }} as DBT_INTERNAL_SOURCE
  on DBT_INTERNAL_SOURCE.{{ columns.dbt_scd_id }} = DBT_INTERNAL_DEST.{{ columns.dbt_scd_id }}

  when matched
    and DBT_INTERNAL_SOURCE.dbt_change_type in ('update', 'delete')
    {% if config.get("dbt_valid_to_current") %}
      and (DBT_INTERNAL_DEST.{{ columns.dbt_valid_to }} = {{ config.get('dbt_valid_to_current') }} or DBT_INTERNAL_DEST.{{ columns.dbt_valid_to }} is null)
    {% else %}
      and DBT_INTERNAL_DEST.{{ columns.dbt_valid_to }} is null
    {% endif %}
    then update set DBT_INTERNAL_DEST.{{ columns.dbt_valid_to }} = DBT_INTERNAL_SOURCE.{{ columns.dbt_valid_to }}

  when not matched by target
    and DBT_INTERNAL_SOURCE.dbt_change_type = 'insert'
    then insert ({{ insert_cols_csv }})
         values ({{ source_columns_csv }})
  {{ apply_label() }}
{% endmacro %}
