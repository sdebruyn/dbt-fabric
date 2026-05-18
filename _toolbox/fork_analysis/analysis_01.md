# Batch 01 analysis (commits 1-46, 2025-03-29 to 2025-04-03)

### f606fd2b — 2025-03-29 — TEST
**Message:** enable CTE tests
**What:** Activated `BaseSingularTestsEphemeral` by overriding `project_config_update` to force `+materialized: table` (Fabric DW Views do not support nested CTEs).
**Why:** Previously the test was a bare `pass`; Fabric's view materialization rejects nested CTEs, so the workaround is to materialize ephemeral as table.

### 58d6f377 — 2025-03-29 — BUG_FIX
**Message:** fix unit testing tests
**What:** Added `src/dbt/include/fabric/macros/adapters/unit_testing.sql` overriding `format_row` to handle case-insensitive column names and rewrite `datetime2` -> `datetime2(6)`. Replaced the previous unit testing test file (which lived under `tests/unit/`) with proper functional tests subclassing `BaseUnitTestingTypes`, `BaseUnitTestCaseInsensivity`, `BaseUnitTestInvalidInput`. Marked `TestCachingUppercaseModel` as skipped.
**Why:** Unit tests broke because Fabric requires `datetime2(6)` precision and the default `format_row` did not normalize column casing the way Fabric DW does.
**Upstream:** `git show upstream/main:src/dbt/include/fabric/macros/adapters/unit_testing.sql` does not exist; upstream still relies on `dbt/include/fabric/macros/materializations/models/unit_test/unit_test_create_table_as.sql` and `unit_test_table.sql` rather than overriding `format_row`. The bare-pass test file `tests/unit/adapters/fabric/test_unit_testing.py` is still present upstream.
**Notes:** Superseded by cd8e63b7 later in this batch, which moves the fix into `FabricColumn.data_type` (Python) and deletes this macro override.

### 4d89d8ce — 2025-03-29 — TEST
**Message:** uncomment empty test
**What:** Uncommented `BaseTestEmpty` subclass and renamed it to `TestFabricEmpty`.
**Why:** Cleanup of dead code that was preventing the empty model test from running.

### a7f46501 — 2025-03-29 — INFRA: add `ERA` lint rule to ruff so commented-out code is rejected.

### 2f4f36e7 — 2025-03-29 — INFRA: add `.github/workflows/lint-format.yml` workflow (ruff format/check on PRs and pushes).

### de19206e — 2025-03-29 — DOCS: add linting badge to README.

### 87c6c73a — 2025-03-29 — INFRA: formatting on two test files.

### 0ee3341b — 2025-03-29 — INFRA: tweak CI integration-tests concurrency settings.

### 8bf38cf2 — 2025-03-29 — BUG_FIX
**Message:** pass sql messages as response
**What:** In `FabricConnectionManager.get_response`, replaced hardcoded `message = "OK"` with `"\n".join(msg[1] for msg in cursor.messages)`. Also removed dead commented code in the same file and tightened `cancel`/`add_begin_query`/`add_commit_query` to pure `pass`. Removed several commented-out entries in the pyodbc `datatypes` dict.
**Why:** Returning a hardcoded "OK" loses Fabric-side messages (warnings, print statements, row counts) that dbt could surface to users.
**Upstream:** Still hardcoded — `dbt/adapters/fabric/fabric_connection_manager.py:746-748` in upstream reads `def get_response(cls, cursor: Any) -> AdapterResponse:` / `# message = str(cursor.statusmessage)` / `message = "OK"`.

### eea2cfe3 — 2025-03-29 — ANTI_PATTERN_REMOVED
**Message:** remove commented code
**What:** Removed 8 lines of commented-out code from `src/dbt/adapters/fabric/relation_configs/base.py`.
**Why:** Dead/commented code violates the new `ERA` ruff rule and clutters the file.
**Upstream:** Upstream still has commented-out code in many files (no ERA rule); this is part of a fork-wide cleanup pattern.

### a9c7d0ec — 2025-03-29 — INFRA: isort fix in `test_caching.py`.

### 1376a643 — 2025-03-29 — ANTI_PATTERN_REMOVED
**Message:** remove commented code
**What:** Removed 5 commented-out lines from `tests/functional/adapter/test_list_relations_without_caching.py`.

