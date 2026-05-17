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

Legend: ✅ = supported on Fabric, ❌ = not supported on Fabric

Macros marked with **(override)** have a T-SQL-compatible override in this adapter. All other supported macros work without any adapter-specific override.

### Overridden macros

| Macro | Why overridden |
|---|---|
| `convert_timezone` | Uses T-SQL `AT TIME ZONE` syntax |
| `date` | Uses Jinja's `modules.datetime.date()` for date construction |
| `date_part` | Uses T-SQL `DATEPART(...)` instead of `EXTRACT(... FROM ...)` |
| `day_name` | Uses T-SQL `FORMAT(date, 'ddd')`/`FORMAT(date, 'dddd')` |
| `day_of_week` | Uses T-SQL `DATEPART(weekday, ...)` with `DATEFIRST` awareness |
| `from_unixtimestamp` | Uses T-SQL `DATEADD(second, ...)` from epoch |
| `get_date_dimension` | Inlined without nested CTEs (not supported in Fabric) |
| `get_fiscal_year_dates` | Rewritten for T-SQL CTE and date arithmetic syntax |
| `iso_week_of_year` | Uses T-SQL `DATEPART(iso_week, ...)` |
| `iso_week_start` | Uses T-SQL `DATEADD`/`DATEDIFF` pattern for ISO week boundaries |
| `iso_year_week` | Combines ISO year and week number using T-SQL functions |
| `month_name` | Uses T-SQL `FORMAT(date, 'MMM')`/`FORMAT(date, 'MMMM')` |
| `to_unixtimestamp` | Uses T-SQL `DATEDIFF(s, '1970-01-01', ...)` |
| `week_end` | Derived from `week_start` using T-SQL date arithmetic |
| `week_of_year` | Uses T-SQL `DATEPART(week, ...)` |
| `week_start` | Uses T-SQL `DATEADD`/`DATEDIFF` pattern for week boundary calculation |

## Timezone limitation

!!! note

    The `dbt_date:time_zone` variable must be set to `UTC` for full compatibility. Other timezones require that the name is valid in both Python's `pytz` (IANA format like `Europe/Brussels`) and T-SQL's `AT TIME ZONE` (Windows format like `Romance Standard Time`). Only `UTC` is valid in both systems.

## Macros that work without override

All other dbt-date macros (e.g., `now`, `today`, `yesterday`, `tomorrow`, `n_days_ago`, `n_days_away`, `periods_since`, etc.) work on Fabric without any adapter-specific override.
