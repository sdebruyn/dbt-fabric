# Package support

This adapter includes macro overrides that make popular dbt community packages work with Microsoft Fabric's T-SQL dialect. Without these overrides, most community packages fail on Fabric because they generate PostgreSQL or Spark-compatible SQL that T-SQL does not accept.

## How it works

Community packages use dbt's [dispatch system](https://docs.getdbt.com/reference/dbt-jinja-functions/dispatch) to allow adapters to override their macros. This adapter ships `fabric__` prefixed versions of incompatible macros in its built-in macro directory.

When a package macro dispatches to find an adapter-specific implementation, dbt looks for `fabric__<macro_name>`. If this adapter provides one, it takes priority over the package's default implementation.

### Required dispatch configuration

To activate the macro overrides, you must add a `dispatch` configuration to your `dbt_project.yml` for each package you use. Without this, dbt's default dispatch does not search the adapter's internal macros for package-namespaced macros.

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

Replace `your_project_name` with the `name` field from your `dbt_project.yml`. Only include entries for the packages you actually use.

The `dbt` entry in the search order tells dbt to check the adapter's built-in macros (the "global project namespace") before falling back to the package's defaults. This is how the adapter's T-SQL-compatible macros take priority.

## Supported packages

| Package | Tested version | Integration tested |
|---|---|---|
| [dbt-utils](dbt-utils.md) | 1.3.3 | Yes |
| [dbt-date](dbt-date.md) | 0.17.2 | Yes |
| [dbt-codegen](dbt-codegen.md) | 0.14.1 | Yes |
| [dbt-expectations](dbt-expectations.md) | 0.10.10 | Yes |
| [dbt-audit-helper](dbt-audit-helper.md) | 0.13.0 | Yes |
| [dbt-external-tables](dbt-external-tables.md) | 0.11.0 | Yes |
| [dbt-profiler](dbt-profiler.md) | 1.0.0 | Yes |

"Tested version" indicates the version against which the adapter runs automated integration tests in CI. Packages without a tested version have macro overrides that are expected to work but are not verified automatically.
