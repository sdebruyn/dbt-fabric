from unittest.mock import MagicMock

from dbt.adapters.fabric.purview_sync import (
    PurviewSync,
    _get_attr,
    _get_node_database,
    _get_node_name,
    _get_node_schema,
    _has_persist_docs_enabled,
    _make_cache_key,
    extract_syncable_models,
)


def _make_node(
    unique_id="model.test.my_model",
    name="my_model",
    alias=None,
    schema="dbo",
    database="my_db",
    resource_type="model",
    description="",
    columns=None,
    tags=None,
    meta=None,
    depends_on=None,
    config=None,
):
    return {
        "unique_id": unique_id,
        "name": name,
        "alias": alias,
        "schema": schema,
        "database": database,
        "resource_type": resource_type,
        "description": description,
        "columns": columns or {},
        "tags": tags or [],
        "meta": meta or {},
        "depends_on": depends_on or {"nodes": []},
        "config": config or {"materialized": "table"},
    }


def _make_test_node(name, depends_on_nodes):
    return {
        "unique_id": f"test.test.{name}",
        "name": name,
        "resource_type": "test",
        "depends_on": {"nodes": depends_on_nodes},
    }


def _make_source(
    unique_id="source.test.raw.orders",
    name="orders",
    schema="raw",
    database="my_db",
):
    return {
        "unique_id": unique_id,
        "name": name,
        "schema": schema,
        "database": database,
        "resource_type": "source",
    }


def _make_result(unique_id="model.test.my_model", resource_type="model", status="pass"):
    return {
        "node": {
            "unique_id": unique_id,
            "resource_type": resource_type,
            "name": unique_id.split(".")[-1],
            "depends_on": {"nodes": []},
        },
        "status": status,
    }


def _make_purview_entity(
    guid="guid-1",
    name="my_model",
    entity_type="fabric_lakehouse_table",
    qualified_name="https://app.fabric.microsoft.com/groups/a1b2c3d4/lakehouses/b2c3d4e5/tables/my_model",
):
    return {
        "id": guid,
        "name": name,
        "entityType": entity_type,
        "qualifiedName": qualified_name,
    }


def _make_fabric_client(lakehouses=None, warehouses=None):
    client = MagicMock()
    client.get_lakehouses.return_value = lakehouses or [{"displayName": "my_db", "id": "b2c3d4e5"}]
    client.get_warehouses.return_value = warehouses or []
    return client


def _make_graph(nodes=None, sources=None):
    return {
        "nodes": nodes or {},
        "sources": sources or {},
    }


class TestExtractSyncableModels:
    def test_filters_by_resource_type(self):
        graph = {
            "nodes": {
                "model.test.a": _make_node(unique_id="model.test.a", resource_type="model"),
                "test.test.t": _make_node(unique_id="test.test.t", resource_type="test"),
                "seed.test.s": _make_node(unique_id="seed.test.s", resource_type="seed"),
                "snapshot.test.snap": _make_node(
                    unique_id="snapshot.test.snap", resource_type="snapshot"
                ),
                "source.test.src": _make_node(unique_id="source.test.src", resource_type="source"),
            }
        }
        models = extract_syncable_models(graph)
        ids = {_get_attr(m, "unique_id") for m in models}
        assert ids == {"model.test.a", "seed.test.s", "snapshot.test.snap"}

    def test_filters_by_results_when_provided(self):
        graph = {
            "nodes": {
                "model.test.a": _make_node(unique_id="model.test.a"),
                "model.test.b": _make_node(unique_id="model.test.b"),
            }
        }
        results = [_make_result(unique_id="model.test.a")]
        models = extract_syncable_models(graph, results)
        assert len(models) == 1
        assert _get_attr(models[0], "unique_id") == "model.test.a"

    def test_no_results_returns_all(self):
        graph = {
            "nodes": {
                "model.test.a": _make_node(unique_id="model.test.a"),
                "model.test.b": _make_node(unique_id="model.test.b"),
            }
        }
        models = extract_syncable_models(graph, results=None)
        assert len(models) == 2

    def test_excludes_persist_docs_all_false(self):
        graph = {
            "nodes": {
                "model.test.a": _make_node(
                    unique_id="model.test.a",
                    config={
                        "materialized": "table",
                        "persist_docs": {"relation": False, "columns": False},
                    },
                ),
                "model.test.b": _make_node(
                    unique_id="model.test.b",
                    config={
                        "materialized": "table",
                        "persist_docs": {"relation": True, "columns": False},
                    },
                ),
            }
        }
        models = extract_syncable_models(graph)
        ids = {_get_attr(m, "unique_id") for m in models}
        assert ids == {"model.test.b"}

    def test_includes_when_persist_docs_not_set(self):
        graph = {
            "nodes": {
                "model.test.a": _make_node(
                    unique_id="model.test.a",
                    config={"materialized": "table"},
                ),
            }
        }
        models = extract_syncable_models(graph)
        assert len(models) == 1


