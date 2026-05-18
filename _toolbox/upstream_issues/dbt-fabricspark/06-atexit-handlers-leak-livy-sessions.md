# Livy session cleanup bypasses dbt's connection-manager lifecycle and uses `atexit` instead

**Repo:** `microsoft/dbt-fabricspark`
**Labels (suggested):** `bug`, `design`, `priority/medium`

> [x] **Validated by maintainer** — code refs, line numbers, and claims confirmed against upstream HEAD

## Summary

dbt-adapters has a documented connection lifecycle. The connection manager owns `open()` and `close()`; dbt-core calls `close()` at the end of every run as part of the standard adapter contract. Sessions and any process-bound resources belong to that lifecycle — that is the stable, documented surface adapters are supposed to use.

This adapter doesn't. Both [`src/dbt/adapters/fabricspark/singleton_livy.py`](https://github.com/microsoft/dbt-fabricspark/blob/d315a56/src/dbt/adapters/fabricspark/singleton_livy.py) and [`src/dbt/adapters/fabricspark/concurrent_livy.py`](https://github.com/microsoft/dbt-fabricspark/blob/d315a56/src/dbt/adapters/fabricspark/concurrent_livy.py) register `atexit` handlers at module-import time for Livy session cleanup. The high-concurrency variant adds a second `atexit` handler with a global `_active_sessions` set. This puts session lifecycle on a Python runtime primitive that is (a) not part of dbt's stable adapter interface, and (b) less reliable than the `close()` path that already exists for this purpose.

Going around dbt-core's lifecycle means session cleanup happens at a point dbt does not control or observe — dbt cannot retry it, log it, or surface failures from it.

## Evidence (HEAD [`d315a56`](https://github.com/microsoft/dbt-fabricspark/tree/d315a56))

- [`src/dbt/adapters/fabricspark/singleton_livy.py`](https://github.com/microsoft/dbt-fabricspark/blob/d315a56/src/dbt/adapters/fabricspark/singleton_livy.py) registers `atexit.register(...)` at module scope.
- [`src/dbt/adapters/fabricspark/concurrent_livy.py`](https://github.com/microsoft/dbt-fabricspark/blob/d315a56/src/dbt/adapters/fabricspark/concurrent_livy.py) registers `atexit.register(...)` at module scope for both per-session cleanup and the `_active_sessions` global.

## User impact

Session cleanup is invisible to dbt. Failures inside `atexit` aren't surfaced as part of any dbt step, can't be retried by dbt's normal error handling, and don't make it to the dbt log.

## Suggested fix

Move Livy session lifecycle onto dbt-adapters' documented `close()` path:

1. Hold the Livy session on the connection object.
2. Close it from `FabricSparkConnectionManager.close()` — dbt-core already calls this at the end of every run.
3. Drop both `atexit.register(...)` calls and the global `_active_sessions` set.

For paths where `close()` cannot run, accept Fabric's server-side session timeout as the backstop rather than inventing a parallel cleanup mechanism outside dbt's adapter interface.

