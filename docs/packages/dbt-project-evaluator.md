# dbt-project-evaluator

**Tested version:** 1.2.4 | **Integration tested:** Yes (Lakehouse only)

[dbt-project-evaluator](https://github.com/dbt-labs/dbt-project-evaluator) audits your dbt project against best practices: model naming, documentation coverage, test coverage, DAG structure, modeling conventions, and more.

## Compute engine support

| Compute engine | Status |
|---|---|
| Lakehouse (FabricSpark) | :white_check_mark: Tested |
| Data Warehouse (Fabric) | :x: Not compatible — upstream PR [dbt-labs/dbt-project-evaluator#576](https://github.com/dbt-labs/dbt-project-evaluator/pull/576) adds Fabric DW support |

## Dispatch configuration

```yaml
dispatch:
  - macro_namespace: dbt_project_evaluator
    search_order: ['your_project_name', 'dbt', 'dbt_project_evaluator']
  - macro_namespace: dbt_utils
    search_order: ['your_project_name', 'dbt', 'dbt_utils']
```

## Macro compatibility

All dbt-project-evaluator macros work on Lakehouse without adapter-specific overrides — the package's logic relies on dbt's graph context and standard SQL operations that Spark SQL handles natively.

## Notes

- Depends on [dbt-utils](dbt-utils.md). Include the dbt-utils dispatch configuration alongside the project-evaluator one.
- If your project DAG depth exceeds the default, override `max_depth_dag` in your `dbt_project.yml` `vars`. The integration tests set it to `9`:

  ```yaml
  vars:
    max_depth_dag: 9
  ```
- The package's `integration_tests` subdirectory has an internal local dependency (`exclude_package/`) that cannot be resolved when installed as a git subdirectory package. This only affects running the package's own integration tests, not normal use of the package against your project.
