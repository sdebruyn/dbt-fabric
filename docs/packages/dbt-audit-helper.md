# dbt-audit-helper

**Tested version:** 0.14.0 | **Integration tested:** Yes

[dbt-audit-helper](https://github.com/dbt-labs/dbt-audit-helper) provides macros for comparing relations and queries during data model refactoring.

## Dispatch configuration

```yaml
dispatch:
  - macro_namespace: audit_helper
    search_order: ['your_project_name', 'dbt', 'audit_helper']
```

## Macro compatibility

Legend: :white_check_mark: = supported on Fabric, :x: = not supported on Fabric

Macros marked with **(override)** have a T-SQL-compatible override in this adapter. All other supported macros work without any adapter-specific override.

### Relation and query comparison

| Macro | Status | Notes |
|---|---|---|
| `compare_queries` | :white_check_mark: **(override)** | `OFFSET/FETCH` instead of `LIMIT`; `ORDER BY` only when limit is used (T-SQL restriction) |
| `compare_relations` | :white_check_mark: **(override)** | Passes `limit` through to `compare_queries` for T-SQL pagination |
| `compare_column_values` | :white_check_mark: **(override)** | `CASE WHEN` instead of bare boolean expressions; adds `column_name` output, emoji toggle, custom relation names (v0.13.0) |
| `compare_column_values_verbose` | :white_check_mark: **(override)** | `CASE WHEN` → 0/1 integers instead of bare boolean expressions and `coalesce(..., false)` |
| `compare_all_columns` | :white_check_mark: **(override)** | Explicit `GROUP BY` instead of positional; `ORDER BY` moved out of CTE; `sum()` on 0/1 integer columns |
| `compare_relation_columns` | :white_check_mark: **(override)** | Fetches metadata via `run_query()` (separate statement) to avoid distributed mode restrictions on `sys.columns`; builds comparison from `VALUES` literals |
| `compare_row_counts` | :white_check_mark: | |
| `compare_which_query_columns_differ` | :white_check_mark: | Works via the adapter's `bool_or` override (`MAX(CASE WHEN ... THEN 1 ELSE 0 END)`) |
| `compare_which_relation_columns_differ` | :white_check_mark: | Delegates to `compare_which_query_columns_differ` |
| `quick_are_queries_identical` | :white_check_mark: | |
| `quick_are_relations_identical` | :white_check_mark: | |
| `compare_and_classify_query_results` | :white_check_mark: **(override)** | 1/0 integers instead of `true`/`false`; companion overrides on `_classify_audit_row_status` (explicit `= 1` comparisons) and `_count_num_rows_in_status` (dense_rank trick — `COUNT(DISTINCT ...) OVER ()` is not supported in T-SQL) |
| `compare_and_classify_relation_rows` | :white_check_mark: | Delegates to `compare_and_classify_query_results` |

## Implementation notes

### `compare_relation_columns` and `run_query()`

The `compare_relation_columns` override uses `run_query()` to fetch column metadata from `sys.columns` in a separate statement before the model is materialized. This avoids Fabric's distributed processing mode restriction that rejects `sys.*` queries inside `CREATE TABLE AS SELECT` statements. The materialized SQL only contains `VALUES` literals with the pre-fetched metadata.

### Integration test limitations

The `compare_relation_columns` equality test is disabled in CI because the upstream package's expected-results seed CSV uses uppercase column headers (`COLUMN_NAME`) while the model outputs lowercase (`column_name`). Fabric's `Latin1_General_100_BIN2_UTF8` collation makes identifiers case-sensitive, so the equality comparison fails. The macro itself works correctly — the model builds with the right data.