### 7b12ec6f — 2025-03-29 — BUG_FIX
**Message:** fix support for case sensitive DWHs
**What:** Added `_make_match_kwargs` override on `FabricAdapter` that returns the database/schema/identifier exactly as passed, using `filter_null_values`. Removed the skip marker from `TestCachingUppercaseModel`.
**Why:** The default `SQLAdapter._make_match_kwargs` lowercases identifiers when `quoting.case_sensitive` is False, which breaks case-sensitive Fabric DWHs.
**Upstream:** `git show upstream/main:dbt/adapters/fabric/fabric_adapter.py | grep _make_match_kwargs` returns nothing. Upstream has no override, so case-sensitive DWHs are still broken in upstream.

### aec6f06e — 2025-03-30 — DBT_NATIVE_REWRITE
**Message:** fix cloning tests
**What:** Deleted the entire custom `materialization clone, adapter='fabric'` block from `src/dbt/include/fabric/macros/materializations/models/table/clone.sql`, keeping only `fabric__can_clone_table` and `fabric__create_or_replace_clone`. In tests, replaced a hand-copy of `BaseClone`/`BaseClonePossible`/`BaseCloneNotPossible` with imports from `dbt.tests.adapter.dbt_clone.test_dbt_clone` and added `TestFabricCloneSameTargetAndState`.
**Why:** The custom materialization was a verbatim copy of dbt-core's default clone materialization (including the `TODO: support actual dispatch for materialization macros` comment). Removing it lets dbt's default materialization handle the dispatch. The test rewrite removes a similar copy-paste of the base test classes.
**Upstream:** Upstream `dbt/include/fabric/macros/materializations/models/table/clone.sql` still contains the full duplicated materialization (see `git show upstream/main:dbt/include/fabric/macros/materializations/models/table/clone.sql`).

### 19e7feb — 2025-03-30 — REFACTOR: rename `test_sql_server_connection_manager.py` -> `test_fabric_connection_manager.py`.

### 82c2b448 — 2025-03-30 — TEST
**Message:** enable test for ephemeral model
**What:** Removed skip on `TestEphemeralErrorHandling`, updated skip reasons for `TestEphemeral`/`TestEphemeralNested` from "Epemeral models are not supported in Fabric DW" to "Nested CTEs not supported in Views".
**Why:** Ephemeral models work; only nested CTE materialization fails. Accurate skip reasons.

### 81ad2e40 — 2025-03-30 — INFRA: drop redundant Python setup step from release workflow.

### 58b50507 — 2025-03-30 — INFRA: add `.github/workflows/nightly-build.yml`.

### 7364374 — 2025-03-30 — INFRA: ruff formatting on two test files.

### 8ef3792e — 2025-03-31 — BUG_FIX
**Message:** fix int type check
**What:** Added `is_integer()` override on `FabricColumn` that returns `super().is_integer() or self.dtype.lower() == "int"`. Cleaned up `test_column_types.py` by moving `schema_yml` import to dbt-tests-adapter and removing the skip marker.
**Why:** At the time, upstream `Column.is_integer()` did not recognize Fabric's `INT` dtype, causing `BaseColumnTypes` tests to fail.
**Upstream:** Upstream has since added a complete `is_integer` override in `FabricColumn` covering `int`, `integer`, `bigint`, `smallint`, `tinyint`; the fork's simpler override is functionally equivalent. Not a current bug in upstream.

### 8070e09d — 2025-03-31 — BUG_FIX
**Message:** fix limit func
**What:** Removed the `@classmethod` decorator on `FabricRelation.render_limited` and switched `TOP` to lowercase `top`, removed the space before `_render_limited_alias()` call.
**Why:** `render_limited` is an instance method (uses `self.render()`, `self.limit`); marking it `@classmethod` made `self` get a class reference and would crash at runtime.
**Upstream:** Upstream has the bug fixed (no `@classmethod`, but with `" AS "` in the alias and uppercase `TOP`).

### 3f698975 — 2025-03-31 — TEST
**Message:** fix empty test
**What:** Adapted `BaseTestEmpty` with a Fabric-specific `model.sql` using union all over a ref, an ephemeral ref, and a source. Added `TestFabricEmptyInlineSourceRef`.
**Why:** The default empty test uses syntax that Fabric DW rejects in some contexts; this aligns the fixture with the real-world `--empty` pattern.

### 1a213a4d — 2025-03-31 — INFRA: ruff formatting on `test_empty.py`.

