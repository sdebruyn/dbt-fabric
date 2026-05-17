# Detailed comparison with microsoft/dbt-fabric

This document provides a detailed technical comparison between this adapter ([sdebruyn/dbt-fabric](https://github.com/sdebruyn/dbt-fabric), published as `dbt-fabric-samdebruyn`) and the upstream Microsoft repository ([microsoft/dbt-fabric](https://github.com/microsoft/dbt-fabric), published as `dbt-fabric`). For a higher-level overview, see the [feature comparison](feature-comparison.md).

---

## Compute engine support

| Feature | dbt-fabric-samdebruyn | microsoft/dbt-fabric |
|---|---|---|
| **Fabric Data Warehouse (T-SQL)** | ✅ (`fabric` adapter type) | ✅ (`fabric` adapter type) |
| **Fabric Lakehouse / Spark SQL** | ✅ (`fabricspark` adapter type) | ❌ |

This adapter provides a full second adapter (`fabricspark`) for Fabric Lakehouse via Spark SQL over Livy sessions. This includes a complete PEP 249 cursor/connection implementation, Livy session management, and 20 FabricSpark-specific macro files. The upstream supports only the Data Warehouse (T-SQL) adapter.

## Supported materializations

| Materialization | dbt-fabric-samdebruyn (Fabric) | dbt-fabric-samdebruyn (FabricSpark) | microsoft/dbt-fabric |
|---|---|---|---|
| Table | ✅ | ✅ | ✅ |
| View | ✅ | ❌ (Fabric Lakehouse limitation) | ✅ |
| Incremental (append) | ✅ | ✅ | ✅ |
| Incremental (delete+insert) | ✅ | ❌ | ✅ |
| Incremental (merge) | ✅ | ✅ | ✅ |
| Incremental (insert_overwrite) | ❌ | ✅ | ❌ |
| Incremental (microbatch) | ✅ | ✅ | ✅ |
| Ephemeral | ✅ | ✅ | ✅ |
| Snapshot | ✅ | ✅ | ✅ |
| Clone | ✅ | ✅ | ✅ |
| Materialized View | ❌ | ✅ (Fabric lake views) | ❌ |
| Python models | ✅ (via Livy) | ✅ (via Livy) | ❌ |

The `fabricspark` adapter supports `materialized_view` as a materialization (creating Fabric lake views with `CREATE OR REPLACE MATERIALIZED LAKE VIEW`). The default materialization is `view`, matching standard dbt behavior. The adapter also uniquely supports `insert_overwrite` for FabricSpark incremental models.

Both Python model support for Fabric DW (via Livy sessions writing through `synapsesql`) and FabricSpark (native PySpark via Livy) are exclusive to this adapter.

## Authentication methods

| Authentication Method | dbt-fabric-samdebruyn | microsoft/dbt-fabric |
|---|---|---|
| ActiveDirectoryServicePrincipal | ✅ | ✅ |
| ActiveDirectoryPassword | ✅ | ✅ |
| ActiveDirectoryInteractive | ✅ | ✅ |
| ActiveDirectoryDefault (auto) | ✅ (default) | ✅ |
| Azure CLI | ✅ | ✅ |
| Environment credentials | ✅ | ✅ |
| Device Code Flow | ✅ | ❌ |
| Managed Identity (MSI) | ✅ | ❌ |
| Fabric Notebook (`notebookutils`) | ✅ (currently broken) | ✅ (`fabricnotebook`) |
| Synapse Spark (mssparkutils) | ❌ (Synapse-specific, not applicable to Fabric) | ✅ (`synapsespark`) |
| ActiveDirectoryAccessToken | ❌ (removed) | ✅ |
| Windows Login | ✅ | ✅ |
| `token_credential` (custom class) | ✅ | ❌ |
| `workload_identity` (federated) | ✅ | ❌ |
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
| **Separate ODBC driver install** | ❌ (bundled in Python package) | ✅ (ODBC Driver 18 for SQL Server) |
| **System dependency** | None (all bundled) | ODBC driver manager + driver |
| **Connection pooling** | Via mssql-python | `pyodbc.pooling = True` |

This adapter uses [`mssql-python`](https://github.com/microsoft/mssql-python), Microsoft's official Python driver for SQL Server, actively maintained by Microsoft. Under the hood it still uses ODBC, but it bundles the Microsoft ODBC Driver 18 for SQL Server and unixODBC directly in the Python package. This eliminates the need for separate system-level ODBC installation, simplifying setup across all platforms (especially macOS and containerized Linux environments). The upstream uses pyODBC, a community-maintained generic ODBC wrapper that requires a separately installed ODBC driver.

## Community package compatibility

This adapter includes 59 macro overrides across 6 popular dbt packages to make them work with Fabric's T-SQL dialect, with integration tests for dbt-utils, dbt-date, dbt-audit-helper, and dbt-external-tables. For community package compatibility details, see [Package support](packages/index.md).

The upstream has only a single `get_tables_by_pattern` utility macro and no package integration tests.

## OPENROWSET / external table support

| Feature | dbt-fabric-samdebruyn | microsoft/dbt-fabric |
|---|---|---|
| **OPENROWSET source macro** | ❌ | ✅ (`openrowset_source()`) |
| **dbt-external-tables override** | ✅ (creates views wrapping OPENROWSET) | ❌ |
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

### Coverage by area

| Test Area | dbt-fabric-samdebruyn (Fabric) | dbt-fabric-samdebruyn (FabricSpark) | microsoft/dbt-fabric |
|---|---|---|---|
| Basic operations | ✅ | ✅ | ✅ |
| Column types | ✅ | ✅ | ✅ |
| Concurrency | ✅ | ✅ | ✅ |
| Catalog | ✅ | ✅ | ✅ |
| Incremental | ✅ | ✅ | ✅ |
| Microbatch | ✅ | - | ✅ |
| Ephemeral | ✅ | ✅ | ✅ |
| Snapshots | ✅ | ✅ | ✅ |
| Snapshot configs | ✅ | - | ✅ |
| Constraints | ✅ | ✅ | ✅ |
| dbt clone | ✅ | ✅ | ✅ |
| dbt show | ✅ | ✅ | ✅ |
| dbt debug | ✅ | ✅ | ✅ |
| Store test failures | ✅ | ✅ | ✅ |
| Unit testing | ✅ | ✅ | - |
| Aliases | ✅ | ✅ | ✅ |
| Caching | ✅ | ✅ | ✅ |
| Persist docs | ✅ | ✅ | - |
| Hooks | ✅ | ✅ | - |
| Query comment | ✅ | ✅ | ✅ |
| Quoting | ✅ | - | ✅ |
| Schema | ✅ | - | ✅ |
| Sources | ✅ | - | ✅ |
| Seeds | ✅ | ✅ | ✅ |
| Relations | ✅ | ✅ | ✅ |
| Functions | ✅ | ✅ | - |
| Sample mode | ✅ | ✅ | - |
| Empty | ✅ | ✅ | ✅ |
| Grants | ✅ | ✅ | - |
| Python models | ✅ | ✅ | - |
| Purview integration | ✅ | ✅ | - |
| Warehouse snapshots | ✅ | - | - |
| Data types | ✅ | ✅ | ✅ |
| Null compare | ✅ | ✅ | ✅ |
| Timestamps | ✅ | ✅ | ✅ |
| Cluster by | ✅ | - | ✅ |
| List relations | ✅ | ✅ | ✅ |
| Utility functions | ✅ | ✅ | ✅ |
| Package integration tests | [✅](packages/index.md) | [✅](packages/index.md) | - |
| OPENROWSET | ✅ (via dbt-external-tables) | - | ✅ |

---

## dbt Core compatibility

For supported dbt-core and Python versions, see the [compatibility page](compatibility.md).

### dbt feature compatibility

| dbt Feature | dbt-fabric-samdebruyn | microsoft/dbt-fabric |
|---|---|---|
| **Microbatch incremental** | ✅ | ✅ |
| **Cluster by** | ✅ | ✅ |
| **dbt show** | ✅ | ✅ |
| **dbt clone** | ✅ | ✅ |
| **Unit testing** | ✅ | ✅ |
| **Sample mode** | ✅ | Not tested |
| **Functions** | ✅ | ❌ |

---

## CI/CD and maturity

| Aspect | dbt-fabric-samdebruyn | microsoft/dbt-fabric |
|---|---|---|
| **Integration tests on PR** | ✅ (runs on every push to main and on-demand per PR) | ❌ (no automated test runs on PRs) |
| **Multi-version Python testing** | ✅ (3.11, 3.12, 3.13) | Only 3.11 |
| **FabricSpark (Lakehouse) testing** | ✅ (weekly + on-demand) | N/A |
| **Latest dbt Core support** | Up to 1.12 | Up to 1.10 |
| **Commits since Jan 2024** | 577 | 113 |
| **Active development** | ✅ (weekly releases) | Sporadic |
| **Build system** | Hatchling + uv | setuptools + pip |
| **Documentation** | [Dedicated docs site](https://dbt-fabric.debruyn.dev) | 1 page (OPENROWSET) |
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
