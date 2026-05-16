# Community package support

This adapter includes macro overrides that make popular dbt community packages work with Microsoft Fabric's T-SQL dialect. Without these overrides, most community packages fail on Fabric because they generate PostgreSQL or Spark-compatible SQL that T-SQL does not accept.

## How it works

Community packages use dbt's [dispatch system](https://docs.getdbt.com/reference/dbt-jinja-functions/dispatch?WT.mc_id=MVP_310840) to allow adapters to override their macros. This adapter ships `fabric__` prefixed versions of incompatible macros in `src/dbt/include/fabric/macros/dbt_package_support/`.

### Required dispatch configuration

To activate the macro overrides, you must add a `dispatch` configuration to your `dbt_project.yml` for each package you use. Without this, dbt's default dispatch does not search the adapter's internal macros.

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
```

Replace `your_project_name` with the `name` field from your `dbt_project.yml`. Only include entries for the packages you actually use. The `insert_by_period` materialization does not require dispatch configuration.

## Supported packages

| Package | Tested version | Macro overrides | Integration tested |
|---|---|---|---|
| [dbt-utils](https://github.com/dbt-labs/dbt-utils) | 1.3.3 | 16 | Yes |
| [dbt-date](https://github.com/godatadriven/dbt-date) | 0.17.2 | 16 | Yes |
| [dbt-expectations](https://github.com/calogica/dbt-expectations) | — | 10 | No |
| [insert_by_period](https://github.com/dbt-labs/dbt-labs-experimental-features/tree/main/insert_by_period) | — | 7 | No |
| [dbt-audit-helper](https://github.com/dbt-labs/dbt-audit-helper) | — | 5 | No |
| [dbt-external-tables](https://github.com/dbt-labs/dbt-external-tables) | 0.11.0 | 5 | Yes |

"Tested version" indicates the version against which the adapter runs automated integration tests in CI. Packages without a tested version have macro overrides that are expected to work but are not verified automatically.

---

## dbt-utils

**Tested version:** 1.3.3

Overrides cover common T-SQL incompatibilities: `LIMIT` → `TOP`, `BOOLEAN` → `BIT`, string functions, date functions, and type casting.

## dbt-date

**Tested version:** 0.17.2

Overrides cover: date/time functions (`week_start`, `week_end`, `day_of_week`, `iso_week_*`, `date_part`), timezone conversion, `day_name`/`month_name` formatting, unix timestamp conversion, fiscal period calculations, and the date dimension generator.

!!! note "Timezone limitation"

    The `dbt_date:time_zone` variable must be set to `UTC` for full compatibility. Other timezones require that the name is valid in both Python's `pytz` (IANA format like `Europe/Brussels`) and T-SQL's `AT TIME ZONE` (Windows format like `Romance Standard Time`). Only `UTC` is valid in both systems.

## dbt-expectations

Overrides cover statistical and schema test macros that use PostgreSQL-specific syntax: regexp functions, array operations, and type casts.

## dbt-audit-helper

Overrides cover the comparison macros (`compare_relations`, `compare_queries`, `compare_column_values`, `compare_relation_columns`) which use PostgreSQL-specific `EXCEPT` and type casting syntax.

## dbt-external-tables

**Tested version:** 0.11.0

This adapter overrides the external table macros to use Fabric's [`OPENROWSET(BULK ...)`](https://learn.microsoft.com/en-us/sql/t-sql/functions/openrowset-transact-sql?view=fabric&WT.mc_id=MVP_310840) function instead of the Synapse-style `CREATE EXTERNAL TABLE`. External sources are created as views wrapping OPENROWSET queries.

See the [external tables guide](external-tables.md) for full setup instructions.

## insert_by_period

This provides a complete `insert_by_period` materialization for Fabric's T-SQL dialect, including all helper macros for period boundary calculation and filter generation. No dispatch configuration is needed for this package — it registers as a materialization, not via dispatch.
