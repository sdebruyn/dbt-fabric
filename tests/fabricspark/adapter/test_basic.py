import pytest

from dbt.tests.adapter.basic import expected_catalog, files
from dbt.tests.adapter.basic.test_adapter_methods import BaseAdapterMethod
from dbt.tests.adapter.basic.test_base import BaseSimpleMaterializations
from dbt.tests.adapter.basic.test_docs_generate import (
    BaseDocsGenerate,
    BaseDocsGenReferences,
    models__readme_md,
    models__schema_yml,
    ref_models__docs_md,
    ref_models__ephemeral_copy_sql,
    ref_models__ephemeral_summary_sql,
    ref_models__schema_yml,
    ref_sources__schema_yml,
)
from dbt.tests.adapter.basic.test_empty import BaseEmpty
from dbt.tests.adapter.basic.test_ephemeral import BaseEphemeral
from dbt.tests.adapter.basic.test_generic_tests import BaseGenericTests
from dbt.tests.adapter.basic.test_get_catalog_for_single_relation import (
    BaseGetCatalogForSingleRelation,
)
from dbt.tests.adapter.basic.test_incremental import (
    BaseIncremental,
    BaseIncrementalBadStrategy,
    BaseIncrementalNotSchemaChange,
)
from dbt.tests.adapter.basic.test_singular_tests import BaseSingularTests
from dbt.tests.adapter.basic.test_singular_tests_ephemeral import (
    BaseSingularTestsEphemeral,
)
from dbt.tests.adapter.basic.test_snapshot_check_cols import BaseSnapshotCheckCols
from dbt.tests.adapter.basic.test_snapshot_timestamp import BaseSnapshotTimestamp
from dbt.tests.adapter.basic.test_table_materialization import BaseTableMaterialization
from dbt.tests.adapter.basic.test_validate_connection import BaseValidateConnection
from dbt.tests.util import (
    AnyInteger,
    check_relation_types,
    check_relations_equal,
    check_result_nodes_by_name,
    relation_from_name,
    run_dbt,
)


class TestSimpleMaterializationsSpark(BaseSimpleMaterializations):
    @pytest.fixture(scope="class")
    def models(self):
        return {
            "view_model.sql": """
  {{ config(materialized="materialized_view") }}
"""
            + files.model_base,
            "table_model.sql": files.base_table_sql,
            "swappable.sql": files.base_materialized_var_sql,
            "schema.yml": files.schema_base_yml,
        }

    def test_base(self, project):
        # seed command
        results = run_dbt(["seed"])
        # seed result length
        assert len(results) == 1

        # run command
        results = run_dbt()
        # run result length
        assert len(results) == 3

        # names exist in result nodes
        check_result_nodes_by_name(results, ["view_model", "table_model", "swappable"])

        # check relation types
        expected = {
            "base": "table",
            "view_model": "materialized_view",
            "table_model": "table",
            "swappable": "table",
        }
        check_relation_types(project.adapter, expected)

        # base table rowcount
        relation = relation_from_name(project.adapter, "base")
        result = project.run_sql(f"select count(*) as num_rows from {relation}", fetch="one")
        assert result[0] == 10

        # relations_equal
        check_relations_equal(project.adapter, ["base", "view_model", "table_model", "swappable"])

        # check relations in catalog
        catalog = run_dbt(["docs", "generate"])
        assert len(catalog.nodes) == 4
        assert len(catalog.sources) == 1

        results = run_dbt(
            ["run", "-s", "swappable", "--vars", "materialized_var: materialized_view"]
        )
        assert len(results) == 1

        # check relation types, swappable is view
        expected = {
            "base": "table",
            "view_model": "materialized_view",
            "table_model": "table",
            "swappable": "materialized_view",
        }
        check_relation_types(project.adapter, expected)

        # run_dbt changing materialized_var to incremental
        results = run_dbt(["run", "-s", "swappable", "--vars", "materialized_var: incremental"])
        assert len(results) == 1

        # check relation types, swappable is table
        expected = {
            "base": "table",
            "view_model": "materialized_view",
            "table_model": "table",
            "swappable": "table",
        }
        check_relation_types(project.adapter, expected)


class TestSingularTestsSpark(BaseSingularTests):
    pass


class TestSingularTestsEphemeralSpark(BaseSingularTestsEphemeral):
    pass


class TestEmptySpark(BaseEmpty):
    pass


class TestEphemeralSpark(BaseEphemeral):
    @pytest.fixture(scope="class")
    def models(self):
        return {
            "ephemeral.sql": files.base_ephemeral_sql,
            "view_model.sql": """
  {{ config(materialized="table") }}

  select * from {{ ref('ephemeral') }}
""",
            "table_model.sql": files.ephemeral_table_sql,
            "schema.yml": files.schema_base_yml,
        }


