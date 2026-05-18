# Module-level `_TOKEN` global in `fabric_connection_manager.py` — thread-safety and lifecycle issues

**Repo:** `microsoft/dbt-fabric`
**Labels (suggested):** `bug`, `concurrency`, `priority/medium`

> [ ] **Validated by maintainer** — code refs, line numbers, and claims confirmed against upstream HEAD

## Summary

[`dbt/adapters/fabric/fabric_connection_manager.py#L57`](https://github.com/microsoft/dbt-fabric/blob/0de2190/dbt/adapters/fabric/fabric_connection_manager.py#L57) declares `_TOKEN: Optional[AccessToken] = None` at module scope, and `get_pyodbc_attrs_before_credentials()` mutates it via `global _TOKEN`. Module-level mutable auth state has three problems:

1. **Thread safety** — dbt runs with parallelism by default. Multiple worker threads call into the auth path concurrently and race on `_TOKEN` reads/writes.
2. **Scope confusion** — a single global means a single token. As soon as the adapter supports multiple scopes or multiple credentials in one process (e.g. T-SQL endpoint + REST API + Purview), the global serves the wrong token to the wrong consumer.
3. **Lifecycle** — the token cannot be invalidated on a per-credential or per-adapter-instance basis. The only way to clear it is to restart the Python process.

## Evidence (HEAD [`0de2190`](https://github.com/microsoft/dbt-fabric/tree/0de2190), v1.10.0)

From [`dbt/adapters/fabric/fabric_connection_manager.py`](https://github.com/microsoft/dbt-fabric/blob/0de2190/dbt/adapters/fabric/fabric_connection_manager.py):

```python
# Line 57:
_TOKEN: Optional[AccessToken] = None

# AZURE_AUTH_FUNCTIONS mapping — module-scope mutable dict (same file)

def get_pyodbc_attrs_before_credentials(credentials):
    global _TOKEN
    ...
```

## User impact

- Race conditions where one thread's auth refresh interleaves with another thread's auth lookup. Symptoms: intermittent "permission denied" errors that don't reproduce on retry; sporadic 401s during high-parallelism runs.
- Cannot use two different credential profiles in a single Python process (e.g. dbt + Purview integration).
- Token expiry is fixed per process; long-running processes can hold expired tokens that the global never refreshes correctly.

## Suggested fix

Encapsulate token acquisition in a class with per-credential instance caching:

```python
class FabricTokenProvider:
    def __init__(self, credentials: FabricCredentials):
        self.credentials = credentials
        self._cache: dict[str, AccessToken] = {}  # by scope
        self._lock = threading.Lock()

    def get_token(self, scope: str) -> AccessToken:
        with self._lock:
            token = self._cache.get(scope)
            if token is None or token.expires_on < time.time() + 60:
                token = self._acquire(scope)
                self._cache[scope] = token
            return token
```

One instance per adapter (or per credentials hash), held on the adapter object. No module-level globals.

Reference fix in [the fork](https://github.com/sdebruyn/dbt-fabric): commit [`c8be16a1`](https://github.com/sdebruyn/dbt-fabric/commit/c8be16a1) (extracted `_TOKEN` global into `FabricTokenProvider` class), plus follow-ups for multi-scope ([`47b4510f`](https://github.com/sdebruyn/dbt-fabric/commit/47b4510f)) and explicit `get_api_token` / `get_sql_token` split ([`0e779bdc`](https://github.com/sdebruyn/dbt-fabric/commit/0e779bdc)).

## Notes

- This is the same general anti-pattern as the `atexit` warehouse-snapshot issue: module-level state with implicit lifecycle that becomes hard to reason about and impossible to test in isolation.
- [The fork](https://github.com/sdebruyn/dbt-fabric) now has zero module-level mutable state in the adapter — every cache and every connection lives on a class instance.