### 7d929150 — 2025-03-31 — TEST
**Message:** fix schema test
**What:** Added `DBT_TEST_USER_1` env var support in `test_schema.py`. If the test user is not `dbo`, the test now grants `select on schema :: dbo` first (Fabric only recognises users once a grant has been issued). Verifies schema owner.
**Why:** Real Fabric DWHs don't recognise users that haven't been granted anything; tests need that pre-step.

### f35550ed — 2025-03-31 — INFRA: ruff formatting on `test_schema.py`.

### 27575d53 — 2025-03-31 — INFRA: add `pytest-cov` dependency (reverted in 48afd75b).

### 2e74d3bf — 2025-03-31 — TEST
**Message:** fix schema test
**What:** Switched schema-owner query in `test_schema.py` from `INFORMATION_SCHEMA.SCHEMATA` to a `sys.schemas` JOIN `sys.database_principals`. Added `_with_custom_auth` suffix to the second verified schema.
**Why:** `INFORMATION_SCHEMA.SCHEMATA.SCHEMA_OWNER` returns the wrong value (or NULL) in Fabric; `sys.schemas`/`sys.database_principals` give correct owner identity.

### 48afd75b — 2025-03-31 — REVERT_OR_MODIFY: Revert "add pytest-cov" (27575d53 in this batch).

### a879b78d — 2025-03-31 — REFACTOR
**Message:** refactor: simplify test structure and update passing test condition
**What:** Removed copy-pasted `StoreTestFailuresBase`/`BaseStoreTestFailures` classes from `test_store_test_failures.py`; replaced with imports from `dbt.tests.adapter.store_test_failures_tests.basic` and `BaseStoreTestFailures`. Changed `where 1=2` to `where 1=0` in the passing-test fixture. Renamed each test class with `TestFabric` prefix.
**Why:** Removes ~140 lines of test harness that duplicated upstream `dbt-tests-adapter` content. `1=2` and `1=0` are equivalent but `1=0` is the canonical false-predicate idiom.

### 233927de — 2025-03-31 — INFRA: expand `.gitignore`, add `.vscode/launch.json`.

### 9a867ddd — 2025-03-31 — TEST
**Message:** initialize test user
**What:** Refactored `test_schema.py` to use class-scoped `test_user` fixture, `dbt_profile_target_update` reading from it, and a new `initialization` fixture that runs the `grant select on schema :: dbo to [test_user]` setup via the adapter (rather than `project.run_sql`).
**Why:** Cleaner setup; uses dbt fixture machinery instead of per-test setup logic.

### 58f5a623 — 2025-03-31 — INFRA: minor cleanup in `conftest.py` and `test_schema.py`.

### 3346796e — 2025-03-31 — INFRA: split CI into a weekly comprehensive integration-tests workflow and a leaner per-push integration workflow; add `publish-docker.yml` trigger.

### 8441fba7 — 2025-03-31 — REFACTOR
**Message:** simplify test
**What:** Replaced ~75 lines of hand-copied debug tests in `test_debug.py` with bare inheritance from `BaseDebugPostgres`, `BaseDebugInvalidProjectPostgres`, `BaseDebugProfileVariable`.
**Why:** The hand-copied `TestDebugFabric` / `TestDebugInvalidProjectFabric` duplicated upstream test classes; inheriting from the canonical base classes keeps Fabric in sync with dbt-tests-adapter changes.

### 92e93f64 — 2025-03-31 — INFRA: formatting on `test_debug.py`.

### 410fd745 — 2025-04-01 — TEST
**Message:** add all remaining tests from adapter package
**What:** Large addition of test classes wiring up `BaseDocsGenerate`, `BaseDocsGenReferences`, `BaseGetCatalogForSingleRelation`, `BaseTableMaterialization`, the full `grants.test_*` suite (model/seed/snapshot/incremental/invalid), the full `hooks.test_model_hooks` and `hooks.test_run_hooks` suites, and a `test_simple.py` with simple snapshot/copy tests + utils. Removed seed/incremental_microbatch placeholder files.
**Why:** Brings Fabric coverage in line with what dbt-tests-adapter exposes — many of these test classes had never been exercised against Fabric.
**Notes:** Several tests added here surface bugs fixed in later commits/PRs.

### cd8e63b7 — 2025-04-02 — BUG_FIX
**Message:** better fix for unit testing
**What:** Added a `data_type` property on `FabricColumn` that auto-expands `datetime2` to `datetime2(self.numeric_scale)`. Deleted `src/dbt/include/fabric/macros/adapters/unit_testing.sql` (the format_row override).
**Why:** Pushes the `datetime2(6)` fix into the Column class so all code paths benefit, not just unit testing. Avoids overriding a global dbt macro.
**Upstream:** Upstream's `FabricColumn.data_type` only checks `if self.dtype.lower() == "datetime2"` and returns the literal `"datetime2(6)"` — the fork's version honours the actual `numeric_scale` from the model.
**Notes:** Supersedes 58d6f377 from this batch.

