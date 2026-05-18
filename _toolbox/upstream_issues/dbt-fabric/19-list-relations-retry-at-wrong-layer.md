# v1.9.10 retry wrapper around `list_relations_without_caching` should go through `add_query`'s `retryable_exceptions`

**Repo:** `microsoft/dbt-fabric`
**Labels (suggested):** `enhancement`, `priority/medium`
**Refs:** Issue [#362](https://github.com/microsoft/dbt-fabric/issues/362)

> [x] **Validated by maintainer** — code refs, line numbers, and claims confirmed against upstream HEAD

## Summary

[Issue #362](https://github.com/microsoft/dbt-fabric/issues/362) (May 2026) is a real, well-documented user report: `list_<schema>` taking 8–20 minutes when another dbt run is active on the same warehouse. The v1.9.10 fix wraps `FabricAdapter.list_relations_without_caching` in a custom retry with exponential back-off.

The fix lands at the wrong layer. dbt-adapters already gives every query a `retryable_exceptions` + `retry_limit` hook through `SQLConnectionManager.add_query`. The same connection-manager file already maintains a `pyodbc.OperationalError`-based retryable-exceptions list (for connection opens). Threading that exception type into `add_query`'s default `retryable_exceptions` would have given **every metadata query and every model query** the same retry coverage. The custom wrapper only protects `list_relations_without_caching`; the same contention hitting any other adapter operation is still unhandled.

## Evidence

- The reporter's symptom (`list_<schema>` slow under contention) generalizes to any metadata query — `get_columns_in_relation`, `get_catalog`, `check_schema_exists`, etc. — and to model queries that hit the same `sys.tables`/`sys.columns` views internally.
- [`dbt/adapters/fabric/fabric_connection_manager.py`](https://github.com/microsoft/dbt-fabric/blob/0de2190/dbt/adapters/fabric/fabric_connection_manager.py) already defines `retryable_exceptions: List[Type[Exception]] = [pyodbc.OperationalError]` for the connection-open path. Extending the same list to `add_query` would cover everything.
- The reporter explicitly flagged their root-cause guess as hypothesis: *"though we have not been able to confirm the exact mechanism."* The fix that landed addresses the surfaced symptom rather than the underlying contention.

## User impact

- Users still see the same contention errors on every adapter operation other than `list_relations_without_caching`.
- There are now two parallel retry layers in the adapter (the new wrapper and the existing connection-open retries) that have to be kept in sync.
- The custom wrapper increases the surface area to maintain without buying coverage proportional to its complexity.

## Suggested fix

Replace the custom wrapper with extension of the existing `retryable_exceptions` list, and override `retry_limit`:

```python
class FabricConnectionManager(SQLConnectionManager):
    TYPE = "fabric"

    retryable_exceptions = [
        pyodbc.OperationalError,
        pyodbc.InternalError,
        # any other Fabric-side transient exception classes
    ]
    retry_limit = 3
```

The base `SQLConnectionManager.add_query` then automatically retries every query — metadata and model — using the same back-off semantics, with no per-method wrapper.

Reference fix in [the fork](https://github.com/sdebruyn/dbt-fabric): commit [`f1c0a512`](https://github.com/sdebruyn/dbt-fabric/commit/f1c0a512) (default `add_query()` retries on `mssql_python.OperationalError`/`InternalError` up to 3 attempts).

## Notes

- The v1.9.10 fix is well-intentioned and addresses a real user report. The concern is the level of abstraction, not the goal.
- This is one of the recurring patterns observed across recent releases (see also #315): code that *looks* sophisticated but ignores a dbt-native primitive that already does the job.
