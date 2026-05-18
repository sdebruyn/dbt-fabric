# `delete_warehouse_snapshot` is a `return True` stub — pretends to delete, does nothing

**Repo:** `microsoft/dbt-fabric`
**Labels (suggested):** `bug`, `priority/high`

> [x] **Validated by maintainer** — code refs, line numbers, and claims confirmed against upstream HEAD

> **Internal note (strip before filing):** Do **not** submit this as a standalone PR. The right move is one combined warehouse-snapshots PR that also addresses #17 (move snapshots off `atexit` onto Jinja macros / `on-run-end`). Fixing only the stub leaves the surrounding lifecycle issues in place; bundling them keeps the diff coherent. Too much scope for now — defer until we are ready to take on the full warehouse-snapshots cleanup.

## Summary

`FabricAdapter.delete_warehouse_snapshot(snapshot_id)` is a stub that returns `True` without making any REST call. Users who think they are cleaning up old warehouse snapshots are accumulating them indefinitely on their Fabric capacity.

## Evidence (HEAD [`0de2190`](https://github.com/microsoft/dbt-fabric/tree/0de2190), v1.10.0)

[`dbt/adapters/fabric/warehouse_snapshots.py#L307-L309`](https://github.com/microsoft/dbt-fabric/blob/0de2190/dbt/adapters/fabric/warehouse_snapshots.py#L307-L309):

```python
def delete_warehouse_snapshot(self, snapshot_id):
    # TODO: implement
    return True
```

(Comment may vary slightly, but the method body is a constant `True` return.)

## User impact

- Warehouse snapshots that the user explicitly requested to delete are never deleted.
- Capacity consumption keeps growing.
- dbt reports the delete as successful, so there is no diagnostic signal that anything is wrong.
- This is a silent-failure mode: the operation succeeds from dbt's view, but the platform state diverges from the user's expectation.

## Suggested fix

Implement the actual `DELETE` against the Fabric REST API:

```python
def delete_warehouse_snapshot(self, snapshot_id: str) -> bool:
    url = f"{self.api_base}/workspaces/{self.workspace_id}/warehouseSnapshots/{snapshot_id}"
    resp = self._api_request("DELETE", url)
    resp.raise_for_status()
    return True
```

(With 429 / rate-limit handling, the same way the other API methods on this client are written.)

Reference fix in [the fork](https://github.com/sdebruyn/dbt-fabric): commit [`412b4732`](https://github.com/sdebruyn/dbt-fabric/commit/412b4732).

## Notes

- This stub method has been shipping in production releases. Anyone using the `warehouse_snapshots` feature for hygiene/cleanup is silently accumulating snapshots they think they have deleted.
- The other `warehouse_snapshots` methods in the same file (create, get, list) do make real REST calls — the stub appears to be an oversight from a partial implementation.
