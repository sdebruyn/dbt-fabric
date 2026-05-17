# dbt-external-tables

**Tested version:** 0.11.0 | **Integration tested:** Yes

[dbt-external-tables](https://github.com/dbt-labs/dbt-external-tables) enables defining external data sources that dbt can reference via `{{ source() }}`. This adapter overrides the package's Fabric plugin to use [`OPENROWSET(BULK ...)`](https://learn.microsoft.com/sql/t-sql/functions/openrowset-bulk-transact-sql?view=fabric) instead of the Synapse-style `CREATE EXTERNAL TABLE` syntax that Fabric Data Warehouse does not support.

For full setup instructions, source configuration examples, and format-specific options, see the [external tables guide](../external-tables.md).

## Dispatch configuration

```yaml
dispatch:
  - macro_namespace: dbt_external_tables
    search_order: ['dbt', 'dbt_external_tables']
```

!!! note

    Unlike other packages, you do not need your project name in the search order for dbt-external-tables. The `dbt` entry is sufficient to route dispatch to the adapter's built-in overrides.

## Macro compatibility

Legend: :white_check_mark: = supported on Fabric, :x: = not supported on Fabric

Macros marked with **(override)** have a Fabric-specific implementation in this adapter. All other supported macros work without any adapter-specific override.

| Macro | Status | Notes |
|---|---|---|
| `stage_external_sources` | :white_check_mark: | Entry point run-operation |
| `create_external_table` | :white_check_mark: **(override)** | Creates a view wrapping `OPENROWSET(BULK ...)` instead of `CREATE EXTERNAL TABLE` |
| `refresh_external_table` | :white_check_mark: **(override)** | No-op (OPENROWSET reads live data on every query) |
| `get_external_build_plan` | :white_check_mark: | |
| `create_external_schema` | :white_check_mark: | |
| `dropif` | :white_check_mark: **(override)** | Drops the OPENROWSET view with `DROP VIEW IF EXISTS` |
| `exit_transaction` | :white_check_mark: | |
| `update_external_table_columns` | :x: | Not implemented for Fabric |
| `recover_partitions` | :x: | Hive-style partitions not supported |

## How it works

When you run `dbt run-operation stage_external_sources`, the overridden macros create **views** that wrap `OPENROWSET` queries. This means:

- External sources are queryable as regular views via `{{ source('my_external', 'my_table') }}`
- Data is always fresh -- `OPENROWSET` reads directly from the file on each query
- No refresh is needed (the `refresh_external_table` macro is a no-op)

## Supported file formats

| Format | Extension detection | Notes |
|---|---|---|
| Parquet | `.parquet` | Column schema inferred automatically if `columns` not defined |
| CSV | `.csv`, `.tsv` | Supports `header_row`, `fieldterminator`, `parser_version` options |
| JSONL | `.jsonl`, `.ldjson`, `.ndjson` | Line-delimited JSON |

## Supported storage locations

- **Fabric OneLake:** `https://onelake.dfs.fabric.microsoft.com/<workspace-id>/<lakehouse-id>/Files/<path>`
- **Azure Data Lake Storage Gen2:** `https://<account>.dfs.core.windows.net/<container>/<path>`
- **Azure Blob Storage:** `https://<account>.blob.core.windows.net/<container>/<path>`

Wildcards are supported (e.g., `*.parquet` to read all Parquet files in a folder).

## Quick example

```yaml
# sources.yml
sources:
  - name: my_external
    schema: dbo
    tables:
      - name: sales
        external:
          location: "https://onelake.dfs.fabric.microsoft.com/<workspace-id>/<lakehouse-id>/Files/data/sales.parquet"
          file_format: parquet
        columns:
          - name: id
            data_type: int
          - name: amount
            data_type: "decimal(10,2)"
```

```shell
dbt run-operation stage_external_sources
```

```sql
-- In a dbt model
select * from {{ source('my_external', 'sales') }}
```

## Limitations

- Fabric Data Warehouse does not support the `DELTA` format in `OPENROWSET`. For Delta Lake tables, use cross-database queries to a Lakehouse instead.
- `OPENROWSET` queries may be slower than querying data stored directly in the warehouse. For frequently accessed data, consider ingesting it into warehouse tables.
- Authentication to external storage is handled by Fabric. The files must be accessible from your Fabric workspace.
