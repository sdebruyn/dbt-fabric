# `varchar(8000)` default in `FabricColumn` silently truncates strings

**Repo:** `microsoft/dbt-fabric`
**Labels (suggested):** `bug`, `data-loss`, `priority/high`

> [x] **Validated by maintainer** — code refs, line numbers, and claims confirmed against upstream HEAD

> **Internal note (strip before filing):** Submittable as a PR — fix is a few lines in `fabric_column.py`. Consider opening with the issue *and* a draft PR linked from it.

## Summary

`FabricColumn.TYPE_LABELS` maps the generic `STRING` type to `VARCHAR(8000)`, and `FabricColumn.string_type()` / `string_size()` both default to `8000` when `char_size` is `None`. Fabric Warehouse supports `varchar(MAX)`, so the 8000-character cap is an unnecessary hard limit that silently truncates any string column produced through these code paths.

## Evidence (HEAD [`0de2190`](https://github.com/microsoft/dbt-fabric/tree/0de2190), v1.10.0)

- [`dbt/adapters/fabric/fabric_column.py`](https://github.com/microsoft/dbt-fabric/blob/0de2190/dbt/adapters/fabric/fabric_column.py) — `TYPE_LABELS` maps `STRING → VARCHAR(8000)`; `string_type(size)` / `string_size()` fall back to `8000` when `size` is `None`.

These defaults flow into any code path that asks the adapter what type a string column should be without specifying a width — most commonly, models that copy long-text source columns (JSON payloads, free-text descriptions, serialized blobs) where the column type is inferred rather than declared in a contract.

## User impact

- Any inferred-width string column is hard-capped at 8000 characters regardless of source data width. Long-text columns from a source — JSON payloads, free-text fields, serialized blobs — silently lose the tail beyond byte 8000 when materialized into a Fabric table.
- The truncation is silent: no warning, no error, just lost data. Users typically only notice when a downstream query returns visibly cut-off text.

## Suggested fix

Default to `varchar(MAX)` (Fabric supports it) and only fall back to a fixed width when the user has explicitly requested one.

```python
TYPE_LABELS = {
    ...
    "STRING": "VARCHAR(MAX)",
}

def string_size(self) -> int:
    if self.char_size is None:
        return self.dtype.upper() == "VARCHAR" and -1 or 8000  # -1 → MAX
    return int(self.char_size)
```

Reference fix in [the fork](https://github.com/sdebruyn/dbt-fabric): commit [`9c3ac010`](https://github.com/sdebruyn/dbt-fabric/commit/9c3ac010) ("string→varchar(MAX) sweep across `TYPE_LABELS`, `string_type`, `fabric__snapshot_hash_arguments`, `fabric__hash`").

