import pytest

from dbt.tests.adapter.constraints.fixtures import (
    my_model_incremental_wrong_name_sql,
    my_model_incremental_wrong_order_sql,
    my_model_wrong_name_sql,
    my_model_wrong_order_sql,
)
from dbt.tests.adapter.constraints.test_constraints import (
    BaseConstraintsColumnsEqual,
    BaseConstraintsRollback,
    BaseConstraintsRuntimeDdlEnforcement,
    BaseIncrementalConstraintsColumnsEqual,
    BaseModelConstraintsRuntimeEnforcement,
    BaseTableConstraintsColumnsEqual,
)

spark_model_schema_yml = """
version: 2
models:
  - name: my_model
    config:
      contract:
        enforced: true
    columns:
      - name: id
        data_type: int
        description: hello
        constraints:
          - type: not_null
          - type: primary_key
          - type: check
            expression: (id > 0)
          - type: check
            expression: id >= 1
        data_tests:
          - unique
      - name: color
        data_type: string
      - name: date_day
        data_type: string
  - name: my_model_error
    config:
      contract:
        enforced: true
    columns:
      - name: id
        data_type: int
        description: hello
        constraints:
          - type: not_null
          - type: primary_key
          - type: check
            expression: (id > 0)
        data_tests:
          - unique
      - name: color
        data_type: string
      - name: date_day
        data_type: string
  - name: my_model_wrong_order
    config:
      contract:
        enforced: true
    columns:
      - name: id
        data_type: int
        description: hello
        constraints:
          - type: not_null
          - type: primary_key
          - type: check
            expression: (id > 0)
        data_tests:
          - unique
      - name: color
        data_type: string
      - name: date_day
        data_type: string
  - name: my_model_wrong_name
    config:
      contract:
        enforced: true
    columns:
      - name: id
        data_type: int
        description: hello
        constraints:
          - type: not_null
          - type: primary_key
          - type: check
            expression: (id > 0)
        data_tests:
          - unique
      - name: color
        data_type: string
      - name: date_day
        data_type: string
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
        return {
            "my_model_wrong_order.sql": my_model_wrong_order_sql,
            "my_model_wrong_name.sql": my_model_wrong_name_sql,
            "constraints_schema.yml": spark_model_schema_yml,
        }

    @pytest.mark.skip("TODO: Delta Lake does not support NOT NULL constraints in CTAS")
    def test__constraints_wrong_column_order(self, project):
        pass

    @pytest.mark.skip(
        "TODO: Delta Lake does not support NOT NULL constraints in CTAS,"
        " preventing data type mismatch detection"
    )
    def test__constraints_wrong_column_data_types(
        self, project, string_type, int_type, schema_string_type, schema_int_type, data_types
    ):
        pass


class TestIncrementalConstraintsColumnsEqualFabricSpark(
    FabricSparkConstraintsTypesMixin, BaseIncrementalConstraintsColumnsEqual
):
    @pytest.fixture(scope="class")
    def models(self):
        return {
            "my_model_wrong_order.sql": my_model_incremental_wrong_order_sql,
            "my_model_wrong_name.sql": my_model_incremental_wrong_name_sql,
            "constraints_schema.yml": spark_model_schema_yml,
        }

    @pytest.mark.skip("TODO: Delta Lake does not support NOT NULL constraints in CTAS")
    def test__constraints_wrong_column_order(self, project):
        pass

    @pytest.mark.skip(
        "TODO: Delta Lake does not support NOT NULL constraints in CTAS,"
        " preventing data type mismatch detection"
    )
    def test__constraints_wrong_column_data_types(
        self, project, string_type, int_type, schema_string_type, schema_int_type, data_types
    ):
        pass


class TestTableConstraintsColumnsEqualFabricSpark(
    FabricSparkConstraintsTypesMixin, BaseTableConstraintsColumnsEqual
):
    @pytest.fixture(scope="class")
    def models(self):
        return {
            "my_model_wrong_order.sql": my_model_wrong_order_sql,
            "my_model_wrong_name.sql": my_model_wrong_name_sql,
            "constraints_schema.yml": spark_model_schema_yml,
        }

    @pytest.mark.skip("TODO: Delta Lake does not support NOT NULL constraints in CTAS")
    def test__constraints_wrong_column_order(self, project):
        pass

    @pytest.mark.skip(
        "TODO: Delta Lake does not support NOT NULL constraints in CTAS,"
        " preventing data type mismatch detection"
    )
    def test__constraints_wrong_column_data_types(
        self, project, string_type, int_type, schema_string_type, schema_int_type, data_types
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
