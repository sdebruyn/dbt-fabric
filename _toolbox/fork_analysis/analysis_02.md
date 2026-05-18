# Batch 02 analysis

**Summary:** 46 commits, dominated by TEST cleanup (29), with 3 BUG_FIX, 2 DBT_NATIVE_REWRITE, 1 NEW_FEATURE, 4 REFACTOR, and 7 INFRA. The dominant pattern is a multi-commit unwind of vendored upstream test code: the first ~12 commits collapse ~1,000 lines of copy-pasted `dbt-tests-adapter` constraint/show/snapshot tests into proper inheritance from the upstream base classes. Three high-impact upstream bugs were found and fixed: (1) `fabric__get_show_grant_sql` using `INFORMATION_SCHEMA.TABLE_PRIVILEGES` which silently misses Entra principals — upstream `apply_grants.sql` is still broken at HEAD; (2) `fabric__get_use_database_sql` emitting `USE [None];` when called without a database — upstream still has no None-guard; (3) the missing `bool_or` macro that breaks dbt's cross-database aggregate and dbt-utils on upstream. One notable DBT_NATIVE_REWRITE: the fork adds a `fabric__run_hooks` override at `materializations/hooks.sql` that strips the `commit;` Fabric DW can't execute — upstream has no such override, so any project using pre/post hooks on upstream is broken at every run boundary. No revert chains within this batch.

---

### c604d926 — 2025-04-03 — TEST
**Message:** inheritance
**What:** Makes the fabric-specific constraint test classes (`BaseConstraintsColumnsEqualFabric`, `BaseConstraintsRuntimeDdlEnforcementFabric`, `BaseModelConstraintsRuntimeEnforcementFabric`, `BaseConstraintsRollbackFabric`) actually inherit from the upstream `dbt.tests.adapter.constraints.test_constraints.Base*` classes instead of being free-standing copy/paste classes.
**Why:** First step in a long refactor sequence to stop maintaining a forked copy of the upstream dbt-tests-adapter constraint test bodies and instead inherit from them.
**Notes:** Starts a multi-commit cleanup chain (c604d926..0abe5332) that removes ~700 lines of duplicated upstream test code from `tests/functional/adapter/test_constraints.py`.

### 143274ee — 2025-04-03 — TEST
**Message:** remove clutter
**What:** Removes copy-pasted docstrings and unnecessary fixture overrides (`schema_string_type`, `schema_int_type`) from the constraint test classes now that they inherit from upstream bases.
**Why:** Redundant once inheritance is in place.

### 1f9f20f6 — 2025-04-03 — TEST
**Message:** remove clutter
**What:** Removes duplicated `_normalize_whitespace`/`_find_and_replace` helpers and a duplicated `test__constraints_wrong_column_order` method (now inherited).
**Why:** Continued cleanup of copy-pasted upstream code.

### 0baeb64e — 2025-04-03 — TEST
**Message:** remove clutter
**What:** Removes more duplicated test methods (`test__constraints_wrong_column_names`, `expected_color` fixture) and obsolete code comments.
**Why:** Continued cleanup of copy-pasted upstream code.

### f0499abb — 2025-04-03 — TEST
**Message:** remove clutter
**What:** Removes two more duplicated upstream test methods (`test__constraints_wrong_column_data_types`, `test__constraints_correct_column_data_types`) inherited from `BaseConstraintsColumnsEqual`.
**Why:** Continued cleanup.

### 9a05c4ae — 2025-04-03 — TEST
**Message:** remove clutter
**What:** Collapses the intermediate `BaseXxxFabric` -> `TestXxxFabric` two-layer hierarchy into direct `TestXxxFabric(BaseXxx)` classes.
**Why:** Once true inheritance is in place there's no need for the fork's own base layer.

### e421ef9f — 2025-04-03 — INFRA: removes unused imports from `test_constraints.py` after inheritance cleanup.

### 3bba5d57 — 2025-04-03 — TEST
**Message:** remove clutter
**What:** Removes duplicated `null_model_sql` fixture overrides from rollback test classes (upstream already provides them with identical values).
**Why:** Cleanup of redundant fixture definitions.

