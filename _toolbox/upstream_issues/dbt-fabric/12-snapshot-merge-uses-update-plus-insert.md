# Custom `fabric__snapshot_merge_sql` is a 30-line UPDATE+INSERT pair — replace with native MERGE

**Repo:** `microsoft/dbt-fabric`
**Labels (suggested):** `enhancement`, `priority/low`
**Related:** issue #14 (`apply_label`) — the only reason this override exists is to thread `apply_label()` between two statements; centralizing the label via dbt-adapters' `query_header` removes the reason this macro exists.

> [x] **Validated by maintainer** — code refs, line numbers, and claims confirmed against upstream HEAD

## Summary

The adapter ships a custom `fabric__snapshot_merge_sql` macro that does an UPDATE statement followed by a separate INSERT statement, with an `apply_label()` helper call between them. dbt-core's `default__snapshot_merge_sql` produces a single `MERGE` statement that Fabric DW supports natively. The custom override is unnecessary, produces non-atomic behavior, and runs two statements where one suffices.

## Evidence (HEAD [`0de2190`](https://github.com/microsoft/dbt-fabric/tree/0de2190), v1.10.0)

[`dbt/include/fabric/macros/materializations/snapshots/snapshot_merge.sql`](https://github.com/microsoft/dbt-fabric/blob/0de2190/dbt/include/fabric/macros/materializations/snapshots/snapshot_merge.sql) defines `fabric__snapshot_merge_sql` as a 30-line UPDATE-then-INSERT pair.

## User impact

- Two warehouse round-trips per snapshot run instead of one.
- Non-atomic semantics: a reader that lands between the UPDATE and the INSERT can see an inconsistent snapshot.
- More code to maintain in the adapter.

## Suggested fix

Delete `fabric__snapshot_merge_sql` entirely and let dbt-core's `default__snapshot_merge_sql` (which uses MERGE) handle Fabric. Fabric Warehouse supports `MERGE INTO` with the standard ANSI syntax dbt-core emits.

This fix is naturally paired with #14 (centralizing query labels via dbt-adapters' `query_header`). Once labeling happens at the connection-manager layer instead of per-statement Jinja, the only justification for the custom override (interleaving `apply_label()` between UPDATE and INSERT) disappears and the macro can simply be deleted.

Reference fix in [the fork](https://github.com/sdebruyn/dbt-fabric): commit [`0857efc1`](https://github.com/sdebruyn/dbt-fabric/commit/0857efc1) (combined deletion of `fabric__snapshot_merge_sql` and the `apply_label()` helper it relied on).

## Notes

- Most reference adapters (Snowflake, BigQuery, Postgres, Spark) inherit `default__snapshot_merge_sql` for the same reason: it just works on engines that support standard `MERGE INTO`.
