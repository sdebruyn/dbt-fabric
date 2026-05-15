# Comparison between dbt-fabric and dbt-fabric-samdebruyn

This adapter has all the features of [Microsoft's dbt-fabric adapter](https://github.com/microsoft/dbt-fabric), plus some additional features.
The following features are exclusive to dbt-fabric-samdebruyn:

## No ODBC driver required

This adapter uses Microsoft's official [`mssql-python`](https://github.com/microsoft/mssql-python) driver instead of pyODBC. This is a pure Python driver for SQL Server and Microsoft Fabric that communicates over the TDS protocol natively, without requiring any system-level ODBC components.

Microsoft's upstream dbt-fabric adapter depends on pyODBC, which requires:

- A system-level ODBC driver manager (unixODBC on Linux/macOS)
- The Microsoft ODBC Driver for SQL Server (`msodbcsql18`)
- Platform-specific installation steps that vary between Linux distributions, macOS, and Windows

With dbt-fabric-samdebruyn, none of this is needed. Installation is a single `pip install` or `uv add` command, with no platform-specific setup. This eliminates a common source of installation issues and makes the adapter work consistently across all platforms, including containerized environments.

## Fabric Lakehouse (Spark SQL) support

This adapter supports both Fabric compute engines: **Data Warehouse (T-SQL)** and **Lakehouse (Spark SQL)**. Microsoft's dbt-fabric only supports Data Warehouse.

The Lakehouse adapter (`type: fabricspark`) uses Spark SQL via Livy sessions and supports tables, materialized lake views, and Python models natively. See the [Lakehouse guide](lakehouse.md) for details.

## dbt Core 1.11 support

This adapter is compatible with dbt Core 1.11, while Microsoft's dbt-fabric adapter is only compatible with dbt Core 1.10.

## Functions in dbt

This adapter supports creating scalar functions as introduced in dbt Core 1.11, while Microsoft's dbt-fabric does not.

## Support for Python models

This adapter supports [Python models](https://docs.getdbt.com/docs/build/python-models). To use this, just add information about your [Fabric Workspace](configuration.md#workspace_name) and [Lakehouse](configuration.md#lakehouse) to the `profiles.yml` file.

## Automatically find the host name of your Fabric Workspace

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

## Extended support for [authentication methods](configuration.md#authentication)

While most authentication methods have been contributed back to dbt-fabric, some newer options are only available in this adapter.

## MERGE in incremental and microbatch models

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
{% endif %}
```

## [CLUSTER BY](cluster-by.md) support

Fabric Data Warehouse supports automatic data clustering via the `CLUSTER BY` clause, which organizes data physically on disk for better query performance. Microsoft's dbt-fabric adapter does not expose this feature. This adapter lets you configure clustering directly from your model config:

```sql
{{ config(
    materialized='table',
    cluster_by=['customer_id', 'order_date']
) }}
```

This works with regular tables, incremental models, and models with contract enforcement.

## Better support for [warehouse snapshots](warehouse-snapshots.md)

Both adapters support Fabric [warehouse snapshots](https://learn.microsoft.com/fabric/data-warehouse/warehouse-snapshot?WT.mc_id=MVP_310840), but Microsoft's implementation hijacks Python runtime components and does not respect the proper dbt lifecycle. This adapter exposes a macro you can call from `on-run-start`, `on-run-end`, `post-hook`, or any other Jinja context — giving you full control over when and how often snapshots are taken.

## [Catalog statistics](catalog-stats.md)

When you run `dbt docs generate`, this adapter includes **approximate row counts** for every table in the catalog output. Microsoft's upstream adapter does not include any statistics — the dbt docs site shows no table size information. With this adapter, table sizes are visible out of the box, with no extra configuration.

## Better support for popular packages

[dbt-utils](https://hub.getdbt.com/dbt-labs/dbt_utils/latest/) is already fully supported and more packages are being tested and added.

## Plenty of bugfixes

The quality of this adapter is guaranteed by an extensive test suite of integration tests, which run on every change. Through this process, quite a few bugs have been found and fixed.

## More on the [roadmap](roadmap.md)

See the [roadmap](roadmap.md) for ideas on future improvements, including:

- Spark SQL and T-SQL models in the same project
- External Iceberg and Delta Lake tables via OneLake shortcuts
- External catalog integration (Unity Catalog, Dremio, Iceberg REST Catalog)
- [Create an issue with your idea](https://github.com/sdebruyn/dbt-fabric/issues)

## Paid support

For companies that want to use this adapter in production, [I offer paid support and consulting services](https://debruyn.dev/services/).
