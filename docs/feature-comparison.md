# Comparison with Microsoft's adapters

[Sam Debruyn](https://debruyn.dev) is the original author of [dbt-fabric](https://github.com/microsoft/dbt-fabric), the first dbt adapter for Microsoft Fabric. After Microsoft took over maintenance of the repository, Sam continued development independently through this fork, adding features, bugfixes, and a second adapter for Fabric Lakehouse. Microsoft has since also published a separate [dbt-fabricspark](https://github.com/microsoft/dbt-fabricspark) package for Lakehouse.

This page summarizes the key differences between this adapter (`dbt-fabric-samdebruyn`) and Microsoft's two packages (`dbt-fabric` and `dbt-fabricspark`).

!!! tip "Looking for a detailed technical comparison?"

    For in-depth comparisons covering architecture, code quality, test suites, and dbt Core compatibility, see:

    - [Detailed comparison with microsoft/dbt-fabric](comparison-dbt-fabric.md) (Data Warehouse / T-SQL adapter)
    - [Detailed comparison with microsoft/dbt-fabricspark](comparison-dbt-fabricspark.md) (Lakehouse / Spark SQL adapter)

## Platform & compatibility

### No separate ODBC driver installation required

This adapter uses Microsoft's official [`mssql-python`](https://github.com/microsoft/mssql-python) driver instead of pyODBC. `mssql-python` is actively maintained by Microsoft and is their recommended Python driver for SQL Server and Microsoft Fabric. Under the hood, it still uses ODBC, but it **bundles the Microsoft ODBC Driver 18 for SQL Server** along with unixODBC directly in the Python package. This means there is no separate system-level installation step required.

Microsoft's upstream dbt-fabric adapter depends on pyODBC, which is a community-maintained generic ODBC wrapper. Using pyODBC requires:

- A system-level ODBC driver manager (unixODBC on Linux/macOS)
- The Microsoft ODBC Driver for SQL Server (`msodbcsql18`), separately installed
- Platform-specific installation steps that vary between Linux distributions, macOS, and Windows

With dbt-fabric-samdebruyn, none of this manual setup is needed. Installation is a single `pip install` or `uv add` command — the bundled ODBC driver is included automatically for all supported platforms (Linux, macOS, Windows). This eliminates a common source of installation issues and makes the adapter work consistently across all platforms, including containerized environments.

### dbt Core compatibility

This adapter is compatible with **dbt Core 1.11 and 1.12**. Microsoft's dbt-fabric is only compatible with dbt Core 1.10, and dbt-fabricspark with 1.11.

### Python version support

This adapter is tested on **Python 3.11, 3.12, and 3.13**. Microsoft's dbt-fabric still lists Python 3.8-3.10 in its classifiers but does not test on 3.12 or 3.13.

## Dual engine support

### Fabric Lakehouse (Spark SQL) support

This adapter supports both Fabric compute engines in a single package: **Data Warehouse (T-SQL)** and **Lakehouse (Spark SQL)**. Microsoft splits this across two separate packages (`dbt-fabric` for T-SQL only, `dbt-fabricspark` for Spark only).

The Lakehouse adapter (`type: fabricspark`) uses Spark SQL via Livy sessions and supports tables, materialized lake views, and Python models natively. See the [Lakehouse guide](lakehouse.md) for details.

### Support for Python models

This adapter supports [Python models](https://docs.getdbt.com/docs/build/python-models) for both Fabric Data Warehouse and Fabric Lakehouse. Microsoft's dbt-fabric does not support Python models. To use this, just add information about your [Fabric Workspace](configuration.md#workspace_name) and [Lakehouse](configuration.md#lakehouse) to the `profiles.yml` file.

### Functions in dbt

This adapter supports creating [scalar functions](https://docs.getdbt.com/docs/build/functions?WT.mc_id=MVP_310840) as introduced in dbt Core 1.11, while neither of Microsoft's adapters does.

## Data governance & observability

### [Microsoft Purview integration](purview-integration.md)

This adapter can automatically sync dbt metadata to [Microsoft Purview Data Catalog](https://learn.microsoft.com/en-us/purview/?WT.mc_id=MVP_310840). The integration creates all table, column, and lineage entities directly via the Purview API — **no Purview scanning or live view configuration is required**. This eliminates the need to set up and schedule Fabric scans in Purview, saving both configuration effort and [scan capacity costs](https://learn.microsoft.com/en-us/purview/concept-elastic-data-map?WT.mc_id=MVP_310840).

- **Descriptions**: model and column descriptions from your dbt YAML files are pushed to Purview automatically after every run.
- **Business metadata**: dbt tags, materialization type, test names, test results, custom meta, and sync timestamps are attached to table entities via a custom `dbt_metadata` business metadata type.
- **Table-level lineage**: a full lineage graph based on dbt's `ref()` and `source()` dependencies is created in Purview. The built-in scanner only provides item-level lineage (e.g., Lakehouse → Notebook → Lakehouse) and [does not support sub-item lineage](https://learn.microsoft.com/en-us/purview/data-map-lineage-fabric?WT.mc_id=MVP_310840).

The sync runs via `{{ purview_sync() }}` as an `on-run-end` hook or as a manual `dbt run-operation`.

### [Catalog statistics](catalog-stats.md)

When you run `dbt docs generate`, this adapter includes **approximate row counts** for every table in the catalog output. Microsoft's upstream adapter does not include any statistics — the dbt docs site shows no table size information. With this adapter, table sizes are visible out of the box, with no extra configuration.

## Modeling features

### MERGE in incremental and microbatch models

!!! info

    MERGE has recently been added in Microsoft's version as well.

Incremental models in dbt-fabric support the `append`, `insert_overwrite`, and `delete+insert` strategies.

This adapter adds support for [MERGE](https://learn.microsoft.com/sql/t-sql/statements/merge-transact-sql?view=sql-server-ver17&WT.mc_id=MVP_310840).

```sql
{{ config(
    materialized='incremental',
    unique_key='id',
    incremental_strategy='merge'
) }}

select * from source('my_source', 'my_table')
{% if is_incremental() %}
where updated_at > (select max(updated_at) from {{ this }})
{% endif %}
```

When using the `merge` strategy, dbt will generate a `MERGE` statement that matches on the `unique_key` and updates existing records or inserts new records as necessary. The `unique_key` can be a single column or a list of columns.

The adapter will use the `merge` strategy by default if a `unique_key` is provided and no `incremental_strategy` is specified.

This also works for microbatch models:

```sql
{{ config(
    materialized='incremental',
    unique_key='id',
    incremental_strategy='microbatch',
    batch_size='day',
    begin='2025-01-01',
    event_time='created_at'
) }}

select * from source('my_source', 'my_table')
```

### [CLUSTER BY](cluster-by.md) support

Fabric Data Warehouse supports automatic data clustering via the `CLUSTER BY` clause, which organizes data physically on disk for better query performance. Microsoft's dbt-fabric adapter does not expose this feature. This adapter lets you configure clustering directly from your model config:

```sql
{{ config(
    materialized='table',
    cluster_by=['customer_id', 'order_date']
) }}
```

This works with regular tables, incremental models, and models with contract enforcement.

### Better support for [warehouse snapshots](warehouse-snapshots.md)

Both adapters support Fabric [warehouse snapshots](https://learn.microsoft.com/fabric/data-warehouse/warehouse-snapshot?WT.mc_id=MVP_310840), but Microsoft's implementation hooks into Python runtime internals (`atexit` handlers and the connection manager's `open()` method) rather than using dbt's own lifecycle. This adapter exposes a macro you can call from `on-run-start`, `on-run-end`, `post-hook`, or any other Jinja context — the standard dbt mechanism for orchestrating side effects.

### Support for [dbt-external-tables](external-tables.md)

This adapter provides [dbt-external-tables](https://github.com/dbt-labs/dbt-external-tables) compatibility macros that use Fabric's `OPENROWSET(BULK ...)` function to query Parquet, CSV, and JSONL files stored in Azure Blob Storage, ADLS, or OneLake. External sources are created as views wrapping OPENROWSET queries, so data is always fresh. See the [external tables guide](external-tables.md) for details.

## Developer experience

### Automatically find the host name of your Fabric Workspace

It can be tedious to find the correct host name for your Fabric Workspace, especially if you have separate Workspaces for development and production environments.

This adapter will automatically retrieve the host name for your Fabric Workspace, based on the [`workspace_name`](configuration.md#workspace_name) or [`workspace_id`](configuration.md#workspace_id) provided in the configuration.

This allows you to write a configuration like this:

```yaml
default:
  target: dev
  outputs:
    dev:
      type: fabric
      workspace: "gold_{{ env_var('FABRIC_ENV', 'dev') }}"
      database: dwh
      schema: dbt
```

Then, to run dbt against your production environment/Workspace, you can simply set the `FABRIC_ENV` environment variable to `prod` (if your Workspaces are named accordingly).

### Extended support for [authentication methods](authentication.md)

This adapter supports 11 authentication methods via a unified token provider, including methods not available in Microsoft's adapters: [workload identity](authentication.md#workload-identity-federated-credentials) (federated OIDC for CI/CD) and [custom token credentials](authentication.md#bring-your-own-tokencredential). Most methods contributed to this adapter have since been added upstream, but the newer options remain exclusive.

### [Community package support](community-packages.md)

This adapter includes **58 macro overrides** across 6 popular dbt packages to make them work with Fabric's T-SQL dialect:

| Package | Macro overrides | Tested version |
|---|---|---|
| [dbt-utils](https://github.com/dbt-labs/dbt-utils) | 16 | 1.3.0 |
| [dbt-date](https://github.com/godatadriven/dbt-date) | 15 | 0.17.2 |
| [dbt-expectations](https://github.com/calogica/dbt-expectations) | 10 | — |
| [insert_by_period](https://github.com/dbt-labs/dbt-labs-experimental-features/tree/main/insert_by_period) | 7 | — |
| [dbt-audit-helper](https://github.com/dbt-labs/dbt-audit-helper) | 5 | — |
| [dbt-external-tables](https://github.com/dbt-labs/dbt-external-tables) | 5 | 0.11.0 |

Microsoft's dbt-fabric has a single utility macro (`get_tables_by_pattern`). Microsoft's dbt-fabricspark has no community package support.

## Maintenance & quality

### Active development

| | dbt-fabric-samdebruyn | microsoft/dbt-fabric | microsoft/dbt-fabricspark |
|---|---|---|---|
| **Latest release** | v1.11.3b0 | v1.9.9 | v1.11.0 |
| **Release tags** | 67+ | 20+ | 8 |
| **Commits since Jan 2024** | 577 | 113 | ~278 |
| **Last commit** | 2026-05-16 | 2026-03-29 | 2026-05-16 |
| **dbt Core support** | 1.11, 1.12 | Up to 1.10 | Up to 1.11 |
| **Documentation** | [Dedicated docs site](https://dbt-fabric.debruyn.dev) | 1 page | README only |

### Test suite

This adapter has **444 integration test classes** across 141 test files, covering both the Fabric and FabricSpark adapters. Tests run automatically on every pull request across Python 3.11, 3.12, and 3.13. Microsoft's dbt-fabric has 117 test classes on Python 3.11 only. Microsoft's dbt-fabricspark has 141 test classes.

The test suite covers all standard dbt adapter operations plus adapter-specific features: Purview integration, Python models, warehouse snapshots, community package compatibility, and utility function overrides.

## Paid support

For companies that want to use this adapter in production, [I offer paid support and consulting services](https://debruyn.dev/services/).
