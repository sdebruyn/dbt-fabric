# `connections.py` sets `botocore` / `boto3` loggers to DEBUG at import time

**Repo:** `microsoft/dbt-fabricspark`
**Labels (suggested):** `bug`, `tech-debt`, `priority/low`

> [x] **Validated by maintainer** — code refs, line numbers, and claims confirmed against upstream HEAD

> **Internal note (strip before filing):** Submittable as a PR — drop `botocore` and `boto3` from the loop body. Consider opening with the issue *and* a draft PR linked from it.

## Summary

[`src/dbt/adapters/fabricspark/connections.py#L42-L50`](https://github.com/microsoft/dbt-fabricspark/blob/d315a56/src/dbt/adapters/fabricspark/connections.py#L42-L50) iterates a list of logger names at module import time and sets each one to DEBUG via `AdapterLogger.set_adapter_dependency_log_level`:

```python
logger = AdapterLogger("Microsoft Fabric-Spark")
for logger_name in [
    "fabricspark.connector",
    "botocore",
    "boto3",
    "Microsoft Fabric-Spark.connector",
]:
    logger.debug(f"Setting {logger_name} to DEBUG")
    logger.set_adapter_dependency_log_level(logger_name, "DEBUG")
```

`botocore` and `boto3` have no business being in that list — the adapter has no AWS dependency (no `boto3` / `botocore` in [`pyproject.toml`](https://github.com/microsoft/dbt-fabricspark/blob/d315a56/pyproject.toml)). They look like a leftover from a `dbt-spark` / Databricks ancestor and survived a refactor of this block (the direct `logging.getLogger(...).setLevel(...)` calls were replaced with the loop-based `AdapterLogger` API, but the AWS entries were not pruned).

## User impact

The two AWS entries are no-ops *until* the user's project transitively imports `boto3` — which is common in dbt projects with S3-backed assets, or in environments where other packages on the path pull AWS SDKs in. When that happens, this code path silently enables `boto3` DEBUG-level logging across the entire process. Every subsequent `boto3` call dumps debug noise (request signing, response bodies, retry traces) into the dbt log, regardless of dbt's own log level.

The effect is not catastrophic but it's invisible to the user — they did not configure boto3 debug logging anywhere in their project, but now it's on.

## Suggested fix

Remove `"botocore"` and `"boto3"` from the loop in [`connections.py#L43-L48`](https://github.com/microsoft/dbt-fabricspark/blob/d315a56/src/dbt/adapters/fabricspark/connections.py#L43-L48). This adapter has no business configuring loggers for libraries it does not depend on. If a user wants verbose AWS logs they will set their own log level.
