# Batch 10 analysis

**Summary:** 46 commits — 8 BUG_FIX, 7 NEW_FEATURE, 13 TEST (several with embedded bug fixes/feature work), 2 DBT_NATIVE_REWRITE, 2 ANTI_PATTERN_REMOVED (one inside the multi-faceted #268), 1 REVERT_OR_MODIFY, 6 DOCS, 1 REFACTOR, 6 INFRA. Standout items: high-concurrency Livy rewrite (#232) replacing the singleton+atexit pattern; cross-workspace 4-part naming (#235); first-class Spark view support (#234) that lets the default materialization revert to dbt-native `view` (#256); synapsesql JDBC schema-lock bug investigated across #239 (fire-and-forget GC) and #272 (promoted to awaited); large dbt-utils sweep (#218) where switching to `dbt build` exposed broken overrides (relationships_where, sequential_values, mutually_exclusive_ranges, split_part multi-char delimiter bug shared with upstream); HC session pooling PR (#268) is an instructive self-correcting story — pool was built, then thrown out because atexit drain duplicated the exact upstream anti-pattern this fork critiques. Many TEST commits were also implementation work: package integration tests for dbt-date, dbt-expectations, dbt-audit-helper, dbt-profiler, dbt-codegen, dbt-utils, dbt-artifacts, dbt-project-evaluator on both Fabric DW and FabricSpark, each adding new fabric/fabricspark macro overrides. One in-batch revert (bf45c646 reverts f37190a8).

---

### 213f705c — 2026-05-16 — BUG_FIX
**Message:** Fix docs: auth method is notebookutils, not FabricSpark/SynapseSpark (#217)
**What:** Corrects documented valid `authentication` values; only `notebookutils` is accepted by the code, not `FabricSpark`/`SynapseSpark`. Adds missing `workload_identity`.
**Why:** Docs listed authentication identifiers that would crash at runtime.
**Upstream:** Upstream `dbt-fabric` doesn't ship these docs/auth methods at all (fork-only feature surface).

### c9b6537e — 2026-05-16 — TEST
**Message:** Add integration tests for dbt-date package (#202)
**What:** Adds `TestDbtDate` (dbt-date 0.17.2 against Fabric DW). Adds/fixes many `dbt_date` overrides: `convert_timezone`, `expression_is_true`, `day_name`/`month_name` (new `language` param), `iso_year_week` (lpad → RIGHT), `fabric__date`, `dim_date`/`dim_date_fiscal` (mod() not in T-SQL). Adds `project_vars`/`extra_dispatches` extensibility to `BaseDbtPackageTests`. Restructures docs.
**Notes:** Test exposed multiple macro bugs and motivated dim_date overrides and the new `expression_is_true` signature.

### e7f23bb9 — 2026-05-17 — NEW_FEATURE
**Message:** Allow configuring Fabric API base URLs for non-production tenants (#226)
**What:** `get_logs_url()` derives portal host from `_credentials.fabric_base_api_uri` (replaces `://api.` → `://app.`) instead of hardcoding `app.fabric.microsoft.com`. Adds conftest env vars for MSIT.
**Upstream:** Upstream has `api_url` field but no Livy/Spark monitor URL code at all.

### 8af2c1d0 — 2026-05-17 — ANTI_PATTERN_REMOVED
**Message:** Remove unused livy_session_lifecycle fixture from conftest (#230)
**What:** Deletes 36-line dead session-scoped fixture.

### 3185d5ee — 2026-05-17 — BUG_FIX
**Message:** Update dbt_utils to 1.3.3 and switch base test to dbt build (#218)
**What:** Switches dbt-utils integration test to `dbt build`. Exposed bugs fixed: `sequential_values` missing var; `mutually_exclusive_ranges` boolean literals and non-deterministic window; `relationships_where` full rewrite; new `equal_rowcount`/`fewer_rows_than` overrides avoiding GROUP BY on alias, with COALESCE for NULL-from-FULL-JOIN; `split_part` (T-SQL `STRING_SPLIT` is single-char-only → REPLACE→CHAR(1) trick). Removes legacy tsql_utils `surrogate_key.sql`/`cast_hash_to_str` dead code. Fixes whitespace-stripping `-#}` Jinja comments that concatenated SQL tokens.
**Upstream:** Upstream `fabric__split_part` (`dbt/include/fabric/macros/utils/split_part.sql`) still single-char `string_split` — bug present. Upstream lacks equal_rowcount/fewer_rows_than overrides; relationships_where and sequential_values still broken in upstream.
**Notes:** Self-contained partial revert: nested CTE refactor of dbt-date macros was tried then reverted (Fabric DW disallows nested CTEs in CREATE VIEW).

### 84c7b1a2 — 2026-05-17 — DOCS: Update package docs: add get_fiscal_year_dates, clarify override notes (#236)

### f095413c — 2026-05-17 — REFACTOR
**Message:** Centralize package versions in base test fixtures, document split_part (#237)

### e25ee599 — 2026-05-17 — NEW_FEATURE
**Message:** Add high-concurrency Livy support for parallel statement execution (#232)
**What:** Adds `HighConcurrencyLivySession` (289 LOC) using Fabric's HC Livy API so each dbt thread acquires its own REPL slot in a shared Spark session. Removes the old singleton `LivySession` class entirely (no fallback). Switches FabricLivyHelper (DW Python models) and FabricSpark to HC. Thread-local REPL storage. Best-effort server-side delete on failure. 29 new unit tests.
**Upstream:** Upstream `dbt-fabric` has no Spark/Livy at all. Upstream `microsoft/dbt-fabricspark` uses singleton sessions + atexit cleanup. Referenced upstream PR microsoft/dbt-fabricspark#186.
**Notes:** PR transiently introduced and reverted fire-and-forget GC (resurfaces in #239 and again awaited in #272).

### 3bb7b174 — 2026-05-17 — TEST
**Message:** Add integration tests for dbt-expectations package (#223)
**What:** `TestDbtExpectations` (dbt-expectations 0.10.10 on Fabric DW). Adds `fabric__type_timestamp`/`fabric__type_datetime` (T-SQL `timestamp` is `rowversion`). Fixes `expect_column_most_common_value_to_be_in_set` (T-SQL CTE-in-subquery limitation). Splits `split_part` further.
**Notes:** Test exposed type and CTE-scoping bugs.

### 5df6de74 — 2026-05-17 — BUG_FIX
**Message:** Force JVM GC after synapsesql write to release JDBC schema locks (#239)
**What:** Adds fire-and-forget `spark._jvm.java.lang.System.gc()` after each Python model write in `FabricLivyHelper.submit()`. synapsesql connector holds Sch-S locks via long-lived JDBC connections; later sp_rename/DROP TABLE blocked on LCK_M_SCH_M.
**Upstream:** Upstream `dbt-fabric` has no Python model executor; upstream `dbt-fabricspark` doesn't integrate with synapsesql writes the same way. Fork-only issue and fix.
**Notes:** Promoted to awaited in 2aa33835.

### d2593b3a — 2026-05-17 — TEST
**Message:** Add integration tests for dbt-codegen package (#222)
**What:** Direct codegen macro exercise (bypassing upstream `integration_tests` which uses `LIMIT 0`).

### 52572266 — 2026-05-17 — BUG_FIX
**Message:** Add dbt-audit-helper 0.13.0 integration tests and macro overrides (#219)
**What:** Brings audit-helper overrides up to 0.13.0 signatures and fixes many bugs: `compare_queries` (limit/OFFSET/FETCH), `compare_column_values` (new params, CASE order: missing-row before both-null), `compare_relations` (limit passthrough), `compare_relation_columns` (INFORMATION_SCHEMA → sys.columns/objects/types; `run_query()` separates the metadata query so sys.* doesn't run inside materialized SQL which Fabric distributed mode rejects), `compare_column_values_verbose` (inline subqueries vs nested WITH), `compare_all_columns` (positional GROUP BY, ORDER BY in CTEs), new `compare_which_query_columns_differ` (CROSS APPLY VALUES instead of CTE inside subquery).
**Upstream:** Upstream `fabric` audit-helper overrides are pre-0.13.0 and contain the above bugs.

### b2ac1d61 — 2026-05-17 — NEW_FEATURE
**Message:** Add integration tests for dbt-profiler package (#220)
**What:** Adds full Fabric DW support for dbt-profiler: `measure_median` (PERCENTILE_CONT), `measure_std_dev_*` (STDEV/STDEVP), `measure_is_unique` ('TRUE'/'FALSE' strings), `measure_avg` (bit NULL preserved), `is_numeric/is_logical/is_date_or_time_dtype` (T-SQL type names), `assert_relation_exists` (TOP 0). `fabric__test_accepted_values` quotes booleans (T-SQL has no TRUE/FALSE keywords). Patches installed `dbt_expectations.expect_column_to_exist` (namespace-qualified tests can't be locally overridden).
**Upstream:** No fabric overrides for dbt-profiler upstream; package was unusable.

### 53ee818c — 2026-05-17 — NEW_FEATURE
**Message:** Add Spark SQL view support for FabricSpark adapter (#234)
**What:** First-class view support: `View` variant in `FabricSparkRelationType`, new view materialization (`CREATE OR REPLACE VIEW`), `try_translate_type` handles "view", metadata via `SHOW TABLE EXTENDED` Type: VIEW, View added to `replaceable_relations`, `persist_docs` via `ALTER VIEW SET TBLPROPERTIES` (no column-level on views). Clone macro: same-schema → SHALLOW CLONE, cross-schema → view fallback.
**Upstream:** Upstream `microsoft/dbt-fabricspark` lacks proper view support (only materialized_view).

### fa561a30 — 2026-05-17 — TEST
**Message:** Add FabricSpark dbt-date integration tests and move BaseDbtPackageTests to shared module (#228)
**What:** Adds `TestDbtDate` for FabricSpark; lifts `BaseDbtPackageTests` from `tests/fabric/packages/` to shared `tests/packages/`.

### 71a7019e — 2026-05-17 — TEST
**Message:** Add FabricSpark integration tests for dbt-expectations package (#229)
**What:** 127/127 pass after excluding regex (upstream `spark__regexp_instr` ignores flags) and two timeseries tests.

### 6106cf0a — 2026-05-17 — NEW_FEATURE
**Message:** Add cross-workspace 4-part naming for FabricSpark (#235)
**What:** Adds `workspace` field to `FabricSparkRelation` + model config `workspace_name` → renders 4-part `workspace.lakehouse.schema.table`. Adds FabricSpark `table` materialization using `this.incorporate()` (preserves workspace). Snapshot skips schema-existence check when workspace set. 390 LOC integration tests across materializations.
**Upstream:** Upstream `dbt-fabricspark` 3-part only.

### db47d5ac — 2026-05-17 — TEST
**Message:** Add FabricSpark integration tests for dbt-codegen package (#249)
**What:** 5/6 codegen tests pass (test_generate_source skipped — Spark has no information_schema).

### e34fcd0d — 2026-05-17 — TEST
**Message:** Add FabricSpark integration tests for dbt-project-evaluator package (#250)

### 19ca2c25 — 2026-05-17 — TEST
**Message:** Add FabricSpark integration tests for dbt_artifacts package (#251)
**What:** Adds `TestDbtArtifacts`. Sets `file_format=delta` (upstream defaults to empty for non-Databricks) and per-model `partition_by` for the microbatch model (BigQuery-style dict was breaking Spark partitioning).

### 486f6ff8 — 2026-05-17 — NEW_FEATURE
**Message:** Add FabricSpark dbt-profiler integration tests and macro overrides (#248)
**What:** Adds `TestDbtProfiler` for FabricSpark plus `fabricspark__get_profile` (delegates to `databricks__get_profile`, which uses DESCRIBE TABLE EXTENDED instead of INFORMATION_SCHEMA.COLUMNS) and `fabricspark__type_string`.

### a32ce3ef — 2026-05-17 — BUG_FIX
**Message:** Fix case mismatch in dbt-date round_timestamp test fixture (#253)
**What:** String replace looked for uppercase `'DATETIME2(6)'` but `fabric__type_timestamp()` emits lowercase, so the replacement never matched.
**Notes:** Fork-introduced fixture bug from #202.

### 473d16e5 — 2026-05-17 — BUG_FIX
**Message:** Fix snapshot_meta_column_names assertion for dbt-core dataclass change (#254)
**What:** dbt-core changed `snapshot_meta_column_names` from dict to `SnapshotMetaColumnNames` dataclass; updated assertion.
**Upstream:** Upstream doesn't override this test, but will hit the same assertion mismatch on dbt-core bump.

### 48d3bfbe — 2026-05-17 — NEW_FEATURE
**Message:** Add FabricSpark dbt-audit-helper integration tests and macro overrides (#244)
**What:** `TestDbtAuditHelper` for FabricSpark. Adds `fabricspark__compare_which_query_columns_differ` (Spark fully-qualifies CTE names in stored view text → use inline subqueries + `lateral view inline(named_struct(...))` unpivot) and `fabricspark__quick_are_queries_identical` (`bit_xor(xxhash64())` for order-independent hashing). 64 → 87 passing tests.

### f6a30e98 — 2026-05-17 — DBT_NATIVE_REWRITE
**Message:** Change FabricSpark default materialization to view (#256)
**What:** Removes the `+materialized: materialized_view` override in `dbt_project.yml`; falls back to dbt's standard `view` default. Made possible by #234.
**Upstream:** Upstream `dbt-fabricspark` defaults to `materialized_view`.

### 87666fe1 — 2026-05-17 — DOCS: Improve documentation completeness (#255)

### 096cc453 — 2026-05-17 — INFRA: Remove DE job 60-min timeout (use 6h GitHub default) and FABRIC_TEST_THREADS=2 override (use conftest default 10).

### 9b545348 — 2026-05-17 — INFRA: Update project description in pyproject.toml.

### fa771d39 — 2026-05-17 — BUG_FIX
**Message:** Add FabricSpark integration tests for dbt-utils package (#246)
**What:** Adds `TestDbtUtils` for FabricSpark. Test exposed a real bug: `spark__escape_single_quotes` (dbt-spark) uses backslash escapes, but Fabric Lakehouse has `escapedStringLiterals=false` → backslash literal. Adds `fabricspark__escape_single_quotes` falling back to SQL-standard doubled quotes. Adds `fabricspark__get_tables_by_pattern_sql` (Spark has no information_schema.tables) using SHOW SCHEMAS + SHOW TABLES + SHOW TABLE EXTENDED with Jinja regex filtering.
**Upstream:** Upstream `dbt-spark` produces invalid output on Fabric Lakehouse; no upstream override for `get_tables_by_pattern_sql`.

### 4159e44e — 2026-05-17 — INFRA
**Message:** Rename package to dbt-fabric and rebrand metadata for Fabric Toolbox
**What:** Drops `samdebruyn` suffix; removes personal funding and analytics config; aligns URLs, default Livy session name, test assertions; renames `feature-comparison.md` → `features.md`.

### f189767d — 2026-05-17 — DOCS
**Message:** Neutralize docs tone and remove personal branding from documentation
**What:** Removes both `comparison-dbt-fabric*.md` pages, replaces feature-comparison.md with non-comparative features.md, strips MVP tracking params from MS Learn links, rewrites critical framings into neutral feature descriptions for Microsoft-owned monorepo.

### ce74bda0 — 2026-05-17 — DOCS
**Message:** Add _toolbox/ handoff artifacts for fabric-toolbox contribution
**What:** Adds `_toolbox/HANDOFF.md`, `_toolbox/PR_DESCRIPTION.md`, `_toolbox/workflows/docs-publish.yml`.

### f37190a8 — 2026-05-18 — INFRA: Bump DE integration test job timeout to 480 min (#259).

### 155633e2 — 2026-05-18 — BUG_FIX
**Message:** Fix FabricSpark escape_single_quotes test (#260) (#262)
**What:** Replaces inheritance from `BaseEscapeSingleQuotesBackslash`; base classes hard-code `expected_length = 7`, but Fabric Lakehouse collapses `''` → `'` at parse time so length is 6.
**Notes:** Test exposed by the `escape_single_quotes` override from fa771d39.

### 3773fc31 — 2026-05-18 — INFRA: Merge branch 'main' into to-toolbox.

### bf45c646 — 2026-05-18 — REVERT_OR_MODIFY
**Message:** Revert "Set DE integration test job timeout to 8 hours (#259)" (#266)
**Notes:** Reverts f37190a8 from same batch.

### 7b1a9c3c — 2026-05-18 — INFRA: Merge remote-tracking branch 'origin/main' into to-toolbox.

### b7b75076 — 2026-05-18 — DOCS: Add dbt-project-evaluator package docs page (#269).

### cbb3c903 — 2026-05-18 — DOCS: Add dbt_artifacts package docs page (#270).

### 95bd9a1e — 2026-05-18 — DBT_NATIVE_REWRITE
**Message:** Speed up FabricSpark integration tests via HC session pooling (#268)
**What:** Multi-iteration PR. Started with process-wide HC pool keyed by session tag (with atexit drain), then dropped pool entirely because atexit-based cleanup duplicated the upstream pattern this fork's docs critique. Final state: (a) replace fixed 3s polling with 0.5s→1s→2s→3s adaptive backoff in `_poll_until_idle` / `wait_for_statement_ready`; (b) CI workflow sets `FABRIC_TEST_THREADS=4`. `close()` returns to delete-and-done.
**Why:** Pooling buys real users nothing (one dbt invocation per process); building atexit/drain infrastructure just for the test harness pollutes production. Adaptive polling is a pure-throughput win.
**Upstream:** Upstream `dbt-fabricspark` uses fixed polling + atexit cleanup; fork explicitly avoids both.
**Notes:** Instructive self-correcting story of resisting the anti-pattern.

### 2aa33835 — 2026-05-18 — BUG_FIX
**Message:** Investigate synapsesql schema-lock workarounds (paths A-D) (#272)
**What:** Promotes the JVM GC from #239 from fire-and-forget to awaited (`wait_for_result=True`). Measurements showed synapsesql JDBC sessions held Sch-S locks for 5-14 min during DW Python model runs; awaited GC drops them in ~3-4s.
**Upstream:** Fork-only because Python model integration is fork-only.

### b84c3e3c — 2026-05-18 — DOCS
**Message:** Add Fabric-only incremental config keys to quality-issues section
**What:** Adds documentation about v1.9.10 `delete_condition`/`delete_not_matched_by_source` as adapter-private knobs on a dbt-core materialization in the toolbox PR description.

### 941558a8 — 2026-05-18 — DOCS
**Message:** Tone down close() override critique in upstream review section
**What:** Pulls back unverified `rollback()` claim from PR_DESCRIPTION.

### 65a82aa9 — 2026-05-18 — INFRA
**Message:** Merge upstream microsoft/dbt-fabric (v1.9.10 + v1.10.0) using ours strategy
**What:** Records upstream/main as merge parent. Notes nothing from those releases needs porting (merge delete strategy / apply_label are adapter-private extensions).

### 8ff3e5a5 — 2026-05-18 — INFRA: Merge branch 'main' into to-toolbox (resolves comparison-dbt-fabricspark.md conflict).

### e17dabaf — 2026-05-18 — DOCS: Drop Appendices section from toolbox PR description.