class TestHasPersistDocsEnabled:
    def test_no_config(self):
        assert _has_persist_docs_enabled({"resource_type": "model"}) is True

    def test_no_persist_docs_key(self):
        assert _has_persist_docs_enabled({"config": {"materialized": "table"}}) is True

    def test_empty_persist_docs(self):
        assert _has_persist_docs_enabled({"config": {"persist_docs": {}}}) is True

    def test_all_false(self):
        node = {"config": {"persist_docs": {"relation": False, "columns": False}}}
        assert _has_persist_docs_enabled(node) is False

    def test_relation_true(self):
        node = {"config": {"persist_docs": {"relation": True, "columns": False}}}
        assert _has_persist_docs_enabled(node) is True

    def test_columns_true(self):
        node = {"config": {"persist_docs": {"relation": False, "columns": True}}}
        assert _has_persist_docs_enabled(node) is True

    def test_relation_false_only(self):
        node = {"config": {"persist_docs": {"relation": False}}}
        assert _has_persist_docs_enabled(node) is True


class TestGetAttr:
    def test_dict(self):
        assert _get_attr({"key": "val"}, "key") == "val"
        assert _get_attr({"key": "val"}, "missing", "default") == "default"

    def test_object(self):
        obj = MagicMock()
        obj.key = "val"
        assert _get_attr(obj, "key") == "val"


class TestNodeAccessors:
    def test_alias_preferred_over_name(self):
        node = _make_node(name="original", alias="aliased")
        assert _get_node_name(node) == "aliased"

    def test_name_when_no_alias(self):
        node = _make_node(name="original", alias=None)
        assert _get_node_name(node) == "original"

    def test_schema_and_database(self):
        node = _make_node(schema="staging", database="analytics")
        assert _get_node_schema(node) == "staging"
        assert _get_node_database(node) == "analytics"


class TestMakeCacheKey:
    def test_lowercase(self):
        assert _make_cache_key("DB", "DBO", "Table") == "db.dbo.table"


class TestBuildTestMapping:
    def test_maps_tests_to_models(self):
        graph = _make_graph(
            nodes={
                "model.test.my_model": _make_node(),
                "test.test.not_null_id": _make_test_node("not_null_id", ["model.test.my_model"]),
                "test.test.unique_id": _make_test_node("unique_id", ["model.test.my_model"]),
            }
        )
        sync = PurviewSync(MagicMock(), _make_fabric_client(), graph)
        assert sorted(sync._get_test_names_for_model("model.test.my_model")) == [
            "not_null_id",
            "unique_id",
        ]

    def test_maps_tests_to_seeds(self):
        graph = _make_graph(
            nodes={
                "seed.test.raw_data": _make_node(
                    unique_id="seed.test.raw_data", resource_type="seed"
                ),
                "test.test.not_null_raw": _make_test_node("not_null_raw", ["seed.test.raw_data"]),
            }
        )
        sync = PurviewSync(MagicMock(), _make_fabric_client(), graph)
        assert sync._get_test_names_for_model("seed.test.raw_data") == ["not_null_raw"]

    def test_ignores_source_dependencies(self):
        graph = _make_graph(
            nodes={
                "test.test.src_test": _make_test_node("src_test", ["source.test.raw.orders"]),
            }
        )
        sync = PurviewSync(MagicMock(), _make_fabric_client(), graph)
        assert sync._get_test_names_for_model("source.test.raw.orders") == []

    def test_no_tests_returns_empty(self):
        graph = _make_graph(nodes={"model.test.my_model": _make_node()})
        sync = PurviewSync(MagicMock(), _make_fabric_client(), graph)
        assert sync._get_test_names_for_model("model.test.my_model") == []


