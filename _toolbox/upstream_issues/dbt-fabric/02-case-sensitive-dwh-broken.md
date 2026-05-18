# Case-sensitive Fabric Warehouses are broken: `_make_match_kwargs` is not overridden

**Repo:** `microsoft/dbt-fabric`
**Labels (suggested):** `bug`, `priority/high`

> [x] **Validated by maintainer** — code refs, line numbers, and claims confirmed against upstream HEAD

> **Internal note (strip before filing):** Submittable as a PR — one-method override on `FabricAdapter`. Consider opening with the issue *and* a draft PR linked from it.

## Summary

`FabricAdapter` does not override `_make_match_kwargs`, so dbt-adapters' default implementation runs unchanged. That default lowercases identifiers whenever `quoting.case_sensitive` is `False` (the dbt-core default). On a Fabric Warehouse provisioned with a case-sensitive collation (e.g. `SQL_Latin1_General_CP1_CS_AS`), dbt then asks Fabric for a relation by its lowercased name and Fabric correctly answers "no such object".

## Evidence (HEAD [`0de2190`](https://github.com/microsoft/dbt-fabric/tree/0de2190), v1.10.0)

```shell
git show 0de2190:dbt/adapters/fabric/fabric_adapter.py | grep _make_match_kwargs
# (returns nothing)
```

No `_make_match_kwargs` override exists on `FabricAdapter` — see [`dbt/adapters/fabric/fabric_adapter.py`](https://github.com/microsoft/dbt-fabric/blob/0de2190/dbt/adapters/fabric/fabric_adapter.py).

## Reproduction

1. Provision a Fabric Warehouse with a case-sensitive collation (`SQL_Latin1_General_CP1_CS_AS`).
2. Create any dbt model with mixed-case identifiers (e.g. `MyTable`).
3. Run `dbt run`.
4. Subsequent `dbt run` / `dbt build` invocations fail with `Relation [MyTable] does not exist` because dbt's relation cache has the lowercased name.

## User impact

The adapter is **unusable** against any case-sensitive Fabric Warehouse. Case-sensitive collations are a supported, documented Fabric Warehouse configuration; anyone using one cannot use dbt-fabric.

## Suggested fix

Add a one-method override on `FabricAdapter`:

```python
@classmethod
def _make_match_kwargs(cls, database, schema, identifier):
    quoting = cls.ConnectionManager.TYPE
    return filter_null_values({
        "database": database,
        "identifier": identifier,
        "schema": schema,
    })
```

Reference fix in [the fork](https://github.com/sdebruyn/dbt-fabric): commit [`7b12ec6f`](https://github.com/sdebruyn/dbt-fabric/commit/7b12ec6f).

