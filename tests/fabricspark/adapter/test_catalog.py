from dbt.tests.adapter.catalog.relation_types import CatalogRelationTypes
from dbt.tests.adapter.catalog_integrations.test_catalog_integration import (
    BaseCatalogIntegrationValidation,
)


class TestCatalogRelationTypesFabricSpark(CatalogRelationTypes):
    pass


class TestCatalogIntegrationValidationFabricSpark(BaseCatalogIntegrationValidation):
    pass
