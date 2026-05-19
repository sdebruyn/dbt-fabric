# `_parse_retry_after` duplicated across two files; both copies use deprecated `datetime.utcnow()`

**Repo:** `microsoft/dbt-fabricspark`
**Labels (suggested):** `bug`, `tech-debt`, `priority/low`

> [x] **Validated by maintainer** — code refs, line numbers, and claims confirmed against upstream HEAD

> **Internal note (strip before filing):** Submittable as a PR — extract to a shared helper module, replace `datetime.utcnow()` with `datetime.now(timezone.utc)`, and route the existing thin wrappers in `singleton_livy.py` / `concurrent_livy.py` through it as well. Consider opening with the issue *and* a draft PR linked from it.

## Summary

The `_parse_retry_after` helper exists in two independent full implementations:

- [`src/dbt/adapters/fabricspark/livysession.py#L370`](https://github.com/microsoft/dbt-fabricspark/blob/d315a56/src/dbt/adapters/fabricspark/livysession.py#L370)
- [`src/dbt/adapters/fabricspark/mlv_api.py#L141`](https://github.com/microsoft/dbt-fabricspark/blob/d315a56/src/dbt/adapters/fabricspark/mlv_api.py#L141)

Plus two thin wrappers that re-export the `livysession.py` copy:

- [`src/dbt/adapters/fabricspark/singleton_livy.py#L34`](https://github.com/microsoft/dbt-fabricspark/blob/d315a56/src/dbt/adapters/fabricspark/singleton_livy.py#L34) — `return _livy_helpers._parse_retry_after(response)`
- [`src/dbt/adapters/fabricspark/concurrent_livy.py#L60`](https://github.com/microsoft/dbt-fabricspark/blob/d315a56/src/dbt/adapters/fabricspark/concurrent_livy.py#L60) — `return _livy_helpers._parse_retry_after(response)`

The two full implementations both use `datetime.utcnow()`, which has been deprecated since Python 3.12 in favor of `datetime.now(timezone.utc)`. When `utcnow()` is eventually removed in a future Python release, the bug surfaces in two places at once — and any fix has to be applied in two places.

The thin wrappers reach into `livysession`'s underscore-prefixed name (`_livy_helpers._parse_retry_after`), which is a clear signal that the helper wants to live in a dedicated module — pulling it through `livysession` is just convenient.

## User impact

- Today: a `DeprecationWarning` from each call site when running on Python 3.12+.
- When Python removes `utcnow()`: every HTTP request that needs to honor a `Retry-After` header breaks, simultaneously, in two files.
- Right now: any future improvement to retry-after handling (timezone-aware HTTP date parsing, jitter, etc.) has to be made in two places and kept in sync. `mlv_api.py`'s copy has already diverged from `livysession.py`'s in subtle ways across past changes.

## Suggested fix

Extract `parse_retry_after` into a dedicated module (e.g. `src/dbt/adapters/fabricspark/_http_utils.py`), import from there in `livysession.py`, `mlv_api.py`, and the two thin wrappers, and fix `datetime.utcnow()` → `datetime.now(timezone.utc)` once:

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