### b394b3e7 — 2025-04-03 — TEST
**Message:** remove module with errors
**What:** Removed five `BaseSnapshot*` test classes from `test_simple.py` (column_names, column_names_from_dbt_project, dbt_valid_to_current, invalid_column_names, multi_unique_key). Trailing-whitespace cleanup in `fabric_column.py`.
**Why:** These tests failed at import/collection time due to missing fixtures or upstream churn; pruned until investigated.

### c85b6ac7 — 2025-04-03 — REFACTOR: removed 59 duplicate test lines from `test_utils.py` and moved a few utils test files under `tests/functional/adapter/utils/`.

### f5e4759 — 2025-04-03 — REFACTOR
**Message:** split out utils test files
**What:** Decomposed monolithic `tests/functional/adapter/test_utils.py` (189 lines) into ~30 single-purpose files under `tests/functional/adapter/utils/` (one per utility macro: `test_any_value.py`, `test_date_spine.py`, `test_dateadd.py`, etc.).
**Why:** Allows targeted execution / parallelisation and makes failures easier to bisect.

### 6fe3b9e3 — 2025-04-03 — NEW_FEATURE
**Message:** import tsql_utils macros
**What:** Bulk import of Fabric-compatible overrides for popular community dbt packages, organised by package under `src/dbt/include/fabric/macros/dbt_package_support/`: dbt-audit-helper (compare_column_values, compare_queries, compare_relation_columns, compare_relations), dbt-date (~14 macros covering convert_timezones, date_part, day_of_week, week boundaries, fiscal periods, date dimension), dbt-expectations (~7 statistical / schema-test macros including grouped_row_values_to_have_recent_data and column_values_to_be_within_n_stdevs), dbt-utils (~17 macros covering date_spine, deduplicate, generate_series, generate_surrogate_key, get_tables_by_pattern_sql, insert_by_period, mutually_exclusive_ranges, relationships_where, schema_cleanup, sequential_values, surrogate_key, width_bucket, test_not_null_where, test_unique_where).
**Why:** Lets Fabric users adopt the dbt community ecosystem (these packages currently ship Synapse-style or Postgres-style SQL that fails on Fabric DW). Note that the existing `utils/get_tables_by_pattern.sql` was moved into the new dispatch-friendly structure.
**Upstream:** `git ls-tree -r upstream/main --name-only | grep -i dbt_package_support` returns nothing — upstream has no community package support whatsoever. This is one of the most impactful fork-only features.

### 3e85abc4 — 2025-04-03 — TEST: removed a non-essential basic test entry (4 lines).

### 3cf6f1f5 — 2025-04-03 — TEST
**Message:** fix a few more tests
**What:** Added `profile_user` fixture (defaulting to "dbo") to `conftest.py`. Provided `expected_catalog` overrides for `TestDocsGenerateFabric` and `TestDocsGenReferencesFabric` using `base_expected_catalog` / `expected_references_catalog` with Fabric-specific types (varchar/datetime2/int/BASE TABLE/VIEW) and `no_stats()`. Trailing newline cleanup across many `tests/functional/adapter/utils/*.py` files.
**Why:** Docs generation tests need adapter-specific column types and table-type strings to compare correctly.

### e43b1c2d — 2025-04-03 — REFACTOR
**Message:** simplify test
**What:** Replaced hand-copied `TestCatalogRelationTypes` body (with inline `MY_SEED`/`MY_TABLE`/`MY_VIEW` and a re-implementation of the test method) with inheritance from `CatalogRelationTypes` and imports from `dbt.tests.adapter.catalog.files`.
**Why:** ~90-line copy of upstream test logic deleted; future upstream changes flow through automatically.

### 9dd9fcfb — 2025-04-03 — REFACTOR
**Message:** simplify test
**What:** Switched `TestFabricColumnTypes` from `BaseColumnTypes` to `BasePostgresColumnTypes` and dropped the now-redundant `test_run_and_test` method.

### 4b81bf4c — 2025-04-03 — REFACTOR
**Message:** rename classes
**What:** Renamed test classes in `test_constraints.py` to use `TestFabric...` prefix consistently.
