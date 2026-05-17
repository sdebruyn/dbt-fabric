{% materialization view, adapter='fabricspark' %}
    {%- set identifier = model['alias'] -%}
    {%- set grant_config = config.get('grants') -%}

    {%- set old_relation = adapter.get_relation(database=database, schema=schema, identifier=identifier) -%}
    {%- set exists_as_view = (old_relation is not none and old_relation.is_view) -%}

    {%- set target_relation = this.incorporate(type='view') -%}

    {{ run_hooks(pre_hooks) }}

    {%- if old_relation is not none and old_relation.is_table -%}
        {%- if should_full_refresh() -%}
            {% do adapter.drop_relation(old_relation) %}
        {%- else -%}
            {{ exceptions.raise_compiler_error("Cannot create view " ~ target_relation ~ " because a table with that name already exists. Use --full-refresh to drop the table first.") }}
        {%- endif -%}
    {%- endif -%}

    {% call statement('main') -%}
        create or replace view {{ target_relation }} as (
            {{ sql }}
        )
    {%- endcall %}

    {% set should_revoke = should_revoke(exists_as_view, full_refresh_mode=True) %}
    {% do apply_grants(target_relation, grant_config, should_revoke=should_revoke) %}

    {{ run_hooks(post_hooks) }}

    {{ return({'relations': [target_relation]}) }}
{%- endmaterialization %}
