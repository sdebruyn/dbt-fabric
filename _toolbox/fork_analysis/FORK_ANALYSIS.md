# Fork analysis: dbt-fabric-samdebruyn vs microsoft/dbt-fabric

This is the master index over `_toolbox/fork_analysis/analysis_00.md` … `analysis_11.md`.
Per-commit detail (what changed, why, upstream comparison) lives in those batch files.
This document indexes the high-impact findings and the long-running development
arcs across the 546 fork commits.

## Scope

- **Fork start:** 2025-03-26 (commit `99b9986` "part 1 of project modernization")
- **Latest analysed commit:** 2026-05-18 (commit `f19e22c`)
- **Commits ahead of `upstream/main`:** 572 total (546 Sam-authored + 26 dependabot)
- **Coverage:** every Sam-authored commit, classified
- **Method:** 12 parallel analysis agents each took 46 commits, classified into
  `BUG_FIX` / `DBT_NATIVE_REWRITE` / `ANTI_PATTERN_REMOVED` / `NEW_FEATURE` /
  `TEST` / `INFRA` / `DOCS` / `REFACTOR` / `REVERT_OR_MODIFY` and verified
  upstream state with `git show upstream/main:<path>` where applicable.

## Category totals

| Category | Count | Notes |
|---|---:|---|
| INFRA | ~151 | CI workflows, build, dependency bumps, ruff formatting |
| TEST | ~117 | dbt-tests-adapter wiring, package integration tests, regression tests |
| DOCS | ~86 | Documentation site (mkdocs → zensical), CLAUDE.md, _toolbox prep |
| BUG_FIX | ~66 | Bug fixes (see "Bugs still present in upstream" below) |
| NEW_FEATURE | ~48 | Features not in upstream (see "Fork-only features" below) |
| REFACTOR | ~32 | Internal restructuring (most around FabricApiClient consolidation) |
| DBT_NATIVE_REWRITE | ~23 | Upstream patterns replaced with dbt-native mechanisms |
| ANTI_PATTERN_REMOVED | ~12 | atexit handlers, global state, dead code, exception swallowing |
| REVERT_OR_MODIFY | ~11 | Unwinds (mostly intra-batch — see "Revert chains" below) |

---

## Bugs still present in upstream (high-impact)

Each entry: fork commit hash, what was fixed, upstream evidence.
Source batch files in parentheses.

### Connection / driver layer

- **`bbfe064c`** (batch 00) — `test_schema.py` fixture uses `env_var('DBT_TEST_USER_1')` with no default; without env var, empty string interpolates into GRANT clause and crashes. Upstream still has no default.
- **`8bf38cf2`** (batch 01) — `FabricConnectionManager.get_response` returned hardcoded `message = "OK"` regardless of cursor messages. Upstream `fabric_connection_manager.py:746-748` still has `message = "OK"` — loses all Fabric-side warnings/notices.
- **`7b12ec6f`** (batch 01) — `_make_match_kwargs` override needed on `FabricAdapter` so case-sensitive Fabric DWHs work; default `SQLAdapter` impl lowercases identifiers. Upstream has no override → case-sensitive DWHs still broken.
- **`9c3ac010`** (batch 04) — `varchar(8000)` → `varchar(MAX)` across `FabricColumn.TYPE_LABELS`, `string_type`, `fabric__snapshot_hash_arguments`, `fabric__hash`. Upstream still defaults to `VARCHAR(8000)` → **silent data truncation** for any string > 8000 chars (hashes, surrogate keys, snapshot hash columns).
- **`fe3d3281`** (batch 04) — Added `pyodbc.odbcversion = "3.8"`. pyodbc's `pooling = True` silently no-ops without this; every connection is freshly created. Upstream sets `pooling` but never `odbcversion` → **pooling is effectively broken in upstream**.
- **`414835b`** (batch 07) — T-SQL bracket quoting with `]`→`]]` escaping across `FabricAdapter.quote()`, `FabricColumn.quoted`, `FabricRelation.quoted`, 5 macros (`columns.sql`, `alter_relation_add_remove_columns`, `get_use_database_sql`, `create_table_as`, `seeds/helpers.sql`). Upstream `fabric_adapter.py:37` is `"[{}]".format(identifier)` with no escaping → reserved-word columns silently break; identifiers containing `]` would terminate the bracket prematurely (**potential T-SQL injection vector**).
- **`f1c0a512`** (batch 09) — Default `add_query()` retries on `mssql_python.OperationalError`/`InternalError` up to 3 attempts. Upstream `fabric_connection_manager.py` has `retry_limit: int = 1` with no retryable exceptions → production users still see flaky `sys.tables`/`sys.columns` metadata queries.
- **`0a018f8`** (batch 07) — Migrated from `pyodbc` to Microsoft's native `mssql-python`. Upstream still uses `pyodbc` + ODBC Driver 18 → requires system-level driver install on every user machine.

