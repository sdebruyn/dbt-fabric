{% materialization incremental, adapter='fabricspark', supported_languages=['sql', 'python'] -%}

  {%- set full_refresh_mode = should_full_refresh() -%}
  {%- set raw_file_format = config.get('file_format', default='delta') -%}
  {%- set unique_key = config.get('unique_key', none) -%}
  {%- set raw_strategy = config.get('incremental_strategy') or ('merge' if unique_key else 'append') -%}
  {%- set grant_config = config.get('grants') -%}

  {%- set file_format = dbt_spark_validate_get_file_format(raw_file_format) -%}
  {%- set strategy = dbt_spark_validate_get_incremental_strategy(raw_strategy, file_format) -%}

  {%- set partition_by = config.get('partition_by', none) -%}
  {%- set language = model['language'] -%}
  {%- set on_schema_change = incremental_validate_on_schema_change(config.get('on_schema_change'), default='ignore') -%}
  {%- set incremental_predicates = config.get('predicates', none) or config.get('incremental_predicates', none) -%}
  {%- set target_relation = this -%}
  {%- set existing_relation = load_relation(this) -%}
  {% set tmp_relation = this.incorporate(path = {"identifier": this.identifier ~ '__dbt_tmp'}) -%}

  {%- if strategy in ['insert_overwrite', 'microbatch'] and partition_by -%}
    {%- call statement() -%}
      set spark.sql.sources.partitionOverwriteMode = DYNAMIC
    {%- endcall -%}
  {%- endif -%}

  {{ run_hooks(pre_hooks, inside_transaction=False) }}
  {{ run_hooks(pre_hooks, inside_transaction=True) }}

  {%- if existing_relation is none -%}
    {%- call statement('main', language=language) -%}
      {{ create_table_as(False, target_relation, compiled_code, language) }}
    {%- endcall -%}
    {% do persist_constraints(target_relation, model) %}
  {%- elif existing_relation.is_view or existing_relation.is_materialized_view or full_refresh_mode -%}
    {# Drop and recreate: Fabric Lakehouse does not support atomic rename for tables #}
    {% do adapter.drop_relation(existing_relation) %}
    {%- call statement('main', language=language) -%}
      {{ create_table_as(False, target_relation, compiled_code, language) }}
    {%- endcall -%}
    {% do persist_constraints(target_relation, model) %}
  {%- else -%}
    {%- call statement('create_tmp_relation', language=language) -%}
      {{ create_table_as(False, tmp_relation, compiled_code, language) }}
    {%- endcall -%}
    {%- do process_schema_changes(on_schema_change, tmp_relation, existing_relation) -%}
    {%- call statement('main') -%}
      {{ dbt_spark_get_incremental_sql(strategy, tmp_relation, target_relation, existing_relation, unique_key, incremental_predicates) }}
    {%- endcall -%}
    {% call statement('drop_tmp_relation') -%}
      drop table if exists {{ tmp_relation }}
    {%- endcall %}
  {%- endif -%}

  {% set should_revoke = should_revoke(existing_relation, full_refresh_mode) %}
  {% do apply_grants(target_relation, grant_config, should_revoke) %}

  {% do persist_docs(target_relation, model) %}

  {{ run_hooks(post_hooks, inside_transaction=True) }}
  {{ run_hooks(post_hooks, inside_transaction=False) }}

  {{ return({'relations': [target_relation]}) }}

{%- endmaterialization %}


{% macro dbt_spark_get_incremental_sql(strategy, source, target, existing, unique_key, incremental_predicates) %}
  {%- if strategy == 'append' -%}
    {{ fabricspark__get_insert_into_sql(source, target) }}
  {%- elif strategy == 'insert_overwrite' -%}
    {{ fabricspark__get_insert_overwrite_sql(source, target) }}
  {%- elif strategy == 'microbatch' -%}
    {% set missing_partition_key_microbatch_msg -%}
      fabricspark 'microbatch' incremental strategy requires a `partition_by` config.
      Ensure you are using a `partition_by` column that is of grain {{ config.get('batch_size') }}.
    {%- endset %}
    {%- if not config.get('partition_by') -%}
      {{ exceptions.raise_compiler_error(missing_partition_key_microbatch_msg) }}
    {%- endif -%}
    {{ fabricspark__get_insert_overwrite_sql(source, target) }}
  {%- elif strategy == 'merge' -%}
    {{ get_merge_sql(target, source, unique_key, dest_columns=none, incremental_predicates=incremental_predicates) }}
  {%- else -%}
    {% set no_sql_for_strategy_msg -%}
      No known SQL for the incremental strategy provided: {{ strategy }}
    {%- endset %}
    {{ exceptions.raise_compiler_error(no_sql_for_strategy_msg) }}
  {%- endif -%}
{% endmacro %}


{# Fabric Lakehouse INSERT INTO ... SELECT fails with REQUIRES_SINGLE_PART_NAMESPACE.
   Use MERGE with always-false condition to append all rows instead. #}
{% macro fabricspark__get_insert_into_sql(source_relation, target_relation) %}

    merge into {{ target_relation }} as DBT_INTERNAL_DEST
    using {{ source_relation }} as DBT_INTERNAL_SOURCE
    on false
    when not matched then insert *

{% endmacro %}


{% macro fabricspark__get_insert_overwrite_sql(source_relation, target_relation) %}

    {%- set dest_columns = adapter.get_columns_in_relation(target_relation) -%}
    {%- set dest_cols_csv = dest_columns | map(attribute='quoted') | join(', ') -%}
    insert overwrite table {{ target_relation.include(database=false) }}
    {{ partition_cols(label="partition") }}
    select {{ dest_cols_csv }} from {{ source_relation }}

{% endmacro %}
