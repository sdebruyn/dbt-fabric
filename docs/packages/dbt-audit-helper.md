# dbt-audit-helper

**Macro overrides:** 5 | **Integration tested:** No

[dbt-audit-helper](https://github.com/dbt-labs/dbt-audit-helper) provides macros for comparing relations and queries during data model refactoring. The overrides address T-SQL incompatibilities with `EXCEPT`, `INTERSECT`, type casting, and system catalog queries.

!!! warning

    This package is **not** integration tested in CI. The macro overrides are expected to work based on manual validation, but edge cases may exist.

## Dispatch configuration

```yaml
dispatch:
  - macro_namespace: audit_helper
    search_order: ['your_project_name', 'dbt', 'audit_helper']
```

## Overridden macros

| Macro | Why overridden |
|---|---|
| `compare_relations` | Uses adapter column introspection with T-SQL-compatible set operations |
| `compare_queries` | Replaces PostgreSQL `EXCEPT`/`INTERSECT` syntax with dbt cross-database macros |
| `compare_column_values` | T-SQL `FULL OUTER JOIN` with `COALESCE` and `CASE` expressions |
| `compare_relation_columns` | Queries `INFORMATION_SCHEMA.COLUMNS` (including `tempdb`) for column metadata |
| `get_columns_in_relation_sql` | Helper that queries T-SQL system views for column ordinal position and data types |

## Macros that work without override

All other dbt-audit-helper macros work on Fabric without any adapter-specific override.
