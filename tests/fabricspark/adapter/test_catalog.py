import pytest

from dbt.artifacts.schemas.catalog import CatalogArtifact
from dbt.tests.adapter.catalog import files
from dbt.tests.adapter.catalog.relation_types import CatalogRelationTypes
from dbt.tests.adapter.catalog_integrations.test_catalog_integration import (
    BaseCatalogIntegrationValidation,
)

MY_MATERIALIZED_VIEW_FROM_SEED = """\
{{ config(
    materialized='materialized_view',
) }}
select *
from {{ ref('my_seed') }}
"""


class TestCatalogRelationTypesFabricSpark(CatalogRelationTypes):
    @pytest.fixture(scope="class", autouse=True)
    def models(self):
        yield {
            "my_table.sql": files.MY_TABLE,
            "my_materialized_view.sql": files.MY_MATERIALIZED_VIEW,
            "my_materialized_view_2.sql": MY_MATERIALIZED_VIEW_FROM_SEED,
        }

    @pytest.mark.parametrize(
        "node_name,relation_type",
        [
            ("seed.test.my_seed", "table"),
            ("model.test.my_table", "table"),
            ("model.test.my_materialized_view", "materialized_view"),
            ("model.test.my_materialized_view_2", "materialized_view"),
        ],
    )
    def test_relation_types_populate_correctly(
        self, docs: CatalogArtifact, node_name: str, relation_type: str
    ):
        super().test_relation_types_populate_correctly(docs, node_name, relation_type)


class TestCatalogIntegrationValidationFabricSpark(BaseCatalogIntegrationValidation):
    pass
