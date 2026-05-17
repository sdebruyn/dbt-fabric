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

Legend: :white_check_mark: = supported on Fabric, :x: = not supported on Fabric

Macros marked with **(override)** have a T-SQL-compatible override in this adapter. All other supported macros work without any adapter-specific override.

### Date dimension generators

| Macro | Status | Notes |
|---|---|---|
| `get_base_dates` | :white_check_mark: | |
| `get_date_dimension` | :white_check_mark: **(override)** | Inlined without nested CTEs (Fabric disallows nested CTEs in `CREATE VIEW`) |

### Current date/time

| Macro | Status | Notes |
|---|---|---|
| `now` | :white_check_mark: | |
| `today` | :white_check_mark: | |
| `yesterday` | :white_check_mark: | |
| `tomorrow` | :white_check_mark: | |

### Relative date navigation

| Macro | Status | Notes |
|---|---|---|
| `n_days_ago` | :white_check_mark: | |
| `n_days_away` | :white_check_mark: | |
| `n_weeks_ago` | :white_check_mark: | |
| `n_weeks_away` | :white_check_mark: | |
| `n_months_ago` | :white_check_mark: | |
| `n_months_away` | :white_check_mark: | |
| `last_week` | :white_check_mark: | |
| `next_week` | :white_check_mark: | |
| `last_month` | :white_check_mark: | |
| `next_month` | :white_check_mark: | |

### Date part extraction

| Macro | Status | Notes |
|---|---|---|
| `date_part` | :white_check_mark: **(override)** | Uses T-SQL `DATEPART(...)` instead of `EXTRACT(... FROM ...)` |
| `day_of_week` | :white_check_mark: **(override)** | Uses T-SQL `DATEPART(weekday, ...)` with `DATEFIRST` awareness |
| `day_of_month` | :white_check_mark: | |
| `day_of_year` | :white_check_mark: | |
| `day_name` | :white_check_mark: **(override)** | Uses T-SQL `FORMAT(date, 'ddd')`/`FORMAT(date, 'dddd')` |
| `month_name` | :white_check_mark: **(override)** | Uses T-SQL `FORMAT(date, 'MMM')`/`FORMAT(date, 'MMMM')` |
| `last_month_name` | :white_check_mark: | |
| `last_month_number` | :white_check_mark: | |
| `next_month_name` | :white_check_mark: | |
| `next_month_number` | :white_check_mark: | |

### Week calculations

| Macro | Status | Notes |
|---|---|---|
| `week_start` | :white_check_mark: **(override)** | Uses T-SQL `DATEADD`/`DATEDIFF` pattern for week boundary calculation |
| `week_end` | :white_check_mark: **(override)** | Derived from `week_start` using T-SQL date arithmetic |
| `week_of_year` | :white_check_mark: **(override)** | Uses T-SQL `DATEPART(week, ...)` |
| `iso_week_start` | :white_check_mark: **(override)** | Uses T-SQL `DATEADD`/`DATEDIFF` pattern for ISO week boundaries |
| `iso_week_end` | :white_check_mark: | |
| `iso_week_of_year` | :white_check_mark: **(override)** | Uses T-SQL `DATEPART(iso_week, ...)` |
| `iso_year_week` | :white_check_mark: **(override)** | Combines ISO year and week number using T-SQL functions |

### Timezone and Unix timestamp

| Macro | Status | Notes |
|---|---|---|
| `convert_timezone` | :white_check_mark: **(override)** | Uses T-SQL `AT TIME ZONE` syntax |
| `from_unixtimestamp` | :white_check_mark: **(override)** | Uses T-SQL `DATEADD(second, ...)` from epoch |
| `to_unixtimestamp` | :white_check_mark: **(override)** | Uses T-SQL `DATEDIFF(s, '1970-01-01', ...)` |

### Other

| Macro | Status | Notes |
|---|---|---|
| `periods_since` | :white_check_mark: | |
| `round_timestamp` | :white_check_mark: | |

### Fiscal calendar

| Macro | Status | Notes |
|---|---|---|
| `get_fiscal_periods` | :white_check_mark: **(override)** | Inlined without nested CTEs; T-SQL date arithmetic and `%` operator |
| `get_fiscal_year_dates` | :white_check_mark: **(override)** | T-SQL positional `GROUP BY` and `ORDER BY` replaced with explicit columns |

### Jinja utilities

| Macro | Status | Notes |
|---|---|---|
| `date` | :white_check_mark: **(override)** | Uses Jinja's `modules.datetime.date()` for date construction |
| `datetime` | :white_check_mark: | |

## Timezone limitation

!!! note

    The `dbt_date:time_zone` variable must be set to `UTC` for full compatibility. Other timezones require that the name is valid in both Python's `pytz` (IANA format like `Europe/Brussels`) and T-SQL's `AT TIME ZONE` (Windows format like `Romance Standard Time`). Only `UTC` is valid in both systems.
