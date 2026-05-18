# `atexit` handlers for Livy session cleanup leak sessions on hard kill / OOM / `os._exit`

**Repo:** `microsoft/dbt-fabricspark`
**Labels (suggested):** `bug`, `priority/medium`

> [ ] **Validated by maintainer** — code refs, line numbers, and claims confirmed against upstream HEAD

## Summary

Both [`src/dbt/adapters/fabricspark/singleton_livy.py`](https://github.com/microsoft/dbt-fabricspark/blob/d315a56/src/dbt/adapters/fabricspark/singleton_livy.py) and [`src/dbt/adapters/fabricspark/concurrent_livy.py`](https://github.com/microsoft/dbt-fabricspark/blob/d315a56/src/dbt/adapters/fabricspark/concurrent_livy.py) register `atexit` handlers at module-import time for session cleanup. The high-concurrency variant additionally registers a second `atexit` handler with a global `_active_sessions` set. `atexit` handlers do not fire when the process is killed via SIGKILL, OOMed, exits with `os._exit`, or hits an exception during shutdown. When the handler doesn't fire, the Livy session stays alive on Fabric and keeps consuming capacity until its server-side timeout (typically 1–2 hours).

## Evidence (HEAD [`d315a56`](https://github.com/microsoft/dbt-fabricspark/tree/d315a56))

- [`src/dbt/adapters/fabricspark/singleton_livy.py`](https://github.com/microsoft/dbt-fabricspark/blob/d315a56/src/dbt/adapters/fabricspark/singleton_livy.py) registers `atexit.register(...)` at module scope.
- [`src/dbt/adapters/fabricspark/concurrent_livy.py`](https://github.com/microsoft/dbt-fabricspark/blob/d315a56/src/dbt/adapters/fabricspark/concurrent_livy.py) registers `atexit.register(...)` at module scope for both per-session cleanup and the `_active_sessions` global.

## User impact

- Stale Livy sessions accumulate on the user's Fabric capacity after every abnormal termination — Ctrl-C handled badly, container OOM, CI job timeout, deploy-time SIGTERM, segfault, etc.
- Fabric capacity has a session cap. Stale sessions consume slots that the next dbt run cannot use, leading to "session quota exceeded" errors on the next run.
- The user gets no signal that anything is wrong: dbt logs report no error (since the handler didn't run), and the stale sessions are invisible to dbt's local state.

## Suggested fix

Use dbt's documented connection-manager `close()` path instead of `atexit`. Sessions should be closed:

1. By dbt-core's normal `close()` flow at end of run (dbt-core already calls this).
2. By a `__del__` or context-manager `__exit__` if a connection is dropped without being closed.
3. On the server side, by relying on Fabric's Livy session timeout for the genuinely-killed cases (this is fine — Fabric will GC stale sessions eventually).

If a defense-in-depth cleanup is desired, register a `signal.signal(signal.SIGTERM, ...)` handler that calls `close()` and re-raises, rather than relying on `atexit`. SIGTERM handlers run earlier in the shutdown sequence and are more reliable across container-orchestrator kills.

