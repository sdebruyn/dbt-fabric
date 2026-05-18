# `FabricAdapter.quote()` does not escape `]` — reserved-word columns break, and identifiers containing `]` are a T-SQL injection vector

**Repo:** `microsoft/dbt-fabric`
**Labels (suggested):** `bug`, `security`, `priority/high`

## Summary

`FabricAdapter.quote()` is `"[{}]".format(identifier)` with no escape. T-SQL bracket quoting requires `]` to be doubled (`]` → `]]`) to escape it inside a bracketed identifier. The current implementation breaks for any identifier that contains `]`, and lets a malicious or careless identifier terminate the bracket prematurely.

## Evidence (HEAD `0de2190`, v1.10.0)

`dbt/adapters/fabric/fabric_adapter.py:37-38`:

```python
@classmethod
def quote(cls, identifier):
    return "[{}]".format(identifier)
```

Same pattern in `FabricColumn.quoted`, `FabricRelation.quoted`, and 5 macros that compose identifiers (`columns.sql`, `alter_relation_add_remove_columns`, `get_use_database_sql`, `create_table_as`, `seeds/helpers.sql`).

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

Reference fix in the fork: commit `414835b`.

## Notes

- This is the standard, documented T-SQL identifier-quoting rule. The single-character escape is canonical.
- No backwards compatibility concern: identifiers with `]` that worked before were silently wrong; identifiers without `]` are unchanged.
