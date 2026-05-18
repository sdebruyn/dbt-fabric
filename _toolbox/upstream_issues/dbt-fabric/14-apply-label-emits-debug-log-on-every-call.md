# `apply_label`: debug `log()` on every invocation, and the helper itself should be replaced by dbt-adapters' `query_header` mechanism

**Repo:** `microsoft/dbt-fabric`
**Labels (suggested):** `bug`, `refactor`, `observability`, `priority/low`
**Related:** issue #12 (`snapshot_merge_sql` UPDATE+INSERT) — the custom snapshot merge exists almost entirely to thread `apply_label()` between two statements; centralizing the label removes the reason that override exists.

> [x] **Validated by maintainer** — code refs, line numbers, and claims confirmed against upstream HEAD

## Summary

Two related problems, one in the macro body and one in the surrounding design:

1. The `apply_label` macro in `dbt/include/fabric/macros/adapters/metadata.sql` opens with `{{ log(config.get('query_tag','dbt-fabric')) }}` — a debug leftover that fires on every macro invocation. `apply_label()` is called from [`catalog.sql`](https://github.com/microsoft/dbt-fabric/blob/0de2190/dbt/include/fabric/macros/adapters/catalog.sql), [`columns.sql`](https://github.com/microsoft/dbt-fabric/blob/0de2190/dbt/include/fabric/macros/adapters/columns.sql), [`metadata.sql`](https://github.com/microsoft/dbt-fabric/blob/0de2190/dbt/include/fabric/macros/adapters/metadata.sql), [`relation.sql`](https://github.com/microsoft/dbt-fabric/blob/0de2190/dbt/include/fabric/macros/adapters/relation.sql), [`merge.sql`](https://github.com/microsoft/dbt-fabric/blob/0de2190/dbt/include/fabric/macros/materializations/models/incremental/merge.sql), [`create_table_as.sql`](https://github.com/microsoft/dbt-fabric/blob/0de2190/dbt/include/fabric/macros/materializations/models/table/create_table_as.sql), and [`seeds/helpers.sql`](https://github.com/microsoft/dbt-fabric/blob/0de2190/dbt/include/fabric/macros/materializations/seeds/helpers.sql), so effectively every SQL statement dbt emits dumps the label string to the dbt log.
2. The `apply_label()` helper is called by hand from each of those seven sites. That is the wrong shape for the job: dbt-adapters ships a generic per-query header/footer mechanism (`MacroQueryStringSetter` + `set_query_header`) that every other reference adapter uses. Threading a custom helper through every materialization and metadata macro both invites the bug above and creates incidental coupling — the custom `fabric__snapshot_merge_sql` (separate issue) exists in part because it has to thread `apply_label()` between its UPDATE and INSERT statements.

The macro body bug is one-line. The structural fix is also small but unlocks deleting the custom snapshot merge and several other one-off overrides.

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

**Short-term:** drop the `log()` call:

```jinja
{% macro apply_label() %}
    ...
{% endmacro %}
```

**Proper fix:** delete the `apply_label()` helper entirely and use [`dbt-adapters`' query-header mechanism](https://github.com/dbt-labs/dbt-adapters/blob/main/dbt-adapters/src/dbt/adapters/base/query_headers.py). Every query that goes through `add_query` is automatically wrapped by the `MacroQueryStringSetter` installed on the connection manager. Users configure the label via `query-comment:` in `dbt_project.yml`, which is the same documented surface every other reference adapter already supports. For Fabric specifically, subclass `MacroQueryStringSetter` so the label becomes a T-SQL `OPTION (LABEL = '...')` suffix instead of a SQL comment, and install it via `set_query_header` on `FabricConnectionManager`. Sketch:

```python
class FabricQueryStringSetter(MacroQueryStringSetter):
    def add(self, sql: str) -> str:
        comment = self.comment()  # rendered from query-comment macro
        if not comment:
            return sql
        return f"{sql}\nOPTION (LABEL = '{comment}')"

class FabricConnectionManager(SQLConnectionManager):
    def set_query_header(self, query_header_context):
        self.query_header = FabricQueryStringSetter(self.profile, query_header_context)
```

That:

- removes the seven hand-rolled `apply_label()` callsites,
- removes the temptation to put debug `log()` calls inside a per-query helper,
- makes the label configurable through the standard `query-comment` config users already know,
- and unblocks deleting the custom `fabric__snapshot_merge_sql` override (see related issue #12), since the only reason that override exists is to interleave `apply_label()` between its UPDATE and INSERT.

Reference fix in [the fork](https://github.com/sdebruyn/dbt-fabric): commit [`5226156539`](https://github.com/sdebruyn/dbt-fabric/commit/5226156539) (initial log-call removal). [The fork](https://github.com/sdebruyn/dbt-fabric) later removed the entire `apply_label()` helper (commit [`0857efc1`](https://github.com/sdebruyn/dbt-fabric/commit/0857efc1)) as part of the same cleanup that deleted the custom `fabric__snapshot_merge_sql`.

