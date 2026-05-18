# `varchar(8000)` default in `FabricColumn` silently truncates strings

**Repo:** `microsoft/dbt-fabric`
**Labels (suggested):** `bug`, `data-loss`, `priority/high`

> [ ] **Validated by maintainer** — code refs, line numbers, and claims confirmed against upstream HEAD

## Summary

`FabricColumn.TYPE_LABELS` maps the generic `STRING` type to `VARCHAR(8000)`, and `FabricColumn.string_type()` / `string_size()` both default to `8000` when `char_size` is `None`. Fabric Warehouse supports `varchar(MAX)`, so the 8000-character cap is an unnecessary hard limit that silently truncates any string column produced through these code paths.

## Evidence (HEAD [`0de2190`](https://github.com/microsoft/dbt-fabric/tree/0de2190), v1.10.0)

- [`dbt/adapters/fabric/fabric_column.py`](https://github.com/microsoft/dbt-fabric/blob/0de2190/dbt/adapters/fabric/fabric_column.py) — `TYPE_LABELS` maps `STRING → VARCHAR(8000)`; `string_type(size)` / `string_size()` fall back to `8000` when `size` is `None`.

These defaults flow into:
- `fabric__snapshot_hash_arguments` in [`dbt/include/fabric/macros/materializations/snapshots/`](https://github.com/microsoft/dbt-fabric/tree/0de2190/dbt/include/fabric/macros/materializations/snapshots) — snapshot `dbt_scd_id` hash inputs.
- `fabric__hash` in [`dbt/include/fabric/macros/utils/hash.sql`](https://github.com/microsoft/dbt-fabric/blob/0de2190/dbt/include/fabric/macros/utils/hash.sql) — surrogate-key materializations (dbt-utils `generate_surrogate_key`, etc.).
- Any model where a string column type is inferred (no explicit size).

## User impact

- Surrogate keys and snapshot hash columns silently truncate at 8000 characters → collisions in `dbt_scd_id`, missed updates in snapshots, broken joins on hashed keys.
- Any inferred-width string column is hard-capped at 8000 chars regardless of source data width.
- The truncation is silent: no warning, no error, just lost data.

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

Reference fix in the fork: commit `9c3ac010` ("string→varchar(MAX) sweep across `TYPE_LABELS`, `string_type`, `fabric__snapshot_hash_arguments`, `fabric__hash`").

## Notes

- Fabric Warehouse documentation confirms `varchar(MAX)` is supported.
- Earlier versions of Fabric DW did cap string columns at `varchar(8000)`, which is presumably where the adapter default originated. Fabric DW now supports `varchar(MAX)`; the adapter default has not been updated to match.
