import json
import time

import dbt_common.exceptions
import requests

from dbt.adapters.events.logging import AdapterLogger
from dbt.adapters.fabric.fabric_token_provider import FabricTokenProvider

logger = AdapterLogger("fabric")

_PURVIEW_SCOPE = "https://purview.azure.net/.default"
_SEARCH_API = "/datamap/api/search/query"
_ENTITY_API = "/datamap/api/atlas/v2/entity"
_ENTITY_BULK_API = "/datamap/api/atlas/v2/entity/bulk"
_RELATIONSHIP_API = "/datamap/api/atlas/v2/relationship"
_TYPEDEF_API = "/datamap/api/atlas/v2/types/typedefs"
_BUSINESS_METADATA_API = "/datamap/api/atlas/v2/entity/guid/{guid}/businessmetadata/{bm_name}"

_BM_APPLICABLE_TYPES = {"DataSet"}

_BM_ATTRIBUTES = [
    ("dbt_model_id", "dbt model unique ID"),
    ("dbt_tags", "Comma-separated dbt tags"),
    ("dbt_materialization", "Materialization type (table, view, incremental, etc.)"),
    ("dbt_meta", "Custom meta from dbt model config (JSON)"),
    ("dbt_tests", "Comma-separated test names on this model"),
    ("dbt_test_status", "Test status summary from last run"),
    ("dbt_last_sync", "ISO 8601 timestamp of last Purview sync"),
]

_DBT_BUSINESS_METADATA_DEF = {
    "businessMetadataDefs": [
        {
            "name": "dbt_metadata",
            "description": "Metadata synced from dbt models",
            "attributeDefs": [
                {
                    "name": name,
                    "typeName": "string",
                    "description": desc,
                    "isOptional": True,
                    "options": {
                        "applicableEntityTypes": json.dumps(sorted(_BM_APPLICABLE_TYPES)),
                        "maxStrLength": "500",
                    },
                }
                for name, desc in _BM_ATTRIBUTES
            ],
        }
    ]
}

_DBT_TRANSFORMATION_TYPE_DEF = {
    "entityDefs": [
        {
            "name": "dbt_transformation",
            "superTypes": ["Process"],
            "serviceType": "dbt",
            "typeVersion": "1.0",
            "attributeDefs": [
                {
                    "name": "dbt_model_id",
                    "typeName": "string",
                    "description": "dbt model unique ID",
                },
                {
                    "name": "dbt_materialization",
                    "typeName": "string",
                    "description": "Materialization type",
                },
            ],
        }
    ]
}


