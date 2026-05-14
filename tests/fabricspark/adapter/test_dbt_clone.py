from collections import Counter

import pytest

from dbt.tests.adapter.dbt_clone import fixtures
from dbt.tests.adapter.dbt_clone.test_dbt_clone import (
    BaseCloneNotPossible,
    BaseClonePossible,
    BaseCloneSameSourceAndTarget,
    BaseCloneSameTargetAndState,
)
from dbt.tests.util import run_dbt

fabricspark_view_model_sql = """
{{ config(materialized='materialized_view') }}
select * from {{ ref('seed') }}

-- establish a macro dependency that trips infinite recursion if not handled
-- depends on: {{ my_infinitely_recursive_macro() }}
"""

fabricspark_snapshot_sql = """
{% snapshot my_cool_snapshot %}

    {{
        config(
            target_database=database,
            target_schema=schema,
            unique_key='id',
            strategy='check',
            check_cols=['id'],
            file_format='delta',
        )
    }}
    select * from {{ ref('view_model') }}

{% endsnapshot %}
"""

fabricspark_clone_fallback_macro_sql = """
{# Override clone materialization to fall back to materialized_view instead of view #}
{# FabricSpark does not support Spark SQL views, only tables and materialized lake views #}

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

  {%- set other_existing_relation = load_cached_relation(defer_relation) -%}

  {% set can_clone_table = can_clone_table() %}

  {%- if other_existing_relation and other_existing_relation.type == 'table' and can_clone_table -%}

      {%- set target_relation = this.incorporate(type='table') -%}
      {% if existing_relation is not none and not existing_relation.is_table %}
        {{ log("Dropping relation " ~ existing_relation ~ " because it is of type " ~ existing_relation.type) }}
        {{ drop_relation_if_exists(existing_relation) }}
      {% endif %}

      {% if target_relation.database == defer_relation.database and
            target_relation.schema == defer_relation.schema and
            target_relation.identifier == defer_relation.identifier %}
        {{ log("Target relation and defer relation are the same, skipping clone for relation: " ~ target_relation.render()) }}
      {% else %}
        {% call statement('main') %}
            {{ create_or_replace_clone(target_relation, defer_relation) }}
        {% endcall %}
      {% endif %}
      {% set should_revoke = should_revoke(existing_relation, full_refresh_mode=True) %}
      {% do apply_grants(target_relation, grant_config, should_revoke=should_revoke) %}
      {% do persist_docs(target_relation, model) %}

      {{ return({'relations': [target_relation]}) }}

  {%- else -%}

      {# Fall back to materialized_view instead of view for FabricSpark #}
      {%- set target_relation = this.incorporate(type='materialized_view') -%}

      {% set search_name = "materialization_materialized_view_" ~ adapter.type() %}
      {% if not search_name in context %}
          {% set search_name = "materialization_materialized_view_default" %}
      {% endif %}
      {% set materialization_macro = context[search_name] %}
      {% set relations = materialization_macro() %}
      {{ return(relations) }}

  {%- endif -%}

{% endmaterialization %}
"""


class TestFabricSparkCloneNotPossible(BaseCloneNotPossible):
    @pytest.fixture(scope="class")
    def models(self):
        return {
            "table_model.sql": fixtures.table_model_sql,
            "view_model.sql": fabricspark_view_model_sql,
            "ephemeral_model.sql": fixtures.ephemeral_model_sql,
            "schema.yml": fixtures.schema_yml,
            "exposures.yml": fixtures.exposures_yml,
        }

    @pytest.fixture(scope="class")
    def snapshots(self):
        return {
            "snapshot.sql": fabricspark_snapshot_sql,
        }

    @pytest.fixture(scope="class")
    def macros(self):
        return {
            "macros.sql": fixtures.macros_sql,
            "my_can_clone_tables.sql": fixtures.custom_can_clone_tables_false_macros_sql,
            "infinite_macros.sql": fixtures.infinite_macros_sql,
            "get_schema_name.sql": fixtures.get_schema_name_sql,
            "clone_override.sql": fabricspark_clone_fallback_macro_sql,
        }

    def test_can_clone_false(self, project, unique_schema, other_schema):
        project.create_test_schema(other_schema)
        self.run_and_save_state(project.project_root, with_snapshot=True)

        clone_args = [
            "clone",
            "--state",
            "state",
            "--target",
            "otherschema",
        ]

        results = run_dbt(clone_args)
        assert len(results) == 4

        schema_relations = project.adapter.list_relations(
            database=project.database, schema=other_schema
        )
        assert all(r.type == "materialized_view" for r in schema_relations)

        results = run_dbt(clone_args)
        assert len(results) == 4
        assert all("no-op" in r.message.lower() for r in results)

        results = run_dbt([*clone_args, "--full-refresh"])
        assert len(results) == 4

        results = run_dbt([*clone_args, "--resource-type", "model"])
        assert len(results) == 2
        assert all("no-op" in r.message.lower() for r in results)


