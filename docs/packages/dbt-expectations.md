# dbt-expectations

**Integration tested:** No

[dbt-expectations](https://github.com/calogica/dbt-expectations) provides data quality tests inspired by Great Expectations.

!!! warning

    This package is **not** integration tested in CI. The macro overrides are expected to work based on manual validation, but edge cases may exist.

## Dispatch configuration

```yaml
dispatch:
  - macro_namespace: dbt_expectations
    search_order: ['your_project_name', 'dbt', 'dbt_expectations']
```

## Macro compatibility

<!-- TODO: fill in full macro table like dbt-utils -->
