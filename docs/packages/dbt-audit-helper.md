# dbt-audit-helper

**Integration tested:** No

[dbt-audit-helper](https://github.com/dbt-labs/dbt-audit-helper) provides macros for comparing relations and queries during data model refactoring.

!!! warning

    This package is **not** integration tested in CI. The macro overrides are expected to work based on manual validation, but edge cases may exist.

## Dispatch configuration

```yaml
dispatch:
  - macro_namespace: audit_helper
    search_order: ['your_project_name', 'dbt', 'audit_helper']
```

## Macro compatibility

<!-- TODO: fill in full macro table like dbt-utils -->
