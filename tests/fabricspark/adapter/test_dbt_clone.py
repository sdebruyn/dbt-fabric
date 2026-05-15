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
        assert len(schema_relations) > 0
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


@pytest.mark.skip(
    "Fabric Lakehouse does not support SHALLOW CLONE (Databricks-specific Delta feature)"
)
class TestFabricSparkClonePossible(BaseClonePossible):
    pass


@pytest.mark.skip(
    "Fabric Lakehouse does not support SHALLOW CLONE (Databricks-specific Delta feature)"
)
class TestFabricSparkCloneSameSourceAndTarget(BaseCloneSameSourceAndTarget):
    pass
