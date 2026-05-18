# `check_for_nested_cte`: a dbt adapter must never parse user SQL — delete this macro

**Repo:** `microsoft/dbt-fabric`
**Labels (suggested):** `bug`, `priority/medium`

> [x] **Validated by maintainer** — code refs, line numbers, and claims confirmed against upstream HEAD

## Summary

A dbt adapter must not parse user SQL. The `check_for_nested_cte` macro at `dbt/include/fabric/macros/materializations/models/unit_test/unit_test_create_table_as.sql` tries anyway: it lowercases the user's SQL, collapses newlines, and counts substring occurrences of `"with "`. Two or more occurrences → "nested CTE detected", which raises a compile error (under `contract`) or surfaces a misleading warning otherwise.

SQL is not a regular language. No amount of substring matching, regex tweaking, or heuristic tuning will make a Jinja-level parser correct — the only correct SQL parser is the database. dbt adapters delegate parsing to the engine for exactly this reason; every other reference adapter (Snowflake, BigQuery, Postgres, Spark) takes that as a baseline rule. This macro violates it, and the rest of the issue is the predictable list of false positives that follows.

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

Delete `check_for_nested_cte` and every call to it. Let the unit-test materialization submit the user's SQL to Fabric and surface whatever error Fabric returns. That is how every reference adapter handles platform-specific SQL limitations, and it is the only approach that is correct in the general case.

There is no version of this macro worth keeping. A "smarter" parser still cannot parse SQL in Jinja, would still produce false positives, and would still ship a false security around CTE limits that are the database's responsibility to enforce. The fix is removal, not refinement.

