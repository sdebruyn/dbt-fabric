{% materialization view, adapter='fabricspark' %}
    {%- set identifier = model['alias'] -%}
    {%- set grant_config = config.get('grants') -%}

    {%- set old_relation = adapter.get_relation(database=database, schema=schema, identifier=identifier) -%}
    {%- set exists_as_view = (old_relation is not none and old_relation.is_view) -%}

    {%- set target_relation = this.incorporate(type='view') -%}

    {# dbt-spark delegates to create_or_replace_view() which calls run_hooks(pre_hooks) without
       inside_transaction. We split into outside/inside to match dbt-adapters' default pattern. #}
    {{ run_hooks(pre_hooks, inside_transaction=False) }}

    {# Upstream create_or_replace_view() only checks old_relation.is_table via handle_existing_table().
       We check any non-view type (table, materialized_view) since FabricSpark has more relation types.
       We also raise an explicit error instead of silently dropping when --full-refresh is not set. #}
    {%- if old_relation is not none and not old_relation.is_view -%}
        {%- if should_full_refresh() -%}
            {% do adapter.drop_relation(old_relation) %}
        {%- else -%}
            {{ exceptions.raise_compiler_error(
                "Cannot create view " ~ target_relation
                ~ " because a relation of type '" ~ old_relation.type
                ~ "' already exists. Use --full-refresh to drop it first."
            ) }}
        {%- endif -%}
    {%- endif -%}

    {{ run_hooks(pre_hooks, inside_transaction=True) }}

    {# Inline SQL instead of dispatching to get_create_view_as_sql() — Spark SQL uses
       CREATE OR REPLACE VIEW directly (no intermediate/rename/backup swap like dbt-adapters default). #}
    {% call statement('main') -%}
        create or replace view {{ target_relation }} as (
            {{ sql }}
        )
    {%- endcall %}

    {% set should_revoke = should_revoke(exists_as_view, full_refresh_mode=True) %}
    {% do apply_grants(target_relation, grant_config, should_revoke=should_revoke) %}

    {{ run_hooks(post_hooks, inside_transaction=True) }}
    {{ run_hooks(post_hooks, inside_transaction=False) }}

    {{ return({'relations': [target_relation]}) }}
{%- endmaterialization %}
