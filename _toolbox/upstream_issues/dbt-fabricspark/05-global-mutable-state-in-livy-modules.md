# Module-level and class-level globals in `singleton_livy.py` / `concurrent_livy.py` cause race conditions under threading

**Repo:** `microsoft/dbt-fabricspark`
**Labels (suggested):** `bug`, `concurrency`, `priority/high`

## Summary

`singleton_livy.py` and `concurrent_livy.py` use module-level and class-level globals to hold authentication tokens, Livy session handles, connection managers, and relation configuration. dbt runs with parallelism by default (the `threads:` profile setting drives a thread pool). Module-level mutable state under threading produces classic race-condition symptoms: one thread's data leaks into another thread's operation, or two threads stomp on the same global.

## Evidence (HEAD `d315a56`)

Both files declare module-level state that is mutated from instance methods without per-instance scoping:

- `singleton_livy.py` — global session handle and global active-session set.
- `concurrent_livy.py` — global `_active_sessions` set, plus module-level `atexit.register(...)` calls (separate issue) that capture the global state by reference.

(Exact line references vary by release; the pattern is pervasive throughout both files.)

## User impact

- Intermittent "permission denied" or "session not found" errors that don't reproduce on retry.
- Occasionally, results written to the wrong relation when one thread's relation handle leaks into another thread's submit.
- Symptoms scale with `threads:` setting — users running `threads: 8` see more failures than `threads: 1`.
- Debugging is hard because the failures are non-deterministic and depend on thread interleaving.

## Suggested fix

Encapsulate session and token state in instance attributes. One Livy session manager per `FabricSparkConnectionManager` (or per credentials hash). No module-level mutable state. Use `threading.Lock` around any mutation that is genuinely shared.

```python
class FabricLivySession:
    def __init__(self, credentials):
        self.credentials = credentials
        self._session_id: str | None = None
        self._lock = threading.Lock()
        self._token_provider = FabricTokenProvider(credentials)

    def get_session_id(self) -> str:
        with self._lock:
            if self._session_id is None or self._is_dead(self._session_id):
                self._session_id = self._create_session()
            return self._session_id
```

Reference fix in the fork: the fork rewrote the entire Livy session layer with instance encapsulation throughout. No module-level mutable state remains.

## Notes

- The same anti-pattern is present in `microsoft/dbt-fabric` for the module-level `_TOKEN` global (separate issue in that repo).
- Module-level mutable state is a known thread-safety risk in any Python codebase that runs under thread pools; dbt is one of the most common consumers of adapter code under threads.
