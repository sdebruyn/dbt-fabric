"""Unit tests for the concurrency-contention mitigations.

1. FabricConnectionManager.close() must NOT issue a ROLLBACK even when
   connection.transaction_open is True (autocommit=True means there is nothing
   to roll back, and the ROLLBACK call itself can block for minutes on Fabric
   when concurrent DDL sessions hold catalog locks).

2. FabricAdapter.list_relations_without_caching() must retry the underlying
   catalog read with exponential back-off when it fails, up to `retries` times,
   and re-raise after all retries are exhausted.

See microsoft/dbt-fabric#362.
"""

from unittest import mock

import pytest

from dbt.adapters.contracts.connection import Connection, ConnectionState
from dbt.adapters.fabric.fabric_adapter import FabricAdapter
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


def _make_fabric_adapter(retries: int = 3) -> FabricAdapter:
    adapter = object.__new__(FabricAdapter)
    adapter.config = mock.MagicMock()
    adapter.config.credentials.retries = retries
    return adapter


_PARENT = "dbt.adapters.sql.impl.SQLAdapter.list_relations_without_caching"


class TestListRelationsRetry:
    def test_succeeds_on_first_attempt(self):
        adapter = _make_fabric_adapter(retries=3)
        expected = [mock.MagicMock()]

        with (
            mock.patch(_PARENT, return_value=expected) as mock_super,
            mock.patch("time.sleep") as mock_sleep,
        ):
            result = adapter.list_relations_without_caching(mock.MagicMock())

        assert result is expected
        mock_super.assert_called_once()
        mock_sleep.assert_not_called()

    def test_retries_and_succeeds_on_second_attempt(self):
        adapter = _make_fabric_adapter(retries=3)
        expected = [mock.MagicMock()]

        with (
            mock.patch(
                _PARENT,
                side_effect=[RuntimeError("catalog locked"), expected],
            ) as mock_super,
            mock.patch("time.sleep") as mock_sleep,
        ):
            result = adapter.list_relations_without_caching(mock.MagicMock())

        assert result is expected
        assert mock_super.call_count == 2
        mock_sleep.assert_called_once_with(1)

    def test_exponential_backoff_delays(self):
        retries = 4
        adapter = _make_fabric_adapter(retries=retries)

        with (
            mock.patch(_PARENT, side_effect=[RuntimeError("locked")] * (retries + 1)),
            mock.patch("time.sleep") as mock_sleep,
            pytest.raises(RuntimeError, match="locked"),
        ):
            adapter.list_relations_without_caching(mock.MagicMock())

        sleep_args = [call.args[0] for call in mock_sleep.call_args_list]
        assert sleep_args == [1, 2, 4, 8]

    def test_backoff_capped_at_30_seconds(self):
        retries = 10
        adapter = _make_fabric_adapter(retries=retries)

        with (
            mock.patch(_PARENT, side_effect=[RuntimeError("locked")] * (retries + 1)),
            mock.patch("time.sleep") as mock_sleep,
            pytest.raises(RuntimeError),
        ):
            adapter.list_relations_without_caching(mock.MagicMock())

        sleep_args = [call.args[0] for call in mock_sleep.call_args_list]
        assert all(w <= 30 for w in sleep_args)
        assert sleep_args[5:] == [30] * (retries - 5)

    def test_raises_after_all_retries_exhausted(self):
        adapter = _make_fabric_adapter(retries=2)
        err = RuntimeError("persistent catalog lock")

        with (
            mock.patch(_PARENT, side_effect=[err] * 3),
            mock.patch("time.sleep"),
            pytest.raises(RuntimeError, match="persistent catalog lock"),
        ):
            adapter.list_relations_without_caching(mock.MagicMock())

    def test_total_attempts_equals_one_plus_retries(self):
        retries = 3
        adapter = _make_fabric_adapter(retries=retries)

        with (
            mock.patch(
                _PARENT, side_effect=[RuntimeError("locked")] * (retries + 1)
            ) as mock_super,
            mock.patch("time.sleep"),
            pytest.raises(RuntimeError),
        ):
            adapter.list_relations_without_caching(mock.MagicMock())

        assert mock_super.call_count == retries + 1
