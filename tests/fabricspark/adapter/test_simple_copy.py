import pytest

from dbt.tests.adapter.simple_copy import fixtures
from dbt.tests.adapter.simple_copy.test_copy_uppercase import BaseSimpleCopyUppercase
from dbt.tests.adapter.simple_copy.test_simple_copy import EmptyModelsArentRunBase, SimpleCopyBase
from dbt.tests.util import check_relations_equal, run_dbt

_FABRICSPARK_VIEW_MODEL = """
{{
  config(
    materialized = "materialized_view"
  )
}}

select * from {{ ref('seed') }}
"""

_FABRICSPARK_DISABLED = """
{{
  config(
    materialized = "table",
    enabled = False
  )
}}

select * from {{ ref('seed') }}
"""


class FabricSparkSimpleCopySetup:
    @pytest.fixture(scope="class")
    def models(self):
        return {
            "advanced_incremental.sql": fixtures._MODELS__ADVANCED_INCREMENTAL,
            "compound_sort.sql": fixtures._MODELS__COMPOUND_SORT,
            "disabled.sql": _FABRICSPARK_DISABLED,
            "empty.sql": fixtures._MODELS__EMPTY,
            "get_and_ref.sql": fixtures._MODELS__GET_AND_REF,
            "incremental.sql": fixtures._MODELS__INCREMENTAL,
            "interleaved_sort.sql": fixtures._MODELS__INTERLEAVED_SORT,
            "materialized.sql": fixtures._MODELS__MATERIALIZED,
            "view_model.sql": _FABRICSPARK_VIEW_MODEL,
        }

    @pytest.fixture(scope="class")
    def properties(self):
        return {
            "schema.yml": fixtures._PROPERTIES__SCHEMA_YML,
        }

    @pytest.fixture(scope="class")
    def seeds(self):
        return {"seed.csv": fixtures._SEEDS__SEED_INITIAL}

    @pytest.fixture(scope="class")
    def project_config_update(self):
        return {"seeds": {"quote_columns": False}}


class TestEmptyModelsArentRunFabricSpark(FabricSparkSimpleCopySetup, EmptyModelsArentRunBase):
    def test_dbt_doesnt_run_empty_models(self, project):
        results = run_dbt(["seed"])
        assert len(results) == 1
        results = run_dbt()
        assert len(results) == 7

        sql = f"SHOW TABLES IN `{project.test_schema}`"
        result = project.run_sql(sql, fetch="all")
        table_names = {row[1].lower() for row in result}

        assert "empty" not in table_names
        assert "disabled" not in table_names


class TestSimpleCopyBaseFabricSpark(FabricSparkSimpleCopySetup, SimpleCopyBase):
    def test_simple_copy(self, project):
        results = run_dbt(["seed"])
        assert len(results) == 1

        results = run_dbt()
        assert len(results) == 7
        check_relations_equal(
            project.adapter, ["seed", "view_model", "incremental", "materialized", "get_and_ref"]
        )

    @pytest.mark.skip(
        "FabricSpark does not support CREATE VIEW or CREATE MATERIALIZED VIEW via raw SQL"
    )
    def test_simple_copy_with_materialized_views(self, project):
        pass


class TestSimpleCopyUppercaseFabricSpark(BaseSimpleCopyUppercase):
    @pytest.fixture(scope="class")
    def dbt_profile_target(self, dbt_profile_target):
        return dbt_profile_target

    @pytest.fixture(scope="class")
    def models(self):
        return {
            "ADVANCED_INCREMENTAL.sql": fixtures._MODELS__ADVANCED_INCREMENTAL,
            "COMPOUND_SORT.sql": fixtures._MODELS__COMPOUND_SORT,
            "DISABLED.sql": _FABRICSPARK_DISABLED,
            "EMPTY.sql": fixtures._MODELS__EMPTY,
            "GET_AND_REF.sql": fixtures._MODELS_GET_AND_REF_UPPERCASE,
            "INCREMENTAL.sql": fixtures._MODELS__INCREMENTAL,
            "INTERLEAVED_SORT.sql": fixtures._MODELS__INTERLEAVED_SORT,
            "MATERIALIZED.sql": fixtures._MODELS__MATERIALIZED,
            "VIEW_MODEL.sql": _FABRICSPARK_VIEW_MODEL,
        }

    def test_simple_copy_uppercase(self, project):
        results = run_dbt(["seed"])
        assert len(results) == 1

        results = run_dbt()
        assert len(results) == 7

        check_relations_equal(
            project.adapter,
            ["seed", "VIEW_MODEL", "INCREMENTAL", "MATERIALIZED", "GET_AND_REF"],
        )
