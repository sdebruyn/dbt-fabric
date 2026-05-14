import pytest

from dbt.tests.adapter.constraints.test_constraints import (
    BaseConstraintsColumnsEqual,
    BaseConstraintsRollback,
    BaseConstraintsRuntimeDdlEnforcement,
    BaseIncrementalConstraintsColumnsEqual,
    BaseModelConstraintsRuntimeEnforcement,
    BaseTableConstraintsColumnsEqual,
)

my_model_table_wrong_order_sql = """
{{
  config(
    materialized = "table"
  )
}}

select
  'blue' as color,
  1 as id,
  '2019-01-01' as date_day
"""

my_model_table_wrong_name_sql = """
{{
  config(
    materialized = "table"
  )
}}

select
  'blue' as color,
  1 as error,
  '2019-01-01' as date_day
"""


class FabricSparkConstraintsTypesMixin:
    @pytest.fixture
    def string_type(self):
        return "string"

    @pytest.fixture
    def int_type(self):
        return "INT"

    @pytest.fixture
    def schema_string_type(self, string_type):
        return string_type

    @pytest.fixture
    def schema_int_type(self, int_type):
        return int_type

    @pytest.fixture
    def data_types(self, schema_int_type, int_type, string_type):
        return [
            ["1", schema_int_type, int_type],
            ["'1'", string_type, string_type],
            ["true", "boolean", "BOOLEAN"],
            ["cast('2013-11-03 00:00:00' as timestamp)", "timestamp", "TIMESTAMP"],
            ["cast(1.0 as decimal(10,2))", "decimal(10,2)", "DECIMAL(10,2)"],
        ]


class TestViewConstraintsColumnsEqualFabricSpark(
    FabricSparkConstraintsTypesMixin, BaseConstraintsColumnsEqual
):
    @pytest.fixture(scope="class")
    def models(self):
        from dbt.tests.adapter.constraints.fixtures import model_schema_yml

        return {
            "my_model_wrong_order.sql": my_model_table_wrong_order_sql,
            "my_model_wrong_name.sql": my_model_table_wrong_name_sql,
            "constraints_schema.yml": model_schema_yml,
        }


class TestIncrementalConstraintsColumnsEqualFabricSpark(
    FabricSparkConstraintsTypesMixin, BaseIncrementalConstraintsColumnsEqual
):
    pass


class TestTableConstraintsColumnsEqualFabricSpark(
    FabricSparkConstraintsTypesMixin, BaseTableConstraintsColumnsEqual
):
    pass


@pytest.mark.skip(
    "TODO: FabricSpark DDL constraint syntax differs from default, needs expected_sql override"
)
class TestTableConstraintsRuntimeDdlEnforcementFabricSpark(BaseConstraintsRuntimeDdlEnforcement):
    pass


@pytest.mark.skip(
    "TODO: FabricSpark DDL constraint syntax differs from default, needs expected_sql override"
)
class TestIncrementalConstraintsRuntimeDdlEnforcementFabricSpark(
    BaseConstraintsRuntimeDdlEnforcement
):
    pass


@pytest.mark.skip(
    "TODO: FabricSpark DDL constraint syntax differs from default, needs expected_sql override"
)
class TestModelConstraintsRuntimeEnforcementFabricSpark(BaseModelConstraintsRuntimeEnforcement):
    pass


@pytest.mark.skip(
    "TODO: FabricSpark does not enforce NOT NULL constraints at runtime for rollback testing"
)
class TestTableConstraintsRollbackFabricSpark(BaseConstraintsRollback):
    pass


@pytest.mark.skip(
    "TODO: FabricSpark does not enforce NOT NULL constraints at runtime for rollback testing"
)
class TestIncrementalConstraintsRollbackFabricSpark(BaseConstraintsRollback):
    pass
