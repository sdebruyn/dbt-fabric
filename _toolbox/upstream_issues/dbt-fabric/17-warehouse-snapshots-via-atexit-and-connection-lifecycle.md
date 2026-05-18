# Warehouse snapshots are coupled to `atexit` handlers and connection-manager `open()` — should be a Jinja macro callable from `on-run-end`

**Repo:** `microsoft/dbt-fabric`
**Labels (suggested):** `bug`, `design`, `priority/medium`

> [ ] **Validated by maintainer** — code refs, line numbers, and claims confirmed against upstream HEAD

## Summary

The warehouse-snapshot feature is implemented as:

1. Module-level globals (`_init_done`, `_snapshot_manager`, `_init_lock`) initialized inside `FabricConnectionManager.open()`.
2. An `atexit.register(lambda: _run_end_action(result))` call from inside `open()` to trigger the snapshot at process exit.
3. A `sys.argv` check that decides whether to register the handler at all, based on what dbt subcommand is running.

This couples a user-facing feature to Python runtime internals and to connection-manager lifecycle methods that are not part of dbt's stable adapter interface. It also introduces two silent-failure modes documented below.

## Evidence (HEAD [`0de2190`](https://github.com/microsoft/dbt-fabric/tree/0de2190), v1.10.0)

- [`dbt/adapters/fabric/fabric_connection_manager.py#L1`](https://github.com/microsoft/dbt-fabric/blob/0de2190/dbt/adapters/fabric/fabric_connection_manager.py#L1) — `import atexit`
- [`dbt/adapters/fabric/fabric_connection_manager.py#L45-L47`](https://github.com/microsoft/dbt-fabric/blob/0de2190/dbt/adapters/fabric/fabric_connection_manager.py#L45-L47) — module-level globals (`_init_done`, `_snapshot_manager`, `_init_lock`)
- [`dbt/adapters/fabric/fabric_connection_manager.py#L602`](https://github.com/microsoft/dbt-fabric/blob/0de2190/dbt/adapters/fabric/fabric_connection_manager.py#L602) — `atexit.register(lambda: _run_end_action(result))` inside `open()`
- The `sys.argv` check in the same file gates registration based on dbt subcommand.

## User impact

**Silent-failure mode 1 — atexit handler doesn't fire.** When the dbt process is killed via SIGKILL, OOMed, exits with `os._exit`, or hits an exception during shutdown after the handler is registered but before it runs, the snapshot silently does not happen. dbt reports the run as successful; the snapshot the user thought they were taking does not exist.

**Silent-failure mode 2 — `delete_warehouse_snapshot` is a stub.** Already filed as a separate issue: snapshots that the user requested to delete are not deleted, while dbt reports success.

**Design constraints:**
- Snapshots can only happen at the fixed lifecycle point `atexit` provides. No dynamic snapshot names (e.g. dated via Jinja).
- No per-model snapshots via `post-hook`.
- No triggering from `dbt run-operation`.
- The feature is invisible to anyone reading the `dbt_project.yml` — it's a hidden side effect of `open()`.

## Suggested fix

Expose warehouse snapshots as a Jinja macro callable from standard dbt orchestration hooks:

```jinja
{# dbt_project.yml #}
on-run-end:
  - "{{ create_or_update_fabric_warehouse_snapshot(name='nightly-' ~ run_started_at.strftime('%Y%m%d')) }}"
```

The macro dispatches to an `@available` adapter method that makes the REST call. No `atexit`, no global state, no `sys.argv` check. Snapshots compose naturally with `target`, `env_var()`, conditionals, `post-hook`, `dbt run-operation`, and other Jinja primitives.

Reference implementation in the fork: commit `7fccebe7` for the initial `create_or_update_fabric_warehouse_snapshot` macro + `@available` adapter method, plus `412b4732` for `delete_warehouse_snapshot`.

## Notes

- `on-run-start` / `on-run-end` are dbt's standard, documented run-orchestration hooks ([docs](https://docs.getdbt.com/reference/project-configs/on-run-start-on-run-end)). Every Snowflake, Postgres, BigQuery, and Spark user already knows them. There is no reason to invent a new lifecycle point when dbt-core already provides exactly this surface.
- The same rewrite eliminates the module-level globals and `atexit` handlers in one change.
