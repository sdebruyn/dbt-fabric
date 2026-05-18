# `apply_label` macro emits a debug `log()` call on every macro invocation — dbt logs are several times noisier than they should be

**Repo:** `microsoft/dbt-fabric`
**Labels (suggested):** `bug`, `observability`, `priority/low`

> [ ] **Validated by maintainer** — code refs, line numbers, and claims confirmed against upstream HEAD

## Summary

The `apply_label` macro in `dbt/include/fabric/macros/adapters/metadata.sql` opens with `{{ log(config.get('query_tag','dbt-fabric')) }}` — a debug leftover that fires on every macro invocation. `apply_label()` is called from [`catalog.sql`](https://github.com/microsoft/dbt-fabric/blob/0de2190/dbt/include/fabric/macros/adapters/catalog.sql), [`columns.sql`](https://github.com/microsoft/dbt-fabric/blob/0de2190/dbt/include/fabric/macros/adapters/columns.sql), [`metadata.sql`](https://github.com/microsoft/dbt-fabric/blob/0de2190/dbt/include/fabric/macros/adapters/metadata.sql), [`relation.sql`](https://github.com/microsoft/dbt-fabric/blob/0de2190/dbt/include/fabric/macros/adapters/relation.sql), [`merge.sql`](https://github.com/microsoft/dbt-fabric/blob/0de2190/dbt/include/fabric/macros/materializations/models/incremental/merge.sql), [`create_table_as.sql`](https://github.com/microsoft/dbt-fabric/blob/0de2190/dbt/include/fabric/macros/materializations/models/table/create_table_as.sql), and [`seeds/helpers.sql`](https://github.com/microsoft/dbt-fabric/blob/0de2190/dbt/include/fabric/macros/materializations/seeds/helpers.sql). Effectively every SQL statement dbt emits dumps the label string to the dbt log.

## Evidence (HEAD [`0de2190`](https://github.com/microsoft/dbt-fabric/tree/0de2190), v1.10.0)

[`dbt/include/fabric/macros/adapters/metadata.sql`](https://github.com/microsoft/dbt-fabric/blob/0de2190/dbt/include/fabric/macros/adapters/metadata.sql):

```jinja
{% macro apply_label() %}
    {{ log(config.get('query_tag','dbt-fabric'))}}
    ...
{% endmacro %}
```

## User impact

- dbt log files are several times noisier than they should be on Fabric.
- The noise hides the messages that actually matter (warnings, statement IDs once those are surfaced — see related issue).
- In CI environments where log volume affects cost or rotation, this is a measurable overhead.

## Suggested fix

Remove the `log()` call:

```jinja
{% macro apply_label() %}
    ...
{% endmacro %}
```

Reference fix in the fork: commit `5226156539`. The fork later removed the entire `apply_label()` helper (commit `0857efc1`) in the broader cleanup that also removed the custom `fabric__snapshot_merge_sql`.

## Notes

- The `log()` call appears to be debug instrumentation from when query-label tagging was being developed. It serves no functional purpose at runtime.
- If query-label tagging is needed for observability, it belongs in a more deliberate, lower-frequency log path, not in a per-statement helper.
