{# dbt-spark returns True (Delta supports SHALLOW CLONE); Fabric Lakehouse does not. #}
{% macro fabricspark__can_clone_table() %}
    {{ return(False) }}
{% endmacro %}


{# dbt-spark's clone requires file_format='delta' and delegates to SHALLOW CLONE or the
   view materialization. We skip the file_format check (no Delta clone in Fabric) and
   always create a view via inline SQL instead of delegating to the view materialization. #}
{% materialization clone, adapter='fabricspark' %}

  {%- set relations = {'relations': []} -%}

  {%- if not defer_relation -%}
      {{ log("No relation found in state manifest for " ~ model.unique_id, info=True) }}
      {{ return(relations) }}
  {%- endif -%}

  {%- set existing_relation = load_cached_relation(this) -%}

  {%- if existing_relation and not flags.FULL_REFRESH -%}
      {{ log("Relation " ~ existing_relation ~ " already exists", info=True) }}
      {{ return(relations) }}
  {%- endif -%}

  {%- set target_relation = this.incorporate(type='view') -%}

  {# dbt-spark only drops non-table relations; we drop any existing relation since
     Fabric has more types (table, materialized_view) that block CREATE OR REPLACE VIEW. #}
  {% if existing_relation is not none %}
      {{ drop_relation_if_exists(existing_relation) }}
  {% endif %}

  {% call statement('main') %}
      create or replace view {{ target_relation }} as (
          select * from {{ defer_relation }}
      )
  {% endcall %}

  {%- set grant_config = config.get('grants') -%}
  {% set should_revoke = should_revoke(existing_relation, full_refresh_mode=True) %}
  {% do apply_grants(target_relation, grant_config, should_revoke=should_revoke) %}

  {{ return({'relations': [target_relation]}) }}

{% endmaterialization %}
