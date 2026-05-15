import pytest

from dbt.tests.adapter.concurrency.test_concurrency import (
    BaseConcurrency,
    models__dep_sql,
    models__invalid_sql,
    models__skip_sql,
    models__table_a_sql,
    models__table_b_sql,
)

models__view_model_materialized_view_sql = """
{{
  config(
    materialized = "materialized_view"
  )
}}

select * from {{ this.schema }}.seed

"""

models__view_with_conflicting_cascade_materialized_view_sql = """
{{
  config(
    materialized = "materialized_view"
  )
}}

select * from {{ref('table_a')}}

union all

select * from {{ref('table_b')}}

"""


class TestConcurrencyFabricSpark(BaseConcurrency):
    @pytest.fixture(scope="class")
    def models(self):
        return {
            "invalid.sql": models__invalid_sql,
            "table_a.sql": models__table_a_sql,
            "table_b.sql": models__table_b_sql,
            "view_model.sql": models__view_model_materialized_view_sql,
            "dep.sql": models__dep_sql,
            "view_with_conflicting_cascade.sql": models__view_with_conflicting_cascade_materialized_view_sql,
            "skip.sql": models__skip_sql,
        }
