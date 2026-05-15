import os

import pytest
import requests

from dbt.adapters.fabric.purview_client import PurviewClient
from dbt.adapters.fabric.purview_sync import PurviewSync, extract_syncable_models
from dbt.tests.util import run_dbt, write_file
from tests.conftest import requires_purview


def _find_any_table(client: PurviewClient) -> dict | None:
    """Search Purview for any table entity to use in tests."""
    url = f"{client._endpoint}/datamap/api/search/query"
    body = {"keywords": "*", "filter": {"objectType": "Tables"}, "limit": 1}
    resp = requests.request("post", url, json=body, headers=client._get_auth_headers())
    if resp.status_code == 200:
        results = resp.json().get("value", [])
        if results:
            return results[0]
    return None


def _find_test_process_entities(client: PurviewClient) -> list[dict]:
    """Find dbt_transformation process entities created by tests."""
    url = f"{client._endpoint}/datamap/api/search/query"
    body = {"keywords": None, "filter": {"and": [{"objectType": "Process"}]}, "limit": 100}
    resp = requests.request("post", url, json=body, headers=client._get_auth_headers())
    if resp.status_code == 200:
        return [
            r
            for r in resp.json().get("value", [])
            if r.get("qualifiedName", "").startswith("dbt://model.test.")
        ]
    return []


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


_BASE_MODEL_SQL = "SELECT 1 AS id, 'hello' AS name"
_DERIVED_MODEL_SQL = "SELECT id, name FROM {{ ref('base_model') }}"
_NO_DOCS_MODEL_SQL = "SELECT 42 AS value"

