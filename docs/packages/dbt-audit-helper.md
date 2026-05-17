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

Legend: ✅ = supported on Fabric, ❌ = not yet supported on Fabric

Macros marked with **(override)** have a T-SQL-compatible override in this adapter. All other supported macros work without any adapter-specific override.

### Relation and query comparison

| Macro | Status | Notes |
|---|---|---|
| `compare_queries` | ✅ **(override)** | `OFFSET/FETCH` instead of `LIMIT`; `ORDER BY` only when limit is used (T-SQL restriction) |
| `compare_relations` | ✅ **(override)** | Passes `limit` through to `compare_queries` for T-SQL pagination |
| `compare_column_values` | ✅ **(override)** | `CASE WHEN` instead of bare boolean expressions; adds `column_name` output, emoji toggle, custom relation names (v0.13.0) |
| `compare_relation_columns` | ✅ **(override)** | Uses `sys.columns` instead of `INFORMATION_SCHEMA` (not supported in Fabric distributed mode); explicit `ON` instead of `USING`; `CASE WHEN` instead of boolean expressions |
| `compare_row_counts` | ✅ | |
| `quick_are_queries_identical` | ✅ | |
| `quick_are_relations_identical` | ✅ | |

### Not yet supported

These macros depend on `compare_column_values_verbose`, which uses bare boolean expressions (`coalesce(..., false)`) that T-SQL does not support. A `fabric__compare_column_values_verbose` override is needed.

| Macro | Status | Notes |
|---|---|---|
| `compare_column_values_verbose` | ❌ | Bare boolean expressions unsupported in T-SQL |
| `compare_all_columns` | ❌ | Depends on `compare_column_values_verbose` |
| `compare_which_query_columns_differ` | ❌ | Depends on `compare_column_values_verbose` |
| `compare_which_relation_columns_differ` | ❌ | Depends on `compare_column_values_verbose` |
| `compare_and_classify_query_results` | ❌ | Bare boolean expressions unsupported in T-SQL |
| `compare_and_classify_relation_rows` | ❌ | Bare boolean expressions unsupported in T-SQL |

## Known limitation

The `compare_relation_columns` model must be materialized as a `table` rather than a `view`. Fabric's distributed query mode does not support `sys.columns` queries inside view definitions.
