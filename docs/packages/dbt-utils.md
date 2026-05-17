# dbt-utils

**Tested version:** 1.3.3 | **Integration tested:** Yes

[dbt-utils](https://github.com/dbt-labs/dbt-utils) is the most widely used dbt community package, providing generic tests, SQL helpers, and schema management utilities.

## Dispatch configuration

```yaml
dispatch:
  - macro_namespace: dbt_utils
    search_order: ['your_project_name', 'dbt', 'dbt_utils']
```

## Macro compatibility

Legend: ✅ = supported on Fabric, ❌ = not supported on Fabric

Macros marked with **(override)** have a T-SQL-compatible override in this adapter. All other supported macros work without any adapter-specific override.

### Generic tests

| Macro | Status | Notes |
|---|---|---|
| `accepted_range` | ✅ | |
| `at_least_one` | ✅ **(override)** | Subquery requires column alias; uses `TOP 1` instead of `LIMIT 1` |
| `cardinality_equality` | ✅ | |
| `equal_rowcount` | ✅ **(override)** | T-SQL subquery and comparison syntax |
| `equality` | ✅ | |
| `expression_is_true` | ✅ **(override)** | T-SQL boolean handling differences |
| `fewer_rows_than` | ✅ **(override)** | T-SQL subquery and comparison syntax |
| `mutually_exclusive_ranges` | ✅ **(override)** | T-SQL window function and boolean syntax |
| `not_accepted_values` | ✅ | |
| `not_constant` | ✅ | |
| `not_empty_string` | ✅ **(override)** | T-SQL string function syntax |
| `not_null_proportion` | ✅ | |
| `not_null_where` | ✅ **(override)** | T-SQL `WHERE` clause handling |
| `recency` | ✅ | |
| `relationships_where` | ✅ **(override)** | T-SQL subquery syntax |
| `sequential_values` | ✅ **(override)** | T-SQL requires table alias; uses `PARTITION BY` syntax |
| `unique_combination_of_columns` | ✅ | |
| `unique_where` | ✅ **(override)** | T-SQL `WHERE` clause handling |

### SQL helpers

| Macro | Status | Notes |
|---|---|---|
| `date_spine` | ✅ | |
| `deduplicate` | ✅ **(override)** | Uses T-SQL `ROW_NUMBER()` pattern |
| `generate_series` | ✅ **(override)** | Uses T-SQL `generate_series()` function |
| `generate_surrogate_key` | ✅ **(override)** | Uses `HASHBYTES('md5', ...)` with T-SQL concat and cast |
| `get_column_values` | ✅ | |
| `get_filtered_columns_in_relation` | ✅ | |
| `get_query_results_as_dict` | ✅ | |
| `get_relations_by_pattern` | ✅ | |
| `get_relations_by_prefix` | ✅ | |
| `get_single_value` | ✅ | |
| `group_by` | ❌ | T-SQL does not support positional `GROUP BY` (e.g., `GROUP BY 1, 2`) |
| `haversine_distance` | ✅ | |
| `nullcheck` | ✅ | |
| `nullcheck_table` | ✅ | |
| `pivot` | ✅ | |
| `safe_add` | ✅ | |
| `safe_divide` | ✅ | |
| `safe_subtract` | ✅ | |
| `star` | ✅ | |
| `union_relations` | ✅ | |
| `unpivot` | ✅ | |
| `width_bucket` | ✅ **(override)** | Implements bucket logic with T-SQL arithmetic (no native `WIDTH_BUCKET`) |

### Web macros

| Macro | Status | Notes |
|---|---|---|
| `get_url_host` | ✅ | |
| `get_url_parameter` | ✅ | |
| `get_url_path` | ✅ | |

### Jinja helpers

| Macro | Status | Notes |
|---|---|---|
| `log_info` | ✅ | |
| `pretty_log_format` | ✅ | |
| `pretty_time` | ✅ | |
| `slugify` | ✅ | |

### Schema cleanup (internal)

These macros are used for schema management, not typically called directly in models:

| Macro | Status | Notes |
|---|---|---|
| `drop_old_relations` | ✅ **(override)** | Uses `sys.tables`/`sys.views` system views |
| `drop_schema_by_name` | ✅ **(override)** | Uses dbt's `drop_schema` API |
| `drop_schemas_by_prefixes` | ✅ **(override)** | Iterates schemas using T-SQL system catalog |
| `get_tables_by_pattern_sql` | ✅ **(override)** | Queries `INFORMATION_SCHEMA` with T-SQL-compatible pattern matching |

