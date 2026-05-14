import pytest

from dbt.tests.adapter.relations.test_changing_relation_type import (
    BaseChangeRelationTypeValidator,
)
from dbt.tests.adapter.relations.test_dropping_schema_named import BaseDropSchemaNamed


@pytest.mark.skip(
    "TODO: FabricSpark relation type changes between table and materialized_view need custom handling"
)
class TestChangeRelationTypesFabricSpark(BaseChangeRelationTypeValidator):
    pass


class TestDropSchemaNamedFabricSpark(BaseDropSchemaNamed):
    pass