### 525db925 — 2025-04-03 — TEST
**Message:** cleanup
**What:** Removes unused fixture imports and a duplicated `assert_expected_error_messages` override; updates expected error messages list (adds `"INSERT fails"`, removes `"There is already an object"`).
**Why:** Continued cleanup; error-message list change reflects actual Fabric error wording observed in tests.

### 5cac0619 — 2025-04-03 — TEST
**Message:** cleanup
**What:** Collapses `BaseIncrementalConstraintsRollbackFabric` -> `TestIncrementalConstraintsRollbackFabric` into a single class and removes a duplicated `test__constraints_enforcement_rollback` method now inherited from upstream.
**Why:** Continued inheritance cleanup.

### 0abe5332 — 2025-04-03 — TEST
**Message:** remove unused test method for constraints enforcement rollback
**What:** Removes another large duplicated `test__constraints_enforcement_rollback` from `TestTableConstraintsRollbackFabric`.
**Why:** Final cleanup in this inheritance chain.

### c6f9e6a2 — 2025-04-04 — INFRA: removes unused imports from `test_constraints.py`.

### 2cb60141 — 2025-04-04 — TEST
**Message:** remove unused model imports and cleanup base class definitions in test_dbt_show.py
**What:** Removes a copy-pasted `BaseShowLimit` definition from the fork's `test_dbt_show.py` and replaces it with the imported `BaseShowLimit` from `dbt.tests.adapter.dbt_show.test_dbt_show`.
**Why:** Same pattern as constraints cleanup — fork was carrying its own pasted copy of an upstream base class instead of importing it.

### bfd3a2ce — 2025-04-04 — INFRA: adds `DBT_TEST_USER_2` / `DBT_TEST_USER_3` env vars to both integration test workflows and `test.env.sample` (more test users for grants tests).

### 42063121 — 2025-04-04 — BUG_FIX
**Message:** fix grants
**What:** Rewrites `fabric__get_show_grant_sql` to query `sys.database_principals` + `sys.database_permissions` instead of `INFORMATION_SCHEMA.TABLE_PRIVILEGES`. Also overrides `privilege_does_not_exist_error` and `grantee_does_not_exist_error` in `TestInvalidGrantsFabric` to use actual Fabric T-SQL error wording.
**Why:** `INFORMATION_SCHEMA.TABLE_PRIVILEGES` does not return the same data as `sys.database_permissions` on Fabric — it misses Entra-principal grants, so dbt's diff-based `apply_grants` logic kept re-issuing the same `GRANT` repeatedly.
**Upstream:** Still uses the broken query at `upstream/main:dbt/include/fabric/macros/adapters/apply_grants.sql`:
```
select GRANTEE as grantee, PRIVILEGE_TYPE as privilege_type
from INFORMATION_SCHEMA.TABLE_PRIVILEGES {{ information_schema_hints() }}
where TABLE_CATALOG = '{{ relation.database }}' ...
```

### 07db1102 — 2025-04-04 — TEST
**Message:** hooks tests
**What:** Adds two T-SQL seed files (`tests/functional/adapter/data/seed_model.sql`, `seed_run.sql`) creating the `on_model_hook` and `on_run_hook` tables for the upstream hooks tests, with Fabric-compatible column types.
**Why:** Upstream `BasePrePostModelHooks` tests load PG-typed setup SQL. Inlined later into `test_hooks.py` in commit 0f1422c3.

### 33f3b12c — 2025-04-04 — TEST
**Message:** fix tests for hooks
**What:** Adds `FabricHooksChecks` mixin that overrides `check_hooks` — asserting `target_type == "fabric"`, `target_threads == 1`, etc. Removes misclassified `TestPrePostModelHooksInConfigSetupFabric`.
**Why:** Upstream `check_hooks` assertions targeted Postgres-style values and failed on Fabric.

