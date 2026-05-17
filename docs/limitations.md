# Known limitations

This page documents platform limitations of Microsoft Fabric that affect dbt models. These are not adapter bugs — they are constraints of the underlying compute engines that cannot be worked around with macro overrides.

## Data Warehouse (T-SQL)

### SQL dialect limitations

| Limitation | Impact | Workaround |
|---|---|---|
| **No regular expressions** | `REGEXP`, `REGEXP_LIKE`, `RLIKE` do not exist | Use `LIKE` or `PATINDEX` for simple patterns; complex regex is not possible |
| **No boolean type** | Cannot use bare `TRUE`/`FALSE` in expressions or cast to boolean | Use `CASE WHEN` expressions or integer `0`/`1` |
| **No positional GROUP BY / ORDER BY** | `GROUP BY 1, 2` is not valid | Use explicit column names or expressions |
| **No nested CTEs in views** | A view definition cannot contain CTEs that reference other CTEs | Materialize as `table` instead of `view`, or restructure the query |
| **No CTEs inside subqueries** | CTEs cannot be used inside `FROM (...)` subqueries | Use inline subqueries or `CROSS APPLY VALUES` to restructure |
| **No `WIDTH_BUCKET()` function** | The standard SQL binning function does not exist | The adapter emulates it with `CEILING` and `CASE` |
| **No `DATE(y, m, d)` constructor** | No function to construct a date from year, month, day | Use `DATEFROMPARTS(y, m, d)` or compile-time Jinja |
| **No interval arithmetic** | Cannot use `+ INTERVAL '6 days'` syntax | Use `DATEADD(day, 6, ...)` |
| **No ISO week truncation** | No `DATE_TRUNC('isoweek', ...)` | Use `DATEADD`/`DATEDIFF` week arithmetic from day 0 |

### DDL and feature limitations

| Limitation | Impact | Workaround |
|---|---|---|
| **No cascading drops** | Dropping a table does not cascade to dependent views | Drop dependent views first, or rebuild them after |
| **No `PERSIST DOCS`** | Cannot persist table/column descriptions via T-SQL DDL | Use [Purview integration](purview-integration.md) for metadata |
| **No materialized views** | Fabric Data Warehouse does not support materialized views | Use tables with incremental materialization |
| **No aggregate functions (UDF)** | `CREATE AGGREGATE` does not exist | Use built-in aggregate functions only |
| **No function volatility** | T-SQL scalar functions have no `DETERMINISTIC`/`STABLE`/`VOLATILE` metadata | Not applicable — all functions are treated the same |
| **No Python functions** | Cannot create Python UDFs in Data Warehouse | Use [Python models](python-models.md) via Livy instead |
| **No `CREATE EXTERNAL TABLE`** | Synapse-style external tables are not supported | Use [OPENROWSET views](external-tables.md) |
| **Type inference for `bigint`** | Uncast integer literals show as `numeric`, not `bigint` | Explicitly cast with `CAST(... AS bigint)` |

### Ephemeral model limitations

Ephemeral models (which compile to CTEs) cannot be used inside view materializations due to the nested CTE restriction. If your model references an ephemeral model, materialize it as a `table` instead:

```yaml
models:
  my_project:
    my_model:
      +materialized: table
```

## Lakehouse (Spark SQL)

### SQL dialect limitations

| Limitation | Impact | Workaround |
|---|---|---|
| **No `information_schema`** | `information_schema.tables`, `information_schema.columns` do not exist | Use `SHOW TABLES`, `SHOW COLUMNS`, `DESCRIBE` |
| **No distinct window functions** | `COUNT(DISTINCT ...) OVER (...)` is not supported | Use subqueries or self-joins |
| **No subqueries in `DELETE`** | `DELETE FROM ... WHERE x IN (SELECT ...)` fails | Use `MERGE INTO` as an alternative |
| **No `CREATE FUNCTION`** | Spark SQL in Fabric does not support `CREATE FUNCTION` (Databricks-only) | Not available — use Python models for custom logic |
| **No `SHALLOW CLONE`** | Delta Lake clone operations are Databricks-specific | Not available in Fabric |
| **3-part name restrictions in DML** | `INSERT INTO` fails with 3-part names when temporary views exist in the session | Strip database component with `.include(database=false)` |
| **`generate_series` compilation errors** | The `upper bound must be positive` error in Spark's implementation | Not available for certain use cases |

### DDL and feature limitations

| Limitation | Impact | Workaround |
|---|---|---|
| **No cascading drops** | Dropping a source table does not drop dependent materialized views | Drop dependent views first |
| **No `DEFAULT` in `ALTER TABLE ADD COLUMN`** | Delta tables do not support default values when adding columns | Backfill defaults after adding the column |
| **No column drops from Delta tables** | `ALTER TABLE DROP COLUMN` is not supported | Recreate the table without the column |
| **No `NOT NULL` constraints in CTAS** | `CREATE TABLE AS SELECT` cannot enforce `NOT NULL` | Use `ALTER TABLE CHANGE COLUMN SET NOT NULL` after creation (where supported) |
| **Limited `ALTER TABLE` constraint enforcement** | `ALTER TABLE CHANGE COLUMN SET NOT NULL` is not supported on Fabric Delta tables | Constraints cannot be enforced after table creation |
| **No SQL `GRANT` statements** | Access control is workspace-level, not SQL-level | Manage access through Fabric workspace settings |
| **No `STRUCT` type** | BigQuery-specific type; not available in Spark SQL on Fabric | Use separate columns or JSON strings |

### Incremental model limitations

| Limitation | Strategy affected | Details |
|---|---|---|
| **Column removal breaks merge** | `merge` | `DELTA_MERGE_UNRESOLVED_EXPRESSION` when merging after a column was removed upstream |
| **`sync_all_columns` not supported** | `merge` | Cannot drop columns from Delta tables, so schema sync is impossible |
| **`partition_by` required** | `insert_overwrite`, `microbatch` | These strategies require `partition_by` to be set in the model config |
