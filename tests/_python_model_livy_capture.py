"""Test-only capture and cleanup of python-model HC Livy sessions.

`FabricLivyHelper` stores the HC Livy session it opens in a thread-local
that escapes dbt's connection management. In tests, those sessions need
to be closed before the test schema is dropped, otherwise the synapsesql
connector keeps JDBC sessions to the DW alive on its warm-up pool, which
hold Sch-S on the schema metadata and block DROP SCHEMA on Sch-M for the
full Spark idle-reap window (25+ min, observed in CI run 26030423528).

This module exists purely to add that cleanup hook on the test side, so
production code does not have to carry a registry it would never use
outside tests.

Usage: `install_capture()` patches `FabricLivyHelper.__init__` to record
each constructed helper's `_thread_local.livy_session` here. `close_all()`
closes every recorded session in parallel and clears the registry.

Scope: ONLY python-model HC sessions. FabricSpark adapter HC sessions are
wrapped in `FabricSparkConnection`, live in dbt's `thread_connections`,
and are closed by `BaseConnectionManager.cleanup_all` — they are never
constructed via `FabricLivyHelper`, so they never land here.
"""

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from dbt.adapters.fabric import fabric_livy_helper
from dbt.adapters.fabric.fabric_hc_livy_session import HighConcurrencyLivySession
from dbt.adapters.fabric.fabric_livy_helper import FabricLivyHelper

_lock = threading.Lock()
_sessions: set[HighConcurrencyLivySession] = set()


def register(session: HighConcurrencyLivySession) -> None:
    with _lock:
        _sessions.add(session)


def close_all() -> None:
    """Close every recorded HC Livy session and clear the registry."""
    with _lock:
        sessions = list(_sessions)
        _sessions.clear()
    if not sessions:
        return
    with ThreadPoolExecutor(max_workers=min(len(sessions), 8)) as pool:
        list(pool.map(lambda s: s.close(), sessions))


def install_capture() -> Callable[[], None]:
    """Patch `FabricLivyHelper.__init__` to register `_thread_local.livy_session`
    after each construction. Returns a teardown callable that restores the
    original `__init__`.

    Must be installed before any `FabricLivyHelper` is constructed (i.e. from
    a session-scoped autouse fixture).
    """
    original_init = FabricLivyHelper.__init__

    def tracking_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        session = getattr(fabric_livy_helper._thread_local, "livy_session", None)
        if session is not None:
            register(session)

    FabricLivyHelper.__init__ = tracking_init

    def restore() -> None:
        FabricLivyHelper.__init__ = original_init

    return restore
