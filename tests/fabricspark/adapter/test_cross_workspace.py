import pytest

from dbt.tests.util import run_dbt

_REMOTE_SCHEMA = "dbo"

_setup_source_macro = """
{% macro create_cross_workspace_source() %}
    {% set remote_ws = var('cross_workspace_name') %}
    {% set remote_lh = var('cross_lakehouse_name') %}
    {% set fqn = '`' ~ remote_ws ~ '`.`' ~ remote_lh ~ '`.`' ~ var('cross_schema', 'dbo') ~ '`' %}

    CREATE TABLE IF NOT EXISTS {{ fqn }}.cross_ws_source (
        id INT,
        name STRING,
        created_at TIMESTAMP
    );

    MERGE INTO {{ fqn }}.cross_ws_source AS t
    USING (
        SELECT 1 as id, 'alice' as name, cast('2024-01-01 00:00:00' as timestamp) as created_at
        UNION ALL
        SELECT 2 as id, 'bob' as name, cast('2024-01-02 00:00:00' as timestamp) as created_at
        UNION ALL
        SELECT 3 as id, 'charlie' as name, cast('2024-01-03 00:00:00' as timestamp) as created_at
    ) AS s
    ON t.id = s.id
    WHEN MATCHED THEN UPDATE SET *
    WHEN NOT MATCHED THEN INSERT *;
{% endmacro %}
"""

_teardown_macro = """
{% macro drop_cross_workspace_objects() %}
    {% set remote_ws = var('cross_workspace_name') %}
    {% set remote_lh = var('cross_lakehouse_name') %}
    {% set fqn = '`' ~ remote_ws ~ '`.`' ~ remote_lh ~ '`.`' ~ var('cross_schema', 'dbo') ~ '`' %}

    DROP TABLE IF EXISTS {{ fqn }}.cross_ws_source;
    DROP TABLE IF EXISTS {{ fqn }}.cross_ws_table_target;
    DROP TABLE IF EXISTS {{ fqn }}.cross_ws_incremental_target;
    DROP VIEW IF EXISTS {{ fqn }}.cross_ws_view_target;
    DROP VIEW IF EXISTS {{ fqn }}.cross_ws_matview_target;
{% endmacro %}
"""

_model_read_from_remote = """
{{ config(materialized='table') }}

{% set remote_ws = var('cross_workspace_name') %}
{% set remote_lh = var('cross_lakehouse_name') %}

select * from `{{ remote_ws }}`.`{{ remote_lh }}`.`dbo`.cross_ws_source
"""

_model_write_table_to_remote = """
{{ config(
    materialized='table',
    workspace_name=var('cross_workspace_name'),
    database=var('cross_lakehouse_name'),
    schema='dbo'
) }}

select 1 as id, 'table_write' as source, cast('2024-06-01 00:00:00' as timestamp) as created_at
"""

_model_write_view_to_remote = """
{{ config(
    materialized='view',
    workspace_name=var('cross_workspace_name'),
    database=var('cross_lakehouse_name'),
    schema='dbo'
) }}

select 1 as id, 'view_write' as source, cast('2024-06-01 00:00:00' as timestamp) as created_at
"""

_model_write_matview_to_remote = """
{{ config(
    materialized='materialized_view',
    workspace_name=var('cross_workspace_name'),
    database=var('cross_lakehouse_name'),
    schema='dbo'
) }}

select 1 as id, 'matview_write' as source, cast('2024-06-01 00:00:00' as timestamp) as created_at
"""

_model_write_incremental_to_remote = """
{{ config(
    materialized='incremental',
    unique_key='id',
    workspace_name=var('cross_workspace_name'),
    database=var('cross_lakehouse_name'),
    schema='dbo'
) }}

select 1 as id, 'inc_write' as source, cast('2024-06-01 00:00:00' as timestamp) as created_at
{% if is_incremental() %}
union all
select 2 as id, 'inc_write_2' as source, cast('2024-06-02 00:00:00' as timestamp) as created_at
{% endif %}
"""

