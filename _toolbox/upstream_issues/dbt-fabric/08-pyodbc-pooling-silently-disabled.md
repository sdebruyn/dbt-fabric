# `pyodbc.pooling = True` is a no-op without `pyodbc.odbcversion = "3.8"` — connection pooling is silently disabled

**Repo:** `microsoft/dbt-fabric`
**Labels (suggested):** `bug`, `performance`, `priority/medium`

> [x] **Validated by maintainer** — code refs, line numbers, and claims confirmed against upstream HEAD

> **Internal note (strip before filing):** Do **not** submit the pyodbc-pooling fix as a PR. The right move is to land [PR #350](https://github.com/microsoft/dbt-fabric/pull/350) (`mssql-python` driver support) instead, which makes this whole bug class disappear. File this issue mainly as supporting evidence for why #350 should be prioritized over patching pyodbc.

## Summary

`pyodbc.pooling = True` only takes effect when `pyodbc.odbcversion = "3.8"` is set first. The adapter sets `pyodbc.pooling` but never sets `pyodbc.odbcversion`. The code reads as if pooling is on, but in practice every dbt operation opens a fresh ODBC connection.

## Evidence (HEAD [`0de2190`](https://github.com/microsoft/dbt-fabric/tree/0de2190), v1.10.0)

[`dbt/adapters/fabric/fabric_connection_manager.py#L571`](https://github.com/microsoft/dbt-fabric/blob/0de2190/dbt/adapters/fabric/fabric_connection_manager.py#L571):

```python
pyodbc.pooling = credentials.pooling if credentials.pooling is not None else True
```

A search for `odbcversion` across the package returns nothing:

```shell
git grep -n "odbcversion" 0de2190 -- 'dbt/**'
# (no matches)
```

## User impact

- Every `list_relations`, every metadata query, every model materialization pays a full TLS handshake to Fabric.
- Cumulative effect on a project with hundreds of models can be several seconds per run, and worse against high-latency regions.
- The user-facing knob `credentials.pooling = True` does nothing.

## Suggested fix

The recommended fix is **not** to patch pyodbc but to land [PR #350](https://github.com/microsoft/dbt-fabric/pull/350) — adding `mssql-python` driver support. `mssql-python` is Microsoft's own native Python driver for SQL Server and Fabric. It does not require an ODBC environment, does not need `pyodbc.odbcversion`, and resolves the pooling-configuration question by construction. It also removes the system-level ODBC Driver 18 install that pyodbc requires on every user machine.

[The fork](https://github.com/sdebruyn/dbt-fabric) has migrated entirely from pyodbc to `mssql-python` and has been running it in production across multiple organizations. The pooling-configuration bug documented here is one of several reasons the fork made that move.

If pyodbc must be kept as the driver for backward compatibility, the minimal patch is to add `pyodbc.odbcversion = "3.8"` immediately before the `pyodbc.pooling` assignment:

```python
pyodbc.odbcversion = "3.8"
pyodbc.pooling = credentials.pooling if credentials.pooling is not None else True
```

Reference fix in [the fork](https://github.com/sdebruyn/dbt-fabric) (before the `mssql-python` migration): commit [`fe3d3281`](https://github.com/sdebruyn/dbt-fabric/commit/fe3d3281).

