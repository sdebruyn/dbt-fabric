import json
from datetime import datetime, timezone

from dbt.adapters.events.logging import AdapterLogger
from dbt.adapters.fabric.fabric_api_client import FabricApiClient
from dbt.adapters.fabric.purview_client import PurviewClient

logger = AdapterLogger("fabric")


def extract_syncable_models(graph: dict, results: list | None = None) -> list[dict]:
    """Extract models, seeds, and snapshots from the dbt graph that should be synced to Purview.

    This is the first step in the sync flow (called before PurviewSync.resolve_entities).
    When results are provided (e.g. from an on-run-end hook), only nodes that actually
    ran in this invocation are included. When results is None (e.g. a manual run-operation),
    all syncable nodes in the graph are returned.
    """
    syncable_types = ("model", "seed", "snapshot")
    models = []

    ran_node_ids: set[str] | None = None
    if results is not None:
        ran_node_ids = set()
        for r in results:
            node = r.node if hasattr(r, "node") else r.get("node", {})
            uid = node.unique_id if hasattr(node, "unique_id") else node.get("unique_id", "")
            if uid:
                ran_node_ids.add(uid)

    nodes = graph.nodes if hasattr(graph, "nodes") else graph.get("nodes", {})
    if hasattr(nodes, "values"):
        node_iter = nodes.values()
    else:
        node_iter = nodes if isinstance(nodes, list) else []

    for node in node_iter:
        resource_type = (
            node.resource_type if hasattr(node, "resource_type") else node.get("resource_type", "")
        )
        if resource_type not in syncable_types:
            continue

        unique_id = node.unique_id if hasattr(node, "unique_id") else node.get("unique_id", "")
        if ran_node_ids is not None and unique_id not in ran_node_ids:
            continue

        if not _has_persist_docs_enabled(node):
            continue

        models.append(node)

    return models


def _has_persist_docs_enabled(node) -> bool:
    """Check whether a node's persist_docs config allows Purview sync.

    Returns True (sync) when persist_docs is absent or has any true value.
    Returns False (skip) only when persist_docs is explicitly configured with all values false.
    """
    config = (
        getattr(node, "config", {})
        if hasattr(node, "config")
        else node.get("config", {})
        if isinstance(node, dict)
        else getattr(node, "config", {})
    )
    persist_docs = (
        config.get("persist_docs")
        if isinstance(config, dict)
        else getattr(config, "persist_docs", None)
    )
    if not persist_docs:
        return True
    if isinstance(persist_docs, dict):
        relation = persist_docs.get("relation", True)
        columns = persist_docs.get("columns", True)
        return relation or columns
    return getattr(persist_docs, "relation", True) or getattr(persist_docs, "columns", True)


def _get_attr(node: object, key: str, default=None):
    """Read an attribute from a dbt node, supporting both object and dict representations."""
    if hasattr(node, key):
        return getattr(node, key, default)
    if isinstance(node, dict):
        return node.get(key, default)
    return default


def _get_node_name(node: object) -> str:
    return _get_attr(node, "alias") or _get_attr(node, "name", "")


def _get_node_schema(node: object) -> str:
    return _get_attr(node, "schema", "")


def _get_node_database(node: object) -> str:
    return _get_attr(node, "database", "")


def _make_cache_key(database: str, schema: str, name: str) -> str:
    return f"{database}.{schema}.{name}".lower()