_snapshot_cross_workspace = """
{% snapshot cross_ws_snapshot %}
{{ config(
    target_database=var('cross_lakehouse_name'),
    target_schema='dbo',
    unique_key='id',
    strategy='timestamp',
    updated_at='created_at',
    workspace_name=var('cross_workspace_name'),
) }}

select * from `{{ var('cross_workspace_name') }}`.`{{ var('cross_lakehouse_name') }}`.`dbo`.cross_ws_source

{% endsnapshot %}
"""


@pytest.mark.cross_workspace
class TestCrossWorkspaceRead:
    @pytest.fixture(scope="class")
    def models(self):
        return {
            "cross_ws_read.sql": _model_read_from_remote,
        }

    @pytest.fixture(scope="class")
    def macros(self):
        return {
            "setup_source.sql": _setup_source_macro,
            "teardown.sql": _teardown_macro,
        }

    @pytest.fixture(scope="class")
    def project_config_update(self, cross_workspace_config):
        return {
            "models": {"+materialized": "table"},
            "vars": {
                "cross_workspace_name": cross_workspace_config["workspace_name"],
                "cross_lakehouse_name": cross_workspace_config["lakehouse_name"],
            },
            "on-run-start": ["{{ create_cross_workspace_source() }}"],
            "on-run-end": ["{{ drop_cross_workspace_objects() }}"],
        }

    def test_read_from_remote_workspace(self, project):
        results = run_dbt(["run"])
        assert len(results) == 1
        assert results[0].status == "success"

        result = project.run_sql(
            f"select count(*) from `{project.database}`.`{project.test_schema}`.cross_ws_read",
            fetch="one",
        )
        assert result[0] == 3


@pytest.mark.cross_workspace
class TestCrossWorkspaceWriteTable:
    @pytest.fixture(scope="class")
    def models(self):
        return {
            "cross_ws_table_target.sql": _model_write_table_to_remote,
        }

    @pytest.fixture(scope="class")
    def macros(self):
        return {"teardown.sql": _teardown_macro}

    @pytest.fixture(scope="class")
    def project_config_update(self, cross_workspace_config):
        return {
            "vars": {
                "cross_workspace_name": cross_workspace_config["workspace_name"],
                "cross_lakehouse_name": cross_workspace_config["lakehouse_name"],
            },
            "on-run-end": ["{{ drop_cross_workspace_objects() }}"],
        }

    def test_write_table_to_remote_workspace(self, project, cross_workspace_config):
        results = run_dbt(["run"])
        assert len(results) == 1
        assert results[0].status == "success"

        ws = cross_workspace_config["workspace_name"]
        lh = cross_workspace_config["lakehouse_name"]
        result = project.run_sql(
            f"select count(*) from `{ws}`.`{lh}`.`dbo`.cross_ws_table_target",
            fetch="one",
        )
        assert result[0] == 1


@pytest.mark.cross_workspace
class TestCrossWorkspaceWriteView:
    @pytest.fixture(scope="class")
    def models(self):
        return {
            "cross_ws_view_target.sql": _model_write_view_to_remote,
        }

    @pytest.fixture(scope="class")
    def macros(self):
        return {"teardown.sql": _teardown_macro}

    @pytest.fixture(scope="class")
    def project_config_update(self, cross_workspace_config):
        return {
            "vars": {
                "cross_workspace_name": cross_workspace_config["workspace_name"],
                "cross_lakehouse_name": cross_workspace_config["lakehouse_name"],
            },
            "on-run-end": ["{{ drop_cross_workspace_objects() }}"],
        }

    def test_write_view_to_remote_workspace(self, project, cross_workspace_config):
        results = run_dbt(["run"])
        assert len(results) == 1
        assert results[0].status == "success"

        ws = cross_workspace_config["workspace_name"]
        lh = cross_workspace_config["lakehouse_name"]
        result = project.run_sql(
            f"select count(*) from `{ws}`.`{lh}`.`dbo`.cross_ws_view_target",
            fetch="one",
        )
        assert result[0] == 1