class TestFabricSparkCloneSameTargetAndState(BaseCloneSameTargetAndState):
    @pytest.fixture(scope="class")
    def models(self):
        return {
            "table_model.sql": fixtures.table_model_sql,
            "view_model.sql": fabricspark_view_model_sql,
            "ephemeral_model.sql": fixtures.ephemeral_model_sql,
            "schema.yml": fixtures.schema_yml,
            "exposures.yml": fixtures.exposures_yml,
        }


class TestFabricSparkClonePossible(BaseClonePossible):
    @pytest.fixture(scope="class")
    def models(self):
        return {
            "table_model.sql": fixtures.table_model_sql,
            "view_model.sql": fabricspark_view_model_sql,
            "ephemeral_model.sql": fixtures.ephemeral_model_sql,
            "schema.yml": fixtures.schema_yml,
            "exposures.yml": fixtures.exposures_yml,
        }

    @pytest.fixture(scope="class")
    def snapshots(self):
        return {
            "snapshot.sql": fabricspark_snapshot_sql,
        }

    @pytest.fixture(scope="class")
    def macros(self):
        return {
            "macros.sql": fixtures.macros_sql,
            "infinite_macros.sql": fixtures.infinite_macros_sql,
            "get_schema_name.sql": fixtures.get_schema_name_sql,
            "clone_override.sql": fabricspark_clone_fallback_macro_sql,
        }

    def test_can_clone_true(self, project, unique_schema, other_schema):
        project.create_test_schema(other_schema)
        self.run_and_save_state(project.project_root, with_snapshot=True)

        clone_args = [
            "clone",
            "--state",
            "state",
            "--target",
            "otherschema",
        ]

        results = run_dbt(clone_args)
        assert len(results) == 4

        schema_relations = project.adapter.list_relations(
            database=project.database, schema=other_schema
        )
        types = Counter(r.type for r in schema_relations)
        assert types == Counter({"table": 3, "materialized_view": 1})

        results = run_dbt(clone_args)
        assert len(results) == 4
        assert all("no-op" in r.message.lower() for r in results)

        results = run_dbt([*clone_args, "--full-refresh"])
        assert len(results) == 4

        results = run_dbt([*clone_args, "--resource-type", "model"])
        assert len(results) == 2
        assert all("no-op" in r.message.lower() for r in results)


fabricspark_source_snapshot_sql = """
{% snapshot source_based_model_snapshot %}

    {{
        config(
            target_database=database,
            target_schema=schema,
            unique_key='id',
            strategy='check',
            check_cols=['id'],
            file_format='delta',
        )
    }}
    select * from {{ source('test_source', 'source_table') }}

{% endsnapshot %}
"""


class TestFabricSparkCloneSameSourceAndTarget(BaseCloneSameSourceAndTarget):
    @pytest.fixture(scope="class")
    def models(self):
        return {
            "source_based_model.sql": fixtures.source_based_model_sql,
            "source_schema.yml": fixtures.source_schema_yml,
        }

    @pytest.fixture(scope="class")
    def snapshots(self):
        return {
            "snapshot_model.sql": fabricspark_source_snapshot_sql,
        }

    @pytest.fixture(scope="class")
    def macros(self):
        return {
            "macros.sql": fixtures.macros_sql,
            "infinite_macros.sql": fixtures.infinite_macros_sql,
            "get_schema_name.sql": fixtures.get_schema_name_sql,
            "clone_override.sql": fabricspark_clone_fallback_macro_sql,
        }
