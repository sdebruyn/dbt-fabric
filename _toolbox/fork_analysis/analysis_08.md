### b1b71ded — 2026-05-14 — DOCS: Fix broken docs site images and restore logo

### 062c800b — 2026-05-14 — DOCS: Add dbt-core 1.11 to compatibility page

### aa28750c — 2026-05-15 — DOCS: Add comprehensive Lakehouse (FabricSpark) documentation across all docs
**What:** New Lakehouse guide page and broad updates across README/installation/configuration/auth/python-models/feature-comparison docs to surface both compute engines (Warehouse + Lakehouse).
**Why:** FabricSpark support is a major fork-only feature; the docs needed to advertise it everywhere a user might land.

### 23e758dc — 2026-05-15 — DOCS: Document mssql-python driver as a key differentiator
**What:** Documents that the fork uses Microsoft's `mssql-python` instead of pyodbc (no system ODBC required).
**Why:** Significant user-facing advantage over upstream, previously undocumented. Also adds Microsoft Learn MVP tracking parameter rule to CLAUDE.md.

### f22e35b5 — 2026-05-15 — BUG_FIX
**Message:** Push schema filter into UNION branches in list_relations_without_caching (#78)
**What:** Moved the `WHERE SCHEMA_NAME(...) like '{{ schema }}'` filter from after the UNION ALL into each branch (tables, views, functions) of `fabric__list_relations_without_caching`.
**Why:** Reduces row scans and avoids potential lock contention against `sys.tables`/`sys.views`/`sys.objects` from concurrent DDL.
**Upstream:** Upstream (`microsoft/dbt-fabric#365`) already pushed the filter into its two-branch version (tables, views). The fork's macro has a third branch for `function` relations; this commit applies the same optimization to that third branch — the function-branch perf fix is fork-only because the third branch itself is fork-only.

### 6ae594d2 — 2026-05-15 — BUG_FIX
**Message:** Handle [SCHEMA_NOT_FOUND] in FabricSpark list_relations_without_caching (#81)
**What:** Override `list_relations_without_caching` in `FabricSparkAdapter` to catch `DbtRuntimeError` with `[SCHEMA_NOT_FOUND]` and return `[]` instead of re-raising. Ported from `microsoft/dbt-fabricspark@9d2a8136`.
**Why:** During `dbt docs generate`, catalog queries fan out to source schemas in foreign lakehouses; an absent schema crashes the run rather than being treated as "no relations here".
**Upstream:** `microsoft/dbt-fabric` (T-SQL adapter, the only one Microsoft currently maintains) has no FabricSpark adapter at all, so the fix is intrinsically fork-only. The original `microsoft/dbt-fabricspark` repo (separately archived) had this fix.

### 73a5eb2b — 2026-05-15 — BUG_FIX
**Message:** Port upstream: fix source freshness failures on Fabric Lakehouse (#79)
**What:** Adds `USE [database]` and `CAST(modify_date AS datetime2(6))` to `fabric__get_relation_last_modified`; adds new `fabric__collect_freshness` using `TRY_CAST(... AS datetimeoffset(6))` and `SYSDATETIMEOFFSET()` so Lakehouse SQL-endpoint sources work even when `loaded_at` columns are stored as `varchar` (e.g. CDC).
**Why:** Lakehouse SQL endpoint returns datetimes as strings and fails the default freshness query; without `USE`, `sys.objects` is queried against the wrong database.
**Upstream:** Upstream now has the same idea but uses `datetime2(3)` for both. The fork's `datetimeoffset(6)` better preserves timezone offsets (avoids dropping the `+HH:MM` from ISO-8601 values like Debezium emits) and gives microsecond precision consistent with adapter convention.

### 4c8e7dea — 2026-05-15 — DOCS: Note Sam Debruyn as original author; soften feature-comparison intro

### 0d3a65de — 2026-05-15 — DOCS: Document @available decorator, capability declaration, credential security, branching rule

### 6434e2d8 — 2026-05-15 — NEW_FEATURE
**Message:** Add dbt-external-tables support using OPENROWSET (#60)
**What:** Adds full dbt-external-tables compatibility macros for Fabric Data Warehouse using `OPENROWSET(BULK ...)` to query Parquet/CSV/JSONL files from Azure Blob, ADLS, or OneLake. Includes 187-line macro file (`src/dbt/include/fabric/macros/dbt_package_support/dbt_external_tables/external_tables.sql`), 229-line docs page, integration tests via the `BaseExternalTableTest` harness, escaping for SQL injection (single quotes in URLs and option values), and dispatch-based override pattern documented in CLAUDE.md.
**Why:** dbt-external-tables ships Synapse-style `CREATE EXTERNAL TABLE` macros that don't fit Fabric; OPENROWSET is the Fabric-native way.
**Upstream:** Upstream has no dbt-external-tables support and no OPENROWSET integration of any kind (`git ls-tree upstream/main | grep external` returns nothing). Substantial fork-only feature backed by docs and integration tests.

### c2d318ca — 2026-05-15 — DOCS: Add docstrings (Args/Raises/behavioral notes) to all fork-specific Fabric adapter methods (FabricApiClient, LivySession, FabricTokenProvider, FabricConnectionManager, FabricAdapter)

### 49f597a3 — 2026-05-15 — DOCS: Make PR creation an explicit step in CLAUDE.md branching workflow

### b193ae49 — 2026-05-15 — INFRA: Fix CI workflows to trigger on `main` instead of `forked-version` branch

### c39d9acb — 2026-05-15 — NEW_FEATURE
**Message:** FabricSpark adapter core improvements (#62)
**What:** Multiple FabricSpark core changes bundled:
- Adds `FabricSparkQuotePolicy` (database=True, schema=True) and `FabricSparkIncludePolicy` (database=True) overriding the inherited `SparkQuotePolicy`/`SparkIncludePolicy` so relations render as 3-part `database.schema.table` names — needed for cross-lakehouse writes. Spark vanilla treats database==schema; Fabric Lakehouse has both.
- Fixes `ApproximateMatchError` on mixed-case database/schema names in the relation cache (Spark default lowercases since quote_policy is False; we set it to True).
- Adds retry + transient-error handling to Livy session lifecycle (`_MAX_CONSECUTIVE_TRANSIENT_ERRORS`, structured `FabricApiError` exception used instead of fragile substring matching).
- Adds `fabricspark__string_literal` macro for Spark SQL compatibility.
- Adds `data_type_code_to_name` mapping in FabricSpark connection manager.
- Adds unit tests for mixed-case matching behavior.
**Why:** Make FabricSpark adapter robust for real-world multi-lakehouse setups and transient Livy API failures.
**Upstream:** No FabricSpark adapter in upstream. The `SparkQuotePolicy`/`SparkIncludePolicy` issue stems from inheriting dbt-spark defaults that don't fit Fabric Lakehouse's catalog model — never addressed upstream because there is no upstream.

### baf52a29 — 2026-05-15 — DOCS: PR scope guidelines in CLAUDE.md

### 48e51bb1 — 2026-05-15 — DOCS: FabricSpark "lessons learned" added to CLAUDE.md

### 3f4b4304 — 2026-05-15 — DOCS: Sync CONTRIBUTING.md with CLAUDE.md, fix test.env.sample variable names (FABRIC_WORKSPACE_NAME → FABRIC_TEST_WORKSPACE_NAME, add HOST/LAKEHOUSE_NAME/LIVY_SESSION_NAME/WORKSPACE_ID)

### 9d450e44 — 2026-05-15 — TEST
**Message:** Skip unsupported GRANT tests for FabricSpark (#91)
**What:** Marks GRANT tests with `@pytest.mark.skip` — Fabric Lakehouse uses workspace-level access control, not SQL GRANT.
**Notes:** Architectural skip, not a TODO.

### 270a0547 — 2026-05-15 — DOCS: Strip premature implementation proposals from roadmap.md

### 107c57a4 — 2026-05-15 — DOCS: Add `cp test.env` step to worktree workflow in CLAUDE.md

### b29f3828 — 2026-05-15 — DOCS: Remove code-derivable sections from CLAUDE.md

### 8dc9f06c — 2026-05-15 — INFRA: Limit DE (FabricSpark) integration tests to weekly schedule + manual dispatch (HTTP 430 rate limits)

### 7eb3da56 — 2026-05-15 — INFRA: Move multi-agent dev workflow from CLAUDE.md into a Claude Code skill

### 081d4d5a — 2026-05-15 — NEW_FEATURE
**Message:** Add dbt Core 1.12 support (#119)
**What:** Bumps dbt-core upper bound to allow 1.12; adds `fabric__list_function_relations_without_caching` macro (new in dbt 1.12), adds `MetadataWithEmptyFlag`, `BasePythonMetaGetTests`, `BaseCatalogIntegrationValidation` tests for both Fabric and FabricSpark; bumps `dbt-tests-adapter` minimum to 1.19.7; documents the upgrade process in CONTRIBUTING.md.
**Why:** Stay current with dbt Core releases.
**Upstream:** Upstream metadata macro file has no `list_function_relations_without_caching` macro (verified: `grep "list_function_relations" upstream/main:dbt/include/fabric/macros/adapters/metadata.sql` → NOT IN UPSTREAM). Upstream is still pinned to older dbt-core; fork explicitly tracks the latest core.

### e2730978 — 2026-05-15 — INFRA: Add path filters to DW integration test triggers (skip when only docs/FabricSpark files change)

### cf18d64c — 2026-05-15 — DOCS: Extract community package tests into a Claude Code skill, shorten test-architecture section in CLAUDE.md

### fcc6287c — 2026-05-15 — INFRA: Add on-demand DE integration tests via PR comment `/test-de` + Copilot `@test-runner` agent

### 708ca38a — 2026-05-15 — INFRA: Split integration-tests.yml into integration-tests-dw.yml and integration-tests-de.yml

### 36a86c4d — 2026-05-15 — TEST: Skip unsupported UDF/UDAF tests for FabricSpark

### 12642ce0 — 2026-05-15 — TEST
**Message:** Fix FabricSpark store_test_failures tests (#113)
**What:** Replaces all `store_failures_as="view"` with `"table"` in test fixtures because `FabricSparkRelationType` has no `View` variant (Fabric Lakehouse with schemas doesn't support Spark SQL views), updates expected `TestResult` types, and fixes a pytest collection warning by importing `TestResult` from the base module.
**Notes:** Pure test adaptation — no implementation change.

### 682cd721 — 2026-05-15 — NEW_FEATURE
**Message:** Add FabricSpark clone materialization (#99)
**What:** Adds `clone` materialization for FabricSpark that materializes the deferred relation as a `materialized_view` (SELECT * FROM defer_relation). Adds `fabricspark__can_clone_table()` returning False (no SHALLOW CLONE since that's Databricks-specific). Skips `BaseClonePossible`/`BaseCloneSameSourceAndTarget`. Adds passing tests for the fallback path.
**Why:** dbt-clone needs an answer on FabricSpark; the obvious copy-from-Databricks fails.
**Upstream:** No upstream FabricSpark to compare against.

### 21cc97e3 — 2026-05-15 — BUG_FIX
**Message:** Fix isolated test item names to use underscores (#133)
**What:** Switches isolated-mode lakehouse/DW item names from `dbt-test-lh-xxx` → `dbt_test_lh_xxx` (hyphens are illegal in Fabric item names; HTTP 400). Also makes `--isolated` opt-in instead of default (Fabric API rate limits are per-SP, not per-item).
**Notes:** This whole infrastructure was later removed in commit c573af2f below.

### ed79e79e — 2026-05-15 — INFRA: Default DW integration tests to Python 3.13 only; full 3.11/3.12/3.13 matrix only on Sunday weekly schedule

### 1a585987 — 2026-05-15 — TEST
**Message:** Fix FabricSpark concurrency tests (#98)
**What:** Override `BaseConcurrency` model fixtures to replace `view` materialization with `materialized_view` — Fabric Lakehouse doesn't support Spark SQL views.
**Notes:** Pure test-fixture adaptation.

### 6915e540 — 2026-05-15 — DOCS: Update feature-comparison to reflect dbt Core 1.12 support

### 078d198d — 2026-05-15 — TEST: Fix FabricSpark ephemeral tests — override fixtures to use table instead of view for non-ephemeral models; add data equality assertion

### fc0b36e2 — 2026-05-15 — TEST
**Message:** Fix FabricSpark hook tests (#111)
**What:** Adds `SparkRunModelFile`, `SparkHooksChecks`, `SparkPrePostHooksFixtures` mixins for Spark-compatible hook table creation (STRING type, backtick-quoted column names, fabricspark target_type validation); replaces seed/snapshot VACUUM hooks with ALTER TABLE ADD COLUMN; adds Spark snapshot fixtures; restores TERM_TEST env var.
**Notes:** Test-fixture adaptation only; the base classes assume PG/T-SQL types and quoting.

### 3cd9bf3f — 2026-05-15 — TEST: Switch FabricSpark current_timestamp test to BaseCurrentTimestampAware (matches Databricks behavior — Spark returns tz-aware UTC)

### 4ba1a275 — 2026-05-15 — NEW_FEATURE
**Message:** Add FabricSpark snapshot materialization (#101)
**What:** Adds a complete FabricSpark snapshot materialization stack:
- `snapshot.sql` (105 lines) — replaces dbt-spark's snapshot which uses temp views; uses real staging tables instead (Fabric Lakehouse with schemas doesn't support Spark SQL views and Spark catalog rejects 3-part DML names against views).
- `helpers.sql` — snapshot column helpers.
- `snapshot_merge.sql` — Spark MERGE adapted for Fabric Lakehouse.
- `strategies.sql` — snapshot strategies.
- `fabricspark__create_schema`/`drop_schema` calling `.without_identifier()` (dbt-spark skips this because vanilla Spark has no schemas; Fabric Lakehouse does).
- Inline Jinja comments document each deviation from dbt-spark.
**Why:** dbt-spark's snapshot doesn't work on Fabric Lakehouse without significant adaptation.
**Upstream:** No upstream FabricSpark to compare against.

### c573af2f — 2026-05-15 — REFACTOR
**Message:** Remove unused --isolated test infrastructure (#143)
**What:** Removes the `--isolated` pytest flag, `FabricTestItemManager` class (`tests/isolated_items.py`), and 155-line item-creation helper. Restores `FABRIC_TEST_WORKSPACE_ID` env var doc (still used in conftest).
**Notes:** Reverses earlier infrastructure including 21cc97e3 above (which renamed item names for --isolated). Net deletion of 229 lines.

### f567b7c6 — 2026-05-15 — NEW_FEATURE
**Message:** Add FabricSpark persist_docs support (#92)
**What:** Adds persist_docs (table + column comments) for FabricSpark via Delta's COMMENT clauses:
- Override `persist_docs` macro to use `COMMENT ON TABLE` (DDL COMMENT clause is silently ignored on materialized lake views).
- Override `alter_column_comment` macro (no `file_format` gate since Fabric Lakehouse is always Delta).
- Adds `table_comment`/`column_comment` to `FabricSparkColumn`, reads them from `DESCRIBE EXTENDED`.
- Adds persist_docs call to `materialized_view` materialization, removes broken COMMENT clause from materialized lake view DDL.
- Uses `validate_doc_columns` (dbt-core default) to warn on missing columns in schema.yml.
**Why:** dbt's persist_docs API is widely used; previously unsupported.
**Upstream:** No upstream FabricSpark to compare against.

### b59495b2 — 2026-05-15 — TEST: Fix FabricSpark null_compare test by casting NULLs to explicit types (Spark assigns type `void` to untyped NULL, which Delta can't store)
**Notes:** Reverted in next commit; reapplied immediately after.

### 4e33f587 — 2026-05-15 — REVERT_OR_MODIFY
**Message:** Revert "Fix FabricSpark null_compare test (#112)"
**What:** Reverts b59495b2 above.
**Notes:** Re-applied immediately in next commit (81e0bdf9).

### 81e0bdf9 — 2026-05-15 — TEST
**Message:** Fix FabricSpark null_compare test (#144)
**What:** Re-applies the b59495b2 fix (cast NULLs to explicit types in null_compare test fixtures).
**Notes:** Net effect: same as b59495b2. The revert + re-apply suggests an accidental direct-to-main commit (b59495b2) that was reverted and re-merged via PR #144.

### 1237b302 — 2026-05-15 — TEST: Override get_intervals_between date format fixture to ISO `2023-09-01` (Spark can't parse `09/01/2023`)

### d2ecba2e — 2026-05-15 — TEST: Use backslash-escaping base class for FabricSpark escape_single_quotes (Spark uses `\'`, inherits `spark__escape_single_quotes` via dependencies)
