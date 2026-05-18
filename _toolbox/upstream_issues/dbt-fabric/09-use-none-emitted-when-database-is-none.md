# `fabric__get_use_database_sql` emits invalid `USE [None];` when `database=None`

**Repo:** `microsoft/dbt-fabric`
**Labels (suggested):** `bug`, `priority/medium`

## Summary

`fabric__get_use_database_sql` has no None-guard, so callers that pass `database=None` (legitimately, in some code paths) cause the macro to render `USE [None];` — syntactically invalid T-SQL.

## Evidence (HEAD `0de2190`, v1.10.0)

`dbt/include/fabric/macros/adapters/metadata.sql`:

```jinja
{%- macro fabric__get_use_database_sql(database) -%}
  USE [{{database | replace('"', '') | replace('[', '') | replace(']', '')}}];
{%- endmacro -%}
```

If `database` is the Python value `None`, Jinja renders it as the string `"None"`.

## User impact

Operations that pass `database=None` (notably `drop_schema` and related metadata helpers in certain dbt-core configurations) fail with a `Invalid object name 'None'` style error. The error appears as a generic T-SQL parsing failure with no obvious connection to dbt's database handling.

## Suggested fix

Wrap the body in a None-guard:

```jinja
{%- macro fabric__get_use_database_sql(database) -%}
  {%- if database is not none -%}
    USE [{{ database | replace('"', '') | replace('[', '') | replace(']', '') }}];
  {%- endif -%}
{%- endmacro -%}
```

Reference fix in the fork: commit `dea31d36`.

## Notes

- The fork additionally escapes `]` as `]]` in this macro (see related issue on identifier quoting). Both fixes belong together.