class TestResolveEntities:
    def test_resolves_single_match(self):
        client = MagicMock()
        entity = _make_purview_entity()
        client.search_entities.return_value = [entity]

        sync = PurviewSync(client, _make_fabric_client(), _make_graph())
        node = _make_node()
        resolved = sync.resolve_entities([node])

        assert "model.test.my_model" in resolved
        assert "my_db.dbo.my_model" in resolved
        assert resolved["model.test.my_model"]["id"] == "guid-1"

    def test_disambiguates_multiple_matches(self):
        client = MagicMock()
        entity_a = _make_purview_entity(
            guid="guid-a",
            qualified_name="https://app.fabric.microsoft.com/groups/a1b2c3d4/lakehouses/other-id/tables/my_model",
        )
        entity_b = _make_purview_entity(
            guid="guid-b",
            qualified_name="https://app.fabric.microsoft.com/groups/a1b2c3d4/lakehouses/b2c3d4e5/tables/my_model",
        )
        client.search_entities.return_value = [entity_a, entity_b]

        sync = PurviewSync(client, _make_fabric_client(), _make_graph())
        node = _make_node()
        resolved = sync.resolve_entities([node])

        assert resolved["model.test.my_model"]["id"] == "guid-b"

    def test_skips_when_no_match(self):
        client = MagicMock()
        client.search_entities.return_value = []

        sync = PurviewSync(client, _make_fabric_client(), _make_graph())
        node = _make_node()
        resolved = sync.resolve_entities([node])

        assert len(resolved) == 0

    def test_deduplicates_same_table(self):
        client = MagicMock()
        entity = _make_purview_entity()
        client.search_entities.return_value = [entity]

        sync = PurviewSync(client, _make_fabric_client(), _make_graph())
        node_a = _make_node(unique_id="model.test.my_model")
        node_b = _make_node(unique_id="model.other.my_model")
        resolved = sync.resolve_entities([node_a, node_b])

        client.search_entities.assert_called_once()


class TestPushDescriptions:
    def test_pushes_model_description_when_persist_docs_relation(self):
        client = MagicMock()
        sync = PurviewSync(client, _make_fabric_client(), _make_graph())

        entity = _make_purview_entity()
        node = _make_node(
            description="This model tracks user events",
            config={"materialized": "table", "persist_docs": {"relation": True, "columns": False}},
        )
        resolved = {"model.test.my_model": entity, "my_db.dbo.my_model": entity}

        sync.push_descriptions([node], resolved)

        client.update_entity_description.assert_called_once_with(
            guid="guid-1",
            type_name="fabric_lakehouse_table",
            qualified_name="https://app.fabric.microsoft.com/groups/a1b2c3d4/lakehouses/b2c3d4e5/tables/my_model",
            name="my_model",
            description="This model tracks user events",
        )
        client.update_column_descriptions.assert_not_called()

    def test_skips_description_when_persist_docs_not_set(self):
        client = MagicMock()
        sync = PurviewSync(client, _make_fabric_client(), _make_graph())

        entity = _make_purview_entity()
        node = _make_node(description="This model tracks user events")
        resolved = {"model.test.my_model": entity, "my_db.dbo.my_model": entity}

        sync.push_descriptions([node], resolved)

        client.update_entity_description.assert_not_called()
        client.update_column_descriptions.assert_not_called()

    def test_skips_description_when_persist_docs_relation_false(self):
        client = MagicMock()
        sync = PurviewSync(client, _make_fabric_client(), _make_graph())

        entity = _make_purview_entity()
        node = _make_node(
            description="Has description but persist_docs is off",
            config={"materialized": "table", "persist_docs": {"relation": False}},
        )
        resolved = {"model.test.my_model": entity, "my_db.dbo.my_model": entity}

        sync.push_descriptions([node], resolved)

        client.update_entity_description.assert_not_called()

    def test_pushes_column_descriptions_when_persist_docs_columns(self):
        client = MagicMock()
        sync = PurviewSync(client, _make_fabric_client(), _make_graph())

        entity = _make_purview_entity()
        node = _make_node(
            columns={
                "user_id": {"name": "user_id", "description": "Primary key"},
                "email": {"name": "email", "description": ""},
            },
            config={
                "materialized": "table",
                "persist_docs": {"relation": False, "columns": True},
            },
        )
        resolved = {"model.test.my_model": entity, "my_db.dbo.my_model": entity}

        sync.push_descriptions([node], resolved)

        client.update_entity_description.assert_not_called()
        client.update_column_descriptions.assert_called_once_with(
            "guid-1", {"user_id": "Primary key"}
        )

    def test_pushes_both_when_persist_docs_fully_enabled(self):
        client = MagicMock()
        sync = PurviewSync(client, _make_fabric_client(), _make_graph())

        entity = _make_purview_entity()
        node = _make_node(
            description="Full docs",
            columns={"user_id": {"name": "user_id", "description": "Primary key"}},
            config={
                "materialized": "table",
                "persist_docs": {"relation": True, "columns": True},
            },
        )
        resolved = {"model.test.my_model": entity, "my_db.dbo.my_model": entity}

        sync.push_descriptions([node], resolved)

        client.update_entity_description.assert_called_once()
        client.update_column_descriptions.assert_called_once()


