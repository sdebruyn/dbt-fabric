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

Legend: :white_check_mark: = supported on Fabric, :x: = not supported on Fabric

Macros marked with **(override)** have a T-SQL-compatible override in this adapter. All other supported macros work without any adapter-specific override.

### Generic tests

| Macro | Status | Notes |
|---|---|---|
| `accepted_range` | :white_check_mark: | |
| `at_least_one` | :white_check_mark: **(override)** | Subquery requires column alias; uses `TOP 1` instead of `LIMIT 1` |
| `cardinality_equality` | :white_check_mark: | |
| `equal_rowcount` | :white_check_mark: **(override)** | Uses `FULL JOIN` with explicit `ON` clause; `COALESCE` for NULL-safe comparison |
| `equality` | :white_check_mark: | |
| `expression_is_true` | :white_check_mark: **(override)** | T-SQL boolean handling differences |
| `fewer_rows_than` | :white_check_mark: **(override)** | Uses `FULL JOIN` with explicit `ON` clause; `CASE` instead of `GREATEST()` |
| `mutually_exclusive_ranges` | :white_check_mark: **(override)** | T-SQL window function and boolean syntax |
| `not_accepted_values` | :white_check_mark: | |
| `not_constant` | :white_check_mark: | |
| `not_empty_string` | :white_check_mark: **(override)** | T-SQL string function syntax |
| `not_null_proportion` | :white_check_mark: | |
| `recency` | :white_check_mark: | |
| `relationships_where` | :white_check_mark: | Upstream defaults `from_condition`/`to_condition` to `1=1`, which is T-SQL-safe; no override needed |
| `sequential_values` | :white_check_mark: **(override)** | T-SQL requires table alias; uses `PARTITION BY` syntax |
| `unique_combination_of_columns` | :white_check_mark: | |

### SQL helpers

| Macro | Status | Notes |
|---|---|---|
| `date_spine` | :white_check_mark: | |
| `deduplicate` | :white_check_mark: **(override)** | Uses T-SQL `ROW_NUMBER()` pattern |
| `generate_series` | :white_check_mark: **(override)** | Uses T-SQL `generate_series()` function |
| `generate_surrogate_key` | :white_check_mark: **(override)** | Uses `HASHBYTES('md5', ...)` with T-SQL concat and cast |
| `get_column_values` | :white_check_mark: | |
| `get_filtered_columns_in_relation` | :white_check_mark: | |
| `get_query_results_as_dict` | :white_check_mark: | |
| `get_relations_by_pattern` | :white_check_mark: | |
| `get_relations_by_prefix` | :white_check_mark: | |
| `get_single_value` | :white_check_mark: | |
| `group_by` | :x: | T-SQL does not support positional `GROUP BY` (e.g., `GROUP BY 1, 2`) |
| `haversine_distance` | :white_check_mark: | |
| `nullcheck` | :white_check_mark: | |
| `nullcheck_table` | :white_check_mark: | |
| `pivot` | :white_check_mark: | |
| `safe_add` | :white_check_mark: | |
| `safe_divide` | :white_check_mark: | |
| `safe_subtract` | :white_check_mark: | |
| `star` | :white_check_mark: | |
| `union_relations` | :white_check_mark: | |
| `unpivot` | :white_check_mark: | |
| `width_bucket` | :white_check_mark: **(override)** | Implements bucket logic with T-SQL arithmetic (no native `WIDTH_BUCKET`) |

### Web macros

| Macro | Status | Notes |
|---|---|---|
| `get_url_host` | :white_check_mark: | |
| `get_url_parameter` | :white_check_mark: | |
| `get_url_path` | :white_check_mark: | |

### Jinja helpers

| Macro | Status | Notes |
|---|---|---|
| `log_info` | :white_check_mark: | |
| `pretty_log_format` | :white_check_mark: | |
| `pretty_time` | :white_check_mark: | |
| `slugify` | :white_check_mark: | |

### Schema cleanup (internal)

These macros are used for schema management, not typically called directly in models:

| Macro | Status | Notes |
|---|---|---|
| `drop_old_relations` | :white_check_mark: **(override)** | Uses `sys.tables`/`sys.views` system views |
| `drop_schema_by_name` | :white_check_mark: **(override)** | Uses dbt's `drop_schema` API |
| `drop_schemas_by_prefixes` | :white_check_mark: **(override)** | Iterates schemas using T-SQL system catalog |
| `get_tables_by_pattern_sql` | :white_check_mark: **(override)** | Queries `INFORMATION_SCHEMA` with T-SQL-compatible pattern matching |

