"""Unit tests for the concurrency-contention mitigations.

FabricConnectionManager.close() must NOT issue a ROLLBACK even when
connection.transaction_open is True. Our connections run with autocommit=True
(set in open()), so there is never a real transaction to roll back, and the
parent's ROLLBACK can block for minutes on Fabric when concurrent DDL sessions
hold catalog locks.

See microsoft/dbt-fabric#362.

Note: query-level retry on transient Fabric errors is already provided by
dbt-adapters' SQLConnectionManager.add_query (retryable_exceptions + retry_limit).
Our FabricConnectionManager.add_query wires those to mssql_python.OperationalError
and mssql_python.InternalError by default, so no adapter-level retry override is
needed for list_relations_without_caching.
"""

from unittest import mock

from dbt.adapters.contracts.connection import Connection, ConnectionState
from dbt.adapters.fabric.fabric_connection_manager import FabricConnectionManager


def _make_connection(transaction_open: bool) -> Connection:
    conn = mock.MagicMock(spec=Connection)
    conn.state = ConnectionState.OPEN
    conn.transaction_open = transaction_open
    conn.handle = mock.MagicMock()
    conn.name = "test_conn"
    return conn


class TestCloseSuppressesRollback:
    def test_no_rollback_when_transaction_open_true(self):
        conn = _make_connection(transaction_open=True)

        with (
            mock.patch.object(FabricConnectionManager, "_rollback_handle") as mock_rollback,
            mock.patch.object(FabricConnectionManager, "_close_handle"),
        ):
            FabricConnectionManager.close(conn)

        mock_rollback.assert_not_called()

    def test_transaction_open_false_after_close(self):
        conn = _make_connection(transaction_open=True)

        with mock.patch.object(FabricConnectionManager, "_close_handle"):
            FabricConnectionManager.close(conn)

        assert conn.transaction_open is False

    def test_close_handle_still_called(self):
        conn = _make_connection(transaction_open=False)

        with mock.patch.object(FabricConnectionManager, "_close_handle") as mock_close_handle:
            FabricConnectionManager.close(conn)

        mock_close_handle.assert_called_once_with(conn)