class TestPushBusinessMetadata:
    def test_pushes_metadata(self):
        client = MagicMock()
        sync = PurviewSync(client, _make_fabric_client(), _make_graph())

        entity = _make_purview_entity()
        node = _make_node(
            tags=["finance", "daily"],
            meta={"owner": "data-team"},
            config={"materialized": "incremental"},
        )
        resolved = {"model.test.my_model": entity, "my_db.dbo.my_model": entity}

        sync.push_business_metadata([node], resolved)

        call_args = client.set_business_metadata.call_args
        assert call_args[0][0] == "guid-1"
        assert call_args[0][1] == "dbt_metadata"
        attrs = call_args[0][2]
        assert attrs["dbt_model_id"] == "model.test.my_model"
        assert attrs.get("dbt_last_sync")
        assert attrs["dbt_tags"] == "finance,daily"
        assert attrs["dbt_materialization"] == "incremental"
        assert "owner" in attrs["dbt_meta"]

    def test_includes_test_results(self):
        client = MagicMock()
        sync = PurviewSync(client, _make_fabric_client(), _make_graph())

        entity = _make_purview_entity()
        node = _make_node()
        resolved = {"model.test.my_model": entity, "my_db.dbo.my_model": entity}

        test_result = _make_result(
            unique_id="test.test.not_null_my_model_id",
            resource_type="test",
            status="pass",
        )
        test_result["node"]["depends_on"] = {"nodes": ["model.test.my_model"]}

        model_result = _make_result(unique_id="model.test.my_model")
        results = [model_result, test_result]

        sync.push_business_metadata([node], resolved, results)

        call_args = client.set_business_metadata.call_args
        attrs = call_args[0][2]
        assert attrs["dbt_test_status"] == "all_passed"

    def test_includes_test_names_from_graph(self):
        client = MagicMock()
        graph = _make_graph(
            nodes={
                "model.test.my_model": _make_node(),
                "test.test.not_null_id": _make_test_node("not_null_id", ["model.test.my_model"]),
                "test.test.unique_id": _make_test_node("unique_id", ["model.test.my_model"]),
            }
        )
        sync = PurviewSync(client, _make_fabric_client(), graph)

        entity = _make_purview_entity()
        node = _make_node()
        resolved = {"model.test.my_model": entity, "my_db.dbo.my_model": entity}

        sync.push_business_metadata([node], resolved)

        call_args = client.set_business_metadata.call_args
        attrs = call_args[0][2]
        test_names = set(attrs["dbt_tests"].split(","))
        assert test_names == {"not_null_id", "unique_id"}


