# `apply_label` macro emits a debug `log()` call on every macro invocation — dbt logs are several times noisier than they should be

**Repo:** `microsoft/dbt-fabric`
**Labels (suggested):** `bug`, `observability`, `priority/low`

## Summary

The `apply_label` macro in `dbt/include/fabric/macros/adapters/metadata.sql` opens with `{{ log(config.get('query_tag','dbt-fabric')) }}` — a debug leftover that fires on every macro invocation. `apply_label()` is called from `catalog.sql`, `columns.sql`, `metadata.sql`, `relation.sql`, `merge.sql`, `create_table_as.sql`, and `seeds/helpers.sql`. Effectively every SQL statement dbt emits dumps the label string to the dbt log.

## Evidence (HEAD `0de2190`, v1.10.0)

`dbt/include/fabric/macros/adapters/metadata.sql`:

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
