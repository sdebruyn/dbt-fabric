import pytest

from dbt.adapters.fabric.fabric_api_client import FabricApiClient
from dbt.adapters.fabric.purview_client import PurviewClient
from dbt.adapters.fabric.purview_sync import _FABRIC_GROUPS_URL
from dbt.tests.util import run_dbt, write_file
from tests.conftest import requires_purview

_CUSTOM_RELATIONSHIP_TYPES = [
    "fabric_warehouse_table_columns",
    "fabric_warehouse_table_schemas",
    "fabric_warehouse_schema_warehouses",
]
_CUSTOM_ENTITY_TYPES = [
    "fabric_warehouse_table_column",
    "fabric_warehouse_table",
    "fabric_warehouse_schema",
    "dbt_transformation",
]
_CUSTOM_BM_TYPES = ["dbt_metadata"]


def _cleanup_custom_types(client: PurviewClient) -> None:
    """Best-effort deletion of custom Purview type definitions.

    Deletion order: relationships first (they reference entity types),
    then entity types, then business metadata types.
    May fail if entities of these types still exist.
    """
    for name in _CUSTOM_RELATIONSHIP_TYPES:
        client.delete_type_def_by_name(name)
    for name in _CUSTOM_ENTITY_TYPES:
        client.delete_type_def_by_name(name)
    for name in _CUSTOM_BM_TYPES:
        client.delete_type_def_by_name(name)


def _build_warehouse_qn(workspace_id: str, warehouse_id: str) -> str:
    return f"{_FABRIC_GROUPS_URL}/{workspace_id}/warehouses/{warehouse_id}"


def _cleanup_test_entities(
    client: PurviewClient,
    workspace_id: str,
    warehouse_id: str,
    schema: str,
    table_names: list[str],
) -> None:
    """Delete all test entities from Purview: process, columns, tables, schema.

    Uses direct qualified-name lookups (not search) so cleanup works even
    immediately after creation (bypasses eventually-consistent search index).
    """
    wh_qn = _build_warehouse_qn(workspace_id, warehouse_id)

    for name in table_names:
        _delete_entity_if_exists(client, "dbt_transformation", f"dbt://model.test.{name}")

    for name in table_names:
        table_qn = f"{wh_qn}/schemas/{schema}/tables/{name}"
        table_result = client.get_entity_by_qualified_name("fabric_warehouse_table", table_qn)
        if table_result and "entity" in table_result:
            for col_guid in table_result.get("referredEntities", {}):
                try:
                    client.delete_entity_by_guid(col_guid)
                except Exception:
                    pass

    for name in table_names:
        _delete_entity_if_exists(
            client, "fabric_warehouse_table", f"{wh_qn}/schemas/{schema}/tables/{name}"
        )

    _delete_entity_if_exists(client, "fabric_warehouse_schema", f"{wh_qn}/schemas/{schema}")

    for proc in client.search_process_entities("dbt://model.test."):
        try:
            client.delete_entity_by_guid(proc["id"])
        except Exception:
            pass


def _delete_entity_if_exists(client: PurviewClient, type_name: str, qualified_name: str) -> None:
    result = client.get_entity_by_qualified_name(type_name, qualified_name)
    if result and "entity" in result:
        try:
            client.delete_entity_by_guid(result["entity"]["guid"])
        except Exception:
            pass


@requires_purview
class TestPurviewEnsureTypeDefinitions:
    """Test custom type definition registration from a clean state.

    Deletes existing custom types before testing so the POST (creation) path
    is exercised, not just the PUT (update) path.
    """

    @pytest.fixture(scope="class", autouse=True)
    def clean_types(self, purview_client: PurviewClient):
        _cleanup_custom_types(purview_client)
        yield

    def test_creates_and_verifies_type_definitions(self, purview_client: PurviewClient):
        purview_client._types_ensured = False
        assert purview_client.ensure_type_definitions()

        for name in _CUSTOM_ENTITY_TYPES + _CUSTOM_BM_TYPES:
            td = purview_client.get_type_def_by_name(name)
            assert td is not None, f"Type {name} not found after registration"

    def test_idempotent_registration(self, purview_client: PurviewClient):
        purview_client._types_ensured = False
        assert purview_client.ensure_type_definitions()
        purview_client._types_ensured = False
        assert purview_client.ensure_type_definitions()
        assert purview_client._types_ensured