class TestIncrementalSpark(BaseIncremental):
    @pytest.fixture(scope="class")
    def project_config_update(self):
        return {"name": "incremental", "models": {"+materialized": "table"}}


class TestIncrementalNotSchemaChangeFabric(BaseIncrementalNotSchemaChange):
    pass


class TestGenericTestsSpark(BaseGenericTests):
    @pytest.fixture(scope="class")
    def models(self):
        return {
            "view_model.sql": """
  {{ config(materialized="materialized_view") }}
"""
            + files.model_base,
            "table_model.sql": files.base_table_sql,
            "schema.yml": files.schema_base_yml,
            "schema_view.yml": files.generic_test_view_yml,
            "schema_table.yml": files.generic_test_table_yml,
        }


class TestSnapshotCheckColsSpark(BaseSnapshotCheckCols):
    @pytest.fixture(scope="class")
    def project_config_update(self):
        return {"name": "snapshot_strategy_check_cols", "models": {"+materialized": "table"}}


class TestSnapshotTimestampSpark(BaseSnapshotTimestamp):
    @pytest.fixture(scope="class")
    def project_config_update(self):
        return {"name": "snapshot_strategy_timestamp", "models": {"+materialized": "table"}}


class TestBaseCachingSpark(BaseAdapterMethod):
    @pytest.fixture(scope="class")
    def models(self):
        adapter_methods_model_sql = """
{% set upstream = ref('upstream') %}

{% if execute %}
    {%- do adapter.drop_schema(upstream) -%}
    {% set existing = adapter.get_relation(upstream.database, upstream.schema, upstream.identifier) %}
    {% if existing is not none %}
        {% do exceptions.raise_compiler_error('expected ' ~ ' to not exist, but it did') %}
    {% endif %}

    {%- do adapter.create_schema(upstream) -%}

    {% set sql = create_table_as(False, upstream, 'select 2 as id') %}
    {% do run_query(sql) %}
{% endif %}


select * from {{ upstream }}
"""
        return {
            "upstream.sql": "select 1 as id",
            "expected.sql": "-- {{ ref('model') }}\nselect 2 as id",
            "model.sql": adapter_methods_model_sql,
        }


class TestValidateConnectionSpark(BaseValidateConnection):
    pass


class TestDocsGenerateSpark(BaseDocsGenerate):
    @pytest.fixture(scope="class")
    def models(self):
        return {
            "schema.yml": models__schema_yml,
            "second_model.sql": """
{{
    config(
        materialized='materialized_view',
        schema='test',
    )
}}

select * from {{ ref('seed') }}
""",
            "readme.md": models__readme_md,
            "model.sql": """
{{
    config(
        materialized='materialized_view',
    )
}}

select * from {{ ref('seed') }}
""",
        }

    @pytest.fixture(scope="class")
    def expected_catalog(self, project, profile_user):
        return expected_catalog.base_expected_catalog(
            project,
            role=None,
            id_type="bigint",
            text_type="string",
            time_type="timestamp",
            view_type="materialized_view",
            table_type="table",
            model_stats=expected_catalog.no_stats(),
        )


class TestDocsGenReferencesSpark(BaseDocsGenReferences):
    @pytest.fixture(scope="class")
    def models(self):
        return {
            "schema.yml": ref_models__schema_yml,
            "sources.yml": ref_sources__schema_yml,
            "view_summary.sql": """
{{
  config(
    materialized = "materialized_view"
  )
}}

select first_name, ct from {{ref('ephemeral_summary')}}
""",
            "ephemeral_summary.sql": ref_models__ephemeral_summary_sql,
            "ephemeral_copy.sql": ref_models__ephemeral_copy_sql,
            "docs.md": ref_models__docs_md,
        }

    @pytest.fixture(scope="class")
    def expected_catalog(self, project, profile_user):
        catalog = expected_catalog.expected_references_catalog(
            project,
            role=None,
            id_type="bigint",
            text_type="string",
            time_type="timestamp",
            bigint_type="bigint",
            view_type="materialized_view",
            table_type="table",
            model_stats=expected_catalog.no_stats(),
        )
        for section in catalog.values():
            for node in section.values():
                for col in node.get("columns", {}).values():
                    col["index"] = AnyInteger()
        return catalog


class TestTableMaterializationSpark(BaseTableMaterialization):
    pass


@pytest.mark.skip(reason="Capability not implemented in FabricSpark.")
class TestGetCatalogForSingleRelationSpark(BaseGetCatalogForSingleRelation):
    pass


class TestIncrementalBadStrategySpark(BaseIncrementalBadStrategy):
    def test_incremental_invalid_strategy(self, project):
        # seed command
        results = run_dbt(["seed"])
        assert len(results) == 2

        # try to run the incremental model, it should fail on the first attempt
        results = run_dbt(["run"], expect_pass=False)
        assert len(results.results) == 1
        assert "Invalid incremental strategy provided: bad_strategy" in results.results[0].message