### SQL / macro layer

- **`42063121`** (batch 02) — Rewrote `fabric__get_show_grant_sql` from `INFORMATION_SCHEMA.TABLE_PRIVILEGES` to `sys.database_principals` + `sys.database_permissions`. Upstream `apply_grants.sql` still uses the broken `INFORMATION_SCHEMA.TABLE_PRIVILEGES` query → misses Entra-principal grants → `apply_grants` re-issues the same GRANT on every run.
- **`dea31d36`** (batch 02) — `fabric__get_use_database_sql` wrapped in None-guard. Upstream `metadata.sql` macro has no None-guard → emits invalid `USE [None];` when called without database.
- **`9c9e8000`** (batch 03) — Removed `EXEC('CREATE TABLE ... AS ...')` wrapper in `fabric__create_table_as`. Upstream still wraps every CTAS in EXEC with manual single-quote escaping → silently breaks models with embedded apostrophes.
- **`62705a00`** (batch 02) — Added `materializations/hooks.sql` overriding `run_hooks` to drop the `commit;` Fabric DW can't execute. Upstream has no such override → **pre/post hooks fail at every run boundary** on upstream.
- **`f9f91e3f`** (batch 02) — Added `fabric__bool_or`. Upstream has no `bool_or.sql` → `dbt.bool_or` (used by dbt-utils) fails on upstream.
- **`aec6f06e`** (batch 01) — Deleted the duplicated `materialization clone, adapter='fabric'` from `clone.sql`. Upstream still has the full duplicate including the `TODO: support actual dispatch` comment.
- **`6cd55d6a`** (batch 06) — Removed dead `elif relation.type == 'table'` branch and `raise_not_implemented` else-branch in `fabric__get_drop_sql`. Upstream still has both → the else-branch prevents dropping function relations.
- **`4ab425e7`** (batch 06) — `fabric__create_or_replace_clone` now drops pre-existing clone. Upstream's macro doesn't drop, so calling it directly (as `BaseClonePossible` does) fails.
- **`257c8999`** (batch 06) — Replaced incremental drop-and-recreate with intermediate/backup swap. Upstream `incremental.sql` still drops the target before re-creating → **data loss if creation fails**.
- **`955ab2e3`** (batch 04) — `fabric__get_incremental_microbatch_sql` upserts via `get_incremental_merge_sql` when `unique_key` is set. Upstream still always does delete+insert.

### Community package layer

