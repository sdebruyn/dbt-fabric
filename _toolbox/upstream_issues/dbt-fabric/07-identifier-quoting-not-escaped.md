# `FabricAdapter.quote()` does not escape `]` — reserved-word columns break, and identifiers containing `]` are a T-SQL injection vector

**Repo:** `microsoft/dbt-fabric`
**Labels (suggested):** `bug`, `security`, `priority/high`

> [x] **Validated by maintainer** — code refs, line numbers, and claims confirmed against upstream HEAD

> **Internal note (strip before filing):** Submittable as a PR — escape `]` as `]]` in `quote()`, `FabricColumn.quoted`, `FabricRelation.quoted`, and the 5 affected macros. Consider opening with the issue *and* a draft PR linked from it.

## Summary

`FabricAdapter.quote()` is `"[{}]".format(identifier)` with no escape. T-SQL bracket quoting requires `]` to be doubled (`]` → `]]`) to escape it inside a bracketed identifier. The current implementation breaks for any identifier that contains `]`, and lets a malicious or careless identifier terminate the bracket prematurely.

## Evidence (HEAD [`0de2190`](https://github.com/microsoft/dbt-fabric/tree/0de2190), v1.10.0)

[`dbt/adapters/fabric/fabric_adapter.py#L37-L38`](https://github.com/microsoft/dbt-fabric/blob/0de2190/dbt/adapters/fabric/fabric_adapter.py#L37-L38):

```python
@classmethod
def quote(cls, identifier):
    return "[{}]".format(identifier)
```

Same pattern in [`FabricColumn`](https://github.com/microsoft/dbt-fabric/blob/0de2190/dbt/adapters/fabric/fabric_column.py), [`FabricRelation`](https://github.com/microsoft/dbt-fabric/blob/0de2190/dbt/adapters/fabric/fabric_relation.py), and 5 macros that compose identifiers — [`columns.sql`](https://github.com/microsoft/dbt-fabric/blob/0de2190/dbt/include/fabric/macros/adapters/columns.sql), [`alter_relation_add_remove_columns`](https://github.com/microsoft/dbt-fabric/blob/0de2190/dbt/include/fabric/macros/adapters/columns.sql), [`get_use_database_sql`](https://github.com/microsoft/dbt-fabric/blob/0de2190/dbt/include/fabric/macros/adapters/metadata.sql), [`create_table_as`](https://github.com/microsoft/dbt-fabric/blob/0de2190/dbt/include/fabric/macros/materializations/models/table/create_table_as.sql), [`seeds/helpers.sql`](https://github.com/microsoft/dbt-fabric/blob/0de2190/dbt/include/fabric/macros/materializations/seeds/helpers.sql).

## Reproduction

```sql
-- A reserved word silently breaks
{{ adapter.quote("order") }}
-- → [order]   ✓ ok, but only because `order` has no special chars

-- An identifier with ]
{{ adapter.quote("weird]name") }}
-- → [weird]name]   ✗ T-SQL parser sees [weird] followed by `name]`
```

## User impact

- Reserved-word column names that happen to contain `]` break silently.
- Far more importantly, this is a **T-SQL injection vector**: a model name, source name, or column name containing `];` followed by arbitrary T-SQL will be emitted by dbt and executed by Fabric. The attack surface is small (dbt projects do not typically take untrusted input as identifiers), but it is not zero — anyone building dbt projects from a multi-tenant catalog or letting users name their own models is exposed.

## Suggested fix

Escape `]` as `]]`:

```python
@classmethod
def quote(cls, identifier):
    return "[{}]".format(identifier.replace("]", "]]"))
```

Apply the same fix to `FabricColumn.quoted`, `FabricRelation.quoted`, and the five macros listed above.

Reference fix in [the fork](https://github.com/sdebruyn/dbt-fabric): commit [`414835b`](https://github.com/sdebruyn/dbt-fabric/commit/414835b).

