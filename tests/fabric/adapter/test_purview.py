import pytest

from dbt.adapters.fabric.purview_client import PurviewClient
from dbt.adapters.fabric.purview_sync import PurviewSync
from tests.conftest import requires_purview


def _find_any_table(client: PurviewClient) -> dict | None:
    """Search Purview for any table entity to use in tests."""
    import requests

    url = f"{client._endpoint}/datamap/api/search/query"
    body = {"keywords": "*", "filter": {"objectType": "Tables"}, "limit": 1}
    resp = requests.request("post", url, json=body, headers=client._get_auth_headers())
    if resp.status_code == 200:
        results = resp.json().get("value", [])
        if results:
            return results[0]
    return None


@requires_purview
class TestPurviewEnsureTypeDefinitions:
    def test_registers_type_definitions(self, purview_client: PurviewClient):
        purview_client.ensure_type_definitions()
        assert purview_client._types_ensured

    def test_idempotent_registration(self, purview_client: PurviewClient):
        purview_client._types_ensured = False
        purview_client.ensure_type_definitions()
        purview_client._types_ensured = False
        purview_client.ensure_type_definitions()
        assert purview_client._types_ensured


@requires_purview
class TestPurviewSearchEntities:
    def test_search_finds_known_table(self, purview_client: PurviewClient):
        entity = _find_any_table(purview_client)
        if entity is None:
            pytest.skip("No tables in Purview to search for")

        results = purview_client.search_entities(name=entity["name"])
        assert len(results) >= 1
        assert any(r["id"] == entity["id"] for r in results)

    def test_search_with_database_filter(
        self, purview_client: PurviewClient, fabric_api_client, credentials
    ):
        entity = _find_any_table(purview_client)
        if entity is None:
            pytest.skip("No tables in Purview to search for")

        database = credentials.database
        identifiers = [database]
        for item in fabric_api_client.get_lakehouses() + fabric_api_client.get_warehouses():
            if item["displayName"] == database:
                identifiers.append(item["id"])
                break

        results = purview_client.search_entities(
            name=entity["name"], database_identifiers=identifiers
        )
        assert isinstance(results, list)

    def test_search_nonexistent_returns_empty(self, purview_client: PurviewClient):
        results = purview_client.search_entities(name="nonexistent_table_xyz_12345")
        assert results == []


@requires_purview
class TestPurviewSyncResolveEntities:
    def test_resolve_matches_purview_entity(
        self, purview_client: PurviewClient, fabric_api_client
    ):
        entity = _find_any_table(purview_client)
        if entity is None:
            pytest.skip("No tables in Purview to resolve")

        graph = {"nodes": {}, "sources": {}}
        sync = PurviewSync(purview_client, fabric_api_client, graph)

        node = {
            "unique_id": "model.test.integration_resolve",
            "name": entity["name"],
            "alias": None,
            "schema": "dbo",
            "database": "unknown_db",
            "resource_type": "model",
            "description": "",
            "columns": {},
            "tags": [],
            "meta": {},
            "depends_on": {"nodes": []},
            "config": {"materialized": "table"},
        }

        resolved = sync.resolve_entities([node])
        assert "model.test.integration_resolve" in resolved
        assert resolved["model.test.integration_resolve"]["id"] == entity["id"]


@requires_purview
class TestPurviewSyncBusinessMetadata:
    def test_push_metadata_to_real_entity(self, purview_client: PurviewClient, fabric_api_client):
        purview_client.ensure_type_definitions()

        entity = _find_any_table(purview_client)
        if entity is None:
            pytest.skip("No tables in Purview to push metadata to")

        purview_client.set_business_metadata(
            entity["id"],
            "dbt_metadata",
            {
                "dbt_model_id": "model.test.integration_test",
                "dbt_last_sync": "2026-01-01T00:00:00+00:00",
            },
        )

    def test_push_description_to_real_entity(
        self, purview_client: PurviewClient, fabric_api_client
    ):
        entity = _find_any_table(purview_client)
        if entity is None:
            pytest.skip("No tables in Purview to push description to")

        purview_client.update_entity_description(
            guid=entity["id"],
            type_name=entity["entityType"],
            qualified_name=entity["qualifiedName"],
            name=entity["name"],
            description="Integration test description",
        )
