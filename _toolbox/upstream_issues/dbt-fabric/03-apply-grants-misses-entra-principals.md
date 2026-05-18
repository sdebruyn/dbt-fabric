# `apply_grants` re-issues the same GRANTs on every run (Entra principals invisible to `INFORMATION_SCHEMA.TABLE_PRIVILEGES`)

**Repo:** `microsoft/dbt-fabric`
**Labels (suggested):** `bug`, `priority/medium`

## Summary

`fabric__get_show_grant_sql` queries `INFORMATION_SCHEMA.TABLE_PRIVILEGES`. On Fabric Warehouse, that view does not surface Entra-principal grants — only SQL-principal grants. dbt's diff-based `apply_grants` machinery therefore sees every Entra-principal grant as "missing" on every run, re-issues the same `GRANT` statement on every run, and fills the warehouse with no-op DDL.

## Evidence (HEAD `0de2190`, v1.10.0)

`dbt/include/fabric/macros/adapters/apply_grants.sql`:

```sql
{% macro fabric__get_show_grant_sql(relation) %}
    select GRANTEE as grantee, PRIVILEGE_TYPE as privilege_type
    from INFORMATION_SCHEMA.TABLE_PRIVILEGES {{ information_schema_hints() }}
    where TABLE_CATALOG = '{{ relation.database }}' ...
{% endmacro %}
```

## User impact

- Every dbt run re-issues GRANTs that are already in place. Logs and warehouse history fill with redundant DDL.
- Audit-trail noise: distinguishing real grant changes from idempotent re-application becomes impossible.
- Minor capacity / latency overhead on each dbt run.

## Suggested fix

Query `sys.database_principals` joined with `sys.database_permissions`, which correctly surfaces both SQL and Entra principals:

```sql
{% macro fabric__get_show_grant_sql(relation) %}
    select dp.name as grantee, dperm.permission_name as privilege_type
    from sys.database_permissions dperm
    inner join sys.database_principals dp on dperm.grantee_principal_id = dp.principal_id
    inner join sys.objects o on dperm.major_id = o.object_id
    inner join sys.schemas s on o.schema_id = s.schema_id
    where dperm.state = 'G'
      and dperm.class_desc = 'OBJECT_OR_COLUMN'
      and s.name = '{{ relation.schema }}'
      and o.name = '{{ relation.identifier }}'
{% endmacro %}
```

Reference fix in the fork: commit `42063121`.

## Notes

- The `INFORMATION_SCHEMA.TABLE_PRIVILEGES` view is part of the ANSI standard but does not have a defined behavior for Microsoft Entra principals. Fabric returns SQL principals only; this is consistent with SQL Server's interpretation but means the standard view is the wrong primitive for Fabric grant introspection.
- Behavior is reproducible by granting `SELECT` to an Entra group on a table and watching `dbt run` re-emit the GRANT every cycle.
