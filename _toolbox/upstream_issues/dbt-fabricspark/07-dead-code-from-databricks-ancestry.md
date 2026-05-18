# Dead code from Databricks/Spark ancestry: Thrift exception handler + AWS logging config + duplicated `_parse_retry_after`

**Repo:** `microsoft/dbt-fabricspark`
**Labels (suggested):** `bug`, `tech-debt`, `priority/low`

## Summary

`connections.py` contains code paths that never run in this adapter, carried over from a Spark/Databricks ancestor (likely `dbt-spark`). The dead code has user-visible side effects (boto3 debug noise in logs) and represents code that nobody removed because nobody worked out what it was for.

## Evidence (HEAD `d315a56`)

**Thrift exception handler** — `connections.py:102-114` references `thrift_resp.status.errorMessage`. Apache Thrift is the protocol `dbt-spark` uses to talk to Spark Thrift Server. This adapter talks Livy over HTTP. The Thrift branch is unreachable in this adapter.

**AWS logging config** — `connections.py:42-50` sets `botocore` and `boto3` loggers to DEBUG at import time:

```python
logging.getLogger("botocore").setLevel(logging.DEBUG)
logging.getLogger("boto3").setLevel(logging.DEBUG)
```

This adapter has no AWS dependencies (no `boto3`, no `botocore` in `pyproject.toml`). The lines are no-ops in terms of behavior but they're not harmless: if the user's project transitively imports boto3 (common in dbt projects with S3-backed assets or in Databricks-adjacent environments), this code injects boto3 debug noise into every user's dbt log output.

**Duplicated `_parse_retry_after`** — the function appears verbatim across four files:
- `livysession.py:370`
- `mlv_api.py:141`
- `concurrent_livy.py:60`
- `singleton_livy.py:34`

All four copies use deprecated `datetime.utcnow()` (deprecated since Python 3.12 in favor of `datetime.now(timezone.utc)`). When `utcnow` is removed in a future Python release, the bug will surface in four places at once.

## User impact

- Confusing debug noise (boto3) for any user whose project transitively pulls in AWS SDKs.
- A Python deprecation today; a hard breakage in some future Python release. All four copies will break together because they share the same bug.
- Code reviewers (human or AI) face dead code that they cannot tell is dead — every change near these sites has to consider the Thrift branch, even though it is unreachable.

## Suggested fix

1. Delete the Thrift exception handler in `connections.py:102-114`. The path is unreachable.
2. Delete the AWS logging configuration in `connections.py:42-50`. This adapter has no AWS dependencies.
3. Extract `_parse_retry_after` into a single shared module (e.g. `_http_utils.py`), import from there in all four files, fix `datetime.utcnow()` → `datetime.now(timezone.utc)` once.

```python
# _http_utils.py
from datetime import datetime, timezone

def parse_retry_after(header_value: str | None) -> float | None:
    if not header_value:
        return None
    try:
        return float(header_value)  # seconds
    except ValueError:
        try:
            target = parsedate_to_datetime(header_value)  # HTTP date
            delta = (target - datetime.now(timezone.utc)).total_seconds()
            return max(delta, 0)
        except (TypeError, ValueError):
            return None
```

## Notes

- The "dead code from sibling-project ancestry" pattern is documented in the broader PR critique: it is the strongest single tell that PRs land without anyone working out what the existing code is for.
- Removing the dead boto3 logging config also removes a small attack surface (one fewer module-import-time side effect that an attacker who can substitute a `boto3` package could exploit).
