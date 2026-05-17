# dbt-profiler

**Tested version:** 1.0.0 | **Integration tested:** Yes

[dbt-profiler](https://github.com/data-mie/dbt-profiler) generates column-level profiling statistics (min, max, median, standard deviation, uniqueness, null rates) for any relation in your dbt project.

## Dispatch configuration

```yaml
dispatch:
  - macro_namespace: dbt_profiler
    search_order: ['your_project_name', 'dbt', 'dbt_profiler']
```

## Macro compatibility

Legend: :white_check_mark: = supported on Fabric, :x: = not supported on Fabric

Macros marked with **(override)** have a T-SQL-compatible override in this adapter. All other supported macros work without any adapter-specific override.

### Measure macros

| Macro | Status | Notes |
|---|---|---|
| `measure_avg` | :white_check_mark: **(override)** | Handles `bit` columns via `CASE` expression (T-SQL `AVG` rejects booleans) |
| `measure_median` | :white_check_mark: **(override)** | Uses `PERCENTILE_CONT` window function with `TOP 1` (T-SQL has no `MEDIAN()`) |
| `measure_std_dev_population` | :white_check_mark: **(override)** | Uses T-SQL `STDEVP()` instead of `stddev_pop()` |
| `measure_std_dev_sample` | :white_check_mark: **(override)** | Uses T-SQL `STDEV()` instead of `stddev_samp()` |
| `measure_is_unique` | :white_check_mark: **(override)** | Returns `'TRUE'`/`'FALSE'` strings (T-SQL has no boolean type) |
| `measure_count` | :white_check_mark: | |
| `measure_count_nulls` | :white_check_mark: | |
| `measure_count_distinct` | :white_check_mark: | |
| `measure_min` | :white_check_mark: | |
| `measure_max` | :white_check_mark: | |
| `measure_not_null_proportion` | :white_check_mark: | |

### Type detection macros

| Macro | Status | Notes |
|---|---|---|
| `is_numeric_dtype` | :white_check_mark: **(override)** | Handles `tinyint`, `smallint`, `decimal`, `money`, `real` |
| `is_logical_dtype` | :white_check_mark: **(override)** | Handles `bit` type |
| `is_date_or_time_dtype` | :white_check_mark: **(override)** | Handles `time`, `smalldatetime` |
| `is_struct_dtype` | :white_check_mark: | |

### Utility macros

| Macro | Status | Notes |
|---|---|---|
| `assert_relation_exists` | :white_check_mark: **(override)** | Uses `TOP 0` instead of `LIMIT 0` |
| `get_profile` | :white_check_mark: | |
| `get_profile_table` | :white_check_mark: | |
| `print_profile` | :white_check_mark: | |
| `print_profile_docs` | :white_check_mark: | |
| `print_profile_schema` | :white_check_mark: | |

### Disabled integration test models

| Model | Reason |
|---|---|
| `profile_struct` | BigQuery-only (uses STRUCT type not available in T-SQL) |
| `profile_over_time` | Incremental model, not needed for basic profiling validation |
