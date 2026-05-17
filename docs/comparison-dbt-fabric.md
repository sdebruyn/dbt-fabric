# Detailed comparison with microsoft/dbt-fabric

This document provides a detailed technical comparison between this adapter ([sdebruyn/dbt-fabric](https://github.com/sdebruyn/dbt-fabric), published as `dbt-fabric-samdebruyn`) and the upstream Microsoft repository ([microsoft/dbt-fabric](https://github.com/microsoft/dbt-fabric), published as `dbt-fabric`). For a higher-level overview, see the [feature comparison](feature-comparison.md).

**Last updated:** 2026-05-16

---

## Compute engine support

| Feature | dbt-fabric-samdebruyn | microsoft/dbt-fabric |
|---|---|---|
| **Fabric Data Warehouse (T-SQL)** | Yes (`fabric` adapter type) | Yes (`fabric` adapter type) |
| **Fabric Lakehouse / Spark SQL** | Yes (`fabricspark` adapter type) | No |
| **Number of adapter types** | 2 | 1 |

This adapter provides a full second adapter (`fabricspark`) for Fabric Lakehouse via Spark SQL over Livy sessions. This includes a complete PEP 249 cursor/connection implementation, Livy session management, and 20 FabricSpark-specific macro files. The upstream supports only the Data Warehouse (T-SQL) adapter.

## Supported materializations

| Materialization | dbt-fabric-samdebruyn (Fabric) | dbt-fabric-samdebruyn (FabricSpark) | microsoft/dbt-fabric |
|---|---|---|---|
| Table | Yes | Yes | Yes |
| View | Yes | No (Fabric Lakehouse limitation) | Yes |
| Incremental (append) | Yes | Yes | Yes |
| Incremental (delete+insert) | Yes | No | Yes |
| Incremental (merge) | Yes | Yes | Yes |
| Incremental (insert_overwrite) | No | Yes | No |
| Incremental (microbatch) | Yes | Yes | Yes |
| Ephemeral | Yes | Yes | Yes |
| Snapshot | Yes | Yes | Yes |
| Clone | Yes | Yes | Yes |
| Materialized View | No | Yes (Fabric lake views) | No |
| Python models | Yes (via Livy) | Yes (via Livy) | No |

The `fabricspark` adapter introduces `materialized_view` as the default materialization (since Fabric Lakehouse doesn't support traditional SQL views, only Delta lake views created with `CREATE OR REPLACE MATERIALIZED LAKE VIEW`). The adapter also uniquely supports `insert_overwrite` for FabricSpark incremental models.

Both Python model support for Fabric DW (via Livy sessions writing through `synapsesql`) and FabricSpark (native PySpark via Livy) are exclusive to this adapter.

## Authentication methods

| Authentication Method | dbt-fabric-samdebruyn | microsoft/dbt-fabric |
|---|---|---|
| ActiveDirectoryServicePrincipal | Yes | Yes |
| ActiveDirectoryPassword | Yes | Yes |
| ActiveDirectoryInteractive | Yes | Yes |
| ActiveDirectoryDefault (auto) | Yes (default) | Yes |
| Azure CLI | Yes | Yes |
| Environment credentials | Yes | Yes |
| Device Code Flow | Yes | No |
| Managed Identity (MSI) | Yes | No |
| Fabric Notebook (`notebookutils`) | Yes (currently broken) | Yes (`fabricnotebook`) |
| Synapse Spark (mssparkutils) | No (Synapse-specific, not applicable to Fabric) | Yes (`synapsespark`) |
| ActiveDirectoryAccessToken | No (removed) | Yes |
| Windows Login | Yes | Yes |
| `token_credential` (custom class) | Yes | No |
| `workload_identity` (federated) | Yes | No |
| SQL Authentication | Rejected | Rejected |

This adapter supports 11 authentication methods via a unified `FabricTokenProvider` class. Notable additions over upstream:

- **`token_credential`**: Accepts any custom `TokenCredential` class via `credential_class` config, allowing integration with arbitrary Azure identity providers.
- **`workload_identity`**: Supports federated credentials via `ClientAssertionCredential`, reading tokens from a URL (with optional auth header) or local file. This is used in the adapter's CI (GitHub OIDC federation).
- **Device Code Flow** and **Managed Identity**: Additional Azure Identity methods not present upstream.

The upstream uses separate standalone functions per auth method, while this adapter centralizes all token acquisition in `FabricTokenProvider` with token caching, scope management, and a single code path for both the `fabric` and `fabricspark` adapters.

## Connection driver

| Aspect | dbt-fabric-samdebruyn | microsoft/dbt-fabric |
|---|---|---|
| **SQL driver** | `mssql-python` (bundles ODBC Driver 18) | `pyodbc` (requires separate ODBC install) |
| **Separate ODBC driver install** | No (bundled in Python package) | Yes (ODBC Driver 18 for SQL Server) |
| **System dependency** | None (all bundled) | ODBC driver manager + driver |
| **Connection pooling** | Via mssql-python | `pyodbc.pooling = True` |

This adapter uses [`mssql-python`](https://github.com/microsoft/mssql-python), Microsoft's official Python driver for SQL Server, actively maintained by Microsoft. Under the hood it still uses ODBC, but it bundles the Microsoft ODBC Driver 18 for SQL Server and unixODBC directly in the Python package. This eliminates the need for separate system-level ODBC installation, simplifying setup across all platforms (especially macOS and containerized Linux environments). The upstream uses pyODBC, a community-maintained generic ODBC wrapper that requires a separately installed ODBC driver.

## Community package compatibility

This adapter includes macro overrides across 8 popular dbt packages to make them work with Fabric's T-SQL dialect, with integration tests for all supported packages. For community package compatibility details, see [Package support](packages/index.md).

The upstream has only a single `get_tables_by_pattern` utility macro and no package integration tests.

## OPENROWSET / external table support

| Feature | dbt-fabric-samdebruyn | microsoft/dbt-fabric |
|---|---|---|
| **OPENROWSET source macro** | No | Yes (`openrowset_source()`) |
| **dbt-external-tables override** | Yes (creates views wrapping OPENROWSET) | No |
| **Supported formats** | Parquet, CSV, JSONL (via dbt-external-tables) | Parquet, CSV, JSONL (via `openrowset_source()`) |

The upstream implements a standalone `openrowset_source()` macro for file-based ingestion. This adapter instead provides this functionality through a [dbt-external-tables](external-tables.md) package override, which creates views wrapping OPENROWSET queries. This integrates with dbt's standard source staging workflow (`dbt run-operation stage_external_sources`), providing lineage tracking and source freshness support out of the box.

The upstream's standalone macro additionally supports JSON path mapping and ordinal column mapping in the `WITH` clause, which this adapter's dbt-external-tables integration does not currently expose.

## Unique features in this adapter

| Feature | Description |
|---|---|
| **[Microsoft Purview integration](purview-integration.md)** | Full metadata sync to Purview: descriptions, lineage, and business metadata. Callable via `{{ purview_sync() }}` macro. |
| **[Warehouse snapshots](warehouse-snapshots.md) (macro-based)** | Create/update/delete warehouse snapshots via Fabric REST API, controllable from `on-run-start`/`on-run-end` hooks. |
| **Fabric API client** | Full REST client for the Fabric API: workspace resolution, warehouse/lakehouse discovery, Livy session management, warehouse snapshot CRUD. |
| **Automatic host resolution** | Auto-resolves the SQL endpoint hostname from workspace name via Fabric API, without needing the `host` config. |
| **SQL injection protection** | `quote()` method escapes `]` as `]]` in identifiers; upstream does not. |
| **[Catalog statistics](catalog-stats.md)** | `dbt docs generate` includes approximate row counts for every table. |
| **[Functions](https://docs.getdbt.com/docs/build/functions?WT.mc_id=MVP_310840)** | Support for scalar functions as introduced in dbt Core 1.11. |

## Unique features in upstream

| Feature | Description |
|---|---|
| **Warehouse snapshots (connection-level)** | Automatically creates/updates snapshots during `dbt run`/`build`/`snapshot` commands, hooked into the connection lifecycle. |
| **Standalone OPENROWSET macro** | `openrowset_source()` macro usable without any package dependency, with JSON path and ordinal column mapping. |

The upstream's warehouse snapshot approach hooks into the connection manager's `open()` method and uses `atexit` handlers. This is fragile and not a dbt best practice — it couples snapshot management to Python runtime internals (`atexit`) and connection lifecycle methods that are not designed for side effects. These hooks are not part of dbt's stable adapter interface and can break across dbt-core versions. This adapter instead exposes snapshot management as a Jinja macro (`{{ create_or_update_fabric_warehouse_snapshot() }}`), callable from dbt's native `on-run-start`/`on-run-end` hooks or `post-hook` — the standard, stable mechanism for orchestrating side effects in dbt.

---

## Test suite

### Test coverage

| Metric | dbt-fabric-samdebruyn | microsoft/dbt-fabric |
|---|---|---|
| **Test files** | 141 | 35 |
| **Test classes** | 444 | 117 |
| **Fabric (T-SQL) test classes** | 217 | 115 |
| **FabricSpark test classes** | 183 | N/A |
| **Unit test classes** | 43 | 2 |

### Coverage by area

| Test Area | dbt-fabric-samdebruyn (Fabric) | dbt-fabric-samdebruyn (FabricSpark) | microsoft/dbt-fabric |
|---|---|---|---|
| Basic operations | Yes | Yes | Yes |
| Column types | Yes | Yes | Yes |
| Concurrency | Yes | Yes | Yes |
| Catalog | Yes | Yes | Yes |
| Incremental | Yes | Yes | Yes |
| Microbatch | Yes | - | Yes |
| Ephemeral | Yes | Yes | Yes |
| Snapshots | Yes | Yes | Yes |
| Snapshot configs | Yes | - | Yes |
| Constraints | Yes | Yes | Yes |
| dbt clone | Yes | Yes | Yes |
| dbt show | Yes | Yes | Yes |
| dbt debug | Yes | Yes | Yes |
| Store test failures | Yes | Yes | Yes |
| Unit testing | Yes | Yes | - |
| Aliases | Yes | Yes | Yes |
| Caching | Yes | Yes | Yes |
| Persist docs | Yes | Yes | - |
| Hooks | Yes | Yes | - |
| Query comment | Yes | Yes | Yes |
| Quoting | Yes | - | Yes |
| Schema | Yes | - | Yes |
| Sources | Yes | - | Yes |
| Seeds | Yes | Yes | Yes |
| Relations | Yes | Yes | Yes |
| Functions | Yes | Yes | - |
| Sample mode | Yes | Yes | - |
| Empty | Yes | Yes | Yes |
| Grants | Yes | Yes | - |
| Python models | Yes | Yes | - |
| Purview integration | Yes | Yes | - |
| Warehouse snapshots | Yes | - | - |
| Data types | Yes | Yes | Yes |
| Null compare | Yes | Yes | Yes |
| Timestamps | Yes | Yes | Yes |
| Cluster by | Yes | - | Yes |
| List relations | Yes | Yes | Yes |
| Utility functions | 28 files, 40+ classes | 28 files, 40+ classes | 5 inline |
| Package integration tests | Yes (dbt-utils, dbt-date, dbt-external-tables) | - | - |
| OPENROWSET | No (uses dbt-external-tables) | - | Yes |

### Test infrastructure

| Aspect | dbt-fabric-samdebruyn | microsoft/dbt-fabric |
|---|---|---|
| **conftest.py** | 346 lines, multi-adapter routing, deep merge | 130 lines, profile-based selection |
| **Adapter type detection** | Automatic from test file path | Single adapter, profile-based |
| **CLI flags** | `--dw`, `--de`, `--with-grants`, `--with-python` | `--profile` |
| **Session-scoped Livy management** | Yes | No |
| **Log directory per test** | Yes | No |
| **Deep merge for project_config_update** | Yes | No |

---

## dbt Core compatibility

### Dependencies

| Dependency | dbt-fabric-samdebruyn | microsoft/dbt-fabric |
|---|---|---|
| **dbt-common** | >=1.37.3, <2.0 | >=1.0.4, <2.0 |
| **dbt-adapters** | >=1.22.6, <2.0 | >=1.1.1, <2.0 |
| **dbt-core** (dev) | >=1.9.6, <1.13.0 | >=1.8.0 |
| **dbt-spark** | >=1.10.1 (optional) | Not used |
| **SQL driver** | mssql-python >=1.4.0 | pyodbc >=5.2.0 |
| **Azure Identity** | >=1.12.0 | >=1.14.0 |

### Python version support

| Python Version | dbt-fabric-samdebruyn | microsoft/dbt-fabric |
|---|---|---|
| 3.8-3.10 | No | Listed in classifiers |
| 3.11 | Yes (tested in CI) | Yes |
| 3.12 | Yes (tested in CI) | Not listed |
| 3.13 | Yes (tested in CI, primary) | Not listed |

### dbt feature compatibility

| dbt Feature | dbt-fabric-samdebruyn | microsoft/dbt-fabric |
|---|---|---|
| **Microbatch incremental** | Yes | Yes |
| **Cluster by** | Yes | Yes |
| **dbt show** | Yes | Yes |
| **dbt clone** | Yes | Yes |
| **Unit testing** | Yes | Yes (custom macros) |
| **Sample mode** | Yes | Not tested |
| **Functions** | Yes | No |

---

## CI/CD

| Aspect | dbt-fabric-samdebruyn | microsoft/dbt-fabric |
|---|---|---|
| **DW test matrix** | Python 3.11/3.12/3.13 on weekly; 3.13 on PR/push | Python 3.11 only |
| **DE (Spark) test matrix** | Weekly + on-demand via `/test-de` PR comment | N/A |
| **Auth in CI** | OIDC federated credentials (`workload_identity`) | OIDC via Azure login action |
| **Runner** | `ubuntu-latest` | Custom Docker container |
| **Package manager** | uv | pip |
| **Concurrency control** | Yes | No |
| **Test log artifacts** | Uploaded on every run | Not uploaded |
| **Path-based triggers** | Yes | No |

---

## Maturity

| Metric | dbt-fabric-samdebruyn | microsoft/dbt-fabric |
|---|---|---|
| **Total commits on main** | 1,671 | 1,207 |
| **Commits since Jan 2024** | 577 | 113 |
| **Last commit date** | 2026-05-16 | 2026-03-29 |
| **Latest release** | v1.11.3b0 | v1.9.9 |
| **dbt Core compatibility** | Up to 1.12 | Up to 1.10 |
| **Build system** | Hatchling + uv | setuptools + pip |
| **Documentation** | Dedicated docs site | 1 page (OPENROWSET) |
| **Type annotations** | Modern (PEP 604) | Legacy (typing module) |
| **Linter** | ruff | pre-commit (flake8, black, mypy) |
| **Code review** | Human-reviewed | Signs of unreviewed AI-generated code (see below) |

### Code quality concerns in upstream

Some recent upstream commits show signs of AI-generated code that was merged without adequate human review. For example, [PR #315](https://github.com/microsoft/dbt-fabric/pull/315) adds `timeout=getattr(credentials, "login_timeout", None)` to all `get_token()` calls in the connection manager. This is a no-op: `login_timeout` does not exist as an attribute on `FabricCredentials` (so `getattr` always returns `None`), and `get_token()` in azure-identity does not accept or use a `timeout` keyword argument — it silently disappears into `**kwargs`. The PR description is also clearly AI-generated (structured headers, numbered references). This kind of dead code adds confusion and suggests insufficient review practices.

---

## Architecture

**This adapter's class hierarchy:**

```
BaseFabricCredentials (abstract)
  +-- FabricCredentials (T-SQL specific)
  +-- FabricSparkCredentials (Spark specific)

BaseFabricConnectionManager (abstract)
  +-- FabricConnectionManager (mssql-python, T-SQL)
  +-- FabricSparkConnectionManager (Livy sessions, Spark SQL)

BaseFabricAdapter (abstract: Python models, Purview sync)
  +-- FabricAdapter (T-SQL DDL, constraints, warehouse snapshots)
  +-- FabricSparkAdapter (also extends SparkAdapter)

FabricTokenProvider (unified token acquisition)
FabricApiClient (Fabric REST API client)
PurviewClient + PurviewSync (metadata sync)
```

The upstream has a flat structure: `FabricCredentials`, `FabricConnectionManager`, `FabricAdapter`, `WarehouseSnapshotManager` -- all standalone with no inheritance hierarchy.

Both repositories use the MIT License.