- **`3185d5ee`** (batch 10) — dbt-utils sweep: `split_part` (T-SQL `STRING_SPLIT` is single-char-only → REPLACE→CHAR(1) trick), `sequential_values` missing var, `mutually_exclusive_ranges` boolean literals + non-deterministic window, `relationships_where` full rewrite, new `equal_rowcount`/`fewer_rows_than` overrides with COALESCE for NULL-from-FULL-JOIN. Upstream `fabric__split_part` (`dbt/include/fabric/macros/utils/split_part.sql`) still has the single-char bug; the other overrides don't exist upstream.
- **`52572266`** (batch 10) — dbt-audit-helper 0.13.0 macro overrides fix: `compare_queries` (limit/OFFSET/FETCH), `compare_column_values` (CASE order: missing-row before both-null), `compare_relation_columns` (INFORMATION_SCHEMA → sys.columns/objects/types; `run_query()` separates metadata query so sys.* doesn't run inside materialized SQL Fabric distributed mode rejects), `compare_all_columns` (positional GROUP BY, ORDER BY in CTEs), new `compare_which_query_columns_differ` (CROSS APPLY VALUES instead of CTE inside subquery). Upstream `fabric` audit-helper overrides are pre-0.13.0 and contain all of the above.
- **`9eae9aee`** (batch 03) — Rewrote `fabric__split_part` to compute both forward/backward indices. Previous version literally referenced bare identifiers `parts` / `split_on` instead of macro args. Upstream later fixed this in commit `eddd1b1`, but the fork beat them to it.

### Fork-only API client / Livy layer

These bugs only exist in the fork because the underlying feature (FabricApiClient,
Livy, Python models) doesn't exist upstream — but they're notable as evidence that
the fork's tests are catching real bugs the upstream pattern wouldn't surface.

- **`76c4a4f8`** (batch 05) — Added 429 rate-limit handling via `_api_request` helper. Upstream's `warehouse_snapshots.py` only does `raise_for_status()` → throttling vulnerability for snapshot ops.
- **`412b4732`** (batch 05) — Implemented real `delete_warehouse_snapshot`. **Upstream's `delete_warehouse_snapshot(snapshot_id)` is `return True` as a stub** — pretends to delete, does nothing.
- **`8060d37f`** (batch 09) — Fixed 4 URL paths from `warehousesnapshots` (lowercase) → `warehouseSnapshots` (camelCase). Caught by writing unit tests for `FabricApiClient` (TEST commit exposed real BUG in same PR).
- **`e317baa1`** (batch 06) — Three Livy session bugs: (1) lookup read wrong JSON key (`"value"` vs `"items"`) → session reuse never worked; (2) missing thread lock → N concurrent threads created N sessions; (3) too-short polling timeouts.
- **`47b4510f`** (batch 04) — Multi-scope token cache (`dict` by scope vs single global). Earlier single-cache served the wrong token to the wrong consumer.
- **`bff925e8`** (batch 09) — Detect fatal Livy session states (`dead`/`killed`/`error`/`shutting_down`) instead of waiting full timeout. Caught by writing unit tests.
- **`25faac00`** (batch 09) — `FabricSparkCursor.__exit__` returned `True` (silent exception swallowing) — same anti-pattern critiqued in upstream. Caught by writing PEP 249 compliance tests.
- **`5a60ef1c`** (batch 09) — `FabricSparkAdapter` forgot to bind `Column = FabricSparkColumn`; MRO fell back to `SparkColumn` returning PG-style `character varying(N)` → all snapshots failed.

---

## Anti-patterns removed (matching the PR critique)

### `atexit` handlers + global state for warehouse snapshots
- **`7fccebe7`** (batch 05) — DBT_NATIVE_REWRITE — replaced upstream's `import atexit` / `_snapshot_manager = None` global / `atexit.register(lambda: _run_end_action(result))` with macro → `@available` adapter method → user-controlled `on-run-start`/`on-run-end` hooks.
- **Upstream evidence:** `upstream/main:dbt/adapters/fabric/fabric_connection_manager.py` still has `import atexit` (line 1), `_init_done = False` / `_snapshot_manager = None` / `_init_lock = threading.Lock()` (lines 45-47), and `atexit.register(...)` at line 602.

### Module-level mutable token global
- **`c8be16a1`** (batch 03) — ANTI_PATTERN_REMOVED — extracted module-level `_TOKEN: Optional[AccessToken] = None` global into `FabricTokenProvider` class with per-credential instance caching.
- **Upstream evidence:** `upstream/main:dbt/adapters/fabric/fabric_connection_manager.py` still has `_TOKEN: Optional[AccessToken] = None` at module scope, `AZURE_AUTH_FUNCTIONS` mapping at module scope, and `global _TOKEN` inside `get_pyodbc_attrs_before_credentials`.

### Custom `add_query` reimplementation
- **`2211d4e1`** (batch 06) — DBT_NATIVE_REWRITE — deleted the custom `add_query` (manually firing `ConnectionUsed`/`SQLQuery`/`SQLQueryStatus` events, re-implementing the cursor binding loop) and replaced with thin override delegating to `SQLConnectionManager.add_query`.
- **Upstream evidence:** Upstream still has the entire custom `add_query` (~line 630+).

### Spurious `log()` call on every macro invocation
- **`5226156539`** (batch 06) — ANTI_PATTERN_REMOVED — removed `{{ log(config.get('query_tag','dbt-fabric')) }}` debug leftover that fired on every SQL statement.
- **Upstream evidence:** Upstream `fabric__apply_label` still has the log call → spams dbt logs on every macro invocation.

### `apply_label()` helper and 2-statement snapshot merge
- **`0857efc1`** (batch 09) — ANTI_PATTERN_REMOVED — removed `apply_label()` helper and all callers across 7 files; deleted custom `fabric__snapshot_merge_sql` (30-line UPDATE+INSERT) so dbt falls through to native MERGE.
- **Upstream evidence:** Upstream still has `apply_label()` across `catalog.sql`, `columns.sql`, `metadata.sql`, `relation.sql`, `merge.sql`; still has UPDATE+INSERT snapshot merge.

### Dead code from sibling-project ancestry
- **Thrift exception handling** in upstream `microsoft/dbt-fabricspark/connections.py:102-114` references `thrift_resp.status.errorMessage` — Apache Thrift pattern from dbt-spark; the FabricSpark adapter talks Livy over HTTP, the path is dead.
- **AWS logging config** in upstream `connections.py:42-50` sets `botocore`/`boto3` to DEBUG at import time — leftover from a Spark/Databricks ancestor.
- **Hardcoded 2028 timestamp** at upstream `livysession.py:184` — `expires_on = 1845972874` for the `int_tests` auth path bypasses all token-refresh logic.
- **`_parse_retry_after`** duplicated verbatim between upstream `livysession.py:370` and `mlv_api.py:141`, both using deprecated `datetime.utcnow()`. The `_getLivySQL` regex-bug helper is duplicated the same way between `singleton_livy.py:488` and `concurrent_livy.py:555`.
- **`get_headers(... tokenPrint=False)`** at upstream `livysession.py:328` logs the full bearer token when `True`.
- **Six `__exit__` methods return `True`** across upstream `singleton_livy.py:55`, `concurrent_livy.py:125/347/634`, etc. — silent exception swallowing.
- **Regex bug** in upstream `_getLivySQL` passes `re.DOTALL` (integer 16) as positional `count` arg → comment-stripping silently capped to 16 replacements per file.

---

## dbt-native rewrites (replacing upstream patterns with dbt mechanisms)

- **`7fccebe7`** (batch 05) — Warehouse snapshots via `on-run-start`/`on-run-end` hooks instead of `atexit` (see above).
- **`257c8999`** (batch 06) — Incremental: `make_intermediate_relation` + `make_backup_relation` + `rename_relation` swap pattern instead of drop-and-recreate.
- **`2211d4e1`** (batch 06) — Connection manager delegates to `SQLConnectionManager.add_query` instead of reimplementing it.
- **`62705a00`** (batch 02) — Run hooks override that drops `commit;` (dbt-adapters default emits it).
- **`80caf6df`** (batch 02) — Test harness's `get_tables_in_schema` uses T-SQL `sys.tables` + `sys.views` instead of `INFORMATION_SCHEMA.TABLES`.
- **`aec6f06e`** (batch 01) — Removed duplicate `materialization clone` block; lets dbt's default materialization handle dispatch.
- **`54e0f0d9`** (batch 03) — Replaced `adapter.get_relation(...)` with dbt-native `load_cached_relation(this)` in `table.sql` (saves per-model metadata round-trip).
- **`eb4f0d69`** (batch 03) — Replaced bespoke `__dbt_tmp_vw` flow with dbt-native `make_intermediate_relation` / `make_backup_relation` / `drop_relation_if_exists` pattern.
- **`201c83fa`** (batch 03) — Replaced 31-line PG-style CTE-bomb `fabric__generate_series` with single `select value as generated_number from generate_series(1, ...)` using Fabric's native table function.
- **`00d791ff`** (batch 03) — Deleted 114-line `fabric__date_spine_sql` + `fabric__date_spine` pair; replaced with 35-line version that delegates to `dbt.generate_series` + `dbt.get_intervals_between` + `dbt.dateadd`.
- **`0857efc1`** (batch 09) — Snapshot merge via native `default__snapshot_merge_sql` instead of custom UPDATE+INSERT.
- **`0e779bdc`** (batch 04) — Split polymorphic `get_token` into explicit `get_api_token()` / `get_sql_token(scope=None)`.
- **`f6a30e98`** (batch 10) — FabricSpark default materialization reverted from `materialized_view` to dbt's standard `view` (now possible because `#234` added view support).
- **`b32853b`** (batch 07) — FabricSpark `get_catalog` delegates to `BaseAdapter.get_catalog` (SparkAdapter's per-database queries don't fit Fabric's workspace/lakehouse/schema layout).
- **`b645e7a`** (batch 07) — Stopped pretending there's a custom `auto` authentication mode; default now `ActiveDirectoryDefault` (the actual mssql-python value).
- **`e134bdbf`** (batch 00) — Collapsed five hand-rolled profile variants + marker-driven autouse `skip_by_profile_type` (~100 LOC of indirection) into single env-var-driven fixture.

---

## Fork-only features (not in either upstream adapter)

### Customer-facing

- **Microsoft Purview integration** — `c181357d` (batch 09). `PurviewClient` + `PurviewSync` + `purview_types.py`, `purview_sync()` macro for both Fabric DW and FabricSpark, custom Purview type definitions, `persist_docs` integration, lineage graph, stale-lineage cleanup. Plus `0eea9621` extending to Lakehouse. ~4400 LOC subsystem.
- **Python models on Fabric DW** — scaffolded `3eec89f3` (batch 03), completed `830ae67e` (batch 05). End-to-end Livy + synapsesql connector. Upstream has zero Python-model support in the `fabric` adapter.
- **Statistics config** — `a9246e99` (batch 09). `statistics` + `statistics_sample_percent` model configs across table/incremental/snapshot.
- **CLUSTER BY model config** — `b24bdb3` (batch 07). Standard model config like Snowflake/BigQuery, with bracket-quoting + `]→]]` escaping.
- **Catalog row-count statistics** — `a3f0dc7` (batch 07). `objectpropertyex(tv.object_id, 'Cardinality')` populates `stats:row_count:*` columns in `dbt docs generate` output.
- **dbt-external-tables OPENROWSET support** — `6434e2d8` (batch 09). 187-line macro file + 229-line docs + integration tests.
- **Scalar functions (dbt 1.11 UDFs)** — `9a136583` (batch 06), default args `2c96f574`. `function` relation type + four macros.
- **Auto host-resolution from workspace name** — `a1f32a80` (batch 04). Workspace name → REST → SQL endpoint without portal lookup.
- **High-concurrency Livy session reuse** — `e25ee599` (batch 10). HC API so each dbt thread gets its own REPL slot in a shared Spark session.
- **Cross-workspace 4-part naming (FabricSpark)** — `6106cf0a` (batch 10). `workspace_name` model config → `workspace.lakehouse.schema.table`.
- **Spark SQL view support (FabricSpark)** — `53ee818c` (batch 10). First-class view materialization, enables dbt-native default.
- **Configurable Fabric API base URLs** (`fabric_base_api_uri`/`powerbi_base_api_uri`) — `6a18ea77` (batch 05) + `e7f23bb9` (batch 10). Non-prod tenant support (MSIT).

### Authentication

- **`workload_identity` auth** — `c29e9b56` (batch 09). Federated OIDC via `ClientAssertionCredential`; supports HTTP URL token source or file path.
- **`token_credential` auth** — `ee83a005` (batch 09). User-supplied `azure.core.credentials.TokenCredential` by dotted import path with kwargs.
- **`FabricTokenProvider`** class — `c8be16a1` (batch 03), API/SQL split `0e779bdc` (batch 04), workspace_name support `1d276c76` (batch 04), SP-for-API support `69231eb0` (batch 04). 10 auth methods across one provider.

### Architecture

- **FabricSpark adapter** — bootstrapped `fd6402f4` + `03094937` (batch 06). Inherits from `dbt-spark`. Microsoft has no equivalent in the `microsoft/dbt-fabricspark` repo's relationship to dbt-spark (standalone `SQLAdapter`).
  - View support (`53ee818c`), incremental (`dc6c24c9`), snapshot (`4ba1a275`), clone (`682cd721`), persist_docs (`f567b7c6`), materialized lake views (`1678fdc` + `df44b2d`), 4-part naming (`6106cf0a`), cross-workspace quote/include policies (`c39d9acb`).
- **Shared `BaseFabricCredentials` / `BaseFabricConnectionManager` / `BaseFabricAdapter`** — extracted `03094937` (batch 06). Multiple inheritance lets `FabricSparkAdapter` extend both `SparkAdapter` and `BaseFabricAdapter`.
- **`FabricApiClient`** — extracted `f63cebfe` (batch 04), refactored to instance class `af65b5e3` (batch 05). One REST client across both adapters: workspaces, warehouses, lakehouses, Livy, snapshots, Purview.
- **Community package compatibility** — initial import `6fe3b9e3` (batch 01); namespace fixes `accc0761`/`3133debf` (batch 03); dbt-utils refresh `3185d5ee`, audit-helper 0.13 `52572266`, dbt-expectations/profiler `3bb7b174`/`b2ac1d61` (batch 10). 9 packages: dbt-utils, dbt-date, dbt-codegen, dbt-expectations, dbt-audit-helper, dbt-external-tables, dbt-profiler, dbt-artifacts, dbt-project-evaluator. Upstream has zero `dbt_package_support/` tree.

---

## Tests that exposed real bugs (TEST → BUG_FIX in the same PR)

This pattern is direct evidence that the dbt-tests-adapter coverage is doing real work.

- **`8060d37f`** (batch 09) — Writing unit tests for `FabricApiClient` exposed wrong-cased URL paths (`warehousesnapshots` vs `warehouseSnapshots`) in 4 warehouse-snapshot operations. Fixed in same PR.
- **`25faac00`** (batch 09) — Writing PEP 249 compliance tests exposed `FabricSparkCursor.__exit__` returning `True` (silent exception swallowing).
- **`bff925e8`** (batch 09) — Writing LivySession unit tests led to detecting fatal session states immediately instead of waiting full timeout.
- **`5a60ef1c`** (batch 09) — Snapshot tests on FabricSpark exposed missing `Column = FabricSparkColumn` binding → all snapshots failed with `character varying` type error.
- **`3185d5ee`** (batch 10) — Switching dbt-utils integration test to `dbt build` exposed bugs in `sequential_values`, `mutually_exclusive_ranges`, `relationships_where`, `split_part`, etc.
- **`52572266`** (batch 10) — Adding dbt-audit-helper 0.13.0 integration tests exposed multiple T-SQL-incompatible patterns in the existing overrides.
- **`fa771d39`** (batch 10) — Adding FabricSpark dbt-utils tests exposed that `spark__escape_single_quotes` (dbt-spark) uses backslash escapes broken on Fabric Lakehouse.
- **`c9b6537e`** (batch 10) — Adding dbt-date integration tests exposed multiple macro bugs, motivated dim_date overrides and new `expression_is_true` signature.
- **`3bb7b174`** (batch 10) — Adding dbt-expectations integration tests exposed type bugs (T-SQL `timestamp` is `rowversion`) and CTE-scoping bugs.
- **`b2ac1d61`** (batch 10) — Adding dbt-profiler integration tests exposed package was effectively unusable on Fabric (no fabric overrides existed).

---

## Notable transformation arcs (cross-batch evolution stories)

### `_TOKEN` global → `FabricTokenProvider` → `get_api_token` / `get_sql_token` split
Module global → class → semantic API.
- `c8be16a1` (batch 03) extracts `_TOKEN` global into `FabricTokenProvider` class
- `47b4510f` (batch 04) adds multi-scope cache (dict by scope vs single)
- `9d65b372` → `9fed7d65` (revert) → `0e779bdc` (batch 04) — flag-based pyodbc gating tried, reverted, replaced with named `get_api_token` / `get_sql_token`
- `69231eb0` (batch 04) — SP token support for Python REST flows
- `bb376b06` → `8c3dbabb` → `772d2100` → `160463ac` (batch 04) — series of small fixes to scope-selection logic as the multi-scope / multi-auth path stabilized

### Python models on Fabric DW
Scaffolding → working end-to-end → high-concurrency.
- `3eec89f3` (batch 03) — first `FabricLivyHelper` scaffolding
- `799d09a3` (batch 04) — workspace_id + REST `get_warehouse_connection_string`
- `a1f32a80` (batch 04) — workspace_name resolution
- `6277687f` (batch 05) — lakehouse_name resolution
- `830ae67e` (batch 05) — complete Python support (`generate_python_submission_response`, synapsesql endpoint injection, unskipped Python tests)
- `95ab823b` (batch 05) — session reuse via existing-session lookup
- `e317baa1` (batch 06) — fixed wrong JSON key (`"value"` vs `"items"`) + threading lock for session reuse
- `5df6de74` (batch 10) — fire-and-forget JVM GC after synapsesql writes (JDBC schema-lock workaround)
- `e25ee599` (batch 10) — replaced singleton `LivySession` with `HighConcurrencyLivySession` using Fabric's HC Livy API
- `2aa33835` (batch 10) — promoted JVM GC from fire-and-forget to awaited

### Warehouse snapshots: atexit → on-run-end hooks
- `7fccebe7` (batch 05) — initial `create_or_update_fabric_warehouse_snapshot` macro + `@available` adapter method
- `76c4a4f8` (batch 05) — added 429 rate limiting
- `412b4732` (batch 05) — completed `delete_warehouse_snapshot` + description support
- `8060d37f` (batch 09) — fixed URL casing exposed by unit tests

### FabricApiClient consolidation
- `799d09a3` (batch 04) — initial REST integration in connection manager
- `f63cebfe` (batch 04) — extracted `FabricApiClient` with class-level cache
- `af65b5e3` (batch 05) — refactored to proper instance class with `create()` factory
- `76c4a4f8` (batch 05) — `_api_request` helper centralising every REST call with 429 handling
- `be106c92` (batch 09) — fixed cross-adapter singleton pollution (the fixture no longer caches anything on the connection manager)

### FabricSpark adapter
- `fd6402f4` (batch 06) — scaffolds adapter with `[spark]` optional extra, splits tests
- `03094937` (batch 06) — initial working adapter, extracts shared base classes
- `c9dc049` (batch 07) — `FabricSparkRelationType` + materialized lake views
- `41f2bf0` (batch 07) — 3-part `workspace.database.schema` catalog
- `1678fdc` (batch 07) — full materialized_view materialization
- `81ec0e7` … `c39d9acb` (batch 09) — quote/include policies for 3-part naming
- `dc6c24c9` (batch 09) — full incremental materialization
- `4ba1a275` (batch 09) — snapshot materialization
- `682cd721` (batch 09) — clone materialization
- `f567b7c6` (batch 09) — persist_docs
- `53ee818c` (batch 10) — view support
- `f6a30e98` (batch 10) — default materialization → `view` (dbt-native)
- `6106cf0a` (batch 10) — cross-workspace 4-part naming

### pyodbc → mssql-python migration
- `e51b3bec` (batch 05) — first mssql-python Docker stage in CI
- `0a018f8` (batch 07) — replaces pyodbc throughout adapter, removes ODBC driver dependency
- `9f986a92` (batch 09) — removes the custom Docker container entirely from CI; just installs `libltdl7` on ubuntu-latest

### dbt-spark inheritance for FabricSpark
- `fd6402f4` (batch 06) — adds `[spark]` extra so `dbt-spark` is the optional dependency
- `03094937` (batch 06) — `FabricSparkAdapter(BaseFabricAdapter, SparkAdapter)` via Python multiple inheritance
- subsequent commits inherit Spark macros and only override Fabric-specific behaviour

---

## Revert / modify chains

Most reverts are **intra-batch** — author's own iteration within the same PR.
Listed here so we don't double-count in the PR_DESCRIPTION.

### Intra-batch reverts (resolved within the same batch)

- **Batch 01:** `48afd75b` reverts `27575d53` (pytest-cov add).
- **Batch 01:** `cd8e63b7` supersedes `58d6f377` (datetime2 fix moved from macro override to `FabricColumn.data_type` property).
- **Batch 02:** `0f1422c3` inlines what `07db1102` added as external SQL files.
- **Batch 03:** `cf9026c5` → `faaa1dd4` (revert) → `accc0761` (minimal re-do) — namespace prefix removal.
- **Batch 04:** `9d65b372` → `9fed7d65` (revert) → `0e779bdc` (rewrite as two named methods) — pyodbc-token gating.
- **Batch 04:** `8c3dbabb` → `772d2100` (fix scope attr typo).
- **Batch 04:** `bb376b06` → `160463ac` (fix authentication attr typo).
- **Batch 04:** `df1b5b6c` → `73a8c9af` (corrected `get_merge_sql` to `get_incremental_merge_sql`).
- **Batch 05:** `b9d47abd` reverts `a8110438` (Debian bump in CI).
- **Batch 05:** `292b6fd4` partially reverts `8c854a49` (drop Python 3.14 from matrix).
- **Batch 05:** `bdc83cfa` rolls back the Swetrix snippet from `22998e1d`.
- **Batch 06:** `b0c35576` re-adds skip removed by `257c8999` (restored skip on `TestPySparkTestsFabric` only — the swap pattern remained).
- **Batch 06:** `2c96f574` → `2b6110aa` (fix `arg.default_value` lookup using `.get()`).
- **Batch 06:** `643330cb` → `a06a2e27` (fix mutable default `dict | None = {}` → `field(default_factory=dict)`).
- **Batch 07:** `4a4b6d9` → `1a7207b` (mssql-python sqltype prep reverted — planned upstream change did not land).
- **Batch 07:** `5a94f78` → `546fdad` (Python 3.14 requires-python reverted).
- **Batch 07:** `044e4d7` → `fb31c03` (Python 3.14 CI matrix reverted).
- **Batch 08:** `b59495b2` → `4e33f587` (revert) → `81e0bdf9` (re-apply via PR) — null_compare test fix; net no-op of net no-op (accidental direct-to-main commit cleaned up via PR).
- **Batch 09:** `6aa023c8` (singleton-caching Livy fixture) → `be106c92` (revoked the singleton caching due to cross-adapter pollution) → `7f91d041` (fixed missing auth fields).
- **Batch 09:** `1e9d9b70` + `50a06bec` — upstream/main merge using `ours` strategy (records merge parent without changing fork's code; upstream features either already in fork or judged inferior).
- **Batch 10:** `bf45c646` reverts `f37190a8` (DE timeout bump rolled back).
- **Batch 10:** `21cc97e3` (isolated-test item-name fix) → `c573af2f` (whole --isolated infrastructure removed).
- **Batch 10:** The HC session pooling PR (`95bd9a1e` / #268) is a self-contained story — pool was built, then dropped within the same PR because atexit drain duplicated the upstream anti-pattern this fork critiques.

### Intra-batch self-corrections (no net change)
- **Batch 03:** `3eec89f3` (Python-model scaffolding) → `9fe0a7aa` (drop unused arg from `py_write_table` call).
- **Batch 03:** `2835a76e` (added several macros) → `a8fe7e4f` (removed spurious `self` parameter from fixture).
- **Batch 06:** `e51b3bec` (mssql-python Docker stage) → `e31a0094` (fixed missing line continuation).

### Cross-batch (intentional supersessions, not reverts)

- **`58d6f377`** (batch 01, macro override) is superseded by **`cd8e63b7`** (same batch, Python property) — datetime2 normalisation moved up the stack.
- **`6aa023c8`** (batch 09, Livy session lifecycle fixture) was tightened over the next two commits; the surrounding singleton-caching approach was later abandoned in favour of per-adapter clients.
- **`257c8999`** (batch 06, incremental swap pattern + unskipped Python tests) — the swap pattern remained; only the test re-skip was reverted in `b0c35576`.

---

## Per-batch detail

| Batch | Range | Commits | File |
|---|---|---:|---|
| 00 | 2025-03-26 to 2025-03-29 | 46 | `analysis_00.md` |
| 01 | 2025-03-29 to 2025-04-03 | 46 | `analysis_01.md` |
| 02 | 2025-04-03 to 2025-04-05 | 46 | `analysis_02.md` |
| 03 | 2025-04-05 to 2025-04-07 | 46 | `analysis_03.md` |
| 04 | 2025-04-07 to 2025-10-05 | 46 | `analysis_04.md` |
| 05 | 2025-10-05 to 2026-02-17 | 46 | `analysis_05.md` |
| 06 | 2026-02-20 to 2026-02-24 | 46 | `analysis_06.md` |
| 07 | 2026-02-24 to 2026-05-14 | 46 | `analysis_07.md` |
| 08 | 2026-05-14 to 2026-05-15 | 46 | `analysis_08.md` |
| 09 | 2026-05-15 to 2026-05-16 | 46 | `analysis_09.md` |
| 10 | 2026-05-16 to 2026-05-18 | 46 | `analysis_10.md` |
| 11 | 2026-05-18 (single day, all DOCS) | 40 | `analysis_11.md` |

Each batch file contains per-commit entries with hash, date, category, message,
what changed, why, upstream comparison, and same-batch revert notes.
