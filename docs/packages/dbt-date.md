# dbt-date

**Tested version:** 0.17.2 | **Macro overrides:** 16 | **Integration tested:** Yes

[dbt-date](https://github.com/godatadriven/dbt-date) provides date/time utility macros for generating date dimensions, extracting date parts, and performing fiscal calendar calculations.

## Dispatch configuration

```yaml
dispatch:
  - macro_namespace: dbt_date
    search_order: ['your_project_name', 'dbt', 'dbt_date']
```

## Overridden macros

The following macros have T-SQL-compatible overrides in this adapter:

### Calendar date functions

| Macro | Why overridden |
|---|---|
| `week_start` | Uses T-SQL `DATEADD`/`DATEDIFF` pattern for week boundary calculation |
| `week_end` | Derived from `week_start` using T-SQL date arithmetic |
| `week_of_year` | Uses T-SQL `DATEPART(week, ...)` |
| `day_of_week` | Uses T-SQL `DATEPART(weekday, ...)` with `DATEFIRST` awareness |
| `iso_week_start` | Uses T-SQL `DATEADD`/`DATEDIFF` pattern for ISO week boundaries |
| `iso_week_of_year` | Uses T-SQL `DATEPART(iso_week, ...)` |
| `iso_year_week` | Combines ISO year and week number using T-SQL functions |
| `date_part` | Uses T-SQL `DATEPART(...)` instead of `EXTRACT(... FROM ...)` |
| `convert_timezone` | Uses T-SQL `AT TIME ZONE` syntax |
| `from_unixtimestamp` | Uses T-SQL `DATEADD(second, ...)` from epoch |
| `to_unixtimestamp` | Uses T-SQL `DATEDIFF(s, '1970-01-01', ...)` |

### Formatting

| Macro | Why overridden |
|---|---|
| `day_name` | Uses T-SQL `FORMAT(date, 'ddd')`/`FORMAT(date, 'dddd')` |
| `month_name` | Uses T-SQL `FORMAT(date, 'MMM')`/`FORMAT(date, 'MMMM')` |

### Utility

| Macro | Why overridden |
|---|---|
| `date` (modules_datetime) | Uses Jinja's `modules.datetime.date()` for date construction |

### Fiscal date functions

| Macro | Why overridden |
|---|---|
| `get_fiscal_year_dates` | Rewritten for T-SQL CTE and date arithmetic syntax |
| `get_date_dimension` | Inlined without nested CTEs (not supported in Fabric) |

## Timezone limitation

!!! note

    The `dbt_date:time_zone` variable must be set to `UTC` for full compatibility. Other timezones require that the name is valid in both Python's `pytz` (IANA format like `Europe/Brussels`) and T-SQL's `AT TIME ZONE` (Windows format like `Romance Standard Time`). Only `UTC` is valid in both systems.

## Macros that work without override

All other dbt-date macros (e.g., `now`, `today`, `yesterday`, `tomorrow`, `n_days_ago`, `n_days_away`, `periods_since`, etc.) work on Fabric without any adapter-specific override.