_BASE_MODEL_SQL = """
{{ config(materialized='table') }}
SELECT 1 AS id, 'hello' AS name, CAST(GETDATE() AS datetime2(6)) AS created_at
"""
_DERIVED_MODEL_SQL = """
{{ config(materialized='table') }}
SELECT id, name, created_at FROM {{ ref('base_model') }}
"""
_NO_DOCS_MODEL_SQL = """
{{ config(materialized='table') }}
SELECT 42 AS value
"""

_SCHEMA_V1 = """\
version: 2
models:
  - name: base_model
    description: "Base model for Purview integration test"
    columns:
      - name: id
        description: "Primary key"
        data_type: int
        tests:
          - not_null
      - name: name
        description: "Display name"
        data_type: varchar
  - name: derived_model
    description: "Derived model referencing base"
  - name: no_docs_model
    description: "This description should NOT be synced to Purview"
    config:
      persist_docs:
        relation: false
        columns: false
    columns:
      - name: value
        description: "This column description should NOT be synced"
"""

_SCHEMA_V2 = """\
version: 2
models:
  - name: base_model
    description: "Updated base model (v2)"
    columns:
      - name: id
        description: "Primary key (updated)"
        data_type: int
        tests:
          - not_null
          - unique
      - name: name
        description: "Display name (updated)"
        data_type: varchar
        tests:
          - not_null
  - name: derived_model
    description: "Updated derived model (v2)"
    columns:
      - name: id
        tests:
          - not_null
  - name: no_docs_model
    description: "Still should NOT be synced"
    config:
      persist_docs:
        relation: false
        columns: false
"""

_TABLE_NAMES = ["base_model", "derived_model", "no_docs_model"]