@pytest.mark.cross_workspace
class TestCrossWorkspaceWriteMaterializedView:
    @pytest.fixture(scope="class")
    def models(self):
        return {
            "cross_ws_matview_target.sql": _model_write_matview_to_remote,
        }

    @pytest.fixture(scope="class")
    def macros(self):
        return {"teardown.sql": _teardown_macro}

    @pytest.fixture(scope="class")
    def project_config_update(self, cross_workspace_config):
        return {
            "vars": {
                "cross_workspace_name": cross_workspace_config["workspace_name"],
                "cross_lakehouse_name": cross_workspace_config["lakehouse_name"],
            },
            "on-run-end": ["{{ drop_cross_workspace_objects() }}"],
        }

    def test_write_matview_to_remote_workspace(self, project, cross_workspace_config):
        results = run_dbt(["run"])
        assert len(results) == 1
        assert results[0].status == "success"

        ws = cross_workspace_config["workspace_name"]
        lh = cross_workspace_config["lakehouse_name"]
        result = project.run_sql(
            f"select count(*) from `{ws}`.`{lh}`.`dbo`.cross_ws_matview_target",
            fetch="one",
        )
        assert result[0] == 1


@pytest.mark.cross_workspace
class TestCrossWorkspaceWriteIncremental:
    @pytest.fixture(scope="class")
    def models(self):
        return {
            "cross_ws_incremental_target.sql": _model_write_incremental_to_remote,
        }

    @pytest.fixture(scope="class")
    def macros(self):
        return {"teardown.sql": _teardown_macro}

    @pytest.fixture(scope="class")
    def project_config_update(self, cross_workspace_config):
        return {
            "vars": {
                "cross_workspace_name": cross_workspace_config["workspace_name"],
                "cross_lakehouse_name": cross_workspace_config["lakehouse_name"],
            },
            "on-run-end": ["{{ drop_cross_workspace_objects() }}"],
        }

    def test_write_incremental_to_remote_workspace(self, project, cross_workspace_config):
        results = run_dbt(["run"])
        assert len(results) == 1
        assert results[0].status == "success"

        ws = cross_workspace_config["workspace_name"]
        lh = cross_workspace_config["lakehouse_name"]
        result = project.run_sql(
            f"select count(*) from `{ws}`.`{lh}`.`dbo`.cross_ws_incremental_target",
            fetch="one",
        )
        assert result[0] == 1

        results = run_dbt(["run"])
        assert len(results) == 1
        assert results[0].status == "success"

        result = project.run_sql(
            f"select count(*) from `{ws}`.`{lh}`.`dbo`.cross_ws_incremental_target",
            fetch="one",
        )
        assert result[0] == 2


@pytest.mark.cross_workspace
class TestCrossWorkspaceSnapshot:
    @pytest.fixture(scope="class")
    def snapshots(self):
        return {
            "cross_ws_snapshot.sql": _snapshot_cross_workspace,
        }

    @pytest.fixture(scope="class")
    def macros(self):
        return {
            "setup_source.sql": _setup_source_macro,
            "teardown.sql": _teardown_macro,
        }

    @pytest.fixture(scope="class")
    def project_config_update(self, cross_workspace_config):
        return {
            "vars": {
                "cross_workspace_name": cross_workspace_config["workspace_name"],
                "cross_lakehouse_name": cross_workspace_config["lakehouse_name"],
            },
            "on-run-start": ["{{ create_cross_workspace_source() }}"],
            "on-run-end": ["{{ drop_cross_workspace_objects() }}"],
            "snapshots": {"+materialized": "table"},
        }

    def test_snapshot_to_remote_workspace(self, project, cross_workspace_config):
        results = run_dbt(["snapshot"])
        assert len(results) == 1
        assert results[0].status == "success"

        ws = cross_workspace_config["workspace_name"]
        lh = cross_workspace_config["lakehouse_name"]
        result = project.run_sql(
            f"select count(*) from `{ws}`.`{lh}`.`dbo`.cross_ws_snapshot",
            fetch="one",
        )
        assert result[0] == 3
