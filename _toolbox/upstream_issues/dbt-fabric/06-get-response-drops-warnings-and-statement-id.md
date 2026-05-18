# `get_response` returns hardcoded `"OK"` and discards every cursor message (warnings + distributed statement ID)

**Repo:** `microsoft/dbt-fabric`
**Labels (suggested):** `bug`, `observability`, `priority/medium`

> [x] **Validated by maintainer** — code refs, line numbers, and claims confirmed against upstream HEAD

> **Internal note (strip before filing):** Submittable as a PR — replace the hardcoded `"OK"` with cursor-message parsing in `fabric_connection_manager.py`. Consider opening with the issue *and* a draft PR linked from it.

## Summary

`FabricConnectionManager.get_response` returns `message = "OK"` regardless of what `cursor.messages` contained. Two things go missing on every query:

1. **SQL warnings, notices, and non-fatal errors** — Fabric surfaces `RAISERROR` with severity < 11, `PRINT` output, deprecation notices, and informational warnings through cursor messages.
2. **The distributed statement ID** — every Fabric DW query gets a server-side GUID emitted in `cursor.messages` as `statement id: {...}`, used by the Fabric portal, query history, and the Capacity Metrics app to identify queries.

## Evidence (HEAD [`0de2190`](https://github.com/microsoft/dbt-fabric/tree/0de2190), v1.10.0)

[`dbt/adapters/fabric/fabric_connection_manager.py#L746-L748`](https://github.com/microsoft/dbt-fabric/blob/0de2190/dbt/adapters/fabric/fabric_connection_manager.py#L746-L748):

```python
def get_response(cls, cursor: Any) -> AdapterResponse:
    # message = str(cursor.statusmessage)
    message = "OK"
```

The first line is commented out; the second hardcodes `"OK"`. `cursor.messages` is never read.

## User impact

- Users see no SQL warnings or `PRINT` output during dbt runs. Issues that Fabric surfaces as warnings (deprecations, optimizer hints, partial-result notices) reach the user only when they escalate into hard errors elsewhere.
- The distributed statement ID is never propagated to dbt's `AdapterResponse.query_id`. Anyone trying to correlate a slow query in the Fabric portal back to the dbt model that issued it has no link.

## Suggested fix

Parse `cursor.messages`:

```python
def get_response(cls, cursor) -> AdapterResponse:
    messages = getattr(cursor, "messages", None) or []
    text_parts: list[str] = []
    statement_id: str | None = None
    for entry in messages:
        text = entry[1] if isinstance(entry, (list, tuple)) and len(entry) > 1 else str(entry)
        text_parts.append(text)
        m = re.search(r"statement id:\s*([0-9A-Fa-f-]{36})", text)
        if m:
            statement_id = m.group(1)
    rows_affected = getattr(cursor, "rowcount", -1)
    return AdapterResponse(
        _message="\n".join(text_parts) if text_parts else "OK",
        rows_affected=rows_affected,
        query_id=statement_id,
    )
```

Reference fix in [the fork](https://github.com/sdebruyn/dbt-fabric): commit [`8bf38cf2`](https://github.com/sdebruyn/dbt-fabric/commit/8bf38cf2).

