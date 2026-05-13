import pytest

from dbt.tests.adapter.constraints.test_constraints import (
    BaseConstraintsColumnsEqual,
    BaseConstraintsRollback,
    BaseConstraintsRuntimeDdlEnforcement,
    BaseIncrementalConstraintsColumnsEqual,
    BaseModelConstraintsRuntimeEnforcement,
    BaseTableConstraintsColumnsEqual,
)

my_model_materialized_view_wrong_order_sql = """
{{
  config(
    materialized = "materialized_view"
  )
}}

select
  'blue' as color,
  1 as id,
  '2019-01-01' as date_day
"""

my_model_materialized_view_wrong_name_sql = """
{{
  config(
    materialized = "materialized_view"
  )
}}

select
  'blue' as color,
  1 as error,
  '2019-01-01' as date_day
"""


class TestViewConstraintsColumnsEqualFabricSpark(BaseConstraintsColumnsEqual):
    @pytest.fixture(scope="class")
    def models(self):
        from dbt.tests.adapter.constraints.fixtures import model_schema_yml

        return {
            "my_model_wrong_order.sql": my_model_materialized_view_wrong_order_sql,
            "my_model_wrong_name.sql": my_model_materialized_view_wrong_name_sql,
            "constraints_schema.yml": model_schema_yml,
        }


class TestIncrementalConstraintsColumnsEqualFabricSpark(BaseIncrementalConstraintsColumnsEqual):
    pass


class TestTableConstraintsColumnsEqualFabricSpark(BaseTableConstraintsColumnsEqual):
    pass


class TestTableConstraintsRuntimeDdlEnforcementFabricSpark(BaseConstraintsRuntimeDdlEnforcement):
    pass


class TestIncrementalConstraintsRuntimeDdlEnforcementFabricSpark(
    BaseConstraintsRuntimeDdlEnforcement
):
    pass


class TestModelConstraintsRuntimeEnforcementFabricSpark(BaseModelConstraintsRuntimeEnforcement):
    pass


class TestTableConstraintsRollbackFabricSpark(BaseConstraintsRollback):
    pass


class TestIncrementalConstraintsRollbackFabricSpark(BaseConstraintsRollback):
    pass
