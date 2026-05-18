# `check_for_nested_cte` macro has false positives on `WITH (NOLOCK)`, string literals, and any identifier containing "with"

**Repo:** `microsoft/dbt-fabric`
**Labels (suggested):** `bug`, `priority/medium`

> [ ] **Validated by maintainer** — code refs, line numbers, and claims confirmed against upstream HEAD

## Summary

The `check_for_nested_cte` macro at `dbt/include/fabric/macros/materializations/models/unit_test/unit_test_create_table_as.sql` attempts to detect nested CTEs by lowercasing the user's SQL, replacing newlines with spaces, and counting occurrences of the substring `"with "`. Two or more occurrences → "nested CTE detected". The detector raises a compile error (with contract enforcement) or a warning otherwise.

This is a category error: dbt does not parse SQL because dbt cannot reliably parse SQL; the database does. Substring-counting SQL keywords in Jinja produces false positives on any input that legitimately contains the substring `with ` in a non-CTE context.

## Evidence (HEAD [`0de2190`](https://github.com/microsoft/dbt-fabric/tree/0de2190), v1.10.0)

[`dbt/include/fabric/macros/materializations/models/unit_test/unit_test_create_table_as.sql`](https://github.com/microsoft/dbt-fabric/blob/0de2190/dbt/include/fabric/macros/materializations/models/unit_test/unit_test_create_table_as.sql) defines `check_for_nested_cte` and is invoked from the unit-test materialization.

The warning text shipped with the macro reads (verbatim): *"Nested CTE's do not support CTAS. However, 2-level nested CTEs are supported due to a code bug. Please expect this fix in the future."* This is an explicit, in-code acknowledgement that the materialization knowingly ships behavior that depends on a bug.

## Reproduction (any of these trigger a false positive)

```sql
-- T-SQL table hint
select * from my_table with (nolock) inner join other_table on ...

-- String literal containing the word
select 'query with metrics' as label, * from my_table

-- Query option
option (label = 'work with priority = 1')

-- Column or alias name
select col_with_value as something_with_more_data from my_table
```

## User impact

- Models that use any of the above patterns either fail to compile (with `contract`) or surface a misleading warning.
- The error message is misleading: users see "nested CTE detected" on a model that contains no CTE at all.
- The shipped warning text admits the macro depends on a bug; that bug is the only reason 2-level nested CTEs pass.

## Suggested fix

Remove the substring-counting check entirely. dbt cannot reliably parse SQL in Jinja; the database is the only correct CTE detector. If a Fabric DW limitation needs surfacing, surface the Fabric error to the user when it occurs, rather than guessing in macro code.

If a heuristic must remain for some platform reason, gate it behind a config flag that is off by default, document its false-positive surface, and never raise compile errors based on heuristic matching.

## Notes

- This macro is a clear example of a category-mistake review would have caught: detecting nested CTEs by lowercasing-and-counting cannot work in the general case, because SQL is not a regular language.
- [The fork](https://github.com/sdebruyn/dbt-fabric) does not ship a unit-test materialization with this check at all; it lets dbt-adapters' default unit-test machinery run and surfaces actual Fabric errors when they occur.
