{% macro fabricspark__can_clone_table() %}
    {{ return(False) }}
{% endmacro %}


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

  {%- set target_relation = this.incorporate(type='materialized_view') -%}

  {% if existing_relation is not none %}
      {{ drop_relation_if_exists(existing_relation) }}
  {% endif %}

  {%- set clone_sql = "select * from " ~ defer_relation -%}

  {% call statement('main') %}
      {{ get_create_materialized_view_as_sql(target_relation, clone_sql) }}
  {% endcall %}

  {%- set grant_config = config.get('grants') -%}
  {% set should_revoke = should_revoke(existing_relation, full_refresh_mode=True) %}
  {% do apply_grants(target_relation, grant_config, should_revoke=should_revoke) %}

  {{ return({'relations': [target_relation]}) }}

{% endmaterialization %}
