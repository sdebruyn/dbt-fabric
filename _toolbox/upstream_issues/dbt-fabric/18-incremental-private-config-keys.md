# Adapter-private `delete_condition` / `delete_not_matched_by_source` configs on the `incremental` materialization break portability

**Repo:** `microsoft/dbt-fabric`
**Labels (suggested):** `design`, `priority/medium`
**Refs:** v1.9.10 release

## Summary

The v1.9.10 release adds two new model-level configs invented by the maintainers: `delete_condition` and `delete_not_matched_by_source`. They are wired into `dbt/include/fabric/macros/materializations/models/incremental/incremental.sql` and dispatched through a new `fabric__get_incremental_merge_sql` macro. Neither config exists in dbt-core or in dbt-adapters. No other reference adapter (Snowflake, BigQuery, Postgres, Redshift, Spark) exposes anything equivalent on the `incremental` materialization.

## Why this is a problem

The `incremental` materialization is part of dbt's user-facing API contract. Its config keys are how thousands of models in production projects describe themselves. Adding adapter-private knobs to it has three consequences:

1. **Portability break.** A model written for Fabric stops being portable. A user moving to Snowflake (or back) has to rewrite the `config()` block, even though the same merge-with-delete semantics could be done with a `post-hook` or with the standard `merge_update_columns` / `merge_exclude_columns` keys that dbt-core already provides.
2. **Validation duplication.** The macros now contain three compile-time exception branches to enforce that the new keys only apply to `merge` and that they are mutually exclusive. That validation has to be reimplemented in Jinja because dbt-core doesn't know about these keys.
3. **Precedent.** The first adapter-private config on a stable materialization is the hardest one to push back on. After that, every next one is easier. Extensions go in macros and hooks, not on the materializations dbt-core ships.

## User impact

- Models authored against Fabric using these configs cannot be lifted to another warehouse without rewriting.
- Models lifted *to* Fabric from other warehouses can't take advantage of these configs without modification, but can also be silently confusing — dbt-core users expect `incremental` config keys to behave the same across platforms.
- Maintenance: the adapter now owns custom validation logic that dbt-core would otherwise handle.

## Suggested fix

Remove the configs from the `incremental` materialization. Provide the same semantics through a Fabric-specific helper macro that users opt into:

```jinja
-- models/my_model.sql
{{ config(
    materialized='incremental',
    unique_key='id',
    post_hook="{{ fabric_purge_unmatched(this, 'date_col >= dateadd(day, -30, getdate())') }}"
) }}
```

A `fabric_purge_unmatched(target, condition)` macro is a clean opt-in extension that does not modify the user-facing surface of `incremental`. dbt-core's `incremental` keys keep their cross-warehouse meaning, and the Fabric extension is documented as Fabric-specific.

Alternatively: if delete-by-condition is genuinely a common-enough need to belong on the materialization, propose it upstream to dbt-core / dbt-adapters as a portable config that all adapters can implement, rather than shipping it adapter-private.

## Notes

- The fork has deliberately avoided adapter-private configs on dbt-core materializations for exactly this reason.
- This is a design issue, not a bug per se — it ships and works. The cost is silent: it leaks into every user's `dbt_project.yml` and is invisible until someone tries to move the project.
