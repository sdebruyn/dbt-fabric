# `get_headers(tokenPrint=True)` logs the full bearer token — security risk one debug flag away

**Repo:** `microsoft/dbt-fabricspark`
**Labels (suggested):** `security`, `priority/high`

> [ ] **Validated by maintainer** — code refs, line numbers, and claims confirmed against upstream HEAD

## Summary

`get_headers()` at [`src/dbt/adapters/fabricspark/livysession.py#L328`](https://github.com/microsoft/dbt-fabricspark/blob/d315a56/src/dbt/adapters/fabricspark/livysession.py#L328) accepts a `tokenPrint` parameter. When `tokenPrint=True`, the function logs the full Authorization header — including the bearer token — to whichever logger is active. The default is `False`, and current callers do not pass `True`. But the parameter is one debug-flag flip, environment-variable toggle, or maintenance-mode edit away from leaking auth tokens into log files, log aggregators (Splunk, Datadog, ELK), CI artifacts, and crash dumps.

## Evidence (HEAD [`d315a56`](https://github.com/microsoft/dbt-fabricspark/tree/d315a56))

[`src/dbt/adapters/fabricspark/livysession.py#L328`](https://github.com/microsoft/dbt-fabricspark/blob/d315a56/src/dbt/adapters/fabricspark/livysession.py#L328):

```python
def get_headers(..., tokenPrint=False):
    headers = {"Authorization": f"Bearer {token}"}
    if tokenPrint:
        logger.debug(f"headers: {headers}")
    return headers
```

(Form may vary slightly; the relevant code is the conditional log of `headers` that includes the bearer token.)

## User impact

- A bearer token in a log file is, for the lifetime of that token, a credential anyone with log access can replay against the user's Fabric tenant.
- Logs in enterprise environments are commonly shipped to centralized aggregators with broad read access. A token leak in dbt logs becomes a token leak in the SIEM.
- The current default mitigates the risk in normal operation, but the affordance exists in the code — debugging an outage by flipping `tokenPrint=True` is exactly the moment when log scrutiny is highest and when the leak would compound the incident.

## Suggested fix

Remove the `tokenPrint` parameter entirely. There is no legitimate operational reason to log the bearer token; debugging auth issues should use the token's `iss`/`aud`/`exp` claims (which can be decoded and logged safely from the JWT header without exposing the signing material).

If a debugging hook is needed, log only the hashed prefix of the token (e.g. first 8 characters of `sha256(token)`) so the log records "which token was used" without exposing the token itself:

```python
def get_headers(...):
    headers = {"Authorization": f"Bearer {token}"}
    logger.debug(f"token_fingerprint={hashlib.sha256(token.encode()).hexdigest()[:8]}")
    return headers
```

