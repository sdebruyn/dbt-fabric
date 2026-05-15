import logging
import threading
import time
import urllib.parse
from typing import Any, Self

import dbt_common.exceptions
import requests

from dbt.adapters.fabric.base_credentials import BaseFabricCredentials
from dbt.adapters.fabric.fabric_token_provider import FabricTokenProvider

logger = logging.getLogger(__name__)

_livy_session_thread_lock = threading.Lock()


class FabricApiError(dbt_common.exceptions.DbtRuntimeError):
    def __init__(self, method: str, url: str, status_code: int, response_text: str) -> None:
        self.status_code = status_code
        super().__init__(
            f"{method} request to {url} failed with status code {status_code}: {response_text}"
        )


class FabricApiClient:
    _LIVY_API_VERSION = "2023-12-01"
    _WAREHOUSE_SNAPSHOT_TIMEOUT_SECONDS = 60 * 30  # 30 minutes
    _instance: Self | None = None

    def __init__(
        self, credentials: BaseFabricCredentials, token_provider: FabricTokenProvider
    ) -> None:
        self._credentials = credentials
        self._token_provider = token_provider
        self._warehouse_connection_string: str | None = None
        self._lakehouse_id: str | None = None
        self._warehouse_id: str | None = None
        self._workspace_id: str | None = None
        self._cached_warehouses: list[dict] | None = None
        self._cached_lakehouses: list[dict] | None = None
        self._livy_session_id: str | None = None
        self._warehouse_snapshot_operations: dict[str, str] = {}

    @classmethod
    def create(
        cls, credentials: BaseFabricCredentials, token_provider: FabricTokenProvider
    ) -> Self:
        """Return a shared singleton instance, creating one on first call.

        Args:
            credentials: Fabric connection credentials.
            token_provider: Provider for Azure access tokens.
        """
        if cls._instance is None:
            cls._instance = FabricApiClient(credentials, token_provider)
        return cls._instance

    def _get_auth_headers(self) -> dict[str, str]:
        token = self._token_provider.get_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

    def _api_request(
        self, url: str, method: str = "get", body: dict | None = None
    ) -> requests.Response:
        """Send an authenticated HTTP request, retrying automatically on 429.

        Args:
            url: The full API URL.
            method: HTTP method (get, post, patch, delete).
            body: Optional JSON body for the request.

        Raises:
            DbtRuntimeError: If the response status code is not 2xx.
        """
        response = requests.request(method, url, json=body, headers=self._get_auth_headers())

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 5))
            time.sleep(retry_after)
            return self._api_request(url, method, body)

        if not (200 <= response.status_code < 300):
            raise FabricApiError(method, url, response.status_code, response.text)
        return response

    def _api_get(self, url: str) -> requests.Response:
        return self._api_request(url, method="get")

    def _api_post(self, url: str, body: dict) -> requests.Response:
        return self._api_request(url, method="post", body=body)

    def _api_patch(self, url: str, body: dict) -> requests.Response:
        return self._api_request(url, method="patch", body=body)

    def _api_delete(self, url: str) -> requests.Response:
        return self._api_request(url, method="delete")

    def get_workspace_id(self) -> str:
        """Resolve the Fabric workspace ID from config or by looking up the workspace name.

        Uses the cached value if available, then falls back to ``workspace_id``
        from credentials, and finally queries the Power BI API by ``workspace_name``.

        Raises:
            DbtConfigError: If neither workspace_id nor workspace_name is configured.
            DbtRuntimeError: If no workspace matches the configured name.
        """
        if self._workspace_id is not None:
            return self._workspace_id
        if self._credentials.workspace_id:
            return self._credentials.workspace_id
        if not self._credentials.workspace_name:
            raise dbt_common.exceptions.DbtConfigError(
                "Either workspace_id or workspace_name must be provided."
            )

        query_param = f"name eq '{self._credentials.workspace_name}'"
        query_param_encoded = urllib.parse.quote_plus(query_param)
        response = self._api_get(
            f"{self._credentials.powerbi_base_api_uri}/myorg/groups?$filter={query_param_encoded}"
        )
        workspaces = response.json().get("value", [])

        if len(workspaces) == 0:
            raise dbt_common.exceptions.DbtRuntimeError(
                f"No workspace found with name {self._credentials.workspace_name}"
            )

        self._workspace_id = workspaces[0]["id"]
        assert self._workspace_id is not None
        return self._workspace_id

    def get_warehouses(self, fetch_all: bool = True) -> list[dict]:
        """List all Data Warehouses in the workspace, with pagination and caching.

        Args:
            fetch_all: If True, follow pagination and cache the full result.
                If False, return only the first page without caching.
        """
        if self._cached_warehouses is not None:
            return self._cached_warehouses

        workspace_id = self.get_workspace_id()

        url = f"{self._credentials.fabric_base_api_uri}/workspaces/{workspace_id}/warehouses"
        warehouses = []

        while url is not None:
            response = self._api_get(url)
            warehouses = warehouses + response.json().get("value", [])
            url = response.json().get("continuationUri", None) if fetch_all else None

        if fetch_all:
            self._cached_warehouses = warehouses
        return warehouses

    def get_lakehouses(self, fetch_all: bool = True) -> list[dict]:
        """List all Lakehouses in the workspace, with pagination and caching.

        Args:
            fetch_all: If True, follow pagination and cache the full result.
                If False, return only the first page without caching.
        """
        if self._cached_lakehouses is not None:
            return self._cached_lakehouses

        workspace_id = self.get_workspace_id()

        url = f"{self._credentials.fabric_base_api_uri}/workspaces/{workspace_id}/lakehouses"
        lakehouses = []

        while url is not None:
            response = self._api_get(url)
            lakehouses = lakehouses + response.json().get("value", [])
            url = response.json().get("continuationUri", None) if fetch_all else None

        if fetch_all:
            self._cached_lakehouses = lakehouses
        return lakehouses

    def get_warehouse_connection_string(self) -> str:
        """Return the SQL endpoint connection string from any warehouse or lakehouse.

        All items in a workspace share the same connection string, so the first
        warehouse or lakehouse found is used.

        Raises:
            DbtRuntimeError: If no warehouses or lakehouses exist in the workspace.
        """
        if self._warehouse_connection_string is not None:
            return self._warehouse_connection_string

        # first we try to find it in any warehouse (they all have the same connection string)
        warehouses = self.get_warehouses(fetch_all=False)
        if len(warehouses) > 0:
            self._warehouse_connection_string = warehouses[0]["properties"]["connectionString"]
            assert self._warehouse_connection_string is not None
            return self._warehouse_connection_string

        # then we try to find it in any lakehouse (also have the same connection string)
        lakehouses = self.get_lakehouses(fetch_all=False)
        if len(lakehouses) > 0:
            self._warehouse_connection_string = lakehouses[0]["properties"][
                "sqlEndpointProperties"
            ]["connectionString"]
            assert self._warehouse_connection_string is not None
            return self._warehouse_connection_string

        raise dbt_common.exceptions.DbtRuntimeError(
            f"No Data Warehouses or Lakehouses found in workspace"
        )

    def get_lakehouse_id(self) -> str:
        """Resolve the Lakehouse ID by matching the configured lakehouse name.

        Raises:
            DbtConfigError: If no lakehouse name is configured.
            DbtRuntimeError: If no lakehouse matches the configured name.
        """
        if self._lakehouse_id is not None:
            return self._lakehouse_id
        if not self._credentials.lakehouse_name:
            raise dbt_common.exceptions.DbtConfigError("lakehouse must be provided.")

        for lakehouse in self.get_lakehouses():
            if lakehouse["displayName"] == self._credentials.lakehouse_name:
                self._lakehouse_id = lakehouse["id"]
                assert self._lakehouse_id is not None
                return self._lakehouse_id

        raise dbt_common.exceptions.DbtRuntimeError(
            f"No Lakehouse found with name {self._credentials.lakehouse_name}"
        )

    def get_warehouse_id(self) -> str:
        """Resolve the Data Warehouse ID by matching the configured database name.

        Raises:
            DbtRuntimeError: If no warehouse matches the configured database name.
        """
        if self._warehouse_id is not None:
            return self._warehouse_id

        for warehouse in self.get_warehouses():
            if warehouse["displayName"] == self._credentials.database:
                self._warehouse_id = warehouse["id"]
                assert self._warehouse_id is not None
                return self._warehouse_id

        raise dbt_common.exceptions.DbtRuntimeError(
            f"No Data Warehouse found with name {self._credentials.database}"
        )

    def get_warehouse_snapshots(self) -> list[dict]:
        """List all warehouse snapshots belonging to the current Data Warehouse."""
        warehouse_id = self.get_warehouse_id()
        workspace_id = self.get_workspace_id()

        url = (
            f"{self._credentials.fabric_base_api_uri}/workspaces/{workspace_id}/warehousesnapshots"
        )
        snapshots = []

        while url is not None:
            response = self._api_get(url)
            for snapshot in response.json().get("value", []):
                parent_warehouse_id = snapshot.get("properties", {}).get("parentWarehouseId")
                if parent_warehouse_id == warehouse_id:
                    snapshots.append(snapshot)

            url = response.json().get("continuationUri", None)

        return snapshots

    def create_warehouse_snapshot(
        self, snapshot_name: str, description: str | None = None
    ) -> None:
        """Create a new warehouse snapshot and track its long-running operation.

        If the API returns a 202 with a Location header, the operation URI is
        stored so ``create_or_update_warehouse_snapshot`` can poll for completion.

        Args:
            snapshot_name: Display name for the new snapshot.
            description: Optional description for the snapshot.
        """
        url = f"{self._credentials.fabric_base_api_uri}/workspaces/{self.get_workspace_id()}/warehousesnapshots"
        body = {
            "displayName": snapshot_name,
            "creationPayload": {"parentWarehouseId": self.get_warehouse_id()},
        }
        if description is not None:
            body["description"] = description

        response = self._api_post(
            url,
            body,
        )

        location_uri = response.headers.get("Location")
        if location_uri is not None and response.status_code == 202:
            self._warehouse_snapshot_operations[snapshot_name] = location_uri

    def update_warehouse_snapshot(
        self, snapshot_id: str, snapshot_name: str, description: str | None = None
    ) -> None:
        """Update the description of an existing warehouse snapshot.

        Args:
            snapshot_id: The ID of the snapshot to update.
            snapshot_name: Display name (used to track the long-running operation).
            description: New description, or None to leave unchanged.
        """
        url = f"{self._credentials.fabric_base_api_uri}/workspaces/{self.get_workspace_id()}/warehousesnapshots/{snapshot_id}"
        body: dict[str, Any] = {"properties": {}}
        if description is not None:
            body["description"] = description
        response = self._api_patch(url, body)

        location_uri = response.headers.get("Location")
        if location_uri is not None and response.status_code == 202:
            self._warehouse_snapshot_operations[snapshot_name] = location_uri

    def wait_and_get_snapshot_id_from_operation(self, operation_uri: str) -> str:
        """Poll a long-running operation until it completes and return the snapshot ID.

        Args:
            operation_uri: The Location URI returned by a snapshot create/update call.

        Raises:
            DbtRuntimeError: If the operation times out or fails.
        """
        timer = time.time()
        while True:
            if time.time() - timer > self._WAREHOUSE_SNAPSHOT_TIMEOUT_SECONDS:
                raise dbt_common.exceptions.DbtRuntimeError(
                    f"Timed out waiting for Warehouse Snapshot operation to complete after {self._WAREHOUSE_SNAPSHOT_TIMEOUT_SECONDS} seconds."
                )

            response = self._api_get(operation_uri)
            operation_status = response.json().get("status", "Unknown")
            retry_sleep = int(response.headers.get("Retry-After", 5))

            if operation_status == "Succeeded":
                result_location = response.headers["Location"]
                result_response = self._api_get(result_location)
                return result_response.json()["id"]

            if operation_status not in ("NotStarted", "Running"):
                raise dbt_common.exceptions.DbtRuntimeError(
                    f"Warehouse Snapshot operation failed with status {operation_status}."
                )

            time.sleep(retry_sleep)

    def create_or_update_warehouse_snapshot(
        self, snapshot_name: str, description: str | None = None
    ) -> None:
        """Create a snapshot if none exists with this name, otherwise update it.

        If a previous create operation is still pending, waits for it to complete
        before deciding whether to update or create.

        Args:
            snapshot_name: Display name for the snapshot.
            description: Optional description for the snapshot.
        """
        existing_snapshot_id = None

        snapshot_operation_uri = self._warehouse_snapshot_operations.get(snapshot_name)
        if snapshot_operation_uri is not None:
            existing_snapshot_id = self.wait_and_get_snapshot_id_from_operation(
                snapshot_operation_uri
            )
        else:
            all_snapshots = self.get_warehouse_snapshots()
            for snapshot in all_snapshots:
                if snapshot["displayName"] == snapshot_name:
                    existing_snapshot_id = snapshot["id"]
                    break

        if existing_snapshot_id is not None:
            self.update_warehouse_snapshot(existing_snapshot_id, snapshot_name, description)
        else:
            self.create_warehouse_snapshot(snapshot_name, description)

    def delete_warehouse_snapshot(self, snapshot_name: str) -> None:
        """Delete a warehouse snapshot by its display name.

        Args:
            snapshot_name: Display name of the snapshot to delete.
        """
        for snapshot in self.get_warehouse_snapshots():
            if snapshot["displayName"] == snapshot_name:
                self._api_delete(
                    f"{self._credentials.fabric_base_api_uri}/workspaces/{self.get_workspace_id()}/warehousesnapshots/{snapshot['id']}"
                )

    def get_livy_base_api_uri(self) -> str:
        """Build the Livy API base URI for the configured lakehouse."""
        workspace_id = self.get_workspace_id()
        lakehouse_id = self.get_lakehouse_id()
        return f"{self._credentials.fabric_base_api_uri}/workspaces/{workspace_id}/lakehouses/{lakehouse_id}/livyapi/versions/{self._LIVY_API_VERSION}"

    def get_existing_livy_session(self) -> str | None:
        """Find an active Livy session matching the configured name, or return None."""
        url = self.get_livy_base_api_uri() + "/sessions"
        response = self._api_get(url)
        sessions = response.json().get("items", [])
        for session in sessions:
            if session["name"] == self._credentials.livy_session_name and session["livyState"] in (
                "idle",
                "starting",
                "running",
                "busy",
            ):
                return session["id"]
        return None

    def initialize_livy_session(self) -> str:
        """Create a new Livy session and wait briefly for it to start."""
        url = self.get_livy_base_api_uri() + "/sessions"
        body = {"name": self._credentials.livy_session_name, "ttl": "30s"}

        max_attempts = 3
        backoff_seconds = 5
        last_exception: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                response = self._api_post(url, body)
                time.sleep(10)
                return response.json()["id"]
            except FabricApiError as e:
                is_transient = e.status_code == 404 or 500 <= e.status_code < 600

                if not is_transient or attempt == max_attempts:
                    raise

                last_exception = e
                wait_time = backoff_seconds * (2 ** (attempt - 1))
                logger.warning(
                    f"Livy session creation returned a transient error (attempt {attempt}/{max_attempts}), "
                    f"retrying in {wait_time}s: {e}"
                )
                time.sleep(wait_time)

        assert last_exception is not None
        raise last_exception

    def get_livy_session_id(self) -> str:
        """Return the active Livy session ID, reusing an existing session or creating one.

        Thread-safe: uses a lock to prevent multiple sessions from being created
        concurrently when dbt runs with multiple threads.
        """
        if self._livy_session_id is None:
            with _livy_session_thread_lock:
                self._livy_session_id = (
                    self.get_existing_livy_session() or self.initialize_livy_session()
                )
        return self._livy_session_id

    def get_livy_session_base_uri(self) -> str:
        """Build the API URI for the current Livy session."""
        return self.get_livy_base_api_uri() + f"/sessions/{self.get_livy_session_id()}"

    def get_livy_session_state(self) -> str:
        """Query the current state of the Livy session (idle, busy, starting, etc.)."""
        response = self._api_get(self.get_livy_session_base_uri())
        return response.json().get("state", "unknown")

    def get_livy_statement(self, statement_id: int) -> dict[str, Any]:
        """Fetch the current status and output of a Livy statement.

        Args:
            statement_id: The statement ID returned by a submit call.
        """
        url = self.get_livy_session_base_uri() + f"/statements/{statement_id}"
        response = self._api_get(url)
        return response.json()

    def submit_livy_python_statement(self, code: str) -> int:
        """Submit Python code to the Livy session and return the statement ID.

        Args:
            code: The Python/PySpark code to execute.
        """
        url = self.get_livy_session_base_uri() + "/statements"
        response = self._api_post(url, {"code": code, "kind": "pyspark"})
        return response.json()["id"]

    def submit_livy_sql_statement(self, code: str) -> int:
        """Submit SQL code to the Livy session and return the statement ID.

        Args:
            code: The Spark SQL code to execute.
        """
        url = self.get_livy_session_base_uri() + "/statements"
        response = self._api_post(url, {"code": code, "kind": "sql"})
        return response.json()["id"]

    def cancel_livy_statement(self, statement_id: int) -> str:
        """Cancel a running Livy statement.

        Args:
            statement_id: The statement ID to cancel.
        """
        url = self.get_livy_session_base_uri() + f"/statements/{statement_id}/cancel"
        response = self._api_post(url, {})
        return response.json()["msg"]
