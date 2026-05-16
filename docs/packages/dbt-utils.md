# dbt-utils

**Tested version:** 1.3.3 | **Macro overrides:** 16 | **Integration tested:** Yes

[dbt-utils](https://github.com/dbt-labs/dbt-utils) is the most widely used dbt community package, providing generic tests, SQL helpers, and schema management utilities.

## Dispatch configuration

```yaml
dispatch:
  - macro_namespace: dbt_utils
    search_order: ['your_project_name', 'dbt', 'dbt_utils']
```

## Overridden macros

The following macros have T-SQL-compatible overrides in this adapter:

### Generic tests

| Macro | Why overridden |
|---|---|
| `test_at_least_one` | Subquery requires column alias in T-SQL; uses `TOP 1` instead of `LIMIT 1` |
| `test_expression_is_true` | T-SQL boolean handling differences |
| `test_not_empty_string` | T-SQL string function syntax |
| `test_mutually_exclusive_ranges` | T-SQL window function and boolean syntax |
| `test_relationships_where` | T-SQL subquery syntax |
| `test_sequential_values` | T-SQL requires table alias for subqueries; uses `PARTITION BY` syntax |
| `test_not_null_where` | T-SQL `WHERE` clause handling |
| `test_unique_where` | T-SQL `WHERE` clause handling |

### SQL helpers

| Macro | Why overridden |
|---|---|
| `deduplicate` | Uses T-SQL `ROW_NUMBER()` pattern without introducing extra columns |
| `generate_series` | Uses T-SQL `generate_series()` function |
| `generate_surrogate_key` | Uses `HASHBYTES('md5', ...)` with T-SQL concat and cast |
| `get_tables_by_pattern_sql` | Queries `INFORMATION_SCHEMA` with T-SQL-compatible pattern matching |
| `width_bucket` | Implements bucket logic with T-SQL arithmetic (no native `WIDTH_BUCKET`) |

### Schema cleanup

| Macro | Why overridden |
|---|---|
| `drop_old_relations` | Uses `sys.tables`/`sys.views` system views |
| `drop_schema_by_name` | Uses dbt's `drop_schema` API |
| `drop_schemas_by_prefixes` | Iterates schemas using T-SQL system catalog |

## Unsupported generic tests

The `group_by` generic test is **not supported**. T-SQL does not support positional `GROUP BY` (e.g., `GROUP BY 1, 2`), which is required by the test's implementation. All other dbt-utils generic tests work as expected.

## Additional macros

This adapter also provides two standalone T-SQL utility macros that complement dbt-utils:

- `surrogate_key` -- Enhanced version with configurable `col_type` and `use_binary_hash` options for T-SQL-specific surrogate key generation
- `cast_hash_to_str` -- Converts a `varbinary` hash to `varchar(32)` for use in tools that require string keys (e.g., Power BI relationships)

## Macros that work without override

All other dbt-utils macros (e.g., `star`, `pivot`, `unpivot`, `union_relations`, `get_column_values`, `date_spine`, etc.) work on Fabric without any adapter-specific override.
