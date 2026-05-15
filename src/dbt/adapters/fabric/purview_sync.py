import json
from datetime import datetime, timezone

from dbt.adapters.events.logging import AdapterLogger
from dbt.adapters.fabric.fabric_api_client import FabricApiClient
from dbt.adapters.fabric.purview_client import PurviewClient

logger = AdapterLogger("fabric")


def extract_syncable_models(graph: dict, results: list | None = None) -> list[dict]:
    """Extract models, seeds, and snapshots from the dbt graph that should be synced to Purview.

    When results are provided, only nodes that actually ran are included.
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

        models.append(node)

    return models


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
    """Orchestrates syncing dbt metadata to Purview: descriptions, business metadata, and lineage."""

    def __init__(self, client: PurviewClient, fabric_client: FabricApiClient) -> None:
        self._client = client
        self._fabric_client = fabric_client
        self._entity_cache: dict[str, dict] = {}
        self._item_id_cache: dict[str, str] = {}

    def _resolve_item_id(self, database: str) -> str | None:
        """Resolve a Fabric item name (Lakehouse or Data Warehouse) to its GUID."""
        if database in self._item_id_cache:
            return self._item_id_cache[database]

        for lh in self._fabric_client.get_lakehouses():
            if lh["displayName"] == database:
                self._item_id_cache[database] = lh["id"]
                return lh["id"]

        for wh in self._fabric_client.get_warehouses():
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

    def resolve_entities(self, models: list) -> dict[str, dict]:
        """Match dbt models to Purview entities by searching on name, schema, and database.

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
            results = self._client.search_entities(
                name=name, schema=schema, database_identifiers=db_ids
            )

            if not results:
                logger.info(f"Purview: no entity found for {cache_key}, skipping")
                continue

            if len(results) == 1:
                entity = results[0]
            else:
                entity = results[0]
                if db_ids:
                    lower_ids = [i.lower() for i in db_ids]
                    for r in results:
                        qn = r.get("qualifiedName", "").lower()
                        if any(i in qn for i in lower_ids):
                            entity = r
                            break
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

    def push_descriptions(self, models: list, resolved: dict) -> None:
        """Sync model and column descriptions from dbt to Purview userDescription fields."""
        for model in models:
            entity = self._resolve_entity_for_node(model, resolved)
            if entity is None:
                continue

            description = _get_attr(model, "description", "")
            if description:
                self._client.update_entity_description(
                    guid=entity["id"],
                    type_name=entity["entityType"],
                    qualified_name=entity["qualifiedName"],
                    name=entity.get("name", _get_node_name(model)),
                    description=description,
                )

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

            if col_descriptions:
                self._client.update_column_descriptions(entity["id"], col_descriptions)

    def push_business_metadata(
        self, models: list, resolved: dict, results: list | None = None
    ) -> None:
        """Sync dbt model metadata (tags, materialization, tests, etc.) as Purview business metadata."""
        test_results = self._collect_test_results(models, results)

        for model in models:
            entity = self._resolve_entity_for_node(model, resolved)
            if entity is None:
                continue

            unique_id = _get_attr(model, "unique_id", "")
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

            test_names = _get_attr(model, "test_names", [])
            if not test_names:
                test_names = self._get_test_names_for_model(unique_id, models)

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

            self._client.set_business_metadata(entity["id"], "dbt_metadata", attrs)

    def push_lineage(self, models: list, resolved: dict) -> None:
        """Create dbt_transformation process entities in Purview to represent data lineage.

        For each model with upstream dependencies (ref/source), creates a Process entity
        with inputs (upstream tables) and outputs (the model's table) so Purview displays
        the lineage graph.
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

            upstream_guids = []
            for dep_id in dep_nodes:
                dep_entity = resolved.get(dep_id)
                if dep_entity is None:
                    parts = dep_id.split(".")
                    if len(parts) >= 3:
                        dep_entity = resolved.get(_make_cache_key(parts[-3], parts[-2], parts[-1]))
                if dep_entity is not None:
                    upstream_guids.append(dep_entity["id"])

            if not upstream_guids:
                continue

            process_qn = f"dbt://{unique_id}"
            process_entity = {
                "typeName": "dbt_transformation",
                "attributes": {
                    "qualifiedName": process_qn,
                    "name": _get_node_name(model),
                    "dbt_model_id": unique_id,
                    "dbt_materialization": str(materialization) if materialization else "",
                    "inputs": [{"guid": guid, "typeName": "DataSet"} for guid in upstream_guids],
                    "outputs": [{"guid": entity["id"], "typeName": "DataSet"}],
                },
            }
            process_entities.append(process_entity)

        if process_entities:
            self._client.bulk_create_or_update(process_entities)

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

    def _get_test_names_for_model(self, model_unique_id: str, models: list) -> list[str]:
        return []

    def _format_test_status(self, test_results: dict[str, str]) -> str:
        """Format test results as a summary string, e.g. 'all_passed' or '3/5 passed'."""
        if not test_results:
            return ""

        total = len(test_results)
        passed = sum(1 for s in test_results.values() if s == "pass")

        if passed == total:
            return "all_passed"
        return f"{passed}/{total} passed"
