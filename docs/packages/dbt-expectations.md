# dbt-expectations

**Tested version:** 0.10.10 | **Integration tested:** Yes

[dbt-expectations](https://github.com/metaplane/dbt-expectations) provides data quality tests inspired by Great Expectations.

## Dispatch configuration

```yaml
dispatch:
  - macro_namespace: dbt_expectations
    search_order: ['your_project_name', 'dbt', 'dbt_expectations']
```

## Macro compatibility

Legend: :white_check_mark: = supported on Fabric, :x: = not supported on Fabric

Macros marked with **(override)** have a T-SQL-compatible override in this adapter. All other supported macros work without any adapter-specific override.

### Utility overrides

| Macro | Status | Notes |
|---|---|---|
| `type_timestamp` | :white_check_mark: **(override)** | T-SQL's `timestamp` is `rowversion`; maps to `datetime2(6)` |
| `type_datetime` | :white_check_mark: **(override)** | Maps to `datetime2(6)` |
| `log_natural` | :white_check_mark: **(override)** | T-SQL has no `LN()`; uses `LOG()` which defaults to natural log |

### Generalized tests

| Macro | Status | Notes |
|---|---|---|
| `equal_expression` | :white_check_mark: **(override)** | T-SQL `FULL OUTER JOIN` with explicit `ON` clause |
| `expression_is_true` | :white_check_mark: **(override)** | T-SQL has no boolean type; uses `CASE WHEN ... THEN 1` and compares `= 1` |

### Aggregate function tests

| Macro | Status | Notes |
|---|---|---|
| `expect_column_most_common_value_to_be_in_set` | :white_check_mark: **(override)** | `ROW_NUMBER()` for top-N; `LEFT JOIN` anti-pattern instead of `NOT IN (SELECT FROM cte)` |
| `expect_column_stdev_to_be_between` | :white_check_mark: **(override)** | T-SQL uses `STDEV()` instead of `STDDEV()` |

### Distributional tests

| Macro | Status | Notes |
|---|---|---|
| `expect_column_values_to_be_within_n_stdevs` | :white_check_mark: **(override)** | T-SQL uses `STDEV()` instead of `STDDEV()` |
| `expect_column_values_to_be_within_n_moving_stdevs` | :white_check_mark: **(override)** | T-SQL uses `STDEV()` instead of `STDDEV()` |

### Multi-column tests

| Macro | Status | Notes |
|---|---|---|
| `expect_select_column_values_to_be_unique_within_record` | :white_check_mark: **(override)** | Uses `UNION ALL` unpivot pattern; `ROW_NUMBER()` with subquery `ORDER BY` |

### Table shape tests

| Macro | Status | Notes |
|---|---|---|
| `expect_grouped_row_values_to_have_recent_data` | :white_check_mark: **(override)** | Uses explicit join key for T-SQL `LEFT JOIN` pattern |

## Unsupported tests

These tests cannot run on Fabric and cannot be fixed with adapter macro overrides:

| Test | Reason |
|---|---|
| `expect_column_values_to_match_regex` | T-SQL has no native regex support |
| `expect_column_values_to_not_match_regex` | T-SQL has no native regex support |
| `expect_column_values_to_match_regex_list` | T-SQL has no native regex support |
| `expect_column_values_to_not_match_regex_list` | T-SQL has no native regex support |
| `expect_column_to_exist` | Renders Python `True`/`False` as SQL literals (no boolean type in T-SQL); does not use `adapter.dispatch()` so no override possible |
| `expect_column_values_to_have_consistent_casing` | Uses positional `GROUP BY 1` (T-SQL requires explicit expressions); does not use `adapter.dispatch()` so no override possible |