class PurviewSync:
    """Orchestrates syncing dbt metadata to Purview: descriptions, business metadata, and lineage.

    Entry point is BaseFabricAdapter.purview_sync(), which is called from the
    {{ purview_sync() }} Jinja macro (typically as an on-run-end hook). The flow is:

        1. extract_syncable_models() — filters the dbt graph to models/seeds/snapshots
        2. resolve_entities() — matches each dbt node to a Purview entity by searching
           on table name and filtering on the Fabric item GUID (resolved via FabricApiClient)
        3. push_descriptions() — writes model and column descriptions to Purview
        4. push_business_metadata() — attaches dbt tags, materialization, test results, etc.
           Test names are derived from the graph: test nodes list their dependencies, so we
           build a reverse mapping of model → test names at init time.
        5. push_lineage() — creates dbt_transformation process entities for upstream
           dependencies, including both model-to-model and source-to-model edges. Source
           entities are resolved lazily from graph["sources"] when encountered as dependencies.

    The graph parameter is the dbt flat_graph dict (available as {{ graph }} in Jinja macros),
    containing all nodes (models, tests, seeds, snapshots) and sources in the project.

    The FabricApiClient is needed because Purview qualifiedNames for Lakehouse tables
    contain the Fabric item GUID (not the human-readable name). This class resolves
    Lakehouse/Warehouse names to GUIDs so search results can be filtered accurately.
    """

    def __init__(self, client: PurviewClient, fabric_client: FabricApiClient, graph: dict) -> None:
        self._client = client
        self._fabric_client = fabric_client
        self._graph = graph
        self._entity_cache: dict[str, dict] = {}
        self._item_id_cache: dict[str, str] = {}
        self._lakehouses: list[dict] | None = None
        self._warehouses: list[dict] | None = None
        self._test_mapping = self._build_test_mapping()

    def _resolve_item_id(self, database: str) -> str | None:
        """Resolve a Fabric item name (Lakehouse or Data Warehouse) to its GUID."""
        if database in self._item_id_cache:
            return self._item_id_cache[database]

        if self._lakehouses is None:
            self._lakehouses = self._fabric_client.get_lakehouses()
        for lh in self._lakehouses:
            if lh["displayName"] == database:
                self._item_id_cache[database] = lh["id"]
                return lh["id"]

        if self._warehouses is None:
            self._warehouses = self._fabric_client.get_warehouses()
        for wh in self._warehouses:
            if wh["displayName"] == database:
                self._item_id_cache[database] = wh["id"]
                return wh["id"]

        return None

    def _database_identifiers(self, database: str) -> list[str]:
        """Build a list of identifiers for a database: its name and its Fabric item GUID."""
        identifiers = [database]
        item_id = self._resolve_item_id(database)
        if item_id:
            identifiers.append(item_id)
        return identifiers

    def _build_test_mapping(self) -> dict[str, list[str]]:
        """Build a mapping of model/seed/snapshot unique_id to test names from the graph.

        Walks all nodes in the graph, finds test nodes, and maps each test back to the
        models/seeds/snapshots it depends on via depends_on.nodes.
        """
        mapping: dict[str, list[str]] = {}
        nodes = self._graph.get("nodes", {})
        node_iter = nodes.values() if hasattr(nodes, "values") else []

        syncable_prefixes = ("model.", "seed.", "snapshot.")
        for node in node_iter:
            if _get_attr(node, "resource_type", "") != "test":
                continue

            test_name = _get_attr(node, "name", "")
            if not test_name:
                continue

            depends_on = _get_attr(node, "depends_on", {})
            dep_nodes = (
                depends_on.get("nodes", [])
                if isinstance(depends_on, dict)
                else _get_attr(depends_on, "nodes", [])
            )

            for dep_id in dep_nodes:
                if any(dep_id.startswith(p) for p in syncable_prefixes):
                    mapping.setdefault(dep_id, []).append(test_name)

        return mapping

    def _pick_best_entity(self, results: list[dict], db_ids: list[str] | None) -> dict:
        """Pick the best Purview entity from search results, preferring database ID matches."""
        if len(results) == 1 or not db_ids:
            return results[0]

        lower_ids = [i.lower() for i in db_ids]
        for r in results:
            qn = r.get("qualifiedName", "").lower()
            if any(i in qn for i in lower_ids):
                return r

        return results[0]

    def resolve_entities(self, models: list) -> dict[str, dict]:
        """Match dbt models to Purview entities by searching on name and database.

        Returns a dict mapping both unique_id and cache_key (database.schema.name) to
        the Purview search result for each matched entity.
        """
        cache: dict[str, dict] = {}

        for model in models:
            name = _get_node_name(model)
            schema = _get_node_schema(model)
            database = _get_node_database(model)
            unique_id = _get_attr(model, "unique_id", "")

            if not name:
                continue

            cache_key = _make_cache_key(database, schema, name)
            if cache_key in cache:
                cache[unique_id] = cache[cache_key]
                continue

            db_ids = self._database_identifiers(database) if database else None
            results = self._client.search_entities(name=name, database_identifiers=db_ids)

            if not results:
                logger.info(f"Purview: no entity found for {cache_key}, skipping")
                continue

            entity = self._pick_best_entity(results, db_ids)
            if len(results) > 1:
                logger.info(
                    f"Purview: {len(results)} entities found for {cache_key}, "
                    f"using {entity.get('qualifiedName', 'unknown')}"
                )

            cache[cache_key] = entity
            cache[unique_id] = entity

        self._entity_cache = cache
        return cache

    def _resolve_entity_for_node(self, node: object, resolved: dict) -> dict | None:
        """Look up the Purview entity for a dbt node, first by unique_id then by cache key."""
        unique_id = _get_attr(node, "unique_id", "")
        if unique_id in resolved:
            return resolved[unique_id]

        cache_key = _make_cache_key(
            _get_node_database(node), _get_node_schema(node), _get_node_name(node)
        )
        return resolved.get(cache_key)

    def push_metadata(
        self,
        models: list,
        resolved: dict,
        results: list | None = None,
        sync_descriptions: bool = True,
        sync_metadata: bool = True,
    ) -> None:
        """Push descriptions, business metadata, and labels to Purview in a single bulk call.

        Combines model descriptions (userDescription), business metadata (dbt_metadata),
        and labels (dbt tags) into one entity update per model, then sends them all in a
        single bulk API call. Column descriptions still require separate calls since they
        need to fetch referred entities first.
        """
        test_results = self._collect_test_results(models, results) if sync_metadata else {}
        entity_updates: list[dict] = []
        column_work: list[tuple] = []

        for model in models:
            entity = self._resolve_entity_for_node(model, resolved)
            if entity is None:
                continue

            config = _get_attr(model, "config", {})
            persist_docs = (
                config.get("persist_docs", {})
                if isinstance(config, dict)
                else _get_attr(config, "persist_docs", {})
            )
            if isinstance(persist_docs, dict):
                persist_relation = persist_docs.get("relation", False)
                persist_columns = persist_docs.get("columns", False)
            else:
                persist_relation = _get_attr(persist_docs, "relation", False)
                persist_columns = _get_attr(persist_docs, "columns", False)

            update: dict = {
                "typeName": entity["entityType"],
                "guid": entity["id"],
                "attributes": {
                    "qualifiedName": entity["qualifiedName"],
                    "name": entity.get("name", _get_node_name(model)),
                },
            }

            if sync_descriptions and persist_relation:
                description = _get_attr(model, "description", "")
                if description:
                    update["attributes"]["userDescription"] = description

            if sync_metadata:
                unique_id = _get_attr(model, "unique_id", "")
                bm_attrs = self._build_business_metadata_attrs(model, unique_id, test_results)
                update["businessAttributes"] = {"dbt_metadata": bm_attrs}

                tags = _get_attr(model, "tags", [])
                if tags:
                    update["labels"] = list(tags) if isinstance(tags, list) else [str(tags)]

            has_content = (
                "userDescription" in update["attributes"]
                or "businessAttributes" in update
                or "labels" in update
            )
            if has_content:
                entity_updates.append(update)

            if sync_descriptions and persist_columns:
                column_work.append((model, entity))

        has_bm = any("businessAttributes" in u for u in entity_updates)
        if entity_updates:
            self._client.bulk_create_or_update(entity_updates, merge_business_attrs=has_bm)

        for model, entity in column_work:
            col_descriptions = self._extract_column_descriptions(model)
            if col_descriptions:
                self._client.update_column_descriptions(entity["id"], col_descriptions)

    def _extract_column_descriptions(self, model) -> dict[str, str]:
        """Extract column name → description mapping from a dbt model node."""
        columns = _get_attr(model, "columns", {})
        if hasattr(columns, "values"):
            col_iter = columns.values()
        elif isinstance(columns, dict):
            col_iter = columns.values()
        else:
            col_iter = columns if isinstance(columns, list) else []

        col_descriptions: dict[str, str] = {}
        for col in col_iter:
            col_name = _get_attr(col, "name", "")
            col_desc = _get_attr(col, "description", "")
            if col_name and col_desc:
                col_descriptions[col_name] = col_desc
        return col_descriptions

    def _build_business_metadata_attrs(
        self, model, unique_id: str, test_results: dict[str, dict[str, str]]
    ) -> dict[str, str]:
        """Build the dbt_metadata business metadata attributes dict for a model."""
        tags = _get_attr(model, "tags", [])
        config = _get_attr(model, "config", {})
        materialization = (
            _get_attr(config, "materialized", "")
            if not isinstance(config, dict)
            else config.get("materialized", "")
        )
        meta = _get_attr(model, "meta", {})
        if isinstance(meta, dict) and not meta:
            meta_str = ""
        else:
            meta_str = json.dumps(meta) if meta else ""

        test_names = self._get_test_names_for_model(unique_id)
        model_test_results = test_results.get(unique_id, {})
        test_status = self._format_test_status(model_test_results)

        attrs: dict[str, str] = {
            "dbt_model_id": unique_id,
            "dbt_last_sync": datetime.now(timezone.utc).isoformat(),
        }
        if tags:
            attrs["dbt_tags"] = ",".join(tags) if isinstance(tags, list) else str(tags)
        if materialization:
            attrs["dbt_materialization"] = str(materialization)
        if meta_str:
            attrs["dbt_meta"] = meta_str
        if test_names:
            attrs["dbt_tests"] = (
                ",".join(test_names) if isinstance(test_names, list) else str(test_names)
            )
        if test_status:
            attrs["dbt_test_status"] = test_status
        return attrs

    def push_lineage(self, models: list, resolved: dict, is_full_sync: bool = False) -> None:
        """Create dbt_transformation process entities in Purview to represent data lineage.

        For each model with upstream dependencies (ref/source), creates a Process entity
        with inputs (upstream tables) and outputs (the model's table) so Purview displays
        the lineage graph. Source dependencies are resolved lazily from the graph.
        """
        process_entities: list[dict] = []

        for model in models:
            entity = self._resolve_entity_for_node(model, resolved)
            if entity is None:
                continue

            depends_on = _get_attr(model, "depends_on", {})
            dep_nodes = (
                _get_attr(depends_on, "nodes", [])
                if not isinstance(depends_on, dict)
                else depends_on.get("nodes", [])
            )

            if not dep_nodes:
                continue

            unique_id = _get_attr(model, "unique_id", "")
            config = _get_attr(model, "config", {})
            materialization = (
                _get_attr(config, "materialized", "")
                if not isinstance(config, dict)
                else config.get("materialized", "")
            )

            upstream_refs = []
            for dep_id in dep_nodes:
                dep_entity = self._resolve_dependency_entity(dep_id, resolved)
                if dep_entity is not None:
                    upstream_refs.append(
                        (dep_entity["id"], dep_entity.get("entityType", "DataSet"))
                    )

            if not upstream_refs:
                continue

            process_qn = f"dbt://{unique_id}"
            process_entity = {
                "typeName": "dbt_transformation",
                "attributes": {
                    "qualifiedName": process_qn,
                    "name": _get_node_name(model),
                    "dbt_model_id": unique_id,
                    "dbt_materialization": str(materialization) if materialization else "",
                    "inputs": [
                        {"guid": guid, "typeName": type_name} for guid, type_name in upstream_refs
                    ],
                    "outputs": [
                        {
                            "guid": entity["id"],
                            "typeName": entity.get("entityType", "DataSet"),
                        }
                    ],
                },
            }
            process_entities.append(process_entity)

        if process_entities:
            self._client.bulk_create_or_update(process_entities)

        if is_full_sync:
            created_qns = {e["attributes"]["qualifiedName"] for e in process_entities}
            existing = self._client.search_process_entities("dbt://")
            for proc in existing:
                if proc.get("qualifiedName", "") not in created_qns:
                    self._client.delete_entity_by_guid(proc["id"])
                    logger.info(f"Purview: removed stale lineage {proc.get('qualifiedName', '')}")

    def _resolve_dependency_entity(self, dep_id: str, resolved: dict) -> dict | None:
        """Resolve a dependency to a Purview entity.

        Handles model/seed/snapshot dependencies via the resolved cache, and source
        dependencies by looking them up in graph["sources"] and searching Purview.
        """
        if dep_id in resolved:
            return resolved[dep_id]

        if dep_id.startswith("source."):
            return self._resolve_source_entity(dep_id, resolved)

        parts = dep_id.split(".")
        if len(parts) >= 3:
            cache_key = _make_cache_key(parts[-3], parts[-2], parts[-1])
            return resolved.get(cache_key)

        return None

    def _resolve_source_entity(self, source_id: str, resolved: dict) -> dict | None:
        """Resolve a dbt source to a Purview entity by searching on name and database."""
        sources = self._graph.get("sources", {})
        source = sources.get(source_id)
        if source is None:
            return None

        name = _get_attr(source, "name", "")
        if not name:
            return None

        database = _get_attr(source, "database", "")
        schema = _get_attr(source, "schema", "")
        cache_key = _make_cache_key(database, schema, name)

        if cache_key in resolved:
            resolved[source_id] = resolved[cache_key]
            return resolved[cache_key]

        db_ids = self._database_identifiers(database) if database else None
        results = self._client.search_entities(name=name, database_identifiers=db_ids)

        if not results:
            logger.info(f"Purview: no entity found for source {source_id}, skipping")
            return None

        entity = self._pick_best_entity(results, db_ids)
        resolved[cache_key] = entity
        resolved[source_id] = entity
        return entity

    def _collect_test_results(
        self, models: list, results: list | None
    ) -> dict[str, dict[str, str]]:
        """Extract test results from a dbt run, grouped by the model each test depends on."""
        if results is None:
            return {}

        test_results: dict[str, dict[str, str]] = {}

        for r in results:
            node = r.node if hasattr(r, "node") else r.get("node", {})
            resource_type = _get_attr(node, "resource_type", "")
            if resource_type != "test":
                continue

            status = r.status if hasattr(r, "status") else r.get("status", "")
            test_name = _get_attr(node, "name", "")

            depends_on = _get_attr(node, "depends_on", {})
            dep_nodes = (
                _get_attr(depends_on, "nodes", [])
                if not isinstance(depends_on, dict)
                else depends_on.get("nodes", [])
            )

            for dep_id in dep_nodes:
                if (
                    dep_id.startswith("model.")
                    or dep_id.startswith("seed.")
                    or dep_id.startswith("snapshot.")
                ):
                    test_results.setdefault(dep_id, {})[test_name] = str(status)

        return test_results

    def _get_test_names_for_model(self, model_unique_id: str) -> list[str]:
        """Return the names of all tests that depend on the given model."""
        return self._test_mapping.get(model_unique_id, [])

    def _format_test_status(self, test_results: dict[str, str]) -> str:
        """Format test results as a summary string, e.g. 'all_passed' or '3/5 passed'."""
        if not test_results:
            return ""

        total = len(test_results)
        passed = sum(1 for s in test_results.values() if s == "pass")

        if passed == total:
            return "all_passed"
        return f"{passed}/{total} passed"
