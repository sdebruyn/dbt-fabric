# dbt-expectations

**Macro overrides:** 10 | **Integration tested:** No

[dbt-expectations](https://github.com/calogica/dbt-expectations) provides data quality tests inspired by Great Expectations. The overrides address T-SQL incompatibilities in statistical functions, boolean handling, and subquery syntax.

!!! warning

    This package is **not** integration tested in CI. The macro overrides are expected to work based on manual validation, but edge cases may exist.

## Dispatch configuration

```yaml
dispatch:
  - macro_namespace: dbt_expectations
    search_order: ['your_project_name', 'dbt', 'dbt_expectations']
```

## Overridden macros

The following macros have T-SQL-compatible overrides in this adapter:

### Math helpers

| Macro | Why overridden |
|---|---|
| `log_natural` | Uses T-SQL `LOG(x)` instead of `LN(x)` |

### Generalized test helpers

| Macro | Why overridden |
|---|---|
| `get_select` | T-SQL boolean expression and `GROUP BY` handling |
| `expression_is_true` | T-SQL does not support `= true` boolean comparisons; rewritten with `CASE` |

### Aggregate function tests

| Macro | Why overridden |
|---|---|
| `test_expect_column_most_common_value_to_be_in_set` | Uses `TOP` instead of `LIMIT`; T-SQL aggregate syntax |
| `test_expect_column_stdev_to_be_between` | Uses `STDEV()` with T-SQL-compatible `HAVING` clause |

### Distributional tests

| Macro | Why overridden |
|---|---|
| `test_expect_column_values_to_be_within_n_stdevs` | T-SQL window function and `STDEV()` syntax |
| `test_expect_column_values_to_be_within_n_moving_stdevs` | T-SQL window function syntax; uses `STDEV()` and `AVG()` with `ROWS BETWEEN` |

### Multi-column tests

| Macro | Why overridden |
|---|---|
| `test_expect_select_column_values_to_be_unique_within_record` | T-SQL `CONCAT` and subquery alias requirements |

### Table shape tests

| Macro | Why overridden |
|---|---|
| `test_expect_grouped_row_values_to_have_recent_data` | T-SQL date comparison and `GROUP BY` syntax |

## Macros that work without override

All other dbt-expectations tests (e.g., `expect_column_values_to_not_be_null`, `expect_column_values_to_be_unique`, `expect_column_values_to_be_between`, `expect_table_row_count_to_equal`, etc.) work on Fabric without any adapter-specific override.
