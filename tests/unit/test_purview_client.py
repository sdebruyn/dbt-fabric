from unittest.mock import MagicMock, patch

import pytest

from dbt.adapters.fabric.purview_client import (
    _DBT_BUSINESS_METADATA_DEF,
    _DBT_TRANSFORMATION_TYPE_DEF,
    _PURVIEW_SCOPE,
    PurviewClient,
)


@pytest.fixture
def token_provider():
    mock = MagicMock()
    mock.get_access_token.return_value = "test-token"
    return mock


@pytest.fixture
def client(token_provider):
    return PurviewClient("https://test.purview.azure.com", token_provider)


class TestPurviewClientAuth:
    def test_auth_headers_use_purview_scope(self, client, token_provider):
        headers = client._get_auth_headers()
        token_provider.get_access_token.assert_called_with(scope=_PURVIEW_SCOPE)
        assert headers["Authorization"] == "Bearer test-token"

    def test_endpoint_trailing_slash_stripped(self, token_provider):
        c = PurviewClient("https://test.purview.azure.com/", token_provider)
        assert c._endpoint == "https://test.purview.azure.com"


class TestSearchEntities:
    @patch("dbt.adapters.fabric.purview_client.requests.request")
    def test_search_by_name(self, mock_request, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {
                    "id": "guid-1",
                    "name": "fct_orders",
                    "qualifiedName": "https://app.fabric.microsoft.com/groups/a1b2c3d4/lakehouses/b2c3d4e5/tables/fct_orders",
                    "entityType": "fabric_lakehouse_table",
                }
            ],
            "@search.count": 1,
        }
        mock_request.return_value = mock_response

        results = client.search_entities(name="fct_orders")
        assert len(results) == 1
        assert results[0]["id"] == "guid-1"

    @patch("dbt.adapters.fabric.purview_client.requests.request")
    def test_search_filters_by_database(self, mock_request, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {
                    "id": "guid-1",
                    "name": "fct_orders",
                    "qualifiedName": "https://app.fabric.microsoft.com/groups/a1b2c3d4/lakehouses/lh-dev/tables/fct_orders",
                    "entityType": "fabric_lakehouse_table",
                },
                {
                    "id": "guid-2",
                    "name": "fct_orders",
                    "qualifiedName": "https://app.fabric.microsoft.com/groups/a1b2c3d4/lakehouses/lh-prod/tables/fct_orders",
                    "entityType": "fabric_lakehouse_table",
                },
            ],
            "@search.count": 2,
        }
        mock_request.return_value = mock_response

        results = client.search_entities(name="fct_orders", database_identifiers=["lh-prod"])
        assert len(results) == 1
        assert results[0]["id"] == "guid-2"

    @patch("dbt.adapters.fabric.purview_client.requests.request")
    def test_search_pagination(self, mock_request, client):
        page1 = MagicMock()
        page1.status_code = 200
        page1.json.return_value = {
            "value": [{"id": f"guid-{i}", "name": "t", "qualifiedName": "q"} for i in range(50)],
            "@search.count": 75,
            "continuationToken": "next-page",
        }
        page2 = MagicMock()
        page2.status_code = 200
        page2.json.return_value = {
            "value": [
                {"id": f"guid-{i}", "name": "t", "qualifiedName": "q"} for i in range(50, 75)
            ],
            "@search.count": 75,
        }
        mock_request.side_effect = [page1, page2]

        results = client.search_entities(name="t")
        assert len(results) == 75

    @patch("dbt.adapters.fabric.purview_client.requests.request")
    def test_search_returns_all_without_database_filter(self, mock_request, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {
                    "id": "guid-1",
                    "name": "fct_orders",
                    "qualifiedName": "https://app.fabric.microsoft.com/groups/a1b2c3d4/lakehouses/lh-dev/tables/fct_orders",
                    "entityType": "fabric_lakehouse_table",
                },
                {
                    "id": "guid-2",
                    "name": "fct_orders",
                    "qualifiedName": "https://app.fabric.microsoft.com/groups/a1b2c3d4/lakehouses/lh-prod/tables/fct_orders",
                    "entityType": "fabric_lakehouse_table",
                },
            ],
            "@search.count": 2,
        }
        mock_request.return_value = mock_response

        results = client.search_entities(name="fct_orders")
        assert len(results) == 2


class TestBulkCreateOrUpdate:
    @patch("dbt.adapters.fabric.purview_client.requests.request")
    def test_single_batch(self, mock_request, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "mutatedEntities": {"CREATE": [{"guid": "g1"}]},
            "guidAssignments": {"-1": "g1"},
        }
        mock_request.return_value = mock_response

        entities = [
            {
                "typeName": "fabric_lakehouse_table",
                "attributes": {
                    "qualifiedName": "https://app.fabric.microsoft.com/groups/a1b2c3d4/lakehouses/b2c3d4e5/tables/fct_orders"
                },
            }
        ]
        result = client.bulk_create_or_update(entities)
        assert "g1" in result["guidAssignments"].values()

    @patch("dbt.adapters.fabric.purview_client.requests.request")
    def test_batching_at_50(self, mock_request, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "mutatedEntities": {"UPDATE": []},
            "guidAssignments": {},
        }
        mock_request.return_value = mock_response

        entities = [
            {"typeName": "t", "attributes": {"qualifiedName": f"e{i}"}} for i in range(120)
        ]
        client.bulk_create_or_update(entities)
        assert mock_request.call_count == 3  # 50 + 50 + 20


