import time

import pytest

from dbt.adapters.fabric.purview_client import PurviewClient
from dbt.tests.util import run_dbt, write_file
from tests.conftest import requires_purview


def _wait_for_purview_indexing(client: PurviewClient, table_name: str, timeout: int = 300):
    """Poll Purview until a table entity with the given name appears."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        results = client.search_entities(name=table_name)
        if results:
            return results[0]
        time.sleep(10)
    pytest.fail(f"Purview did not index table '{table_name}' within {timeout}s")


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


_BASE_MODEL_SQL = """
{{ config(materialized='table') }}
SELECT 1 AS id, 'hello' AS name
"""
_DERIVED_MODEL_SQL = """
{{ config(materialized='table') }}
SELECT id, name FROM {{ ref('base_model') }}
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
        tests:
          - not_null
      - name: name
        description: "Display name"
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
        tests:
          - not_null
          - unique
      - name: name
        description: "Display name (updated)"
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


@requires_purview
class TestPurviewSync:
    """Full integration test for Purview sync.

    Creates dbt models, runs them, waits for Purview to index the tables,
    then syncs and verifies that metadata, descriptions, and lineage land
    correctly in Purview.
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
    def base_model_entity(self, project, purview_client):
        """Run dbt models and wait for Purview to index base_model."""
        run_dbt(["run"])
        return _wait_for_purview_indexing(purview_client, "base_model")

    @pytest.fixture(scope="class", autouse=True)
    def cleanup_purview(self, purview_client, base_model_entity, project):
        yield
        for name in ("base_model", "derived_model", "no_docs_model"):
            results = purview_client.search_entities(name=name)
            for entity in results:
                guid = entity["id"]
                try:
                    purview_client.delete_business_metadata(guid, "dbt_metadata")
                except Exception:
                    pass
                try:
                    purview_client.update_entity_description(
                        guid=guid,
                        type_name=entity["entityType"],
                        qualified_name=entity["qualifiedName"],
                        name=entity["name"],
                        description="",
                    )
                except Exception:
                    pass
        for proc in purview_client.search_process_entities("dbt://model.test."):
            try:
                purview_client.delete_entity_by_guid(proc["id"])
            except Exception:
                pass

    def test_sync_completes(self, base_model_entity, project):
        run_dbt(["run-operation", "purview_sync"])

    def test_description_landed(self, purview_client, base_model_entity):
        entity_data = purview_client.get_entity_by_guid(base_model_entity["id"])
        desc = entity_data["entity"]["attributes"].get("userDescription", "")
        assert desc == "Base model for Purview integration test"

    def test_business_metadata_landed(self, purview_client, base_model_entity):
        entity_data = purview_client.get_entity_by_guid(base_model_entity["id"])
        bm = entity_data["entity"].get("businessAttributes", {}).get("dbt_metadata", {})
        assert bm["dbt_model_id"] == "model.test.base_model"
        assert "dbt_last_sync" in bm
        assert bm.get("dbt_materialization") == "table"
        assert "not_null" in bm.get("dbt_tests", "")

    def test_lineage_created(self, purview_client):
        processes = purview_client.search_process_entities("dbt://model.test.derived_model")
        assert len(processes) >= 1

    def test_persist_docs_false_skips_model(self, purview_client):
        results = purview_client.search_entities(name="no_docs_model")
        if not results:
            return
        entity_data = purview_client.get_entity_by_guid(results[0]["id"])
        bm = entity_data["entity"].get("businessAttributes", {}).get("dbt_metadata")
        assert bm is None

    def test_selective_flags(self, base_model_entity, project):
        run_dbt(
            [
                "run-operation",
                "purview_sync",
                "--args",
                "{sync_descriptions: true, sync_lineage: false, sync_metadata: true}",
            ]
        )

    def test_update_overwrites(self, project, purview_client, base_model_entity):
        write_file(_SCHEMA_V2, project.project_root, "models", "schema.yml")
        run_dbt(["run"])
        run_dbt(["run-operation", "purview_sync"])

        entity_data = purview_client.get_entity_by_guid(base_model_entity["id"])
        bm = entity_data["entity"].get("businessAttributes", {}).get("dbt_metadata", {})
        desc = entity_data["entity"]["attributes"].get("userDescription", "")

        assert desc == "Updated base model (v2)"
        assert "unique" in bm.get("dbt_tests", "")

    def test_persist_docs_false_does_not_overwrite(
        self, project, purview_client, base_model_entity
    ):
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

        entity_data = purview_client.get_entity_by_guid(base_model_entity["id"])
        desc = entity_data["entity"]["attributes"].get("userDescription", "")
        bm = entity_data["entity"].get("businessAttributes", {}).get("dbt_metadata", {})

        assert desc == "Updated base model (v2)"
        assert "unique" in bm.get("dbt_tests", "")
