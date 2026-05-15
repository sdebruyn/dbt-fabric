import pytest

from dbt.adapters.fabric.purview_client import PurviewClient
from dbt.tests.util import run_dbt, write_file
from tests.conftest import requires_purview


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
    """Validates that dbt metadata lands correctly in Purview entities.

    Uses a model name from a real Purview entity so that purview_sync resolves it.
    The purview_table fixture (session-scoped, from conftest) queries Purview
    independently to break the fixture dependency cycle.
    """

    @pytest.fixture(scope="class")
    def models(self, purview_table):
        name = purview_table["name"]
        return {
            f"{name}.sql": "SELECT 1 AS id, 'test' AS name",
            "schema.yml": (
                "version: 2\n"
                "models:\n"
                f"  - name: {name}\n"
                "    description: 'Integration test description v1'\n"
                "    config:\n"
                "      persist_docs:\n"
                "        relation: true\n"
                "        columns: true\n"
                "    columns:\n"
                "      - name: id\n"
                "        description: 'Primary key'\n"
                "        tests:\n"
                "          - not_null\n"
                "      - name: name\n"
                "        description: 'Display name'\n"
            ),
        }

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
        for proc in purview_client.search_process_entities("dbt://model.test."):
            try:
                purview_client.delete_entity_by_guid(proc["id"])
            except Exception:
                pass

    def test_run_and_sync(self, project):
        run_dbt(["run"])
        run_dbt(["run-operation", "purview_sync"])

    def test_business_metadata_landed(self, purview_client, purview_table):
        entity_data = purview_client.get_entity_by_guid(purview_table["id"])
        bm = entity_data["entity"].get("businessAttributes", {}).get("dbt_metadata", {})
        name = purview_table["name"]
        assert bm["dbt_model_id"] == f"model.test.{name}"
        assert "dbt_last_sync" in bm
        assert bm.get("dbt_materialization") == "table"
        assert "not_null" in bm.get("dbt_tests", "")

    def test_description_landed(self, purview_client, purview_table):
        entity_data = purview_client.get_entity_by_guid(purview_table["id"])
        desc = entity_data["entity"]["attributes"].get("userDescription", "")
        assert desc == "Integration test description v1"

    def test_update_overwrites(self, project, purview_client, purview_table):
        name = purview_table["name"]
        write_file(
            "version: 2\n"
            "models:\n"
            f"  - name: {name}\n"
            "    description: 'Updated description v2'\n"
            "    config:\n"
            "      persist_docs:\n"
            "        relation: true\n"
            "        columns: true\n"
            "    columns:\n"
            "      - name: id\n"
            "        description: 'Updated primary key'\n"
            "        tests:\n"
            "          - not_null\n"
            "          - unique\n"
            "      - name: name\n"
            "        description: 'Updated display name'\n",
            project.project_root,
            "models",
            "schema.yml",
        )
        run_dbt(["run"])
        run_dbt(["run-operation", "purview_sync"])

        entity_data = purview_client.get_entity_by_guid(purview_table["id"])
        bm = entity_data["entity"].get("businessAttributes", {}).get("dbt_metadata", {})
        desc = entity_data["entity"]["attributes"].get("userDescription", "")

        assert desc == "Updated description v2"
        assert "unique" in bm.get("dbt_tests", "")

    def test_persist_docs_false_skips_sync_entirely(self, project, purview_client, purview_table):
        name = purview_table["name"]
        write_file(
            "version: 2\n"
            "models:\n"
            f"  - name: {name}\n"
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

        entity_data = purview_client.get_entity_by_guid(purview_table["id"])
        desc = entity_data["entity"]["attributes"].get("userDescription", "")
        bm = entity_data["entity"].get("businessAttributes", {}).get("dbt_metadata", {})

        # Description and metadata should still be from v2 (previous test), not overwritten
        assert desc == "Updated description v2"
        assert "unique" in bm.get("dbt_tests", "")
