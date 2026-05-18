# PR #315: `timeout=getattr(credentials, "login_timeout", None)` is a no-op on every line

**Repo:** `microsoft/dbt-fabric`
**Labels (suggested):** `bug`, `priority/low`
**Refs:** PR [#315](https://github.com/microsoft/dbt-fabric/pull/315)

> [ ] **Validated by maintainer** — code refs, line numbers, and claims confirmed against upstream HEAD

## Summary

[PR #315](https://github.com/microsoft/dbt-fabric/pull/315) adds `timeout=getattr(credentials, "login_timeout", None)` to every `get_token()` call. The whole change is functionally a no-op:

1. `login_timeout` does not exist as an attribute on `FabricCredentials`, so `getattr(credentials, "login_timeout", None)` always returns `None`.
2. `get_token()` in `azure-identity` does not accept a `timeout` argument; it silently disappears into `**kwargs` and never reaches any underlying HTTP call.

## Evidence

The [PR #315 diff](https://github.com/microsoft/dbt-fabric/pull/315/files) shows the parameter being threaded through every `get_token()` invocation, but [`dbt/adapters/fabric/fabric_credentials.py`](https://github.com/microsoft/dbt-fabric/blob/0de2190/dbt/adapters/fabric/fabric_credentials.py) does not declare a `login_timeout` field, and the [`azure-identity` SDK's `TokenCredential.get_token` signature](https://learn.microsoft.com/en-us/python/api/azure-core/azure.core.credentials.tokencredential?view=azure-python&WT.mc_id=MVP_310840) does not accept a `timeout` keyword.

## User impact

- Users who configured `login_timeout` in their profile (or who saw the parameter in release notes and expected it to do something) see no behavior change.
- The parameter is dead code: it touches every auth path but affects none.
- The PR description follows clearly AI-generated patterns, suggesting the change was not validated against either the `FabricCredentials` schema or the `azure-identity` API.

## Suggested fix

Either:
1. Revert the change, since it has no effect.
2. Actually implement a login timeout. That requires (a) adding `login_timeout: Optional[float] = None` to `FabricCredentials`, (b) wrapping `get_token()` in a real timeout — `concurrent.futures.ThreadPoolExecutor` + `Future.result(timeout=...)` is one option, or `azure.core.pipeline.policies.RetryPolicy` for the underlying HTTP layer.

The first option is preferable: the dbt adapter is not the right layer to invent token-acquisition timeouts when Azure SDK callers don't have a documented timeout knob there.

## Notes

- This PR is referenced in the broader pattern observed across recent releases (v1.9.10, v1.10.0) where AI-assisted suggestions land without review by someone with the dbt-domain or Azure SDK expertise to spot that the suggested fix doesn't actually do what the description claims.
- Filing this as a discrete issue rather than a broader review concern, because the concrete bug (parameter is a no-op) is independently actionable.
