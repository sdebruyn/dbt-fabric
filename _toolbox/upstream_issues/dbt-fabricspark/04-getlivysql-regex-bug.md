# `_getLivySQL`: `re.DOTALL` passed as positional `count` arg — comment-stripping silently capped at 16 replacements per file

**Repo:** `microsoft/dbt-fabricspark`
**Labels (suggested):** `bug`, `priority/medium`

> [x] **Validated by maintainer** — code refs, line numbers, and claims confirmed against upstream HEAD

> **Internal note (strip before filing):** Submittable as a PR — swap `re.DOTALL` from positional to `flags=re.DOTALL` in both copies; extracting a shared `_strip_sql_comments(sql)` helper is a small bonus to keep the bug from reoccurring. Consider opening with the issue *and* a draft PR linked from it.

## Summary

`_getLivySQL` passes `re.DOTALL` as the positional `count` argument to `re.sub` instead of as `flags=re.DOTALL`. `re.DOTALL` is an integer enum value (16). `re.sub`'s positional signature is `re.sub(pattern, repl, string, count=0, flags=0)`. Passing `re.DOTALL` positionally sets `count=16`, capping comment-stripping to at most 16 replacements per file.

## Evidence (HEAD [`d315a56`](https://github.com/microsoft/dbt-fabricspark/tree/d315a56))

`_getLivySQL` is duplicated verbatim between [`src/dbt/adapters/fabricspark/singleton_livy.py#L488`](https://github.com/microsoft/dbt-fabricspark/blob/d315a56/src/dbt/adapters/fabricspark/singleton_livy.py#L488) and [`src/dbt/adapters/fabricspark/concurrent_livy.py#L555`](https://github.com/microsoft/dbt-fabricspark/blob/d315a56/src/dbt/adapters/fabricspark/concurrent_livy.py#L555). Both copies call `re.sub(pattern, '', sql, re.DOTALL)` (positional) when they meant `re.sub(pattern, '', sql, flags=re.DOTALL)`.

## User impact

- Model SQL files with more than 16 `/* */` comment blocks have some comments left in the SQL submitted to Spark.
- Most of the time Spark's parser shrugs them off, but commented-out SQL can introduce surprises — particularly when the leftover comment contains characters that interact with the Livy/Spark parser, or when the comment contains SQL keywords that the parser must lexically skip past.
- Without `re.DOTALL` set, comment blocks containing newlines are not matched at all by the multi-line comment pattern — so the bug is doubly broken: count is set to 16, and the DOTALL flag that the code intended to set is not set.

## Reproduction

```python
import re
pattern = r"/\*.*?\*/"
sql = ("/* a */\n" * 20) + "select 1"
# Buggy call:
result_buggy = re.sub(pattern, "", sql, re.DOTALL)
# count=16 is set; flags=0 (no DOTALL); .*? does not cross newlines anyway
# but the count cap kicks in regardless.
```

## Suggested fix

Use keyword args:

```python
sql = re.sub(pattern, "", sql, flags=re.DOTALL)
```

Fix both copies ([`singleton_livy.py#L488`](https://github.com/microsoft/dbt-fabricspark/blob/d315a56/src/dbt/adapters/fabricspark/singleton_livy.py#L488) and [`concurrent_livy.py#L555`](https://github.com/microsoft/dbt-fabricspark/blob/d315a56/src/dbt/adapters/fabricspark/concurrent_livy.py#L555)). Better: extract a single `_strip_sql_comments(sql)` helper and call it from both files so the bug can't reoccur in only one place.

