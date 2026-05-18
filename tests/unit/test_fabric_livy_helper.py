from unittest.mock import MagicMock

import pytest

from dbt.adapters.fabric import fabric_livy_helper
from dbt.adapters.fabric.fabric_livy_helper import _close_all_python_model_livy_sessions


@pytest.fixture(autouse=True)
def _reset_python_model_livy_sessions_registry():
    """Clear the module-global registry before and after each test so
    state from one test (or from concurrent test runs under pytest-xdist)
    never leaks into another."""
    with fabric_livy_helper._python_model_livy_sessions_lock:
        fabric_livy_helper._python_model_livy_sessions.clear()
    try:
        yield
    finally:
        with fabric_livy_helper._python_model_livy_sessions_lock:
            fabric_livy_helper._python_model_livy_sessions.clear()


def test_close_all_python_model_livy_sessions_closes_and_clears():
    sessions = [MagicMock(), MagicMock(), MagicMock()]
    with fabric_livy_helper._python_model_livy_sessions_lock:
        fabric_livy_helper._python_model_livy_sessions.update(sessions)

    _close_all_python_model_livy_sessions()

    for s in sessions:
        s.close.assert_called_once_with()
    assert fabric_livy_helper._python_model_livy_sessions == set()


def test_close_all_python_model_livy_sessions_noop_when_empty():
    _close_all_python_model_livy_sessions()

    assert fabric_livy_helper._python_model_livy_sessions == set()


def test_close_all_python_model_livy_sessions_surfaces_close_exceptions():
    failing = MagicMock()
    failing.close.side_effect = RuntimeError("delete failed")
    with fabric_livy_helper._python_model_livy_sessions_lock:
        fabric_livy_helper._python_model_livy_sessions.add(failing)

    with pytest.raises(RuntimeError, match="delete failed"):
        _close_all_python_model_livy_sessions()
