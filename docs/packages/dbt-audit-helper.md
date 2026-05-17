# dbt-audit-helper

**Tested version:** 0.13.0 | **Integration tested:** Yes

[dbt-audit-helper](https://github.com/dbt-labs/dbt-audit-helper) provides macros for comparing relations and queries during data model refactoring.

## Dispatch configuration

```yaml
dispatch:
  - macro_namespace: audit_helper
    search_order: ['your_project_name', 'dbt', 'audit_helper']
```

## Macro compatibility

Legend: ✅ = supported on Fabric, ❌ = not supported on Fabric

Macros marked with **(override)** have a T-SQL-compatible override in this adapter. All other supported macros work without any adapter-specific override.

### Relation and query comparison

| Macro | Status | Notes |
|---|---|---|
| `compare_queries` | ✅ **(override)** | `OFFSET/FETCH` instead of `LIMIT`; `ORDER BY` only when limit is used (T-SQL restriction) |
| `compare_relations` | ✅ **(override)** | Passes `limit` through to `compare_queries` for T-SQL pagination |
| `compare_column_values` | ✅ **(override)** | `CASE WHEN` instead of bare boolean expressions; adds `column_name` output, emoji toggle, custom relation names (v0.13.0) |
| `compare_column_values_verbose` | ✅ **(override)** | `CASE WHEN` → 0/1 integers instead of bare boolean expressions and `coalesce(..., false)` |
| `compare_all_columns` | ✅ **(override)** | Explicit `GROUP BY` instead of positional; `ORDER BY` moved out of CTE; `sum()` on 0/1 integer columns |
| `compare_relation_columns` | ✅ **(override)** | Uses `sys.columns` instead of `INFORMATION_SCHEMA` (not supported in Fabric distributed mode); explicit `ON` instead of `USING`; `CASE WHEN` instead of boolean expressions |
| `compare_row_counts` | ✅ | |
| `compare_which_query_columns_differ` | ✅ | Works via the adapter's `bool_or` override (`MAX(CASE WHEN ... THEN 1 ELSE 0 END)`) |
| `compare_which_relation_columns_differ` | ✅ | Delegates to `compare_which_query_columns_differ` |
| `quick_are_queries_identical` | ✅ | |
| `quick_are_relations_identical` | ✅ | |

### Not supported

| Macro | Status | Notes |
|---|---|---|
| `compare_and_classify_query_results` | ❌ | Not dispatched; uses `true`/`false` literals (no boolean type in T-SQL) |
| `compare_and_classify_relation_rows` | ❌ | Delegates to `compare_and_classify_query_results` |

## Known limitation

The `compare_relation_columns` model must be materialized as a `table` rather than a `view`. Fabric's distributed query mode does not support `sys.columns` queries inside view definitions.
