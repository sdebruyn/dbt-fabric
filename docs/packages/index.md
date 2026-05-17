# Package support

This adapter includes macro overrides that make popular dbt community packages work with Microsoft Fabric. Without these overrides, most community packages fail because they generate PostgreSQL-compatible SQL that neither T-SQL nor Fabric's Spark SQL accepts.

## How it works

Community packages use dbt's [dispatch system](https://docs.getdbt.com/reference/dbt-jinja-functions/dispatch) to allow adapters to override their macros. This adapter ships `fabric__` and `fabricspark__` prefixed versions of incompatible macros in its built-in macro directories.

When a package macro dispatches to find an adapter-specific implementation, dbt looks for `fabric__<macro_name>` (Data Warehouse) or `fabricspark__<macro_name>` (Lakehouse). If this adapter provides one, it takes priority over the package's default implementation.

### Required dispatch configuration

To activate the macro overrides, you must add a `dispatch` configuration to your `dbt_project.yml` for each package you use. Without this, dbt's default dispatch does not search the adapter's internal macros for package-namespaced macros.

=== "Data Warehouse"

    ```yaml
    dispatch:
      - macro_namespace: dbt_utils
        search_order: ['your_project_name', 'dbt', 'dbt_utils']
      - macro_namespace: dbt_date
        search_order: ['your_project_name', 'dbt', 'dbt_date']
      - macro_namespace: dbt_expectations
        search_order: ['your_project_name', 'dbt', 'dbt_expectations']
      - macro_namespace: dbt_external_tables
        search_order: ['your_project_name', 'dbt', 'dbt_external_tables']
      - macro_namespace: audit_helper
        search_order: ['your_project_name', 'dbt', 'audit_helper']
      - macro_namespace: dbt_profiler
        search_order: ['your_project_name', 'dbt', 'dbt_profiler']
    ```

=== "Lakehouse"

    ```yaml
    dispatch:
      - macro_namespace: dbt_utils
        search_order: ['your_project_name', 'dbt', 'dbt_utils']
      - macro_namespace: dbt_date
        search_order: ['your_project_name', 'dbt', 'dbt_date']
      - macro_namespace: dbt_expectations
        search_order: ['your_project_name', 'dbt', 'dbt_expectations']
      - macro_namespace: audit_helper
        search_order: ['your_project_name', 'dbt', 'audit_helper']
      - macro_namespace: dbt_profiler
        search_order: ['your_project_name', 'dbt', 'dbt_profiler']
    ```

Replace `your_project_name` with the `name` field from your `dbt_project.yml`. Only include entries for the packages you actually use.

The `dbt` entry in the search order tells dbt to check the adapter's built-in macros (the "global project namespace") before falling back to the package's defaults. This is how the adapter's compatible macros take priority.

## Supported packages

| Package | Tested version | Data Warehouse | Lakehouse |
|---|---|---|---|
| [dbt-utils](dbt-utils.md) | 1.3.3 | :white_check_mark: Tested | :white_check_mark: Via dbt-spark |
| [dbt-date](dbt-date.md) | 0.17.2 | :white_check_mark: Tested | :white_check_mark: Tested |
| [dbt-codegen](dbt-codegen.md) | 0.14.1 | :white_check_mark: Tested | :white_check_mark: Tested |
| [dbt-expectations](dbt-expectations.md) | 0.10.10 | :white_check_mark: Tested | :white_check_mark: Tested |
| [dbt-audit-helper](dbt-audit-helper.md) | 0.13.0 | :white_check_mark: Tested | :white_check_mark: Tested |
| [dbt-external-tables](dbt-external-tables.md) | 0.11.0 | :white_check_mark: Tested | :x: Not applicable |
| [dbt-profiler](dbt-profiler.md) | 1.0.0 | :white_check_mark: Tested | :white_check_mark: Tested |

"Tested" means the adapter runs automated integration tests for that package on the given compute engine. "Via dbt-spark" means the package works through inherited dbt-spark macros without adapter-specific overrides.

!!! info "dbt-external-tables on Lakehouse"

    The dbt-external-tables package is not applicable to the Lakehouse adapter. Fabric Lakehouse uses [OneLake shortcuts](https://learn.microsoft.com/fabric/onelake/onelake-shortcuts-overview?WT.mc_id=MVP_310840) for external data access, not SQL-level external tables.

### Package-specific limitations

Some package features do not work due to [platform limitations](../limitations.md). The package detail pages document which specific macros or tests are affected and why.

#### Data Warehouse

- **dbt-expectations**: regex tests (`expect_column_values_to_match_regex` and variants) do not work because T-SQL has no native regex support. Timeseries tests that depend on dbt-date's date arithmetic also fail.
- **dbt-audit-helper**: `compare_relation_columns` has case-sensitivity issues with Fabric's BIN2 collation. Struct/unit test models are not supported.
- **dbt-profiler**: `profile_struct` does not work (BigQuery-specific `STRUCT` type).

#### Lakehouse

- **dbt-expectations**: regex tests produce wrong results because the upstream guards them with `target.type in ['spark']` but this adapter reports `fabricspark`. `generate_series`-based tests fail with compilation errors.
- **dbt-audit-helper**: struct models and `compare_and_classify` (which uses distinct window functions) are not supported.
- **dbt-codegen**: `generate_source` does not work because it queries `information_schema.tables`, which does not exist in Spark SQL.
- **dbt-profiler**: `profile_struct` does not work (`STRUCT` type is BigQuery-specific).