class PurviewClient:
    def __init__(self, endpoint: str, token_provider: FabricTokenProvider) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._token_provider = token_provider
        self._types_ensured = False

    def _get_auth_headers(self) -> dict[str, str]:
        token = self._token_provider.get_access_token(scope=_PURVIEW_SCOPE)
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _api_request(
        self, url: str, method: str = "get", body: dict | list | None = None
    ) -> requests.Response:
        response = requests.request(method, url, json=body, headers=self._get_auth_headers())

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 5))
            for attempt in range(10):
                time.sleep(retry_after)
                response = requests.request(
                    method, url, json=body, headers=self._get_auth_headers()
                )
                if response.status_code != 429:
                    break
                retry_after = int(response.headers.get("Retry-After", 5))
            else:
                raise dbt_common.exceptions.DbtRuntimeError(
                    f"Purview {method.upper()} {url} rate limited after 10 retries"
                )

        if not (200 <= response.status_code < 300):
            raise dbt_common.exceptions.DbtRuntimeError(
                f"Purview {method.upper()} {url} failed ({response.status_code}): {response.text}"
            )
        return response

    def _api_get(self, url: str) -> requests.Response:
        return self._api_request(url, method="get")

    def _api_post(self, url: str, body: dict | list) -> requests.Response:
        return self._api_request(url, method="post", body=body)

    def _api_put(self, url: str, body: dict | list) -> requests.Response:
        return self._api_request(url, method="put", body=body)

    def search_entities(
        self,
        name: str,
        schema: str | None = None,
        database: str | None = None,
    ) -> list[dict]:
        url = f"{self._endpoint}{_SEARCH_API}"
        base_filters: list[dict] = [
            {"attributeName": "name", "operator": "eq", "attributeValue": name},
            {"objectType": "Tables"},
        ]

        # Try progressively broader searches until we find results:
        # 1. name + schema in QN + database in QN (works for azure_sql_table)
        # 2. name + database in QN (schema not in QN)
        # 3. name only (Fabric Lakehouse entities use GUIDs in QN)
        results = self._run_search(url, base_filters, schema)
        if database:
            filtered = [
                r for r in results if database.lower() in r.get("qualifiedName", "").lower()
            ]
            if filtered:
                return filtered

        if results:
            return results

        if schema:
            results = self._run_search(url, base_filters, None)
            if database:
                filtered = [
                    r for r in results if database.lower() in r.get("qualifiedName", "").lower()
                ]
                if filtered:
                    return filtered

        return results

    def _run_search(self, url: str, base_filters: list[dict], schema: str | None) -> list[dict]:
        filters = list(base_filters)
        if schema:
            filters.append(
                {
                    "attributeName": "qualifiedName",
                    "operator": "contains",
                    "attributeValue": schema,
                }
            )

        body: dict = {
            "keywords": None,
            "filter": {"and": filters},
            "limit": 50,
        }

        results: list[dict] = []
        while True:
            response = self._api_post(url, body)
            data = response.json()
            results.extend(data.get("value", []))
            total_count = data.get("@search.count", 0)
            if len(results) >= total_count or "continuationToken" not in data:
                break
            body["continuationToken"] = data["continuationToken"]

        return results

    def get_entity_by_guid(self, guid: str) -> dict:
        url = f"{self._endpoint}{_ENTITY_API}/guid/{guid}"
        response = self._api_get(url)
        return response.json()

    def bulk_create_or_update(self, entities: list[dict]) -> dict:
        url = f"{self._endpoint}{_ENTITY_BULK_API}"
        all_results: dict = {"mutatedEntities": {}, "guidAssignments": {}}

        for i in range(0, len(entities), 50):
            batch = entities[i : i + 50]
            response = self._api_post(url, {"entities": batch})
            data = response.json()
            for action, ents in data.get("mutatedEntities", {}).items():
                all_results["mutatedEntities"].setdefault(action, []).extend(ents)
            all_results["guidAssignments"].update(data.get("guidAssignments", {}))

        return all_results

    def create_relationship(self, relationship: dict) -> dict:
        url = f"{self._endpoint}{_RELATIONSHIP_API}"
        response = self._api_post(url, relationship)
        return response.json()

    def set_business_metadata(self, guid: str, bm_name: str, attrs: dict) -> None:
        url = f"{self._endpoint}{_BUSINESS_METADATA_API.format(guid=guid, bm_name=bm_name)}"
        self._api_post(url, attrs)

    def ensure_type_definitions(self) -> None:
        if self._types_ensured:
            return

        url = f"{self._endpoint}{_TYPEDEF_API}"

        bm_ok = False
        try:
            self._api_post(url, _DBT_BUSINESS_METADATA_DEF)
            bm_ok = True
        except dbt_common.exceptions.DbtRuntimeError:
            logger.debug("dbt_metadata business metadata type already exists or update failed")
            try:
                self._api_put(url, _DBT_BUSINESS_METADATA_DEF)
                bm_ok = True
            except dbt_common.exceptions.DbtRuntimeError:
                logger.debug("dbt_metadata business metadata type update also failed, continuing")

        entity_ok = False
        try:
            self._api_post(url, _DBT_TRANSFORMATION_TYPE_DEF)
            entity_ok = True
        except dbt_common.exceptions.DbtRuntimeError:
            logger.debug("dbt_transformation entity type already exists or update failed")
            try:
                self._api_put(url, _DBT_TRANSFORMATION_TYPE_DEF)
                entity_ok = True
            except dbt_common.exceptions.DbtRuntimeError:
                logger.debug("dbt_transformation entity type update also failed, continuing")

        self._types_ensured = bm_ok and entity_ok

    def update_entity_description(
        self, guid: str, type_name: str, qualified_name: str, name: str, description: str
    ) -> None:
        entity = {
            "typeName": type_name,
            "guid": guid,
            "attributes": {
                "qualifiedName": qualified_name,
                "name": name,
                "userDescription": description,
            },
        }
        self.bulk_create_or_update([entity])

    def update_column_descriptions(
        self, table_guid: str, column_descriptions: dict[str, str]
    ) -> None:
        if not column_descriptions:
            return

        entity_data = self.get_entity_by_guid(table_guid)
        referred_entities = entity_data.get("referredEntities", {})

        updates: list[dict] = []
        for col_guid, col_entity in referred_entities.items():
            col_name = col_entity.get("attributes", {}).get("name", "")
            if col_name.lower() in {k.lower(): v for k, v in column_descriptions.items()}:
                desc = next(
                    v for k, v in column_descriptions.items() if k.lower() == col_name.lower()
                )
                updates.append(
                    {
                        "typeName": col_entity["typeName"],
                        "guid": col_guid,
                        "attributes": {
                            "qualifiedName": col_entity["attributes"]["qualifiedName"],
                            "name": col_name,
                            "userDescription": desc,
                        },
                    }
                )

        if updates:
            self.bulk_create_or_update(updates)
