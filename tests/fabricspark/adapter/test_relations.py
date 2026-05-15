from dbt.tests.adapter.relations.test_changing_relation_type import (
    BaseChangeRelationTypeValidator,
)
from dbt.tests.adapter.relations.test_dropping_schema_named import BaseDropSchemaNamed


class TestChangeRelationTypesFabricSpark(BaseChangeRelationTypeValidator):
    def test_changing_materialization_changes_relation_type(self, project):
        self._run_and_check_materialization("materialized_view")
        self._run_and_check_materialization("table")
        self._run_and_check_materialization("materialized_view")
        self._run_and_check_materialization("table", extra_args=["--full-refresh"])


class TestDropSchemaNamedFabricSpark(BaseDropSchemaNamed):
    pass
