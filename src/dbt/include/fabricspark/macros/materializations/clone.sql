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

  {% set search_name = "materialization_materialized_view_" ~ adapter.type() %}
  {% if not search_name in context %}
      {% set search_name = "materialization_materialized_view_default" %}
  {% endif %}
  {% set materialization_macro = context[search_name] %}
  {% set relations = materialization_macro() %}
  {{ return(relations) }}

{% endmaterialization %}