class TestPushLineage:
    def test_creates_process_entities(self):
        client = MagicMock()
        client.bulk_create_or_update.return_value = {"mutatedEntities": {}, "guidAssignments": {}}
        sync = PurviewSync(client, _make_fabric_client(), _make_graph())

        upstream = _make_purview_entity(guid="guid-upstream", name="source_table")
        downstream = _make_purview_entity(guid="guid-downstream", name="my_model")

        node = _make_node(
            depends_on={"nodes": ["model.test.source_table"]},
        )

        resolved = {
            "model.test.my_model": downstream,
            "my_db.dbo.my_model": downstream,
            "model.test.source_table": upstream,
        }

        sync.push_lineage([node], resolved)

        client.bulk_create_or_update.assert_called_once()
        entities = client.bulk_create_or_update.call_args[0][0]
        assert len(entities) == 1
        process = entities[0]
        assert process["typeName"] == "dbt_transformation"
        assert process["attributes"]["qualifiedName"] == "dbt://model.test.my_model"
        assert len(process["attributes"]["inputs"]) == 1
        assert process["attributes"]["inputs"][0]["guid"] == "guid-upstream"
        assert process["attributes"]["inputs"][0]["typeName"] == "fabric_lakehouse_table"
        assert len(process["attributes"]["outputs"]) == 1
        assert process["attributes"]["outputs"][0]["guid"] == "guid-downstream"
        assert process["attributes"]["outputs"][0]["typeName"] == "fabric_lakehouse_table"

    def test_resolves_source_dependencies(self):
        client = MagicMock()
        client.bulk_create_or_update.return_value = {"mutatedEntities": {}, "guidAssignments": {}}

        source_entity = _make_purview_entity(
            guid="guid-source",
            name="orders",
            qualified_name="https://app.fabric.microsoft.com/groups/a1b2c3d4/lakehouses/b2c3d4e5/tables/orders",
        )
        client.search_entities.return_value = [source_entity]

        graph = _make_graph(
            sources={
                "source.test.raw.orders": _make_source(),
            }
        )
        sync = PurviewSync(client, _make_fabric_client(), graph)

        downstream = _make_purview_entity(guid="guid-downstream", name="my_model")
        node = _make_node(
            depends_on={"nodes": ["source.test.raw.orders"]},
        )
        resolved = {
            "model.test.my_model": downstream,
            "my_db.dbo.my_model": downstream,
        }

        sync.push_lineage([node], resolved)

        client.search_entities.assert_called_once_with(
            name="orders", database_identifiers=["my_db", "b2c3d4e5"]
        )
        client.bulk_create_or_update.assert_called_once()
        entities = client.bulk_create_or_update.call_args[0][0]
        assert entities[0]["attributes"]["inputs"][0]["guid"] == "guid-source"

    def test_source_resolution_is_cached(self):
        client = MagicMock()
        client.bulk_create_or_update.return_value = {"mutatedEntities": {}, "guidAssignments": {}}

        source_entity = _make_purview_entity(guid="guid-source", name="orders")
        client.search_entities.return_value = [source_entity]

        graph = _make_graph(
            sources={
                "source.test.raw.orders": _make_source(),
            }
        )
        sync = PurviewSync(client, _make_fabric_client(), graph)

        downstream_a = _make_purview_entity(guid="guid-a", name="model_a")
        downstream_b = _make_purview_entity(guid="guid-b", name="model_b")
        node_a = _make_node(
            unique_id="model.test.model_a",
            name="model_a",
            depends_on={"nodes": ["source.test.raw.orders"]},
        )
        node_b = _make_node(
            unique_id="model.test.model_b",
            name="model_b",
            depends_on={"nodes": ["source.test.raw.orders"]},
        )
        resolved = {
            "model.test.model_a": downstream_a,
            "my_db.dbo.model_a": downstream_a,
            "model.test.model_b": downstream_b,
            "my_db.dbo.model_b": downstream_b,
        }

        sync.push_lineage([node_a, node_b], resolved)

        client.search_entities.assert_called_once()

    def test_skips_when_source_not_in_graph(self):
        client = MagicMock()
        sync = PurviewSync(client, _make_fabric_client(), _make_graph())

        downstream = _make_purview_entity()
        node = _make_node(
            depends_on={"nodes": ["source.test.raw.unknown"]},
        )
        resolved = {
            "model.test.my_model": downstream,
            "my_db.dbo.my_model": downstream,
        }

        sync.push_lineage([node], resolved)

        client.bulk_create_or_update.assert_not_called()

    def test_skips_when_no_upstream_resolved(self):
        client = MagicMock()
        sync = PurviewSync(client, _make_fabric_client(), _make_graph())

        downstream = _make_purview_entity()
        node = _make_node(
            depends_on={"nodes": ["model.test.unknown"]},
        )

        resolved = {
            "model.test.my_model": downstream,
            "my_db.dbo.my_model": downstream,
        }

        sync.push_lineage([node], resolved)

        client.bulk_create_or_update.assert_not_called()

    def test_skips_when_no_depends_on(self):
        client = MagicMock()
        sync = PurviewSync(client, _make_fabric_client(), _make_graph())

        entity = _make_purview_entity()
        node = _make_node(depends_on={"nodes": []})
        resolved = {"model.test.my_model": entity, "my_db.dbo.my_model": entity}

        sync.push_lineage([node], resolved)

        client.bulk_create_or_update.assert_not_called()


class TestFormatTestStatus:
    def test_all_passed(self):
        sync = PurviewSync(MagicMock(), _make_fabric_client(), _make_graph())
        assert sync._format_test_status({"t1": "pass", "t2": "pass"}) == "all_passed"

    def test_partial_pass(self):
        sync = PurviewSync(MagicMock(), _make_fabric_client(), _make_graph())
        assert sync._format_test_status({"t1": "pass", "t2": "fail"}) == "1/2 passed"

    def test_empty(self):
        sync = PurviewSync(MagicMock(), _make_fabric_client(), _make_graph())
        assert sync._format_test_status({}) == ""