@requires_purview
class TestPurviewSync:
    """Full integration test for Purview sync.

    Creates dbt models, runs them, then syncs metadata to Purview.
    Cleans up all created entities both before (stale state from previous runs)
    and after the test class.
    """

    @pytest.fixture(scope="class")
    def models(self):
        return {
            "base_model.sql": _BASE_MODEL_SQL,
            "derived_model.sql": _DERIVED_MODEL_SQL,
            "no_docs_model.sql": _NO_DOCS_MODEL_SQL,
            "schema.yml": _SCHEMA_V1,
        }

    @pytest.fixture(scope="class")
    def warehouse_info(self, fabric_api_client: FabricApiClient, project):
        workspace_id = fabric_api_client.get_workspace_id()
        warehouses = fabric_api_client.get_warehouses()
        warehouse_id = next(wh["id"] for wh in warehouses if wh["displayName"] == project.database)
        return workspace_id, warehouse_id

    @pytest.fixture(scope="class")
    def synced_entities(self, project, purview_client, warehouse_info):
        """Run dbt models and sync to Purview, then look up created entities.

        Cleans up stale entities from previous runs before syncing.
        Uses get_entity_by_qualified_name (bypasses eventually-consistent search index).
        """
        workspace_id, warehouse_id = warehouse_info
        schema = project.test_schema

        _cleanup_test_entities(purview_client, workspace_id, warehouse_id, schema, _TABLE_NAMES)

        run_dbt(["run"])
        run_dbt(["run-operation", "purview_sync"])

        entities = {}
        for name in _TABLE_NAMES:
            qn = (
                f"{_FABRIC_GROUPS_URL}/{workspace_id}/warehouses/{warehouse_id}"
                f"/schemas/{schema}/tables/{name}"
            )
            result = purview_client.get_entity_by_qualified_name("fabric_warehouse_table", qn)
            if result and "entity" in result:
                entity = result["entity"]
                entities[name] = {
                    "id": entity["guid"],
                    "name": entity["attributes"].get("name", name),
                    "entityType": entity["typeName"],
                    "qualifiedName": entity["attributes"]["qualifiedName"],
                }
        return entities

    @pytest.fixture(scope="class", autouse=True)
    def cleanup_purview(self, purview_client, synced_entities, warehouse_info, project):
        yield
        workspace_id, warehouse_id = warehouse_info
        _cleanup_test_entities(
            purview_client, workspace_id, warehouse_id, project.test_schema, _TABLE_NAMES
        )

    def test_sync_creates_entities(self, synced_entities):
        assert "base_model" in synced_entities
        assert "derived_model" in synced_entities

    def test_description_landed(self, purview_client, synced_entities):
        entity = synced_entities["base_model"]
        entity_data = purview_client.get_entity_by_guid(entity["id"])
        desc = entity_data["entity"]["attributes"].get("userDescription", "")
        assert desc == "Base model for Purview integration test"

    def test_column_entities_created(self, purview_client, synced_entities):
        entity = synced_entities["base_model"]
        entity_data = purview_client.get_entity_by_guid(entity["id"])
        referred = entity_data.get("referredEntities", {})

        col_names = {
            e["attributes"]["name"]: e
            for e in referred.values()
            if "column" in e.get("typeName", "").lower()
        }
        assert "id" in col_names, "Column 'id' not found"
        assert "name" in col_names, "Column 'name' not found"

        id_col = col_names["id"]
        assert id_col["attributes"].get("userDescription") == "Primary key"

        name_col = col_names["name"]
        assert name_col["attributes"].get("userDescription") == "Display name"

    def test_undocumented_columns_discovered_from_catalog(self, purview_client, synced_entities):
        """Columns not in dbt YAML should still appear in Purview from catalog discovery."""
        entity = synced_entities["base_model"]
        entity_data = purview_client.get_entity_by_guid(entity["id"])
        referred = entity_data.get("referredEntities", {})

        col_names = {
            e["attributes"]["name"]: e
            for e in referred.values()
            if "column" in e.get("typeName", "").lower()
        }
        assert "created_at" in col_names, (
            "Undocumented column 'created_at' should be discovered from catalog"
        )
        created_at = col_names["created_at"]
        assert created_at["attributes"].get("data_type"), (
            "Catalog-discovered column should have a data_type"
        )
        assert "userDescription" not in created_at["attributes"] or not created_at[
            "attributes"
        ].get("userDescription"), "Undocumented column should not have a description"

    def test_business_metadata_landed(self, purview_client, synced_entities):
        entity = synced_entities["base_model"]
        entity_data = purview_client.get_entity_by_guid(entity["id"])
        bm = entity_data["entity"].get("businessAttributes", {}).get("dbt_metadata", {})
        assert bm["dbt_model_id"] == "model.test.base_model"
        assert "dbt_last_sync" in bm
        assert bm.get("dbt_materialization") == "table"
        assert "not_null" in bm.get("dbt_tests", "")

    def test_lineage_created(self, purview_client):
        result = purview_client.get_entity_by_qualified_name(
            "dbt_transformation", "dbt://model.test.derived_model"
        )
        assert result is not None and "entity" in result

    def test_persist_docs_false_skips_model(self, purview_client, synced_entities):
        if "no_docs_model" not in synced_entities:
            return
        entity_data = purview_client.get_entity_by_guid(synced_entities["no_docs_model"]["id"])
        bm = entity_data["entity"].get("businessAttributes", {}).get("dbt_metadata")
        assert bm is None

    def test_selective_flags(self, synced_entities, project):
        run_dbt(
            [
                "run-operation",
                "purview_sync",
                "--args",
                "{sync_descriptions: true, sync_lineage: false, sync_metadata: true}",
            ]
        )

    def test_update_overwrites(self, project, purview_client, synced_entities):
        write_file(_SCHEMA_V2, project.project_root, "models", "schema.yml")
        run_dbt(["run"])
        run_dbt(["run-operation", "purview_sync"])

        entity = synced_entities["base_model"]
        entity_data = purview_client.get_entity_by_guid(entity["id"])
        bm = entity_data["entity"].get("businessAttributes", {}).get("dbt_metadata", {})
        desc = entity_data["entity"]["attributes"].get("userDescription", "")

        assert desc == "Updated base model (v2)"
        assert "unique" in bm.get("dbt_tests", "")

    def test_persist_docs_false_does_not_overwrite(self, project, purview_client, synced_entities):
        write_file(
            "version: 2\n"
            "models:\n"
            "  - name: base_model\n"
            "    description: 'Should NOT be synced'\n"
            "    config:\n"
            "      persist_docs:\n"
            "        relation: false\n"
            "        columns: false\n",
            project.project_root,
            "models",
            "schema.yml",
        )
        run_dbt(["run"])
        run_dbt(["run-operation", "purview_sync"])

        entity = synced_entities["base_model"]
        entity_data = purview_client.get_entity_by_guid(entity["id"])
        desc = entity_data["entity"]["attributes"].get("userDescription", "")
        bm = entity_data["entity"].get("businessAttributes", {}).get("dbt_metadata", {})

        assert desc == "Updated base model (v2)"
        assert "unique" in bm.get("dbt_tests", "")
