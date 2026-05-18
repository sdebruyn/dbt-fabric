from unittest.mock import MagicMock

from dbt.adapters.fabric import fabric_livy_helper
from dbt.adapters.fabric.fabric_livy_helper import close_all_open_livy_sessions


def test_close_all_open_livy_sessions_closes_and_clears():
    sessions = [MagicMock(), MagicMock(), MagicMock()]
    with fabric_livy_helper._active_sessions_lock:
        fabric_livy_helper._active_sessions.update(sessions)

    close_all_open_livy_sessions()

    for s in sessions:
        s.close.assert_called_once_with()
    assert fabric_livy_helper._active_sessions == set()


def test_close_all_open_livy_sessions_noop_when_empty():
    with fabric_livy_helper._active_sessions_lock:
        fabric_livy_helper._active_sessions.clear()

    close_all_open_livy_sessions()

    assert fabric_livy_helper._active_sessions == set()
