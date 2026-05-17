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

Legend: ✅ = supported on Fabric, ❌ = not supported on Fabric

Macros marked with **(override)** have a T-SQL-compatible override in this adapter. All other supported macros work without any adapter-specific override.

### Utility overrides

| Macro | Status | Notes |
|---|---|---|
| `type_timestamp` | ✅ **(override)** | T-SQL's `timestamp` is `rowversion`; maps to `datetime2(6)` |
| `type_datetime` | ✅ **(override)** | Maps to `datetime2(6)` |
| `log_natural` | ✅ **(override)** | T-SQL has no `LN()`; uses `LOG()` which defaults to natural log |

### Generalized tests

| Macro | Status | Notes |
|---|---|---|
| `equal_expression` | ✅ **(override)** | T-SQL `FULL OUTER JOIN` with explicit `ON` clause |
| `expression_is_true` | ✅ **(override)** | T-SQL has no boolean type; uses `CASE WHEN ... THEN 1` and compares `= 1` |

### Aggregate function tests

| Macro | Status | Notes |
|---|---|---|
| `expect_column_most_common_value_to_be_in_set` | ✅ **(override)** | Uses `ROW_NUMBER()` instead of `LIMIT` for top-N selection |
| `expect_column_stdev_to_be_between` | ✅ **(override)** | T-SQL uses `STDEV()` instead of `STDDEV()` |

### Distributional tests

| Macro | Status | Notes |
|---|---|---|
| `expect_column_values_to_be_within_n_stdevs` | ✅ **(override)** | T-SQL uses `STDEV()` instead of `STDDEV()` |
| `expect_column_values_to_be_within_n_moving_stdevs` | ✅ **(override)** | T-SQL uses `STDEV()` instead of `STDDEV()` |

### Multi-column tests

| Macro | Status | Notes |
|---|---|---|
| `expect_select_column_values_to_be_unique_within_record` | ✅ **(override)** | Uses `UNION ALL` unpivot pattern; `ROW_NUMBER()` with subquery `ORDER BY` |

### Table shape tests

| Macro | Status | Notes |
|---|---|---|
| `expect_grouped_row_values_to_have_recent_data` | ✅ **(override)** | Uses explicit join key for T-SQL `LEFT JOIN` pattern |
