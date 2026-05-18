# `connections.py` sets `botocore` / `boto3` loggers to DEBUG at import time

**Repo:** `microsoft/dbt-fabricspark`
**Labels (suggested):** `bug`, `tech-debt`, `priority/low`

> [x] **Validated by maintainer** — code refs, line numbers, and claims confirmed against upstream HEAD

> **Internal note (strip before filing):** Submittable as a PR — delete the 9 lines that configure boto3/botocore loggers. Consider opening with the issue *and* a draft PR linked from it.

## Summary

[`src/dbt/adapters/fabricspark/connections.py#L42-L50`](https://github.com/microsoft/dbt-fabricspark/blob/d315a56/src/dbt/adapters/fabricspark/connections.py#L42-L50) sets the `botocore` and `boto3` loggers to DEBUG at module import time:

```python
logging.getLogger("botocore").setLevel(logging.DEBUG)
logging.getLogger("boto3").setLevel(logging.DEBUG)
```

This adapter has no AWS dependency (no `boto3` / `botocore` in [`pyproject.toml`](https://github.com/microsoft/dbt-fabricspark/blob/d315a56/pyproject.toml)). The lines look like a leftover from a `dbt-spark` / Databricks ancestor.

## User impact

The lines are no-ops *until* the user's project transitively imports `boto3` — which is common in dbt projects with S3-backed assets, or in environments where other packages on the path pull AWS SDKs in. When that happens, this code path silently enables `boto3` DEBUG-level logging across the entire process. Every subsequent `boto3` call dumps debug noise (request signing, response bodies, retry traces) into the dbt log, regardless of dbt's own log level.

The effect is not catastrophic but it's invisible to the user — they did not configure boto3 debug logging anywhere in their project, but now it's on.

## Suggested fix

Delete [`connections.py#L42-L50`](https://github.com/microsoft/dbt-fabricspark/blob/d315a56/src/dbt/adapters/fabricspark/connections.py#L42-L50). This adapter has no business configuring loggers for libraries it does not depend on. If a user wants verbose AWS logs they will set their own log level.