### 62705a00 — 2025-04-04 — DBT_NATIVE_REWRITE
**Message:** hooks fixes
**What:** Adds `src/dbt/include/fabric/macros/materializations/hooks.sql` overriding `run_hooks` to drop the `commit;` statement emitted at start of out-of-transaction hook execution. Also re-implements multiple seed/snapshot hooks tests with Fabric-typed columns (`int` not `boolean`) and calls `dbt.type_int()` for dependency tracking (per dbt-core #6806).
**Why:** Upstream `run_hooks` emits `commit;` to exit the implicit transaction wrapping a model, but Fabric DW does not yet support BEGIN/COMMIT TRAN. Without this override hooks fail at every run boundary.
**Upstream:** `upstream/main` has no `materializations/hooks.sql` override — confirmed by `git ls-tree`. It inherits dbt-adapters' default `run_hooks` which always emits `commit;` for outside-transaction hooks. Real runtime bug in upstream for any project using pre/post hooks on Fabric DW.

### 117eff7e — 2025-04-04 — INFRA: adds missing `pytest` import in `test_hooks.py` (typo fix in previous commit).

### 453226af — 2025-04-04 — INFRA: removes two unused imports from `test_hooks.py`.

### 8311e1f3 — 2025-04-04 — TEST
**Message:** match test as in parent
**What:** Adds `unique_key='id'` to the microbatch model fixture so it matches upstream `BaseMicrobatch` expectations (Fabric's MERGE requires a unique key — Snowflake's microbatch doesn't).
**Why:** Test was failing because microbatch incremental on Fabric needs a unique key for the MERGE statement.

### acdca039 — 2025-04-04 — TEST
**Message:** enable more tests
**What:** Re-enables `TestIncrementalOnSchemaChangeFabric` (was fully skipped) and only skips one sub-test (`test_run_incremental_sync_all_columns`) with accurate reason: "ALTER TABLE cannot drop columns for now (on the roadmap)".
**Why:** Old skip reason was overly broad; only the sub-test that requires column drops genuinely fails.

### dea31d36 — 2025-04-04 — BUG_FIX
**Message:** fix drop schema macro
**What:** Wraps the body of `fabric__get_use_database_sql` in `{%- if database is not none -%}` so the macro emits no `USE [None];` when called with a None database. Also deletes an obsolete `TestCatalogRelationTypes` test class from `test_relations.py`.
**Why:** `drop_schema` and related ops pass `database=None` in some code paths; upstream's macro then renders `USE [None];` — invalid T-SQL.
**Upstream:** Still buggy at `upstream/main:dbt/include/fabric/macros/adapters/metadata.sql`:
```
{%- macro fabric__get_use_database_sql(database) -%}
  USE [{{database | replace('"', '') | replace('[', '') | replace(']', '')}}];
{%- endmacro -%}
```
No None-guard.

### d3ef3f0b — 2025-04-04 — TEST
**Message:** fix a few more simple tests
**What:** Adds Fabric-typed seed/property overrides for `test_simple_seed.py`: `fixed_seeds___expected_sql` replaces PG types (`TIMESTAMP WITHOUT TIME ZONE` → `datetime2(6)`, `TEXT` → `varchar(100)`, `INTEGER` → `int`); `fixed_properties__schema_yml` replaces PG type names in schema YAML. Adds `FixedSeedSetup` mixin that pre-creates the expected table with Fabric types.
**Why:** Upstream PG-style `seeds__expected_sql` won't run on Fabric DW.

### 7de71719 — 2025-04-04 — TEST
**Message:** skip test
**What:** Skips `test_simple_seed_full_refresh_flag` sub-test in `TestBasicSeedTestsFabric` with reason: "This test assumes that if you drop a table, that it will cascade to all views".
**Why:** Fabric DW lacks `DROP TABLE ... CASCADE`.

### 0be3a79c — 2025-04-04 — REFACTOR
**Message:** split tests
**What:** Splits `tests/functional/adapter/test_simple.py` into three files: `test_simple_seed.py`, `test_simple_snapshot.py`, `test_simple_copy.py`.
**Why:** Better organization so failures map cleanly to a subject area.

### 80caf6df — 2025-04-04 — DBT_NATIVE_REWRITE
**Message:** fix project fixture
**What:** Subclasses dbt's `TestProjInfo` test fixture into `TestProjInfoFabric` that overrides `get_tables_in_schema` to use T-SQL `sys.tables` + `sys.schemas` joins instead of `INFORMATION_SCHEMA.TABLES`. Wires it in via a `project` fixture override in `conftest.py`. Creates `tests/test_proj_info.py` (later consolidated in 20a174c3).
**Why:** Upstream test harness uses `information_schema.tables` with `lower(table_schema)` matching, but Fabric's information_schema doesn't list all tables/views consistently, causing `get_tables_in_schema()` assertions to fail in catalog/relation tests.

### 15d42168 — 2025-04-04 — REFACTOR
**Message:** fix project helper
**What:** Rewrites the SQL inside `TestProjInfoFabric.get_tables_in_schema` to use a UNION of `sys.tables` + `sys.views`.
**Why:** Earlier version still queried information_schema; switches to more reliable sys-catalog approach.

### 9676fb99 — 2025-04-04 — TEST
**Message:** fix test
**What:** Skips `TestSimpleCopyBaseFabric.test_simple_copy_with_materialized_views` (materialized views not supported on Fabric DW). Adds a `dbt_profile_target` override in `TestSimpleCopyUppercaseFabric` to pass through the conftest fixture instead of being replaced with PG defaults from the upstream base class.
**Why:** Standard fork patterns — skip unsupported features, restore conftest fixture overridden by upstream base.

### e9709e3d — 2025-04-04 — INFRA: ruff formatting of `test_simple_copy.py`.

### 20a174c3 — 2025-04-04 — REFACTOR
**Message:** fix imports
**What:** Moves `TestProjInfoFabric` from its own file `tests/test_proj_info.py` (pytest tried to collect it as test code) into `tests/conftest.py` directly.
**Why:** Files named `test_*.py` with classes starting `Test*` are auto-collected by pytest — the fixture helper was being scanned as actual test code.

### 0f1422c3 — 2025-04-05 — REFACTOR
**Message:** remove files in test_data_dir
**What:** Deletes the two T-SQL setup files `tests/functional/adapter/data/seed_{model,run}.sql` added in 07db1102, replacing them with inline `RunModelFile` fixtures in `test_hooks.py` that call `project.run_sql(...)` with the CREATE TABLE DDL directly. Adds `RunModelFile` mixin to several hook test classes.
**Why:** External SQL files were too far from the tests using them; inlining keeps the setup co-located with the test.

### 2dea92ae — 2025-04-05 — REFACTOR
**Message:** remove seed_bom
**What:** Deletes the 501-line `seed_bom.csv` test data file and uses `inspect.getfile(BaseSimpleSeedWithBOM).parent` to copy the same file from the upstream `dbt-tests-adapter` package at runtime.
**Why:** No need to vendor the upstream test data file — read it directly from the installed package.

### c3b869be — 2025-04-05 — TEST
**Message:** fix another test
**What:** In `TestSimpleSeedColumnOverrideFabric`, overrides upstream `seeds`/`models` fixtures: replaces `boolean` with `int` (Fabric has no bool, only `bit`); adds a custom `column_type` test macro using `col_type.startswith(type)` for flexible matching; provides a Fabric-typed `seed_tricky.csv` (booleans as 0/1, dates as plain datetime). Skips `TestSeedConfigFullRefreshOnFabric`.
**Why:** Upstream test asserts boolean column types Fabric doesn't have, with date/bool literal formats incompatible with Fabric T-SQL seed loader.

### 0d7b0f99 — 2025-04-05 — TEST
**Message:** fix 2 more tests
**What:** Adds `TestSimpleSeedEnabledViaConfigFabric` overrides: Fabric-typed seeds fixture and a `clear_test_schema` function-scoped fixture that explicitly drops the schema after each test.
**Why:** Upstream test relies on between-test cleanup that doesn't happen naturally on Fabric, causing subtests collisions.

### a27112ee — 2025-04-05 — TEST
**Message:** fix snapshot tests
**What:** Adds `BaseSimpleSnapshotBaseFabric` mixin overriding `_assert_results` (replaces strict equality with `assert in expected`) and `add_fact_column`/`update_fact_records` to drop default value clauses (Fabric does not support default values on `ADD COLUMN`). Also overrides `test_new_column_captured_by_snapshot` and `test_updates_are_captured_by_snapshot` to use `dateadd(day, 1, updated_at)` (T-SQL) and `+` string concat.
**Why:** Upstream snapshot tests use PG/ANSI syntax (`||` concat, `INTERVAL '1 day'`, equality-based assertions); Fabric needs T-SQL equivalents.

### 7c85ecd9 — 2025-04-05 — INFRA: renames `integration-tests.yml` → `weekly-integration-tests.yml` and `integration-tests-weekly.yml` → `regular-integration-tests.yml` (swap), adds a new `case-insensitive-integration-tests-fabric-dw` job that runs the suite against a case-insensitive collation DW. Updates README badge URL.

### 72465b23 — 2025-04-05 — TEST
**Message:** remove duplicate test
**What:** Deletes `tests/functional/adapter/test_snapshot_configs.py` (714 lines) — these were copy-pasted from `dbt-tests-adapter`.
**Why:** Vendored copies of upstream tests are unmaintainable; proper subclass tests in `test_simple_snapshot.py` already exercise the same paths.

### 4191ada0 — 2025-04-05 — TEST
**Message:** remove duplicate test
**What:** Deletes `tests/functional/adapter/test_snapshot_new_record_mode.py` (227 lines) — another copy-pasted upstream test file. Removes a stale code comment in `test_sources.py`.
**Why:** Same as 72465b23 — eliminating vendored upstream test code.

### b09ab8d2 — 2025-04-05 — TEST
**Message:** mark flaky test
**What:** Marks `TestSimpleSeedEnabledViaConfigFabric` with `@pytest.mark.flaky`.
**Why:** Test occasionally fails due to Fabric DW transient schema/state issues.

### 30fd024b — 2025-04-05 — BUG_FIX
**Message:** fix sources test
**What:** Replaces the `TestSourcesFabric` source definition pointing to `sys.tables` (which triggers "object not supported in distributed processing mode" on Fabric) with a per-test temporary `sample` table. Removes the test-level `pytest.mark.skip`.
**Why:** Test was previously fully skipped; with a real user-table source it now exercises actual `source()` resolution on Fabric.

### cbea832a — 2025-04-05 — TEST
**Message:** skip array tests
**What:** Adds `@pytest.mark.skip(reason="Array concat is not supported in Fabric")` to `TestArrayAppendFabric` and `TestArrayConcatFabric`.
**Why:** Fabric DW T-SQL has no array data type.

### 55029e0b — 2025-04-05 — TEST
**Message:** delete invalid test
**What:** Deletes `tests/functional/adapter/utils/test_array_utils.py` — `BaseArrayUtils` is meaningless without array types in Fabric.

### e2455ac5 — 2025-04-05 — TEST
**Message:** delete invalid test
**What:** Deletes `tests/functional/adapter/utils/test_base_utils.py`.

### f9f91e3f — 2025-04-05 — NEW_FEATURE
**Message:** add support for bool_or
**What:** Adds `src/dbt/include/fabric/macros/utils/bool_or.sql` implementing `fabric__bool_or(expression)` as `MAX(CASE WHEN expression THEN 1 ELSE 0 END)` — standard T-SQL workaround for the missing `BOOL_OR` aggregate.
**Why:** dbt's `bool_or` cross-database macro fails out-of-the-box on Fabric because Fabric T-SQL lacks `BOOL_OR`. This is a core dbt-utils dependency.
**Upstream:** `upstream/main:dbt/include/fabric/macros/utils/` contains no `bool_or.sql` — confirmed via `git ls-tree`. Any project on upstream using `dbt.bool_or` or dbt-utils macros depending on it would fail.

### 706b4d5f — 2025-04-05 — TEST
**Message:** fix test
**What:** Overrides the model fixture in `TestCastBoolToTextFabric` to use Fabric-compatible literal syntax: replaces `true`/`false` with `0`/`1` and `null::boolean` with plain `null`.
**Why:** Upstream test uses PG bool literals which Fabric T-SQL doesn't accept.
