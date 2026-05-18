# Hardcoded `expires_on = 1845972874` (year 2028) in `int_tests` auth path bypasses all token refresh

**Repo:** `microsoft/dbt-fabricspark`
**Labels (suggested):** `bug`, `security`, `priority/high`

> [x] **Validated by maintainer** — code refs, line numbers, and claims confirmed against upstream HEAD

## Summary

[`src/dbt/adapters/fabricspark/livysession.py#L184`](https://github.com/microsoft/dbt-fabricspark/blob/d315a56/src/dbt/adapters/fabricspark/livysession.py#L184) constructs an `AccessToken` with `expires_on = 1845972874` — a Unix timestamp pointing at 2028-06-09. The `int_tests` authentication path uses this token directly, bypassing all token-refresh logic. The pattern looks like a developer stub that landed in production code.

## Evidence (HEAD [`d315a56`](https://github.com/microsoft/dbt-fabricspark/tree/d315a56))

[`src/dbt/adapters/fabricspark/livysession.py#L184`](https://github.com/microsoft/dbt-fabricspark/blob/d315a56/src/dbt/adapters/fabricspark/livysession.py#L184) constructs `AccessToken(..., expires_on=1845972874)` in the `int_tests` auth branch.

## User impact

- Any flow that follows the `int_tests` auth code path silently gets a token marked as valid until 2028. Token-refresh logic never runs against the actual remote token state.
- If the underlying token is invalidated server-side (revocation, password rotation, conditional-access policy change), the client keeps presenting the stale token because `expires_on` says it is still valid. Errors then surface as opaque 401s with no diagnostic path.
- If this code path is reachable in production (not just CI), it disables the entire token-refresh mechanism for that path.

## Suggested fix

1. Remove the hardcoded timestamp. Compute `expires_on` from the actual token introspection or from the token-issuance response.
2. If the `int_tests` path genuinely needs a long-lived test token, gate it behind a clearly named env var (e.g. `_DBT_FABRICSPARK_TEST_TOKEN_NO_REFRESH=1`), assert that env var is not set in production code paths, and add a unit test that confirms the hardcoded value is unreachable from any user-facing code path.

```python
# WRONG (current code)
token = AccessToken(token=..., expires_on=1845972874)

# RIGHT
# Either derive expires_on from the JWT 'exp' claim,
# or use the token endpoint's stated expiry.
```

