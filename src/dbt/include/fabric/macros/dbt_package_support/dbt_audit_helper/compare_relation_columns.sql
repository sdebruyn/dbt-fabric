{#- Uses sys.columns/sys.objects instead of INFORMATION_SCHEMA (not supported in
    Fabric distributed mode). Joins sys.objects (not sys.tables) so views are
    included. Uses row_number() for ordinal position since column_id can have
    gaps after schema changes. Replaces USING with explicit ON and boolean
    expressions with CASE WHEN. -#}
{% macro fabric__compare_relation_columns(a_relation, b_relation) %}

select
    coalesce(a_cols.column_name, b_cols.column_name) as column_name,
    a_cols.ordinal_position as a_ordinal_position,
    b_cols.ordinal_position as b_ordinal_position,
    a_cols.data_type as a_data_type,
    b_cols.data_type as b_data_type,
    case when a_cols.ordinal_position = b_cols.ordinal_position then 1 else 0 end as has_ordinal_position_match,
    case when a_cols.data_type = b_cols.data_type then 1 else 0 end as has_data_type_match
from ({{ fabric__get_columns_in_relation_sql(a_relation) }}) a_cols
full outer join ({{ fabric__get_columns_in_relation_sql(b_relation) }}) b_cols
    on a_cols.column_name = b_cols.column_name

{% endmacro %}


{% macro fabric__get_columns_in_relation_sql(relation) %}
  select
      row_number() over (order by c.column_id) as ordinal_position,
      c.name as column_name,
      t.name as data_type,
      c.max_length as character_maximum_length,
      c.precision as numeric_precision,
      c.scale as numeric_scale
  from sys.columns c
  inner join sys.types t on c.user_type_id = t.user_type_id
  inner join sys.objects o on c.object_id = o.object_id
  inner join sys.schemas s on o.schema_id = s.schema_id
  where o.name = '{{ relation.identifier }}'
    and s.name = '{{ relation.schema }}'
{% endmacro %}
