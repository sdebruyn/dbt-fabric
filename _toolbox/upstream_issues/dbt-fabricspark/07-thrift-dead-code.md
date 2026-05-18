# Dead Thrift exception handler from dbt-spark ancestry

**Repo:** `microsoft/dbt-fabricspark`
**Labels (suggested):** `bug`, `tech-debt`, `priority/low`

> [ ] **Validated by maintainer** — code refs, line numbers, and claims confirmed against upstream HEAD

## Summary

[`src/dbt/adapters/fabricspark/connections.py#L102-L114`](https://github.com/microsoft/dbt-fabricspark/blob/d315a56/src/dbt/adapters/fabricspark/connections.py#L102-L114) contains a Thrift exception handler that references `thrift_resp.status.errorMessage`. Apache Thrift is the protocol `dbt-spark` uses to talk to Spark Thrift Server. This adapter talks to Fabric Livy over HTTP and has no Thrift dependency. The handler is unreachable from any code path in this adapter — it survives as a copy-paste from a `dbt-spark` ancestor that nobody removed.

## User impact

- No direct runtime impact (the branch never executes).
- Indirect: every reviewer who reads this file has to work out whether the handler is reachable. Repeatedly. The presence of dead code makes future changes around the connection path harder to reason about than they need to be.

## Suggested fix

Delete [`connections.py#L102-L114`](https://github.com/microsoft/dbt-fabricspark/blob/d315a56/src/dbt/adapters/fabricspark/connections.py#L102-L114). No imports, no callers, no tests need to change.
