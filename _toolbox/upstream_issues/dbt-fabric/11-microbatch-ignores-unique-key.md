# `fabric__get_incremental_microbatch_sql` ignores `unique_key` — always delete+insert, never MERGE

**Repo:** `microsoft/dbt-fabric`
**Labels (suggested):** `bug`, `priority/medium`

> [ ] **Validated by maintainer** — code refs, line numbers, and claims confirmed against upstream HEAD

## Summary

`fabric__get_incremental_microbatch_sql` always performs a delete-then-insert sequence, even when `unique_key` is configured on the model. Fabric DW supports native `MERGE`, which is atomic and avoids the intermediate "empty rows" window that delete-then-insert exposes to concurrent readers.

## Evidence (HEAD [`0de2190`](https://github.com/microsoft/dbt-fabric/tree/0de2190), v1.10.0)

[`dbt/include/fabric/macros/materializations/models/incremental/microbatch.sql`](https://github.com/microsoft/dbt-fabric/blob/0de2190/dbt/include/fabric/macros/materializations/models/incremental/microbatch.sql): the macro emits a delete-by-microbatch-key followed by an insert, with no branch on `unique_key`.

## User impact

- For models with `unique_key` configured, what should be one atomic MERGE becomes two statements.
- Concurrent readers see a window where the deleted rows are gone but the inserts have not yet landed. On a typical Fabric DW with snapshot isolation this is bounded but observable.
- More warehouse work per run than necessary.

## Suggested fix

When `unique_key` is present, dispatch to `get_incremental_merge_sql` so the operation runs as a single MERGE:

```jinja
{% macro fabric__get_incremental_microbatch_sql(arg_dict) %}
    {%- if arg_dict["unique_key"] -%}
        {{ get_incremental_merge_sql(arg_dict) }}
    {%- else -%}
        {{ get_incremental_delete_insert_sql(arg_dict) }}
    {%- endif -%}
{% endmacro %}
```

Reference fix in [the fork](https://github.com/sdebruyn/dbt-fabric): commit [`955ab2e3`](https://github.com/sdebruyn/dbt-fabric/commit/955ab2e3).

## Notes

- The same MERGE-when-possible pattern is also worth applying to `fabric__snapshot_merge_sql`, which currently is a custom 2-statement UPDATE+INSERT. See related issue.
