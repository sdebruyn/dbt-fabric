# `_parse_retry_after` duplicated verbatim across four files; all copies use deprecated `datetime.utcnow()`

**Repo:** `microsoft/dbt-fabricspark`
**Labels (suggested):** `bug`, `tech-debt`, `priority/low`

> [x] **Validated by maintainer** — code refs, line numbers, and claims confirmed against upstream HEAD

## Summary

The `_parse_retry_after` helper appears verbatim across four files:

- [`src/dbt/adapters/fabricspark/livysession.py#L370`](https://github.com/microsoft/dbt-fabricspark/blob/d315a56/src/dbt/adapters/fabricspark/livysession.py#L370)
- [`src/dbt/adapters/fabricspark/mlv_api.py#L141`](https://github.com/microsoft/dbt-fabricspark/blob/d315a56/src/dbt/adapters/fabricspark/mlv_api.py#L141)
- [`src/dbt/adapters/fabricspark/concurrent_livy.py#L60`](https://github.com/microsoft/dbt-fabricspark/blob/d315a56/src/dbt/adapters/fabricspark/concurrent_livy.py#L60)
- [`src/dbt/adapters/fabricspark/singleton_livy.py#L34`](https://github.com/microsoft/dbt-fabricspark/blob/d315a56/src/dbt/adapters/fabricspark/singleton_livy.py#L34)

All four copies use `datetime.utcnow()`, which has been deprecated since Python 3.12 in favor of `datetime.now(timezone.utc)`. When `utcnow()` is eventually removed in a future Python release, the bug surfaces in four places at once — and any fix has to be applied in four places too.

## User impact

- Today: a `DeprecationWarning` from each call site when running on Python 3.12+.
- When Python removes `utcnow()`: every HTTP request that needs to honor a `Retry-After` header breaks, simultaneously, in four files.
- Right now: any future improvement to retry-after handling (timezone-aware HTTP date parsing, jitter, etc.) has to be made in four places and kept in sync.

## Suggested fix

Extract `_parse_retry_after` into a single shared module (e.g. `src/dbt/adapters/fabricspark/_http_utils.py`), import from there in all four files, and fix `datetime.utcnow()` → `datetime.now(timezone.utc)` once:

```python
# _http_utils.py
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

def parse_retry_after(header_value: str | None) -> float | None:
    if not header_value:
        return None
    try:
        return float(header_value)
    except ValueError:
        try:
            target = parsedate_to_datetime(header_value)
            return max((target - datetime.now(timezone.utc)).total_seconds(), 0)
        except (TypeError, ValueError):
            return None
```
