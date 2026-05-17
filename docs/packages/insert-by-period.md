# insert_by_period

**Integration tested:** No

[insert_by_period](https://github.com/dbt-labs/dbt-labs-experimental-features/tree/main/insert_by_period) is an experimental materialization from dbt Labs that loads data incrementally by time period. This adapter provides a complete T-SQL implementation of the materialization and its helper macros.

!!! warning

    This package is **not** integration tested in CI. The materialization is expected to work based on manual validation, but edge cases may exist.

## No dispatch configuration needed

Unlike other packages, `insert_by_period` registers as a **materialization**, not via dispatch. No `dispatch` configuration in `dbt_project.yml` is required. The materialization is automatically available when this adapter is installed.

## Provided macros

This adapter implements the full `insert_by_period` materialization for Fabric's T-SQL dialect:

| Macro | Purpose |
|---|---|
| `insert_by_period` (materialization) | Main materialization that orchestrates period-by-period loading |
| `get_start_stop_dates` | Determines the date range to process from config or source models |
| `check_placeholder` | Validates that the model SQL contains the `__PERIOD_FILTER__` placeholder |
| `replace_placeholder_with_period_filter` | Injects T-SQL `DATEADD`/`CAST` period filter into model SQL |
| `get_period_boundaries` | Queries the target table to find current data boundaries |
| `get_period_of_load` | Calculates the specific period being loaded for a given offset |
| `get_period_filter_sql` | Combines the period filter with the base SQL for execution |

## Usage

Define a model with the `insert_by_period` materialization and include the `__PERIOD_FILTER__` placeholder:

```sql
{{ config(
    materialized='insert_by_period',
    period='day',
    timestamp_field='created_at',
    start_date='2024-01-01',
    stop_date='2024-12-31'
) }}

select *
from {{ source('raw', 'events') }}
where __PERIOD_FILTER__
```

The materialization will:

1. Create the target table if it does not exist
2. Determine the date range (from config or by querying source models)
3. Loop through each period (day, week, month, etc.)
4. Insert filtered data for each period into the target table

## Configuration options

| Option | Required | Description |
|---|---|---|
| `period` | Yes | Time granularity: `day`, `week`, `month`, `year` |
| `timestamp_field` | Yes | Column used for period filtering |
| `start_date` | No | Fixed start date (alternative: `date_source_models`) |
| `stop_date` | No | Fixed end date (defaults to current timestamp if omitted) |
| `date_source_models` | No | List of model names to derive date range from |
