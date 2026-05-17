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

Legend: ✅ = supported on Fabric, ❌ = not supported on Fabric

Macros marked with **(override)** have a T-SQL-compatible override in this adapter. All other supported macros work without any adapter-specific override.

### Date dimension generators

| Macro | Status | Notes |
|---|---|---|
| `get_base_dates` | ✅ | |
| `get_date_dimension` | ✅ **(override)** | Inlined without nested CTEs (Fabric disallows nested CTEs in `CREATE VIEW`) |

### Current date/time

| Macro | Status | Notes |
|---|---|---|
| `now` | ✅ | |
| `today` | ✅ | |
| `yesterday` | ✅ | |
| `tomorrow` | ✅ | |

### Relative date navigation

| Macro | Status | Notes |
|---|---|---|
| `n_days_ago` | ✅ | |
| `n_days_away` | ✅ | |
| `n_weeks_ago` | ✅ | |
| `n_weeks_away` | ✅ | |
| `n_months_ago` | ✅ | |
| `n_months_away` | ✅ | |
| `last_week` | ✅ | |
| `next_week` | ✅ | |
| `last_month` | ✅ | |
| `next_month` | ✅ | |

### Date part extraction

| Macro | Status | Notes |
|---|---|---|
| `date_part` | ✅ **(override)** | Uses T-SQL `DATEPART(...)` instead of `EXTRACT(... FROM ...)` |
| `day_of_week` | ✅ **(override)** | Uses T-SQL `DATEPART(weekday, ...)` with `DATEFIRST` awareness |
| `day_of_month` | ✅ | |
| `day_of_year` | ✅ | |
| `day_name` | ✅ **(override)** | Uses T-SQL `FORMAT(date, 'ddd')`/`FORMAT(date, 'dddd')` |
| `month_name` | ✅ **(override)** | Uses T-SQL `FORMAT(date, 'MMM')`/`FORMAT(date, 'MMMM')` |
| `last_month_name` | ✅ | |
| `last_month_number` | ✅ | |
| `next_month_name` | ✅ | |
| `next_month_number` | ✅ | |

### Week calculations

| Macro | Status | Notes |
|---|---|---|
| `week_start` | ✅ **(override)** | Uses T-SQL `DATEADD`/`DATEDIFF` pattern for week boundary calculation |
| `week_end` | ✅ **(override)** | Derived from `week_start` using T-SQL date arithmetic |
| `week_of_year` | ✅ **(override)** | Uses T-SQL `DATEPART(week, ...)` |
| `iso_week_start` | ✅ **(override)** | Uses T-SQL `DATEADD`/`DATEDIFF` pattern for ISO week boundaries |
| `iso_week_end` | ✅ | |
| `iso_week_of_year` | ✅ **(override)** | Uses T-SQL `DATEPART(iso_week, ...)` |
| `iso_year_week` | ✅ **(override)** | Combines ISO year and week number using T-SQL functions |

### Timezone and Unix timestamp

| Macro | Status | Notes |
|---|---|---|
| `convert_timezone` | ✅ **(override)** | Uses T-SQL `AT TIME ZONE` syntax |
| `from_unixtimestamp` | ✅ **(override)** | Uses T-SQL `DATEADD(second, ...)` from epoch |
| `to_unixtimestamp` | ✅ **(override)** | Uses T-SQL `DATEDIFF(s, '1970-01-01', ...)` |

### Other

| Macro | Status | Notes |
|---|---|---|
| `periods_since` | ✅ | |
| `round_timestamp` | ✅ | |

### Fiscal calendar

| Macro | Status | Notes |
|---|---|---|
| `get_fiscal_periods` | ✅ **(override)** | Inlined without nested CTEs; T-SQL date arithmetic and `%` operator |
| `get_fiscal_year_dates` | ✅ **(override)** | T-SQL positional `GROUP BY` and `ORDER BY` replaced with explicit columns |

### Jinja utilities

| Macro | Status | Notes |
|---|---|---|
| `date` | ✅ **(override)** | Uses Jinja's `modules.datetime.date()` for date construction |
| `datetime` | ✅ | |

## Timezone limitation

!!! note

    The `dbt_date:time_zone` variable must be set to `UTC` for full compatibility. Other timezones require that the name is valid in both Python's `pytz` (IANA format like `Europe/Brussels`) and T-SQL's `AT TIME ZONE` (Windows format like `Romance Standard Time`). Only `UTC` is valid in both systems.
