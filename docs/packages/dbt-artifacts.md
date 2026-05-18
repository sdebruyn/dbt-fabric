# dbt_artifacts

**Tested version:** 2.10.1 | **Integration tested:** Yes (Lakehouse only)

[dbt_artifacts](https://github.com/brooklyn-data/dbt_artifacts) persists dbt run metadata (model runs, test results, sources, exposures, seeds, snapshots) into tables in your warehouse so you can query and monitor your project's execution history.

## Compute engine support

| Compute engine | Status |
|---|---|
| Lakehouse (FabricSpark) | :white_check_mark: Tested |
| Data Warehouse (Fabric) | :x: Not compatible — upstream PR [brooklyn-data/dbt_artifacts#529](https://github.com/brooklyn-data/dbt_artifacts/pull/529) adds Synapse and Fabric DW support |

## Dispatch configuration

```yaml
dispatch:
  - macro_namespace: dbt_artifacts
    search_order: ['your_project_name', 'dbt', 'dbt_artifacts']
  - macro_namespace: dbt_utils
    search_order: ['your_project_name', 'dbt', 'dbt_utils']
```

## Required project configuration

dbt_artifacts must use the `delta` file format on Lakehouse, otherwise the on-run-end hooks fail to insert rows.

```yaml
models:
  dbt_artifacts:
    +file_format: delta
```

## Macro compatibility

All dbt_artifacts macros work on Lakehouse without adapter-specific overrides. The package targets Spark SQL via dbt-spark's macro implementations, which this adapter inherits.

## Notes

- Depends on [dbt-utils](dbt-utils.md). Include the dbt-utils dispatch configuration alongside the dbt_artifacts one.
- Enable the package's on-run-end upload hooks by adding them to your `dbt_project.yml`:

  ```yaml
  on-run-end:
    - "{{ dbt_artifacts.upload_results(results) }}"
  ```
- For microbatch incremental models that store artifacts over time, configure `partition_by` on the timestamp column (the integration tests partition by `transaction_ts`).
