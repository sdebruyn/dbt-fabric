# `_getLivySQL`: `re.DOTALL` passed as positional `count` arg — comment-stripping silently capped at 16 replacements per file

**Repo:** `microsoft/dbt-fabricspark`
**Labels (suggested):** `bug`, `priority/medium`

## Summary

`_getLivySQL` passes `re.DOTALL` as the positional `count` argument to `re.sub` instead of as `flags=re.DOTALL`. `re.DOTALL` is an integer enum value (16). `re.sub`'s positional signature is `re.sub(pattern, repl, string, count=0, flags=0)`. Passing `re.DOTALL` positionally sets `count=16`, capping comment-stripping to at most 16 replacements per file.

## Evidence (HEAD `d315a56`)

`_getLivySQL` is duplicated verbatim between `singleton_livy.py:488` and `concurrent_livy.py:555`. Both copies call `re.sub(pattern, '', sql, re.DOTALL)` (positional) when they meant `re.sub(pattern, '', sql, flags=re.DOTALL)`.

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

Fix both copies (`singleton_livy.py:488` and `concurrent_livy.py:555`). Better: extract a single `_strip_sql_comments(sql)` helper and call it from both files so the bug can't reoccur in only one place.

## Notes

- This is the type of bug a linter (Ruff `RUF*`, Pylint `W0102`-family) or even a careful code review would catch. It is currently invisible to dbt users because the partial comment-stripping still produces SQL Spark can parse — until it doesn't.
- The duplicated `_getLivySQL` (and the same-pattern duplicated `_parse_retry_after` — see related issue) suggests the codebase would benefit from a small shared utilities module.
