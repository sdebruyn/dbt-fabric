# `pyodbc.pooling = True` is a no-op without `pyodbc.odbcversion = "3.8"` — connection pooling is silently disabled

**Repo:** `microsoft/dbt-fabric`
**Labels (suggested):** `bug`, `performance`, `priority/medium`

> [ ] **Validated by maintainer** — code refs, line numbers, and claims confirmed against upstream HEAD

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

Add `pyodbc.odbcversion = "3.8"` immediately before the `pyodbc.pooling` assignment:

```python
pyodbc.odbcversion = "3.8"
pyodbc.pooling = credentials.pooling if credentials.pooling is not None else True
```

Reference fix in [the fork](https://github.com/sdebruyn/dbt-fabric): commit [`fe3d3281`](https://github.com/sdebruyn/dbt-fabric/commit/fe3d3281) (before [the fork](https://github.com/sdebruyn/dbt-fabric) migrated entirely from pyodbc to `mssql-python`, which doesn't have this issue).

## Notes

- The `odbcversion` requirement is documented in the pyodbc source code as part of the `SQLSetEnvAttr` call sequence that ODBC requires before pool registration.
- An alternative path is to migrate from pyodbc + ODBC Driver 18 to Microsoft's native `mssql-python` driver (which [the fork](https://github.com/sdebruyn/dbt-fabric) has done). That eliminates the pooling configuration question entirely and removes the system-level ODBC dependency.
