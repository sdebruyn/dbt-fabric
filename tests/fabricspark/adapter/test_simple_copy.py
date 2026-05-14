import pytest

from dbt.tests.adapter.simple_copy import fixtures
from dbt.tests.adapter.simple_copy.test_copy_uppercase import BaseSimpleCopyUppercase
from dbt.tests.adapter.simple_copy.test_simple_copy import EmptyModelsArentRunBase, SimpleCopyBase
from dbt.tests.util import check_relations_equal, run_dbt

_MODELS__VIEW_MODEL_AS_MATERIALIZED_VIEW = """\
{{
  config(
    materialized = "materialized_view"
  )
}}

select * from {{ ref('seed') }}
"""

_MODELS__DISABLED_AS_TABLE = """\
{{
  config(
    materialized = "table",
    enabled = False
  )
}}

select * from {{ ref('seed') }}
"""


class TestEmptyModelsArentRunFabricSpark(EmptyModelsArentRunBase):
    pass


class TestSimpleCopyBaseFabricSpark(SimpleCopyBase):
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
            "DISABLED.sql": _MODELS__DISABLED_AS_TABLE,
            "EMPTY.sql": fixtures._MODELS__EMPTY,
            "GET_AND_REF.sql": fixtures._MODELS_GET_AND_REF_UPPERCASE,
            "INCREMENTAL.sql": fixtures._MODELS__INCREMENTAL,
            "INTERLEAVED_SORT.sql": fixtures._MODELS__INTERLEAVED_SORT,
            "MATERIALIZED.sql": fixtures._MODELS__MATERIALIZED,
            "VIEW_MODEL.sql": _MODELS__VIEW_MODEL_AS_MATERIALIZED_VIEW,
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
