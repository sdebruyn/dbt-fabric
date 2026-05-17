# dbt-date

**Tested version:** 0.17.2 | **Integration tested:** Yes

[dbt-date](https://github.com/godatadriven/dbt-date) provides date/time utility macros for generating date dimensions, extracting date parts, and performing fiscal calendar calculations.

## Dispatch configuration

```yaml
dispatch:
  - macro_namespace: dbt_date
    search_order: ['your_project_name', 'dbt', 'dbt_date']
```

## Macro compatibility

<!-- TODO: fill in full macro table like dbt-utils -->

## Timezone limitation

!!! note

    The `dbt_date:time_zone` variable must be set to `UTC` for full compatibility. Other timezones require that the name is valid in both Python's `pytz` (IANA format like `Europe/Brussels`) and T-SQL's `AT TIME ZONE` (Windows format like `Romance Standard Time`). Only `UTC` is valid in both systems.
