# `fabric__get_use_database_sql` emits invalid `USE [None];` when `database=None`

**Repo:** `microsoft/dbt-fabric`
**Labels (suggested):** `bug`, `priority/medium`

> [x] **Validated by maintainer** — code refs, line numbers, and claims confirmed against upstream HEAD

> **Internal note (strip before filing):** Submittable as a PR — three-line None-guard in `metadata.sql`. Consider opening with the issue *and* a draft PR linked from it.

## Summary

`fabric__get_use_database_sql` has no None-guard, so callers that pass `database=None` (a legitimate dbt-core code path, see below) cause the macro to render `USE [None];` — syntactically invalid T-SQL.

## Evidence (HEAD [`0de2190`](https://github.com/microsoft/dbt-fabric/tree/0de2190), v1.10.0)

[`dbt/include/fabric/macros/adapters/metadata.sql`](https://github.com/microsoft/dbt-fabric/blob/0de2190/dbt/include/fabric/macros/adapters/metadata.sql):

```jinja
{%- macro fabric__get_use_database_sql(database) -%}
  USE [{{database | replace('"', '') | replace('[', '') | replace(']', '')}}];
{%- endmacro -%}
```

If `database` is the Python value `None`, Jinja renders it as the string `"None"`.

## How `database=None` happens in practice

This is not a hypothetical. dbt-core's [`default__drop_schema_named`](https://github.com/dbt-labs/dbt-adapters/blob/main/dbt-adapters/src/dbt/include/global_project/macros/relations/schema.sql) macro builds a relation with **no database** and hands it to `drop_schema`:

```jinja
{% macro default__drop_schema_named(schema_name) %}
  {% set schema_relation = api.Relation.create(schema=schema_name) %}
  {{ adapter.drop_schema(schema_relation) }}
{% endmacro %}
```

`api.Relation.create(schema=schema_name)` creates a relation with `relation.database = None` because the caller did not specify one. `drop_schema` then dispatches into `fabric__drop_schema`, which calls `fabric__get_use_database_sql(relation.database)` — i.e. `fabric__get_use_database_sql(None)` — and the macro renders `USE [None];`.

User-facing triggers for this code path:
- `dbt run-operation drop_schema_named --args '{schema_name: foo}'` — the documented way to drop a schema by name without specifying a database.
- The `BaseDropSchemaNamed` test class in `dbt-tests-adapter` exercises this exact path, which is how the bug was caught in the fork (see commit message of the linked fix).
- Any user-authored macro that calls `api.Relation.create(schema=...)` without a database arg and then hands the relation to a metadata helper.

## User impact

A `dbt run-operation drop_schema_named` call fails with `Invalid object name 'None'`. The error appears as a generic T-SQL parsing failure with no obvious connection to dbt's database handling — users typically waste time looking at their schema name or permissions before tracing it back to the macro.

## Suggested fix

Wrap the body in a None-guard:

```jinja
{%- macro fabric__get_use_database_sql(database) -%}
  {%- if database is not none -%}
    USE [{{ database | replace('"', '') | replace('[', '') | replace(']', '') }}];
  {%- endif -%}
{%- endmacro -%}
```

Reference fix in [the fork](https://github.com/sdebruyn/dbt-fabric): commit [`dea31d36`](https://github.com/sdebruyn/dbt-fabric/commit/dea31d36).