class TestRetry:
    @patch("dbt.adapters.fabric.purview_client.time.sleep")
    @patch("dbt.adapters.fabric.purview_client.requests.request")
    def test_429_retry(self, mock_request, mock_sleep, client):
        throttled = MagicMock()
        throttled.status_code = 429
        throttled.headers = {"Retry-After": "1"}

        success = MagicMock()
        success.status_code = 200
        success.json.return_value = {"value": [], "@search.count": 0}

        mock_request.side_effect = [throttled, success]

        results = client.search_entities(name="test")
        assert results == []
        mock_sleep.assert_called_once_with(1)


class TestEnsureTypeDefinitions:
    @patch("dbt.adapters.fabric.purview_client.requests.request")
    def test_registers_types_once(self, mock_request, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_request.return_value = mock_response

        client.ensure_type_definitions()
        client.ensure_type_definitions()

        assert mock_request.call_count == 2  # one PUT for BM def, one PUT for entity def

    @patch("dbt.adapters.fabric.purview_client.requests.request")
    def test_uses_put_for_idempotent_updates(self, mock_request, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_request.return_value = mock_response

        client.ensure_type_definitions()

        for call in mock_request.call_args_list:
            assert call[0][0] == "put"


class TestBusinessMetadata:
    @patch("dbt.adapters.fabric.purview_client.requests.request")
    def test_set_business_metadata(self, mock_request, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        client.set_business_metadata("guid-1", "dbt_metadata", {"dbt_model_id": "model.test.x"})

        call_args = mock_request.call_args
        assert "guid-1" in call_args[0][1]
        assert "dbt_metadata" in call_args[0][1]

    @patch("dbt.adapters.fabric.purview_client.requests.request")
    def test_delete_business_metadata(self, mock_request, client):
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_request.return_value = mock_response

        client.delete_business_metadata("guid-1", "dbt_metadata")

        call_args = mock_request.call_args
        assert call_args[0][0] == "delete"
        assert "guid-1" in call_args[0][1]
        assert "dbt_metadata" in call_args[0][1]


class TestDeleteEntity:
    @patch("dbt.adapters.fabric.purview_client.requests.request")
    def test_delete_entity_by_guid(self, mock_request, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        client.delete_entity_by_guid("guid-1")

        call_args = mock_request.call_args
        assert call_args[0][0] == "delete"
        assert "guid-1" in call_args[0][1]


class TestUpdateColumnDescriptions:
    @patch("dbt.adapters.fabric.purview_client.requests.request")
    def test_updates_matching_columns(self, mock_request, client):
        get_response = MagicMock()
        get_response.status_code = 200
        get_response.json.return_value = {
            "entity": {"typeName": "fabric_lakehouse_table"},
            "referredEntities": {
                "col-guid-1": {
                    "typeName": "fabric_lakehouse_column",
                    "attributes": {
                        "name": "user_id",
                        "qualifiedName": "https://app.fabric.microsoft.com/groups/a1b2c3d4/lakehouses/b2c3d4e5/tables/fct_orders/columns/user_id",
                    },
                },
                "col-guid-2": {
                    "typeName": "fabric_lakehouse_column",
                    "attributes": {
                        "name": "email",
                        "qualifiedName": "https://app.fabric.microsoft.com/groups/a1b2c3d4/lakehouses/b2c3d4e5/tables/fct_orders/columns/email",
                    },
                },
            },
        }

        bulk_response = MagicMock()
        bulk_response.status_code = 200
        bulk_response.json.return_value = {"mutatedEntities": {}, "guidAssignments": {}}

        mock_request.side_effect = [get_response, bulk_response]

        client.update_column_descriptions("table-guid", {"user_id": "The user identifier"})

        bulk_call = mock_request.call_args_list[1]
        body = bulk_call[1]["json"]
        assert len(body["entities"]) == 1
        assert body["entities"][0]["attributes"]["userDescription"] == "The user identifier"

    @patch("dbt.adapters.fabric.purview_client.requests.request")
    def test_case_insensitive_column_matching(self, mock_request, client):
        get_response = MagicMock()
        get_response.status_code = 200
        get_response.json.return_value = {
            "entity": {"typeName": "fabric_lakehouse_table"},
            "referredEntities": {
                "col-guid-1": {
                    "typeName": "fabric_lakehouse_column",
                    "attributes": {
                        "name": "User_ID",
                        "qualifiedName": "https://app.fabric.microsoft.com/groups/a1b2c3d4/lakehouses/b2c3d4e5/tables/fct_orders/columns/User_ID",
                    },
                },
            },
        }

        bulk_response = MagicMock()
        bulk_response.status_code = 200
        bulk_response.json.return_value = {"mutatedEntities": {}, "guidAssignments": {}}

        mock_request.side_effect = [get_response, bulk_response]

        client.update_column_descriptions("table-guid", {"user_id": "The user identifier"})

        bulk_call = mock_request.call_args_list[1]
        body = bulk_call[1]["json"]
        assert len(body["entities"]) == 1
