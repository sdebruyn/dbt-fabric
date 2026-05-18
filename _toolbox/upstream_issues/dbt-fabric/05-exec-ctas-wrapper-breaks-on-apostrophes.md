# CTAS wrapped in `EXEC('CREATE TABLE ... AS ...')` silently breaks on embedded apostrophes

**Repo:** `microsoft/dbt-fabric`
**Labels (suggested):** `bug`, `priority/high`

> [x] **Validated by maintainer** — code refs, line numbers, and claims confirmed against upstream HEAD

> **Internal note (strip before filing):** Submittable as a PR — drop the `EXEC()` wrapper in `create_table_as.sql`. Consider opening with the issue *and* a draft PR linked from it.

## Summary

`fabric__create_table_as` wraps every `CREATE TABLE AS SELECT` statement inside `EXEC('...')` with manual single-quote escaping. Fabric Warehouse supports CTAS as a first-class statement, so the wrapper is unnecessary. It also breaks any model whose SQL body contains an apostrophe inside a string literal, because the manual escape is not robust.

## Evidence (HEAD [`0de2190`](https://github.com/microsoft/dbt-fabric/tree/0de2190), v1.10.0)

[`dbt/include/fabric/macros/materializations/models/table/create_table_as.sql#L31-L33`](https://github.com/microsoft/dbt-fabric/blob/0de2190/dbt/include/fabric/macros/materializations/models/table/create_table_as.sql#L31-L33):

```sql
EXEC('
    CREATE TABLE {{ relation }} AS
    {{ sql | replace("'", "''") }}
')
```

The `replace("'", "''")` only escapes top-level single quotes. Apostrophes inside string literals that themselves contain `''` (already-escaped) get re-escaped to `''''`, breaking SQL parsing.

## Reproduction

```sql
-- models/example.sql
{{ config(materialized='table') }}
select 'O''Reilly' as customer_name
```

This compiles to broken SQL on Fabric DW.

## User impact

Any model with an apostrophe in a string literal silently fails to materialize. Common cases: customer names (`O'Reilly`), product descriptions, error message templates, French/Italian/etc. text data.

## Suggested fix

Drop the `EXEC()` wrapper and emit a plain CTAS:

```jinja
CREATE TABLE {{ relation }} AS
    {{ sql }}
```

Reference fix in [the fork](https://github.com/sdebruyn/dbt-fabric): commit [`9c9e8000`](https://github.com/sdebruyn/dbt-fabric/commit/9c9e8000).

## Notes

- The `EXEC()` wrapper is a leftover from a SQL Server / Synapse ancestor where CTAS was not a first-class statement and required dynamic SQL. Fabric Warehouse supports CTAS natively; the wrapper is dead infrastructure.
- [The fork](https://github.com/sdebruyn/dbt-fabric)'s removal of the wrapper has been running in production across multiple organizations without issue.
