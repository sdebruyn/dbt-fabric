# Incremental `--full-refresh` drops the target before recreating it — data loss if creation fails

**Repo:** `microsoft/dbt-fabric`
**Labels (suggested):** `bug`, `data-loss`, `priority/high`

> [ ] **Validated by maintainer** — code refs, line numbers, and claims confirmed against upstream HEAD

## Summary

`fabric__incremental` (via `dbt/include/fabric/macros/materializations/models/incremental/incremental.sql`) calls `adapter.drop_relation(target_relation)` before re-creating the table. If the subsequent `CREATE TABLE AS SELECT` then fails for any reason — transient Fabric error, query timeout, broken model SQL, capacity issue, OOM, network hiccup — the user is left with no table at all. This is the documented data-loss anti-pattern that every other reference adapter (dbt-postgres, dbt-snowflake, dbt-spark, dbt-bigquery) avoids by using an intermediate-relation + backup-rename swap.

## Evidence (HEAD [`0de2190`](https://github.com/microsoft/dbt-fabric/tree/0de2190), v1.10.0)

[`dbt/include/fabric/macros/materializations/models/incremental/incremental.sql#L30-L34`](https://github.com/microsoft/dbt-fabric/blob/0de2190/dbt/include/fabric/macros/materializations/models/incremental/incremental.sql#L30-L34):

```jinja
{% if full_refresh_mode %}
    {% do adapter.drop_relation(target_relation) %}
    ...
    {% set build_sql = create_table_as(False, target_relation, sql) %}
{% endif %}
```

The drop happens unconditionally, before the create. There is no rollback path.

## Reproduction

1. Set up a nightly job that runs `dbt build --full-refresh` against a production Fabric DW.
2. On a network hiccup, capacity throttling event, or transient Fabric error during the CTAS step, the target table is gone.
3. Downstream BI dashboards and reports that depend on the table now point at nothing.

## User impact

Silent destructive failure mode. A single transient infrastructure error can wipe a production table that downstream consumers depend on. The user only learns about it when the dashboard goes blank or when the next dbt run reports missing dependencies.

## Suggested fix

Use the standard dbt-native intermediate + backup + rename swap pattern that every other reference adapter uses:

```jinja
{% if full_refresh_mode %}
    {% set intermediate_relation = make_intermediate_relation(target_relation) %}
    {% do adapter.drop_relation(intermediate_relation) %}
    {% set build_sql = create_table_as(False, intermediate_relation, sql) %}
    {% do run_query(build_sql) %}
    {% set backup_relation = make_backup_relation(target_relation, target_relation.type) %}
    {% do adapter.drop_relation(backup_relation) %}
    {% do adapter.rename_relation(target_relation, backup_relation) %}
    {% do adapter.rename_relation(intermediate_relation, target_relation) %}
    {% do adapter.drop_relation(backup_relation) %}
{% endif %}
```

This is the same pattern dbt-postgres, dbt-snowflake, and dbt-spark use. The existing target keeps its data if creation fails.

Reference fix in the fork: commit `257c8999`.

## Notes

- This is one of the most consequential bugs in the adapter because the failure mode is invisible until it has already destroyed data, and because nightly full-refresh runs are common.
- The same anti-pattern (drop-then-create) is the reason dbt-spark replaced its own version of this code several releases ago.
