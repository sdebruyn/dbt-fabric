# Six `__exit__` methods return `True` — silent exception swallowing throughout session lifecycle

**Repo:** `microsoft/dbt-fabricspark`
**Labels (suggested):** `bug`, `data-loss`, `priority/high`

> [ ] **Validated by maintainer** — code refs, line numbers, and claims confirmed against upstream HEAD

## Summary

Six `__exit__` methods across `singleton_livy.py` and `concurrent_livy.py` end with `return True`. In Python, returning a truthy value from `__exit__` suppresses any exception raised inside the `with` block. Every database error, timeout, `KeyboardInterrupt`, and programming bug raised inside a `with`-using one of these context managers is silently dropped on the floor.

## Evidence (HEAD [`d315a56`](https://github.com/microsoft/dbt-fabricspark/tree/d315a56))

- [`src/dbt/adapters/fabricspark/singleton_livy.py#L49`](https://github.com/microsoft/dbt-fabricspark/blob/d315a56/src/dbt/adapters/fabricspark/singleton_livy.py#L49)
- [`src/dbt/adapters/fabricspark/singleton_livy.py#L378`](https://github.com/microsoft/dbt-fabricspark/blob/d315a56/src/dbt/adapters/fabricspark/singleton_livy.py#L378)
- [`src/dbt/adapters/fabricspark/singleton_livy.py#L706`](https://github.com/microsoft/dbt-fabricspark/blob/d315a56/src/dbt/adapters/fabricspark/singleton_livy.py#L706)
- [`src/dbt/adapters/fabricspark/concurrent_livy.py#L119`](https://github.com/microsoft/dbt-fabricspark/blob/d315a56/src/dbt/adapters/fabricspark/concurrent_livy.py#L119)
- [`src/dbt/adapters/fabricspark/concurrent_livy.py#L340`](https://github.com/microsoft/dbt-fabricspark/blob/d315a56/src/dbt/adapters/fabricspark/concurrent_livy.py#L340)
- [`src/dbt/adapters/fabricspark/concurrent_livy.py#L627`](https://github.com/microsoft/dbt-fabricspark/blob/d315a56/src/dbt/adapters/fabricspark/concurrent_livy.py#L627)

All six methods end with `return True` (sometimes preceded by best-effort cleanup logic).

## User impact

- A dbt run can report success while models that ran inside one of these context managers silently failed. Users typically only notice when a downstream report or dashboard comes out wrong — sometimes weeks later.
- `KeyboardInterrupt` being swallowed means `Ctrl+C` may not actually stop a long-running command.
- Programming bugs (e.g. `AttributeError`, `TypeError`) raised during cleanup are hidden, making them effectively impossible to diagnose from the dbt log.

## Suggested fix

`__exit__` should return `False` (or `None`) unless there is a documented, deliberate reason to suppress a specific exception class. Cleanup logic belongs in the body of `__exit__`; suppressing exceptions belongs nowhere except in narrow, well-documented cases (and even then, suppress a specific exception type, not all of them).

```python
def __exit__(self, exc_type, exc_val, exc_tb):
    try:
        self.close()
    except Exception:
        log.warning("error closing session", exc_info=True)
    return False  # propagate any exception raised inside the with-block
```

## Notes

- This is the same anti-pattern the upstream `microsoft/dbt-fabric` code base also has in `FabricSparkCursor.__exit__` (caught and fixed in the fork via PEP 249 compliance tests — see fork commit `25faac00`).
- A PEP 249 compliance test suite for cursor context-manager behavior is a small investment that catches this class of bug at change time.