_SCHEMA_V1 = """\
version: 2
models:
  - name: base_model
    description: "Base model for Purview integration test"
    config:
      persist_docs:
        relation: true
        columns: true
    columns:
      - name: id
        description: "Primary key"
        tests:
          - not_null
      - name: name
        description: "Display name"
  - name: derived_model
    description: "Derived model referencing base"
    config:
      persist_docs:
        relation: true
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
    config:
      persist_docs:
        relation: true
        columns: true
    columns:
      - name: id
        description: "Primary key (updated)"
        tests:
          - not_null
          - unique
      - name: name
        description: "Display name (updated)"
        tests:
          - not_null
  - name: derived_model
    description: "Updated derived model (v2)"
    config:
      persist_docs:
        relation: true
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


@requires_purview
class TestPurviewProjectFlow:
    """Runs a full dbt project with models, tests, and purview_sync via run-operation."""

    @pytest.fixture(scope="class")
    def models(self):
        return {
            "base_model.sql": _BASE_MODEL_SQL,
            "derived_model.sql": _DERIVED_MODEL_SQL,
            "no_docs_model.sql": _NO_DOCS_MODEL_SQL,
            "schema.yml": _SCHEMA_V1,
        }

    def test_dbt_run_succeeds(self, project):
        results = run_dbt(["run"])
        assert len(results) == 3

    def test_dbt_test_succeeds(self, project):
        results = run_dbt(["test"])
        assert len(results) >= 1

    def test_purview_sync_completes(self, project):
        run_dbt(["run-operation", "purview_sync"])

    def test_purview_sync_selective_flags(self, project):
        run_dbt(
            [
                "run-operation",
                "purview_sync",
                "--args",
                "{sync_descriptions: true, sync_lineage: false, sync_metadata: true}",
            ]
        )

    def test_updated_project_syncs(self, project):
        write_file(_SCHEMA_V2, project.project_root, "models", "schema.yml")
        results = run_dbt(["run"])
        assert len(results) == 3
        run_dbt(["run-operation", "purview_sync"])


@requires_purview
class TestPurviewMetadataSync:
    """Validates that dbt metadata actually lands correctly in Purview entities."""

    @pytest.fixture(scope="class")
    def purview_table(self, purview_client):
        entity = _find_any_table(purview_client)
        if entity is None:
            pytest.skip("No tables indexed in Purview")
        return entity

    @pytest.fixture(scope="class")
    def models(self):
        return {"_placeholder.sql": "SELECT 1 AS id"}

    @pytest.fixture(scope="class", autouse=True)
    def cleanup_purview(self, purview_client, purview_table, project):
        """Remove all dbt artifacts from the Purview entity after tests."""
        yield
        guid = purview_table["id"]
        try:
            purview_client.delete_business_metadata(guid, "dbt_metadata")
        except Exception:
            pass
        try:
            purview_client.update_entity_description(
                guid=guid,
                type_name=purview_table["entityType"],
                qualified_name=purview_table["qualifiedName"],
                name=purview_table["name"],
                description="",
            )
        except Exception:
            pass
        for proc in _find_test_process_entities(purview_client):
            try:
                purview_client.delete_entity_by_guid(proc["id"])
            except Exception:
                pass

    def _make_graph(self, table_name, description="", tags=None, tests=None, persist_docs=None):
        model_id = f"model.test.{table_name}"
        if persist_docs is None:
            persist_docs = {"relation": True, "columns": True}

        nodes = {
            model_id: {
                "unique_id": model_id,
                "name": table_name,
                "alias": None,
                "schema": "dbo",
                "database": os.getenv("FABRIC_TEST_DWH_NAME", ""),
                "resource_type": "model",
                "description": description,
                "columns": {"id": {"name": "id", "description": "Primary key"}},
                "tags": tags or [],
                "meta": {},
                "depends_on": {"nodes": []},
                "config": {"materialized": "table", "persist_docs": persist_docs},
            },
        }
        if tests:
            for t in tests:
                tid = f"test.test.{t}"
                nodes[tid] = {
                    "unique_id": tid,
                    "name": t,
                    "resource_type": "test",
                    "depends_on": {"nodes": [model_id]},
                }
        return {"nodes": nodes, "sources": {}}

    def _sync(self, purview_client, fabric_api_client, graph):
        models = extract_syncable_models(graph)
        sync = PurviewSync(purview_client, fabric_api_client, graph)
        resolved = sync.resolve_entities(models)
        return sync, models, resolved

    def test_pushes_business_metadata(self, purview_client, fabric_api_client, purview_table):
        purview_client.ensure_type_definitions()
        name = purview_table["name"]
        graph = self._make_graph(
            name,
            description="Metadata test",
            tags=["integration-test", "ci"],
            tests=["not_null_id", "unique_id"],
        )

        sync, models, resolved = self._sync(purview_client, fabric_api_client, graph)
        if f"model.test.{name}" not in resolved:
            pytest.skip("Entity not resolvable in Purview")

        sync.push_business_metadata(models, resolved)

        entity_data = purview_client.get_entity_by_guid(purview_table["id"])
        bm = entity_data["entity"].get("businessAttributes", {}).get("dbt_metadata", {})

        assert bm["dbt_model_id"] == f"model.test.{name}"
        assert "dbt_last_sync" in bm
        assert bm["dbt_tags"] == "integration-test,ci"
        assert bm["dbt_materialization"] == "table"
        assert "not_null_id" in bm.get("dbt_tests", "")
        assert "unique_id" in bm.get("dbt_tests", "")

    def test_pushes_description(self, purview_client, fabric_api_client, purview_table):
        name = purview_table["name"]
        graph = self._make_graph(name, description="Integration test: description push")

        sync, models, resolved = self._sync(purview_client, fabric_api_client, graph)
        if not resolved:
            pytest.skip("Entity not resolvable in Purview")

        sync.push_descriptions(models, resolved)

        entity_data = purview_client.get_entity_by_guid(purview_table["id"])
        desc = entity_data["entity"]["attributes"].get("userDescription", "")
        assert desc == "Integration test: description push"

    def test_update_overwrites_previous_sync(
        self, purview_client, fabric_api_client, purview_table
    ):
        purview_client.ensure_type_definitions()
        name = purview_table["name"]

        graph_v1 = self._make_graph(name, description="Version 1", tags=["v1"])
        sync_v1, models_v1, resolved_v1 = self._sync(purview_client, fabric_api_client, graph_v1)
        if not resolved_v1:
            pytest.skip("Entity not resolvable in Purview")
        sync_v1.push_descriptions(models_v1, resolved_v1)
        sync_v1.push_business_metadata(models_v1, resolved_v1)

        graph_v2 = self._make_graph(
            name,
            description="Version 2",
            tags=["v2", "updated"],
            tests=["unique_check"],
        )
        sync_v2, models_v2, resolved_v2 = self._sync(purview_client, fabric_api_client, graph_v2)
        sync_v2.push_descriptions(models_v2, resolved_v2)
        sync_v2.push_business_metadata(models_v2, resolved_v2)

        entity_data = purview_client.get_entity_by_guid(purview_table["id"])
        bm = entity_data["entity"].get("businessAttributes", {}).get("dbt_metadata", {})
        desc = entity_data["entity"]["attributes"].get("userDescription", "")

        assert desc == "Version 2"
        assert bm["dbt_tags"] == "v2,updated"
        assert "unique_check" in bm.get("dbt_tests", "")

    def test_persist_docs_false_skips_description(
        self, purview_client, fabric_api_client, purview_table
    ):
        name = purview_table["name"]

        graph_with = self._make_graph(name, description="Should persist")
        sync_with, models_with, resolved_with = self._sync(
            purview_client, fabric_api_client, graph_with
        )
        if not resolved_with:
            pytest.skip("Entity not resolvable in Purview")
        sync_with.push_descriptions(models_with, resolved_with)

        graph_without = self._make_graph(
            name,
            description="Should NOT be pushed",
            persist_docs={"relation": False, "columns": False},
        )
        sync_without, models_without, resolved_without = self._sync(
            purview_client, fabric_api_client, graph_without
        )
        sync_without.push_descriptions(models_without, resolved_without)

        entity_data = purview_client.get_entity_by_guid(purview_table["id"])
        desc = entity_data["entity"]["attributes"].get("userDescription", "")
        assert desc == "Should persist"

    def test_persist_docs_false_still_pushes_business_metadata(
        self, purview_client, fabric_api_client, purview_table
    ):
        purview_client.ensure_type_definitions()
        name = purview_table["name"]

        graph = self._make_graph(
            name,
            description="Should NOT land in Purview",
            tags=["persist-docs-false"],
            persist_docs={"relation": False, "columns": False},
        )
        sync, models, resolved = self._sync(purview_client, fabric_api_client, graph)
        if not resolved:
            pytest.skip("Entity not resolvable in Purview")

        sync.push_descriptions(models, resolved)
        sync.push_business_metadata(models, resolved)

        entity_data = purview_client.get_entity_by_guid(purview_table["id"])
        bm = entity_data["entity"].get("businessAttributes", {}).get("dbt_metadata", {})
        desc = entity_data["entity"]["attributes"].get("userDescription", "")

        assert bm["dbt_tags"] == "persist-docs-false"
        assert desc != "Should NOT land in Purview"
