# Fork analysis: dbt-fabric-samdebruyn vs microsoft/dbt-fabric

A complete record of every Sam-authored commit on the fork since divergence
from `microsoft/dbt-fabric`. The top of this document indexes the high-impact
findings; the chronological log at the bottom has every commit with the
upstream comparison.

## Scope

- **Fork start:** 2025-03-26 (commit `99b9986` "part 1 of project modernization")
- **Latest analysed commit:** 2026-05-18 (commit `f19e22c`)
- **Commits ahead of `upstream/main`:** 572 total (546 Sam-authored + 26 dependabot)
- **Coverage:** every Sam-authored commit, classified
- **Method:** walked every commit, classified into
  `BUG_FIX` / `DBT_NATIVE_REWRITE` / `ANTI_PATTERN_REMOVED` / `NEW_FEATURE` /
  `TEST` / `INFRA` / `DOCS` / `REFACTOR` / `REVERT_OR_MODIFY` and verified
  upstream state with `git show upstream/main:<path>` where applicable.

> **Upstream verification:** every "Bugs still present in upstream" and
> "Anti-patterns removed" claim below was re-verified against fresh clones of
> `microsoft/dbt-fabric` (HEAD `0de2190`, v1.10.0) and
> `microsoft/dbt-fabricspark` (HEAD `d315a56`) on 2026-05-18. File:line
> references point at upstream HEAD at that time.

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
| REVERT_OR_MODIFY | ~11 | Unwinds (mostly intra-PR — see "Revert chains" below) |

---

## Bugs still present in upstream (high-impact)

Each entry: fork commit hash, what was fixed, upstream evidence.

### Connection / driver layer

- **`bbfe064c`** — `test_schema.py` fixture uses `env_var('DBT_TEST_USER_1')` with no default; without env var, empty string interpolates into GRANT clause and crashes. Upstream `tests/functional/adapter/dbt_show_test.py` / `test_schema.py` fixtures still have no default.
- **`8bf38cf2`** — `FabricConnectionManager.get_response` returned hardcoded `message = "OK"` regardless of cursor messages. Upstream `dbt/adapters/fabric/fabric_connection_manager.py:748` still has `message = "OK"` — loses all Fabric-side warnings/notices and the distributed statement ID emitted on `cursor.messages`.
- **`7b12ec6f`** — `_make_match_kwargs` override needed on `FabricAdapter` so case-sensitive Fabric DWHs work; default `SQLAdapter` impl lowercases identifiers. Upstream `dbt/adapters/fabric/fabric_adapter.py` has no `_make_match_kwargs` override → case-sensitive DWHs still broken.
- **`9c3ac010`** — `varchar(8000)` → `varchar(MAX)` across `FabricColumn.TYPE_LABELS`, `string_type`, `fabric__snapshot_hash_arguments`, `fabric__hash`. Upstream `dbt/adapters/fabric/fabric_column.py` `TYPE_LABELS` still maps `STRING → VARCHAR(8000)` → **silent data truncation** for any string > 8000 chars (hashes, surrogate keys, snapshot hash columns).
- **`fe3d3281`** — Added `pyodbc.odbcversion = "3.8"`. pyodbc's `pooling = True` silently no-ops without this; every connection is freshly created. Upstream `dbt/adapters/fabric/fabric_connection_manager.py:571` sets `pyodbc.pooling = credentials.pooling if credentials.pooling is not None else True` but `odbcversion` is never set anywhere in the package → **pooling is effectively broken in upstream**.
- **`414835b`** — T-SQL bracket quoting with `]`→`]]` escaping across `FabricAdapter.quote()`, `FabricColumn.quoted`, `FabricRelation.quoted`, 5 macros (`columns.sql`, `alter_relation_add_remove_columns`, `get_use_database_sql`, `create_table_as`, `seeds/helpers.sql`). Upstream `dbt/adapters/fabric/fabric_adapter.py:37-38` is `def quote(cls, identifier): return "[{}]".format(identifier)` with no escaping → reserved-word columns silently break; identifiers containing `]` would terminate the bracket prematurely (**potential T-SQL injection vector**).
- **`f1c0a512`** — Default `add_query()` retries on `mssql_python.OperationalError`/`InternalError` up to 3 attempts. Upstream `dbt/adapters/fabric/fabric_connection_manager.py` has `retry_limit: int = 1` on `FabricConnectionManager` and no `retryable_exceptions` list → production users still see flaky `sys.tables`/`sys.columns` metadata queries (the original symptom that motivated upstream's parallel `list_relations_without_caching` retry in v1.9.10).
- **`0a018f8`** — Migrated from `pyodbc` to Microsoft's native `mssql-python`. Upstream `pyproject.toml` still lists `pyodbc` and the connection manager still imports it → requires system-level ODBC Driver 18 install on every user machine.

### SQL / macro layer

- **`42063121`** — Rewrote `fabric__get_show_grant_sql` from `INFORMATION_SCHEMA.TABLE_PRIVILEGES` to `sys.database_principals` + `sys.database_permissions`. Upstream `dbt/include/fabric/macros/adapters/apply_grants.sql:5` still uses `INFORMATION_SCHEMA.TABLE_PRIVILEGES` → misses Entra-principal grants → `apply_grants` re-issues the same GRANT on every run.
- **`dea31d36`** — `fabric__get_use_database_sql` wrapped in None-guard. Upstream `dbt/include/fabric/macros/adapters/metadata.sql` `fabric__get_use_database_sql` has no None-guard → emits invalid `USE [None];` when called without database.
- **`9c9e8000`** — Removed `EXEC('CREATE TABLE ... AS ...')` wrapper in `fabric__create_table_as`. Upstream `dbt/include/fabric/macros/materializations/models/table/create_table_as.sql:31,33` still wraps every CTAS in `EXEC('CREATE TABLE ... AS ...')` with manual single-quote escaping → silently breaks models with embedded apostrophes.
- **`62705a00`** — Added `materializations/hooks.sql` overriding `run_hooks` to drop the `commit;` Fabric DW can't execute. Upstream has no `dbt/include/fabric/macros/materializations/hooks.sql` → dbt-adapters' default `run_hooks` runs unchanged and emits `commit;` → **pre/post hooks fail at every run boundary** on upstream.
- **`f9f91e3f`** — Added `fabric__bool_or`. Upstream has no `dbt/include/fabric/macros/utils/bool_or.sql` → `dbt.bool_or` (used by dbt-utils) fails on upstream.
- **`aec6f06e`** — Deleted the duplicated `materialization clone, adapter='fabric'` from `clone.sql`. Upstream `dbt/include/fabric/macros/materializations/models/table/clone.sql:11` still has a second `materialization clone, adapter='fabric'` block including the `TODO: support actual dispatch` comment.
- **`6cd55d6a`** — Removed dead `elif relation.type == 'table'` branch and `raise_not_implemented` else-branch in `fabric__get_drop_sql`. Upstream `dbt/include/fabric/macros/adapters/relation.sql` `fabric__get_drop_sql` still has both → the else-branch prevents dropping function relations.
- **`4ab425e7`** — `fabric__create_or_replace_clone` now drops pre-existing clone. Upstream's macro doesn't drop, so calling it directly (as `BaseClonePossible` does) fails.
- **`257c8999`** — Replaced incremental drop-and-recreate with intermediate/backup swap. Upstream `dbt/include/fabric/macros/materializations/models/incremental/incremental.sql:30-34` still calls `adapter.drop_relation(target_relation)` before re-creating → **data loss if creation fails**.
- **`955ab2e3`** — `fabric__get_incremental_microbatch_sql` upserts via `get_incremental_merge_sql` when `unique_key` is set. Upstream `fabric__get_incremental_microbatch_sql` still always does delete+insert regardless of `unique_key`.

### Community package layer

- **`3185d5ee`** — dbt-utils sweep: `split_part` (T-SQL `STRING_SPLIT` is single-char-only → REPLACE→CHAR(1) trick), `sequential_values` missing var, `mutually_exclusive_ranges` boolean literals + non-deterministic window, `relationships_where` full rewrite, new `equal_rowcount`/`fewer_rows_than` overrides with COALESCE for NULL-from-FULL-JOIN. Upstream `fabric__split_part` (`dbt/include/fabric/macros/utils/split_part.sql`) still has the single-char bug; the other overrides don't exist upstream.
- **`52572266`** — dbt-audit-helper 0.13.0 macro overrides fix: `compare_queries` (limit/OFFSET/FETCH), `compare_column_values` (CASE order: missing-row before both-null), `compare_relation_columns` (INFORMATION_SCHEMA → sys.columns/objects/types; `run_query()` separates metadata query so sys.* doesn't run inside materialized SQL Fabric distributed mode rejects), `compare_all_columns` (positional GROUP BY, ORDER BY in CTEs), new `compare_which_query_columns_differ` (CROSS APPLY VALUES instead of CTE inside subquery). Upstream `fabric` audit-helper overrides are pre-0.13.0 and contain all of the above.
- **`9eae9aee`** — Rewrote `fabric__split_part` to compute both forward/backward indices. Previous version literally referenced bare identifiers `parts` / `split_on` instead of macro args. Upstream later fixed this in commit `eddd1b1`, but the fork beat them to it.

### Fork-only API client / Livy layer

These bugs only exist in the fork because the underlying feature (FabricApiClient,
Livy, Python models) doesn't exist upstream — but they're notable as evidence that
the fork's tests are catching real bugs the upstream pattern wouldn't surface.

- **`76c4a4f8`** — Added 429 rate-limit handling via `_api_request` helper. Upstream `dbt/adapters/fabric/warehouse_snapshots.py` only does `raise_for_status()` → throttling vulnerability for snapshot ops.
- **`412b4732`** — Implemented real `delete_warehouse_snapshot`. **Upstream `dbt/adapters/fabric/warehouse_snapshots.py:307-309` `delete_warehouse_snapshot(snapshot_id)` is `return True` as a stub** — pretends to delete, does nothing.
- **`8060d37f`** — Fixed 4 URL paths from `warehousesnapshots` (lowercase) → `warehouseSnapshots` (camelCase). Caught by writing unit tests for `FabricApiClient` (TEST commit exposed real BUG in same PR).
- **`e317baa1`** — Three Livy session bugs: (1) lookup read wrong JSON key (`"value"` vs `"items"`) → session reuse never worked; (2) missing thread lock → N concurrent threads created N sessions; (3) too-short polling timeouts.
- **`47b4510f`** — Multi-scope token cache (`dict` by scope vs single global). Earlier single-cache served the wrong token to the wrong consumer.
- **`bff925e8`** — Detect fatal Livy session states (`dead`/`killed`/`error`/`shutting_down`) instead of waiting full timeout. Caught by writing unit tests.
- **`25faac00`** — `FabricSparkCursor.__exit__` returned `True` (silent exception swallowing) — same anti-pattern critiqued in upstream. Caught by writing PEP 249 compliance tests.
- **`5a60ef1c`** — `FabricSparkAdapter` forgot to bind `Column = FabricSparkColumn`; MRO fell back to `SparkColumn` returning PG-style `character varying(N)` → all snapshots failed.

---

## Anti-patterns removed (matching the PR critique)

### `atexit` handlers + global state for warehouse snapshots
- **`7fccebe7`** — DBT_NATIVE_REWRITE — replaced upstream's `import atexit` / `_snapshot_manager = None` global / `atexit.register(lambda: _run_end_action(result))` with macro → `@available` adapter method → user-controlled `on-run-start`/`on-run-end` hooks.
- **Upstream evidence:** `upstream/main:dbt/adapters/fabric/fabric_connection_manager.py` still has `import atexit` (line 1), `_init_done = False` / `_snapshot_manager = None` / `_init_lock = threading.Lock()` (lines 45-47), and `atexit.register(...)` at line 602.

### Module-level mutable token global
- **`c8be16a1`** — ANTI_PATTERN_REMOVED — extracted module-level `_TOKEN: Optional[AccessToken] = None` global into `FabricTokenProvider` class with per-credential instance caching.
- **Upstream evidence:** `upstream/main:dbt/adapters/fabric/fabric_connection_manager.py:57` still has `_TOKEN: Optional[AccessToken] = None` at module scope, plus `AZURE_AUTH_FUNCTIONS` mapping at module scope and `global _TOKEN` inside `get_pyodbc_attrs_before_credentials`.

### Custom `add_query` reimplementation
- **`2211d4e1`** — DBT_NATIVE_REWRITE — deleted the custom `add_query` (manually firing `ConnectionUsed`/`SQLQuery`/`SQLQueryStatus` events, re-implementing the cursor binding loop) and replaced with thin override delegating to `SQLConnectionManager.add_query`.
- **Upstream evidence:** Upstream `dbt/adapters/fabric/fabric_connection_manager.py:630` still defines the full custom `def add_query(self, sql, auto_begin=True, bindings=None, abridge_sql_log=False, retryable_exceptions=tuple(), retry_limit=1)` and manually re-fires the events instead of dispatching to the base implementation.

### Spurious `log()` call on every macro invocation
- **`5226156539`** — ANTI_PATTERN_REMOVED — removed `{{ log(config.get('query_tag','dbt-fabric')) }}` debug leftover that fired on every SQL statement.
- **Upstream evidence:** Upstream `apply_label` macro in `dbt/include/fabric/macros/adapters/metadata.sql` still has the log call → spams dbt logs on every macro invocation.

### `apply_label()` helper and 2-statement snapshot merge
- **`0857efc1`** — ANTI_PATTERN_REMOVED — removed `apply_label()` helper and all callers across 7 files; deleted custom `fabric__snapshot_merge_sql` (30-line UPDATE+INSERT) so dbt falls through to native MERGE.
- **Upstream evidence:** Upstream `dbt/include/fabric/macros/adapters/metadata.sql` still defines `apply_label`; it's still called from `catalog.sql`, `columns.sql`, `metadata.sql`, `relation.sql`, `merge.sql`, `create_table_as.sql`, and `seeds/helpers.sql`. Upstream `dbt/include/fabric/macros/materializations/snapshots/snapshot_merge.sql` still defines the custom 2-statement `fabric__snapshot_merge_sql` (UPDATE then INSERT).

### Dead code from sibling-project ancestry
- **Thrift exception handling** in upstream `microsoft/dbt-fabricspark/connections.py:102-114` references `thrift_resp.status.errorMessage` — Apache Thrift pattern from dbt-spark; the FabricSpark adapter talks Livy over HTTP, the path is dead.
- **AWS logging config** in upstream `connections.py:42-50` sets `botocore`/`boto3` to DEBUG at import time — leftover from a Spark/Databricks ancestor.
- **Hardcoded 2028 timestamp** at upstream `livysession.py:184` — `expires_on = 1845972874` for the `int_tests` auth path bypasses all token-refresh logic.
- **`_parse_retry_after`** duplicated verbatim across four upstream files: `livysession.py:370`, `mlv_api.py:141`, `concurrent_livy.py:60`, and `singleton_livy.py:34` — all using deprecated `datetime.utcnow()`. The `_getLivySQL` regex-bug helper is duplicated the same way between `singleton_livy.py:488` and `concurrent_livy.py:555`.
- **`get_headers(... tokenPrint=False)`** at upstream `livysession.py:328` logs the full bearer token when `True`.
- **Six `__exit__` methods return `True`** across upstream `singleton_livy.py:49/378/706` and `concurrent_livy.py:119/340/627` — silent exception swallowing.
- **Regex bug** in upstream `_getLivySQL` passes `re.DOTALL` (integer 16) as positional `count` arg → comment-stripping silently capped to 16 replacements per file.

---

## dbt-native rewrites (replacing upstream patterns with dbt mechanisms)

- **`7fccebe7`** — Warehouse snapshots via `on-run-start`/`on-run-end` hooks instead of `atexit` (see above).
- **`257c8999`** — Incremental: `make_intermediate_relation` + `make_backup_relation` + `rename_relation` swap pattern instead of drop-and-recreate.
- **`2211d4e1`** — Connection manager delegates to `SQLConnectionManager.add_query` instead of reimplementing it.
- **`62705a00`** — Run hooks override that drops `commit;` (dbt-adapters default emits it).
- **`80caf6df`** — Test harness's `get_tables_in_schema` uses T-SQL `sys.tables` + `sys.views` instead of `INFORMATION_SCHEMA.TABLES`.
- **`aec6f06e`** — Removed duplicate `materialization clone` block; lets dbt's default materialization handle dispatch.
- **`54e0f0d9`** — Replaced `adapter.get_relation(...)` with dbt-native `load_cached_relation(this)` in `table.sql` (saves per-model metadata round-trip).
- **`eb4f0d69`** — Replaced bespoke `__dbt_tmp_vw` flow with dbt-native `make_intermediate_relation` / `make_backup_relation` / `drop_relation_if_exists` pattern.
- **`201c83fa`** — Replaced 31-line PG-style CTE-bomb `fabric__generate_series` with single `select value as generated_number from generate_series(1, ...)` using Fabric's native table function.
- **`00d791ff`** — Deleted 114-line `fabric__date_spine_sql` + `fabric__date_spine` pair; replaced with 35-line version that delegates to `dbt.generate_series` + `dbt.get_intervals_between` + `dbt.dateadd`.
- **`0857efc1`** — Snapshot merge via native `default__snapshot_merge_sql` instead of custom UPDATE+INSERT.
- **`0e779bdc`** — Split polymorphic `get_token` into explicit `get_api_token()` / `get_sql_token(scope=None)`.
- **`f6a30e98`** — FabricSpark default materialization reverted from `materialized_view` to dbt's standard `view` (now possible because `#234` added view support).
- **`b32853b`** — FabricSpark `get_catalog` delegates to `BaseAdapter.get_catalog` (SparkAdapter's per-database queries don't fit Fabric's workspace/lakehouse/schema layout).
- **`b645e7a`** — Stopped pretending there's a custom `auto` authentication mode; default now `ActiveDirectoryDefault` (the actual mssql-python value).
- **`e134bdbf`** — Collapsed five hand-rolled profile variants + marker-driven autouse `skip_by_profile_type` (~100 LOC of indirection) into single env-var-driven fixture.

---

## Fork-only features (not in either upstream adapter)

### Customer-facing

- **Microsoft Purview integration** — `c181357d`. `PurviewClient` + `PurviewSync` + `purview_types.py`, `purview_sync()` macro for both Fabric DW and FabricSpark, custom Purview type definitions, `persist_docs` integration, lineage graph, stale-lineage cleanup. Plus `0eea9621` extending to Lakehouse. ~4400 LOC subsystem.
- **Python models on Fabric DW** — scaffolded `3eec89f3`, completed `830ae67e`. End-to-end Livy + synapsesql connector. Upstream has zero Python-model support in the `fabric` adapter.
- **Statistics config** — `a9246e99`. `statistics` + `statistics_sample_percent` model configs across table/incremental/snapshot.
- **Catalog row-count statistics** — `a3f0dc7`. `objectpropertyex(tv.object_id, 'Cardinality')` populates `stats:row_count:*` columns in `dbt docs generate` output.
- **dbt-external-tables compatibility via dispatch** — `6434e2d8`. Override macros so the `dbt-external-tables` package works on Fabric DW with `source()` references and `dbt run-operation stage_external_sources`. Upstream ships a standalone `openrowset_source()` macro instead, which doesn't integrate with the package.
- **Scalar functions (dbt 1.11 UDFs)** — `9a136583`, default args `2c96f574`. `function` relation type + four macros.
- **Auto host-resolution from `workspace_name`** — `a1f32a80`. The fork resolves the SQL endpoint from a human-readable workspace name; upstream only accepts `workspace_id` (the GUID).

### Authentication

- **`workload_identity` auth** — `c29e9b56`. Federated OIDC via `ClientAssertionCredential`; supports HTTP URL token source or file path. Not in either upstream adapter.
- **`FabricTokenProvider`** class — `c8be16a1`, API/SQL split `0e779bdc`, workspace_name support `1d276c76`, SP-for-API support `69231eb0`. One provider covering all auth methods, shared across both adapter types; upstream `microsoft/dbt-fabric` still has module-level `_TOKEN` global + `AZURE_AUTH_FUNCTIONS` dict.

### Architecture

- **FabricSpark adapter** — bootstrapped `fd6402f4` + `03094937`. Inherits from `dbt-spark`. Microsoft has no equivalent in the `microsoft/dbt-fabricspark` repo's relationship to dbt-spark (standalone `SQLAdapter`).
  - View support (`53ee818c`), incremental (`dc6c24c9`), snapshot (`4ba1a275`), clone (`682cd721`), persist_docs (`f567b7c6`), materialized lake views (`1678fdc` + `df44b2d`), 4-part naming (`6106cf0a`), cross-workspace quote/include policies (`c39d9acb`).
- **Shared `BaseFabricCredentials` / `BaseFabricConnectionManager` / `BaseFabricAdapter`** — extracted `03094937`. Multiple inheritance lets `FabricSparkAdapter` extend both `SparkAdapter` and `BaseFabricAdapter`.
- **`FabricApiClient`** — extracted `f63cebfe`, refactored to instance class `af65b5e3`. One REST client across both adapters: workspaces, warehouses, lakehouses, Livy, snapshots, Purview.
- **Community package compatibility** — initial import `6fe3b9e3`; namespace fixes `accc0761`/`3133debf`; dbt-utils refresh `3185d5ee`, audit-helper 0.13 `52572266`, dbt-expectations/profiler `3bb7b174`/`b2ac1d61`. 9 packages: dbt-utils, dbt-date, dbt-codegen, dbt-expectations, dbt-audit-helper, dbt-external-tables, dbt-profiler, dbt-artifacts, dbt-project-evaluator. Upstream has zero `dbt_package_support/` tree.

---

## Tests that exposed real bugs (TEST → BUG_FIX in the same PR)

This pattern is direct evidence that the dbt-tests-adapter coverage is doing real work.

- **`8060d37f`** — Writing unit tests for `FabricApiClient` exposed wrong-cased URL paths (`warehousesnapshots` vs `warehouseSnapshots`) in 4 warehouse-snapshot operations. Fixed in same PR.
- **`25faac00`** — Writing PEP 249 compliance tests exposed `FabricSparkCursor.__exit__` returning `True` (silent exception swallowing).
- **`bff925e8`** — Writing LivySession unit tests led to detecting fatal session states immediately instead of waiting full timeout.
- **`5a60ef1c`** — Snapshot tests on FabricSpark exposed missing `Column = FabricSparkColumn` binding → all snapshots failed with `character varying` type error.
- **`3185d5ee`** — Switching dbt-utils integration test to `dbt build` exposed bugs in `sequential_values`, `mutually_exclusive_ranges`, `relationships_where`, `split_part`, etc.
- **`52572266`** — Adding dbt-audit-helper 0.13.0 integration tests exposed multiple T-SQL-incompatible patterns in the existing overrides.
- **`fa771d39`** — Adding FabricSpark dbt-utils tests exposed that `spark__escape_single_quotes` (dbt-spark) uses backslash escapes broken on Fabric Lakehouse.
- **`c9b6537e`** — Adding dbt-date integration tests exposed multiple macro bugs, motivated dim_date overrides and new `expression_is_true` signature.
- **`3bb7b174`** — Adding dbt-expectations integration tests exposed type bugs (T-SQL `timestamp` is `rowversion`) and CTE-scoping bugs.
- **`b2ac1d61`** — Adding dbt-profiler integration tests exposed package was effectively unusable on Fabric (no fabric overrides existed).

---

## Notable transformation arcs (cross-cutting evolution stories)

### `_TOKEN` global → `FabricTokenProvider` → `get_api_token` / `get_sql_token` split
Module global → class → semantic API.
- `c8be16a1` extracts `_TOKEN` global into `FabricTokenProvider` class
- `47b4510f` adds multi-scope cache (dict by scope vs single)
- `9d65b372` → `9fed7d65` (revert) → `0e779bdc` — flag-based pyodbc gating tried, reverted, replaced with named `get_api_token` / `get_sql_token`
- `69231eb0` — SP token support for Python REST flows
- `bb376b06` → `8c3dbabb` → `772d2100` → `160463ac` — series of small fixes to scope-selection logic as the multi-scope / multi-auth path stabilized

### Python models on Fabric DW
Scaffolding → working end-to-end → high-concurrency.
- `3eec89f3` — first `FabricLivyHelper` scaffolding
- `799d09a3` — workspace_id + REST `get_warehouse_connection_string`
- `a1f32a80` — workspace_name resolution
- `6277687f` — lakehouse_name resolution
- `830ae67e` — complete Python support (`generate_python_submission_response`, synapsesql endpoint injection, unskipped Python tests)
- `95ab823b` — session reuse via existing-session lookup
- `e317baa1` — fixed wrong JSON key (`"value"` vs `"items"`) + threading lock for session reuse
- `5df6de74` — fire-and-forget JVM GC after synapsesql writes (JDBC schema-lock workaround)
- `e25ee599` — replaced singleton `LivySession` with `HighConcurrencyLivySession` using Fabric's HC Livy API
- `2aa33835` — promoted JVM GC from fire-and-forget to awaited

### Warehouse snapshots: atexit → on-run-end hooks
- `7fccebe7` — initial `create_or_update_fabric_warehouse_snapshot` macro + `@available` adapter method
- `76c4a4f8` — added 429 rate limiting
- `412b4732` — completed `delete_warehouse_snapshot` + description support
- `8060d37f` — fixed URL casing exposed by unit tests

### FabricApiClient consolidation
- `799d09a3` — initial REST integration in connection manager
- `f63cebfe` — extracted `FabricApiClient` with class-level cache
- `af65b5e3` — refactored to proper instance class with `create()` factory
- `76c4a4f8` — `_api_request` helper centralising every REST call with 429 handling
- `be106c92` — fixed cross-adapter singleton pollution (the fixture no longer caches anything on the connection manager)

### FabricSpark adapter
- `fd6402f4` — scaffolds adapter with `[spark]` optional extra, splits tests
- `03094937` — initial working adapter, extracts shared base classes
- `c9dc049` — `FabricSparkRelationType` + materialized lake views
- `41f2bf0` — 3-part `workspace.database.schema` catalog
- `1678fdc` — full materialized_view materialization
- `c39d9acb` — quote/include policies for 3-part naming
- `dc6c24c9` — full incremental materialization
- `4ba1a275` — snapshot materialization
- `682cd721` — clone materialization
- `f567b7c6` — persist_docs
- `53ee818c` — view support
- `f6a30e98` — default materialization → `view` (dbt-native)
- `6106cf0a` — cross-workspace 4-part naming

### pyodbc → mssql-python migration
- `e51b3bec` — first mssql-python Docker stage in CI
- `0a018f8` — replaces pyodbc throughout adapter, removes ODBC driver dependency
- `9f986a92` — removes the custom Docker container entirely from CI; just installs `libltdl7` on ubuntu-latest

### dbt-spark inheritance for FabricSpark
- `fd6402f4` — adds `[spark]` extra so `dbt-spark` is the optional dependency
- `03094937` — `FabricSparkAdapter(BaseFabricAdapter, SparkAdapter)` via Python multiple inheritance
- subsequent commits inherit Spark macros and only override Fabric-specific behaviour

---

## Revert / modify chains

Most reverts are intra-PR — author's own iteration within the same PR.
Listed here so we don't double-count anywhere else.

### Within the same PR (resolved before merge)

- `48afd75b` reverts `27575d53` (pytest-cov add).
- `cd8e63b7` supersedes `58d6f377` (datetime2 fix moved from macro override to `FabricColumn.data_type` property).
- `0f1422c3` inlines what `07db1102` added as external SQL files.
- `cf9026c5` → `faaa1dd4` (revert) → `accc0761` (minimal re-do) — namespace prefix removal.
- `9d65b372` → `9fed7d65` (revert) → `0e779bdc` (rewrite as two named methods) — pyodbc-token gating.
- `8c3dbabb` → `772d2100` (fix scope attr typo).
- `bb376b06` → `160463ac` (fix authentication attr typo).
- `df1b5b6c` → `73a8c9af` (corrected `get_merge_sql` to `get_incremental_merge_sql`).
- `b9d47abd` reverts `a8110438` (Debian bump in CI).
- `292b6fd4` partially reverts `8c854a49` (drop Python 3.14 from matrix).
- `bdc83cfa` rolls back the Swetrix snippet from `22998e1d`.
- `b0c35576` re-adds skip removed by `257c8999` (restored skip on `TestPySparkTestsFabric` only — the swap pattern remained).
- `2c96f574` → `2b6110aa` (fix `arg.default_value` lookup using `.get()`).
- `643330cb` → `a06a2e27` (fix mutable default `dict | None = {}` → `field(default_factory=dict)`).
- `4a4b6d9` → `1a7207b` (mssql-python sqltype prep reverted — planned upstream change did not land).
- `5a94f78` → `546fdad` (Python 3.14 requires-python reverted).
- `044e4d7` → `fb31c03` (Python 3.14 CI matrix reverted).
- `b59495b2` → `4e33f587` (revert) → `81e0bdf9` (re-apply via PR) — null_compare test fix; net no-op of net no-op (accidental direct-to-main commit cleaned up via PR).
- `6aa023c8` (singleton-caching Livy fixture) → `be106c92` (revoked the singleton caching due to cross-adapter pollution) → `7f91d041` (fixed missing auth fields).
- `1e9d9b70` + `50a06bec` — upstream/main merge using `ours` strategy (records merge parent without changing fork's code; upstream features either already in fork or judged inferior).
- `bf45c646` reverts `f37190a8` (DE timeout bump rolled back).
- `21cc97e3` (isolated-test item-name fix) → `c573af2f` (whole --isolated infrastructure removed).
- The HC session pooling PR (`95bd9a1e` / #268) is a self-contained story — pool was built, then dropped within the same PR because atexit drain duplicated the upstream anti-pattern this fork critiques.

### Self-corrections (no net change)
- `3eec89f3` (Python-model scaffolding) → `9fe0a7aa` (drop unused arg from `py_write_table` call).
- `2835a76e` (added several macros) → `a8fe7e4f` (removed spurious `self` parameter from fixture).
- `e51b3bec` (mssql-python Docker stage) → `e31a0094` (fixed missing line continuation).

### Intentional supersessions (not reverts)

- **`58d6f377`** (macro override) is superseded by **`cd8e63b7`** (Python property) — datetime2 normalisation moved up the stack.
- **`6aa023c8`** (Livy session lifecycle fixture) was tightened over the next two commits; the surrounding singleton-caching approach was later abandoned in favour of per-adapter clients.
- **`257c8999`** (incremental swap pattern + unskipped Python tests) — the swap pattern remained; only the test re-skip was reverted in `b0c35576`.

---

## Full chronological log

Every Sam-authored commit since fork divergence (2025-03-26), in chronological order.

### 99b9986e — 2025-03-26 — INFRA: part 1 of project modernization — replaced setup.py/Makefile/dev_requirements.txt with `pyproject.toml` + `uv.lock`, added `.python-version`, dropped `.pre-commit-config.yaml`, `CHANGELOG.md`, `pytest.ini`, `MANIFEST.in`; moved `devops/CI.Dockerfile` to `.github/CI.Dockerfile`; updated CI workflows.
**Upstream:** Still uses `setup.py`, `Makefile`, `dev_requirements.txt`, `.pre-commit-config.yaml`, `pytest.ini`, `MANIFEST.in`, `devops/CI.Dockerfile`, and a build-system-only `pyproject.toml`.

### ce0554fe — 2025-03-26 — INFRA: clean up configs — moved adapter package from `dbt/` to `src/dbt/` (src layout), trimmed `requirements-dev.txt`, refined ruff config in `pyproject.toml`.
**Upstream:** Still uses flat `dbt/` layout.

### fbb08c44 — 2025-03-26 — INFRA: ruff fmt — apply ruff formatting across the codebase after move to src layout.

### 17259ce0 — 2025-03-26 — INFRA: add less checks — removed several ruff rule categories from `pyproject.toml` (slimmer enforced ruleset).

### e134bdbf — 2025-03-26 — DBT_NATIVE_REWRITE
**Message:** simplify testing
**What:** Collapsed the multi-profile (`--profile`/`PROFILE_NAME`) conftest into a single environment-driven `dbt_profile_target` fixture; removed the `_profile_*` helper functions and the `skip_by_profile_type` autouse fixture; removed `skip_profile`/`only_with_profile` pytest markers.
**Why:** Five hand-rolled profile variants (`ci_azure_cli`, `ci_azure_auto`, `ci_azure_environment`, `user_azure`, `integration_tests`) and the marker-based skip plumbing are scaffolding the harness shouldn't need — env vars + the standard `dbt_profile_target_update` fixture cover the same surface with far less code.
**Upstream:** `tests/conftest.py` upstream still defines `pytest_addoption("--profile")`, five `_profile_*` helpers, the marker-driven `skip_by_profile_type` autouse fixture, and registers `skip_profile`/`only_with_profile` markers in `pyproject.toml`. Roughly 100 lines of indirection the fork removed.

### 4daecf5a — 2025-03-26 — INFRA: test warnings — tighten `filterwarnings` in `pyproject.toml`.

### ac162d96 — 2025-03-26 — INFRA: update docker imgs — refactor `publish-docker.yml` actions/tags.

### 36261378 — 2025-03-26 — INFRA: simpler publishing — simplify `release-version.yml` workflow.

### 4fbece14 — 2025-03-26 — INFRA: fix unit test flow — tweak `unit-tests.yml`.

### abe0bfb5 — 2025-03-26 — INFRA: fix current tests — restructure `integration-tests-azure.yml`, removing legacy steps.

### 68630a73 — 2025-03-26 — INFRA: debian img — switch CI Dockerfile base image to Debian.

### c702e421 — 2025-03-26 — INFRA: cleanup docs — rename `integration-tests-azure.yml` to `integration-tests.yml`; trim `CONTRIBUTING.md`.

### deeed954 — 2025-03-26 — INFRA: clean up more things — also fixes filename typo `test_snpashot_configs.py` → `test_snapshot_configs.py`.

### ba675aac — 2025-03-26 — INFRA: Merge PR #1 (project-modernization-2025) — aggregate merge of the above modernization commits.

### 51d5c80f — 2025-03-26 — INFRA: forked project name — rename PyPI package to fork-specific name and bump version.

### 8bd8bbec — 2025-03-26 — INFRA: target 'forked-version' branch in workflows + expand Python matrix.

### 886382a4 — 2025-03-26 — INFRA: casing — case fix in `CI.Dockerfile`.

### b8bf180d — 2025-03-26 — INFRA: simplify docker img — reduce `CI.Dockerfile` from 23 to 7 lines.

### d6c2153c — 2025-03-26 — INFRA: merge project-modernization-2025 into forked-version.

### 19c4ad70 — 2025-03-26 — INFRA: fix platforms for docker.

### c6c47aff — 2025-03-26 — INFRA: merge project-modernization-2025 into forked-version.

### 27d17011 — 2025-03-26 — INFRA: fix unit test ci — simplify `unit-tests.yml`.

### c05c7193 — 2025-03-26 — INFRA: merge project-modernization-2025 into forked-version.

### 0148b809 — 2025-03-29 — INFRA: bump version to alpha.

### 82ab328b — 2025-03-29 — INFRA: version from tag — generate adapter version from git tag in release workflow.

### a3467b4a — 2025-03-29 — DBT_NATIVE_REWRITE
**Message:** use trusted publishing
**What:** Drop `.pypirc` token bootstrapping from `release-version.yml`; rely on PyPI OIDC trusted publishing.
**Why:** Removes the need to store and rotate a long-lived `PYPI_DBT_FABRIC` API token in GitHub Secrets.
**Upstream:** `microsoft/dbt-fabric` `release-version.yml` still writes a `.pypirc` with `password = ${{ secrets.PYPI_DBT_FABRIC }}` and uploads via `twine upload`. No trusted publisher configured.
**Notes:** Mechanism is INFRA but the security/supply-chain improvement is worth flagging for the contribution case.

### 0b116542 — 2025-03-29 — INFRA: add permissions for token — grant `id-token: write` for OIDC.

### 4d9ede1c — 2025-03-29 — INFRA: use correct container in `integration-tests.yml`.

### 6ae56767 — 2025-03-29 — INFRA: login to azure cli using OIDC — `azure/login@v2` with OIDC federation.
**Notes:** Upstream still authenticates via stored client secrets / older auth flows in `integration-tests-azure.yml`. OIDC removes long-lived Azure secrets from the CI environment.

### 31eadd6f — 2025-03-29 — INFRA: add environment azure for oidc — declare GitHub environment for federated credential trust.

### 21a7e2bf — 2025-03-29 — INFRA: disable subscriptions in azure/login step.

### 0f30d0f3 — 2025-03-29 — INFRA: uv run in integration tests — invoke pytest via `uv run`.

### bb228891 — 2025-03-29 — INFRA: set correct odbc driver in CI.

### 9a1c177c — 2025-03-29 — INFRA: correct ODBC driver version reference in integration tests.

### 20c169c2 — 2025-03-29 — INFRA: secret refs — fix env var names in workflow secrets.

### c333c26b — 2025-03-29 — INFRA: limit concurrency in `integration-tests.yml`.

### 1b8b002c — 2025-03-29 — DOCS: update package references and badges in README.md (point at the fork's PyPI/repo).

### bbfe064c — 2025-03-29 — BUG_FIX
**Message:** add default dbo user in schema creation tests
**What:** In `tests/functional/adapter/test_schema.py`, fall back to `'dbo'` when `DBT_TEST_USER_1` isn't set in the env (both in `schema_authorization` and `_verify_schema_owner`).
**Why:** Without the fallback, the test fixture interpolates an empty string into a GRANT/AUTHORIZATION clause, producing a runtime SQL failure when running locally without the env var set.
**Upstream:** Upstream `tests/functional/adapter/test_schema.py` still uses `env_var('DBT_TEST_USER_1')` and `os.getenv("DBT_TEST_USER_1")` with no default.

### 9d861bc0 — 2025-03-29 — INFRA: add dbt test user to CI — export `DBT_TEST_USER_1` env var in the workflow.

### 0bc7374c — 2025-03-29 — INFRA: fix python version usage in ci.

### 077a2b7c — 2025-03-29 — INFRA: try without concurrency limitation.

### ae91dbdf — 2025-03-29 — INFRA: concurrent tests — re-enable concurrent test execution.

### fa51a13a — 2025-03-29 — TEST
**Message:** add a secondary dwh with case insensitive collation
**What:** Wire up a second Fabric Data Warehouse (case-insensitive collation) via env var `FABRIC_TEST_DWH_CI_NAME` and use it in `TestCachingUppercaseModel` to actually run the case-insensitive cache test instead of skipping it.
**Why:** Upstream blanket-skips the case-insensitivity caching test with the comment "Fabric DW does not support Case Insensivity" — but Fabric *does* support CI collations when the warehouse is provisioned with one. The skip masks a real test that can run with the right fixture.
**Upstream:** `tests/functional/adapter/test_caching.py` upstream still has `@pytest.mark.skip(reason="Fabric DW does not support Case Insensivity.")` on `TestCachingUppercaseModel`. The fork proves the test is runnable with a properly-collated DWH.

### 4c96067e — 2025-03-29 — TEST
**Message:** enable ephemeral tests
**What:** Remove `@pytest.mark.skip(reason="Nested CTE is not supported")` from `TestSingularTestsEphemeralFabric`.
**Why:** The skip's claim ("Nested CTE is not supported") is incorrect — Fabric supports nested CTEs. The test runs.
**Upstream:** Upstream still has the skip on `TestSingularTestsEphemeralFabric` with the same incorrect rationale.

### 8359b9cf — 2025-03-29 — INFRA: set secondary dwh in ci — export `FABRIC_TEST_DWH_CI_NAME` to the workflow env.

### 477d451a — 2025-03-29 — TEST
**Message:** remove skip from ci tests
**What:** Remove the class-level `@pytest.mark.skip` from `TestCachingUppercaseModel` (kept the conditional skip inside the fixture for when the env var is unset).
**Why:** Follow-up to fa51a13a — once the secondary CI-collation DWH is wired into CI, the class no longer needs the blanket skip.
**Upstream:** Upstream still has the blanket class-level skip.
**Notes:** Modifies fa51a13a from same batch; together these two commits convert a permanently-skipped upstream test into a real, running one when the proper fixture warehouse exists.

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

### cf9026c5 — 2025-04-05 — DBT_NATIVE_REWRITE
**Message:** remove tsql_utils namespace
**What:** First attempt at stripping the `tsql_utils.` namespace from internal cross-macro calls in vendored community-package macros under `src/dbt/include/fabric/macros/dbt_package_support/` (dbt_audit_helper, dbt_utils, materializations/insert_by_period). Whole-file reformat plus prefix removal.
**Why:** The vendored macros referenced `tsql_utils.fabric__*` from a third-party adapter package as if `tsql_utils` were imported, but they live in `dbt_fabric` itself, so the namespace prefix is wrong. Cleaning it up makes them dispatch-resolvable inside the adapter.
**Upstream:** The entire `dbt_package_support/` directory does not exist in `upstream/main` (`git ls-tree upstream/main dbt/include/fabric/macros/` returns only `adapters/`, `materializations/`, `utils/`). The fork ships first-class community-package compatibility overrides; upstream leaves users to figure out dbt_utils/dbt_audit_helper themselves.
**Notes:** Immediately reverted by faaa1dd4 (same day); the heavy auto-reformat was undone before re-doing the minimal prefix-removal change in accc0761.

### faaa1dd4 — 2025-04-05 — REVERT_OR_MODIFY
**Message:** Revert "remove tsql_utils namespace"
**What:** Reverts cf9026c5 in full.
**Why:** Author backed out the noisy reformat from cf9026c5 to redo the change minimally.
**Notes:** Reverts cf9026c5 from this same batch.

### accc0761 — 2025-04-05 — DBT_NATIVE_REWRITE
**Message:** remove tsql utils prefix
**What:** Minimal version of cf9026c5: replaces `tsql_utils.fabric__*` / `tsql_utils.surrogate_key` / `tsql_utils.replace_placeholder_with_period_filter` calls with bare macro calls across 6 files. No reformatting.
**Why:** Same as cf9026c5 — these vendored package-support macros were referencing a non-existent `tsql_utils` namespace; resolving to the local macros makes them actually callable.
**Upstream:** No `dbt_package_support/` directory upstream; this entire compatibility surface is fork-only.

### 0777760f — 2025-04-05 — TEST
**Message:** remove invalid test
**What:** Drops `TestCurrentTimestampAwareFabric(BaseCurrentTimestampAware)` from `tests/functional/adapter/utils/test_current_timestamp.py` because Fabric's `current_timestamp` returns a naive `datetime2`, so a timezone-aware test is meaningless.
**Why:** Removes a test that can never be valid against Fabric's T-SQL semantics.

### 827ce82c — 2025-04-05 — TEST
**Message:** remove invalid test
**What:** Drops `TestEscapeSingleQuotesBackslashFabric` — Fabric/T-SQL only escapes single quotes by doubling them, never with backslashes.
**Why:** Same pattern — base class for a dialect feature Fabric doesn't have.

### 3133debf — 2025-04-05 — DBT_NATIVE_REWRITE
**Message:** remove dbt_utils namespace
**What:** Strips the `dbt_utils.` prefix from internal cross-macro calls in the vendored dbt_utils support macros (9 files) — `dbt_utils.default__test_relationships_where` → `default__test_relationships_where`, `dbt_utils.get_powers_of_two` → `get_powers_of_two`, `dbt_utils.current_timestamp` → `current_timestamp`, etc. Also fixes `utils/last_day.sql`.
**Why:** Same as accc0761 — these vendored macros assumed the `dbt_utils` namespace would resolve, but they're inside `dbt_fabric`, so the prefix breaks dispatch.
**Upstream:** No `dbt_package_support/` directory upstream.

### 0a678402 — 2025-04-05 — TEST
**Message:** fix test
**What:** Overrides `project_config_update` in `TestGenerateSeriesFabric` to force `+materialized: table` because Fabric DW views don't support nested CTEs (the default view materialization of the base test would fail).
**Why:** Adapt PostgreSQL-shaped base test to Fabric's view limitation.

### 1f7610c9 — 2025-04-05 — TEST
**Message:** fix test
**What:** Overrides the `models` fixture in `TestListaggFabric` with a hand-rolled `test_listagg.sql` that drops the `string_text COLLATE Latin1_General_CI_AS_KS_WS` syntax used in the base fixture (Fabric DW does not support arbitrary COLLATE in SELECT).
**Why:** Base fixture uses PG-style collation syntax incompatible with T-SQL/Fabric.

### a8e63b5a — 2025-04-05 — TEST
**Message:** fix test
**What:** Adds `valid_sql` fixture returning `"select current_timestamp as c"` for `TestCalculateFreshnessMethodFabric` — the base class's default SQL doesn't compile in Fabric DW.
**Why:** Base class assumes a portable freshness SQL that isn't portable.

### 9eae9aee — 2025-04-05 — BUG_FIX
**Message:** fix split_part
**What:** Rewrites `fabric__split_part` to compute both forward and backward indices in a single subquery and select the right one. Replaces hardcoded `parts` / `split_on` placeholder strings (the previous version literally referenced non-substituted names) with `{{ string_text }}` / `{{ delimiter_text }}`. Also forces `+materialized: table` in the test.
**Why:** The macro was broken — the prior version referenced bare identifiers `parts` and `split_on` rather than the macro arguments, so it could never compile against a real table.
**Upstream:** Upstream `dbt/include/fabric/macros/utils/split_part.sql` was later fixed (commit `eddd1b1` upstream), so the current upstream version works, but the fix landed earlier in the fork. The fork's variant computes both indices in one CTE; upstream uses one conditional `idx`.

### a10b33d8 — 2025-04-05 — TEST
**Message:** fix timestamp test
**What:** Updates `TestCurrentTimestampFabric.expected_schema` from `datetime2` to `datetime2(6)` to match the actual precision returned by Fabric.
**Why:** Bug in test fixture; not a code change.

### 25977e05 — 2025-04-05 — NEW_FEATURE
**Message:** validate_sql macros
**What:** Adds `src/dbt/include/fabric/macros/utils/validate_sql.sql` implementing `fabric__validate_sql` via `SET SHOWPLAN_ALL ON; <sql>; SET SHOWPLAN_ALL OFF;`. Also unskip-and-skip pattern on the test (currently skipped with reason "Fabric does not support SHOWPLAN at the moment").
**Why:** Provide the dbt-adapters `validate_sql` capability so `dbt show` / preview features work; the SHOWPLAN approach is the closest T-SQL equivalent.
**Upstream:** `git show upstream/main:dbt/include/fabric/macros/utils/validate_sql.sql` returns "does not exist" — upstream has no `validate_sql` macro at all.

### 293dbf8f — 2025-04-05 — TEST
**Message:** fix dateadd test
**What:** Overrides `project_config_update` in `TestDateAddFabric` to return `{}` (overriding a parent fixture that set `materialized: table`, so DateAdd runs as default view).
**Why:** Test was inheriting an incompatible default; needed to be cleared.

### 201c83fa — 2025-04-05 — DBT_NATIVE_REWRITE
**Message:** simpler generate series
**What:** Replaces the 31-line `fabric__generate_series` (powers-of-two CTE expansion copied from dbt-utils default) with a single `select value as generated_number from generate_series(1, {{ upper_bound }} - 1)` — Fabric SQL has a native `generate_series` table function.
**Why:** Use the native Fabric/T-SQL `generate_series` instead of porting the PostgreSQL-style CTE explosion. Smaller, faster, and exposes a real Fabric primitive instead of mimicking PG.
**Upstream:** Not in upstream — `dbt_package_support/` is fork-only.

### 00d791ff — 2025-04-05 — DBT_NATIVE_REWRITE
**Message:** fix date spine
**What:** Deletes the 114-line `fabric__date_spine_sql` + `fabric__date_spine` pair from `dbt_package_support/dbt_utils/datetime/date_spine.sql` and replaces with a 35-line adapter-level `src/dbt/include/fabric/macros/utils/date_spine.sql` that delegates to `dbt.generate_series` + `dbt.get_intervals_between` + `dbt.dateadd`. Adds materialization workaround in the test.
**Why:** Previous implementation was a PG-style CTE-bomb that imperatively ran a `run_query` to enumerate dates then UNION-ALL'd them into a literal SQL select — replaced by composing dbt-core's own `generate_series`/`dateadd` macros, which is what dbt-core actually expects adapters to provide.
**Upstream:** Upstream has no `date_spine` macro under `dbt/include/fabric/macros/utils/`. Users must bring their own.

### 071189bd — 2025-04-05 — BUG_FIX
**Message:** remove date_spine limitation
**What:** Inlines the multi-CTE structure of `fabric__date_spine` into a single nested subquery, then removes the `+materialized: table` workaround from the test. The CTE form failed for views (Fabric DW limitation), the subquery form works for both.
**Why:** Lets `date_spine`-using models materialize as views again. The CTE chain triggered the "nested CTEs in views" Fabric DW limitation; flattening to subqueries works around it.

### 5887cf45 — 2025-04-05 — BUG_FIX
**Message:** fix date_spine
**What:** Fixes off-by-one in `fabric__generate_series`: `generate_series(1, {{ upper_bound }} - 1)` → `generate_series(1, {{ upper_bound }})`. Also expands `TestDateFabric` with a hand-rolled SQL model that exercises the date_spine path.
**Why:** The off-by-one truncated date spines by one element. Caught by the new date-spine test.

### 3e181e9a — 2025-04-05 — ANTI_PATTERN_REMOVED
**Message:** remove old docker compose file
**What:** Deletes top-level `docker-compose.yml` that built a local SQL Server 2022 container for testing.
**Why:** Fabric tests run against real Fabric workspaces, not a local SQL Server. The file was dead infrastructure leftover from dbt-sqlserver ancestry.

### d7e06832 — 2025-04-05 — ANTI_PATTERN_REMOVED
**Message:** remove flaky
**What:** Removes the `flaky==3.8.1` dev dependency and the `@pytest.mark.flaky` decorator on `TestSimpleSeedEnabledViaConfigFabric`.
**Why:** Marking tests as flaky hides real bugs. Replaced shortly after by splitting the class into multiple test classes (7bb78a34) so each test gets its own isolation.

### 7bb78a34 — 2025-04-05 — TEST
**Message:** split tests in multiple classes
**What:** Splits `TestSimpleSeedEnabledViaConfigFabric` into 3 separate classes (`TestSimpleSeedEnabledViaConfigFabricDisabled`, `…Selection`, `…Exclude`), each running exactly one of the three methods and skipping the others. Also changes `clear_test_schema` to a no-op rather than dropping the schema.
**Why:** The base class assumed each test method could be run with a fresh schema (via `clear_test_schema` dropping and recreating), but Fabric's drop+create-schema is expensive and racy. Splitting into separate classes gives each its own pytest class-scoped project setup. Direct replacement for the `@flaky` decorator removed in d7e06832.

### faf5f20e — 2025-04-05 — TEST
**Message:** fix grantee test
**What:** Loosens grantee-not-found error matching from `"could not be found or this principal type is not supported"` to `"could not be"` in `TestInvalidGrantsFabric`.
**Why:** Fabric returns different error text variations depending on principal type and edition; the loose prefix match covers all.

### 598c0883 — 2025-04-06 — ANTI_PATTERN_REMOVED
**Message:** remove xdist as Fabric's isolation lvl makes this unusable
**What:** Drops `pytest-xdist==3.6.1` dev dependency. Companion to 7ff8dccc which removes the `-n auto` CLI arg.
**Why:** Per commit message: Fabric's snapshot-isolation-level DWH makes parallel test workers conflict (concurrent DDL causes `sys.tables` metadata query failures). xdist was actively making the suite unreliable; the replacement is dbt-native threading per profile (see 669802d3).
**Upstream:** Upstream still ships pytest-xdist in dev deps. Upstream's per-test isolation problem is unsolved.

### 669802d3 — 2025-04-06 — NEW_FEATURE
**Message:** add support for threads
**What:** Adds `FABRIC_TEST_THREADS` env var read in `tests/conftest.py` as `target["threads"]`, exposes it in `test.env.sample`. Removes a fragile `assert ctx["target_threads"] == 1` from `test_hooks.py`.
**Why:** With xdist gone, parallelism shifts inside dbt itself via the `threads:` profile setting. Lets CI configure thread count from env without touching code.

### 8ff3566e — 2025-04-06 — INFRA: consolidate two integration-test workflows into one matrix-based `integration-tests.yml` covering Python 3.9–3.13, ODBC 17/18, and a 20-thread variant.

### 6e189fbe — 2025-04-06 — INFRA: rename CI job from `full-integration-tests-fabric-dw` to `integration-tests-fabric-dw`.

### 7ff8dccc — 2025-04-06 — INFRA: remove `-n auto` (xdist) from unit-tests workflow command.

### b53a82cd — 2025-04-06 — INFRA: upload `logs/` dir as test-results artifact after CI run.

### ad431b3d — 2025-04-06 — INFRA: fix log path in upload step.

### cf50bcbf — 2025-04-06 — INFRA
**Message:** print logs dir
**What:** Adds `logs_dir` class-scoped fixture in `tests/conftest.py` that sets `DBT_LOG_PATH` to `<rootdir>/logs/<prefix>` and prints the path so failing tests display where to look.
**Why:** Makes debugging failing integration tests far easier — author can now grep the exact dbt log per test class. CLAUDE.md still references this pattern.

### 55799beb — 2025-04-06 — REFACTOR
**Message:** fix pytest warning
**What:** Moves the `TestProjInfoFabric` subclass definition (with `get_tables_in_schema` override) from module level into the `project` fixture local scope to silence pytest's "cannot collect test class" warning caused by the `Test*` prefix on a non-test helper.
**Why:** Cosmetic test infra cleanup. The class wasn't a real test class but pytest treated it as collectible.

### b3787e15 — 2025-04-06 — INFRA: tweak log artifact name in upload step.

### e4f809fd — 2025-04-06 — INFRA: drop per-matrix `threads:` parameter from CI, just set `FABRIC_TEST_THREADS: 20` globally; bump default in test.env.sample.

### 71171eea — 2025-04-06 — BUG_FIX
**Message:** fix test on ci dwhs
**What:** Wraps the literal datetime strings in `_input_model_sql` (used by `TestMicrobatchFabric`) with explicit `cast(... as datetime2(6))`.
**Why:** Fabric's case-insensitive collation DWHs return implicit-cast strings as `varchar`, not `datetime2`, breaking microbatch's `event_time` schema check. Explicit cast normalizes the column type across CI DWH variants.

### 2835a76e — 2025-04-06 — NEW_FEATURE
**Message:** fix a few tests and add first part of dbt_utils integration tests
**What:** (a) Adds `fabric__test_at_least_one` to dbt_utils package-support macros (T-SQL-friendly subquery using `count() ... having = 0` instead of dbt_utils' PG default). (b) Rewrites `fabric__get_tables_by_pattern_sql` to use `sys.tables` / `sys.schemas` joins instead of `information_schema.tables` (Fabric's info_schema has caveats). (c) Fixes `fabric__split_part` (uses macro args instead of `parts`/`split_on` placeholders — same fix as 9eae9aee but in a different location). (d) Adds `dbt_core_bug_workaround` conftest fixture for dbt-core #5410. (e) Adds first end-to-end `tests/functional/packages/test_dbt_utils.py` exercising dbt_utils 1.3.0 against Fabric via `dispatch`.
**Why:** Provide real integration-test coverage for the dbt-utils package-support macros (which upstream lacks entirely), and harden the macros caught by those tests.
**Upstream:** No `dbt_package_support/` directory upstream; no community-package integration tests upstream.

### a8fe7e4f — 2025-04-06 — BUG_FIX
**Message:** fix fixture
**What:** Removes the spurious `self` parameter from the `dbt_core_bug_workaround` fixture introduced in 2835a76e — pytest fixtures are module-level functions.
**Why:** Trivial follow-up: fixture wouldn't run due to the bad signature.
**Notes:** Fixes 2835a76e from this same batch.

### 902fd966 — 2025-04-06 — NEW_FEATURE
**Message:** fix not_empty_string
**What:** Adds `fabric__test_not_empty_string` to dbt_utils package-support. Uses T-SQL's `datalength()` (rather than `length()`) on the trimmed column to detect empty strings.
**Why:** dbt_utils' default uses `length()`, which doesn't exist as such in T-SQL; `datalength` returns byte length and is the right primitive on Fabric DW.
**Upstream:** Not in upstream; package-support is fork-only.

### 3eec89f3 — 2025-04-06 — NEW_FEATURE
**Message:** add a few placeholders for python model support
**What:** First scaffolding for Python models in Fabric DW: registers `FabricLivyHelper` as the `livy` Python submission method on `FabricAdapter`, adds `default_python_submission_method = "livy"`, creates a placeholder `FabricLivyHelper.submit` (calls `super().submit()`), threads `language='python'` through `fabric__create_table_as`, adds `py_write_table` macro that emits `df.write.mode("overwrite").synapsesql("{{target_relation}}")`, marks the `table` materialization as `supported_languages=['sql', 'python']`, and adds skipped placeholder tests for Python model behavior.
**Why:** Lay groundwork for Python model support via Fabric Livy sessions (which becomes a major fork-only feature). Upstream still lacks any Python model support in the `fabric` adapter.
**Upstream:** Upstream `table.sql` is still `{% materialization table, adapter='fabric' %}` (no `supported_languages`). Upstream `create_table_as` only takes `(temporary, relation, sql)`, no language dispatch. No `FabricLivyHelper` or `python_submission_helpers` upstream.

### 97bdb207 — 2025-04-07 — INFRA: ruff formatting (newline + blank-line fixes in 2 files).

### 54e0f0d9 — 2025-04-07 — DBT_NATIVE_REWRITE
**Message:** refactor: replace adapter.get_relation with load_cached_relation for existing relation retrieval
**What:** In `table.sql`, replaces `adapter.get_relation(database=..., schema=..., identifier=...)` with the dbt-native `load_cached_relation(this)` helper (twice).
**Why:** `load_cached_relation` reads from dbt-core's relation cache and is dbt's standard pattern. Bypassing it with `adapter.get_relation` hits the warehouse every time, wasting a metadata round-trip per model.
**Upstream:** Upstream still uses `adapter.get_relation(database=this.database, schema=this.schema, identifier=this.identifier)` directly in `dbt/include/fabric/macros/materializations/models/table/table.sql` (verified).

### 9c9e8000 — 2025-04-07 — BUG_FIX
**Message:** refactor: simplify SQL table creation by removing unnecessary EXEC statement
**What:** In `fabric__create_table_as`, replaces `EXEC('CREATE TABLE {{relation}} AS {{sql_with_quotes}} {{ query_label_option }}');` (with manual single-quote escaping) with a plain `CREATE TABLE {{relation}} AS {{compiled_code}} {{ query_label }}`.
**Why:** The EXEC wrapper was inherited from dbt-sqlserver ancestry where dynamic SQL was needed; Fabric DW's `CREATE TABLE AS SELECT` (CTAS) is a real statement and runs directly. The EXEC indirection forces dbt to double-escape every model body, which silently breaks anything with embedded apostrophes inside string literals.
**Upstream:** Upstream still uses `EXEC('CREATE TABLE {{relation}} {{ cluster_by_clause }} AS SELECT * FROM {{tmp_vw_relation}} {{ query_label_option }}');` (verified via `git show upstream/main:dbt/include/fabric/macros/materializations/models/table/create_table_as.sql`).

### 9bf6c9fb — 2025-04-07 — REFACTOR
**Message:** refactor: improve readability of SQL materialization by replacing comments with Jinja-style documentation
**What:** In `table.sql`: converts `-- ...` SQL comments to `{# ... #}` Jinja comments so they're stripped at compile time. Reorders blocks: existing-relation drop logic now follows the `main` create_table statement.
**Why:** SQL-line comments leak into compiled output and into the query plan; Jinja comments don't. Also tidies the reordering so the temp relation is created before deciding whether to drop the old view.

### eb4f0d69 — 2025-04-07 — DBT_NATIVE_REWRITE
**Message:** refactor: streamline table materialization
**What:** Replaces the bespoke `make_temp_relation` + `__dbt_tmp_vw` flow with the dbt-native `make_intermediate_relation` / `make_backup_relation` / `drop_relation_if_exists` pattern used by every other adapter. Drops the fork-overridden `fabric__make_temp_relation` macro that just suffixed `__dbt_temp`. Removes the duplicated logic that loaded the existing relation twice via `load_cached_relation(this)`.
**Why:** Brings table materialization in line with the dbt-adapters reference pattern, eliminating Fabric-specific naming concepts (`__dbt_tmp_vw`) in favor of intermediate/backup relations. Cleaner, less code, and uses helpers that already handle edge cases (e.g., conditional drop).

### 9fe0a7aa — 2025-04-07 — REFACTOR
**Message:** refactor: remove unnecessary parameter from py_write_table call in create_table_as macro
**What:** Drops `table_type=relation.get_ddl_prefix_for_create(config.model.config, temporary)` from the `py_write_table(...)` call in `fabric__create_table_as`. The `py_write_table` placeholder macro doesn't accept that arg.
**Why:** Cleanup of the python-models scaffolding from 3eec89f3 — that arg was never consumed.
**Notes:** Follow-up to 3eec89f3.

### c8be16a1 — 2025-04-07 — ANTI_PATTERN_REMOVED
**Message:** refactor: consolidate Azure token retrieval logic into FabricTokenProvider class
**What:** Extracts all token-related code from `fabric_connection_manager.py` into a new `FabricTokenProvider` class in `fabric_token_provider.py`. Replaces the module-level `_TOKEN: Optional[AccessToken] = None` global, the `AZURE_AUTH_FUNCTIONS` mapping, and the freestanding `get_*_access_token` functions with instance methods on the class. Adds `token_scope` and `livy_session_connection_string` fields to `FabricCredentials`. The connection manager now uses `cls.get_fabric_token_provider(credentials).get_pyodbc_attributes()`. Token provider supports auto-detection of credential scope from host suffix (`azuresynapse.net` → Synapse scope, `fabric.microsoft.com` → Fabric scope, `database.windows.net` → SQL scope). Also adds `pyodbc.InterfaceError` to default retryable exceptions and threads `credentials.retries` into `ConnectRetryCount`.
**Why:** The upstream pattern of a module-level mutable `_TOKEN` is a classic anti-pattern: shared mutable state across all adapter instances, untestable, racy across threads. Encapsulating in a class with per-credential caching fixes all of that and unlocks the multi-scope (Fabric vs SQL vs Synapse) support needed for Livy/Spark integration.
**Upstream:** Upstream `fabric_connection_manager.py` still has `_TOKEN: Optional[AccessToken] = None` at module scope, `AZURE_AUTH_FUNCTIONS` mapping at module scope, and `global _TOKEN` inside `get_pyodbc_attrs_before_credentials` (verified by grep on `upstream/main`). Also upstream hardcodes `ConnectRetryCount=3` instead of using `credentials.retries`.

### 55737144 — 2025-04-07 — ANTI_PATTERN_REMOVED
**Message:** remove unit tests as they test azure-identity instead of this adapter
**What:** Deletes `tests/unit/adapters/fabric/test_fabric_connection_manager.py` (132 lines mocking `AzureCliCredential`), the unit-tests GitHub workflow, and the README badge for it. CI integration job now runs `uv run pytest -ra -v` (full suite) instead of `tests/functional`.
**Why:** Those "unit tests" mocked Azure SDK internals and reproduced their contracts — they tested azure-identity, not the adapter. After the FabricTokenProvider refactor (c8be16a1), they were also coupled to the old global-state implementation. Removing dead/wrong tests is faster than rewriting them against the new abstraction.
**Upstream:** Upstream still ships these unit tests.

### b6191ebd — 2025-04-07 — INFRA: drop one duplicate matrix entry from `integration-tests.yml` (had two identical-ish entries for dwh08).

### c8483dbf — 2025-04-07 — BUG_FIX
**Message:** fix python 3.9 compat
**What:** Replaced `AccessToken | None` (PEP 604 union) with `Optional[AccessToken]` in `fabric_token_provider.py` so the file parses under Python 3.9.
**Why:** Earlier batch refactor introduced a `X | Y` annotation; the project still claimed `python>=3.9` support, where PEP 604 unions are syntax errors.
**Upstream:** Not applicable — upstream has no separate `fabric_token_provider.py` (token handling is inline in `fabric_connection_manager.py`); this is a fork-only file.

### 40ac03c6 — 2025-04-07 — INFRA: nightly-build base version corrected from 1.9.5 → 1.9.4.

### d0e551c5 — 2025-04-07 — REFACTOR
**Message:** add a base class for package tests
**What:** Extracted `BaseDbtPackageTests` in `tests/functional/packages/base_package_test.py` and refactored `TestDbtUtils` to inherit from it (parametrized via `package_name`, `package_repo`, `package_revision`, `models_config`, `seeds_config`, `tests_config` fixtures).
**Why:** Lays groundwork for adding integration tests against many community packages (dbt-date, dbt-expectations, audit-helper, etc.) without duplicating dispatch/profile boilerplate.

### ad8d2c3e — 2025-04-07 — REFACTOR
**Message:** add timezone var
**What:** Set `vars: {dbt_date:time_zone: UTC}` in the base package test project config.
**Why:** dbt-date requires a `time_zone` var to be set; failing to set it breaks every package that depends on it.

### 55e34683 — 2025-04-07 — REFACTOR
**Message:** add dbt utils dispatching to every package
**What:** Made `BaseDbtPackageTests` auto-add `dbt-labs/dbt_utils@1.3.0` as a package and add a `dbt_utils` dispatch entry whenever the test target is not `dbt_utils` itself; dropped the unused `dbt_fabric` namespace from `search_order`.
**Why:** Many community packages depend on `dbt_utils` macros, but our adapter-specific overrides must take precedence — they need a dispatch entry, not just installation.

### b1e8f997 — 2025-04-07 — INFRA: add empty `tests/__init__.py` to make `tests` an importable package (fixes "module not found" when importing helpers).

### 47b4510f — 2025-04-07 — BUG_FIX
**Message:** cache tokens by scope
**What:** Replaced the single class-level `_token: AccessToken | None` cache with `_tokens: dict[str, AccessToken]` keyed by scope; converted the auth helpers to `@staticmethod` taking an explicit `scope` argument; `get_token(scope=None)` now uses per-scope cache lookup; also exported `FabricLivyHelper`, `FabricRelation`, `FabricTokenProvider` from the package `__init__`.
**Why:** A single cached token is fine for one consumer (pyodbc), but the fork uses multiple scopes (SQL endpoint scope, Fabric/PBI API scope, Livy scope). The shared cache served the wrong token to the wrong consumer.
**Upstream:** `dbt/adapters/fabric/fabric_connection_manager.py` still has `global _TOKEN` (single token) — only ever cached at `AZURE_CREDENTIAL_SCOPE` (`get_pyodbc_attrs_before_credentials` ignores scope). Upstream never needed a multi-scope cache because it has no API-calling features.

### 799d09a3 — 2025-04-17 — NEW_FEATURE
**Message:** add requests dependency and update Fabric classes for improved connection handling
**What:** Added `requests>=2.32.3` as a runtime dep. Introduced workspace/lakehouse-id-based connection: new `workspace_id` and `lakehouse_id` credential fields, made `host` optional, added `FabricConnectionManager.get_warehouse_connection_string()` that calls the Fabric REST API to resolve the SQL connection string from `workspace_id` + `database`, and `get_host()` that picks `host` or falls back to the REST resolver. Built out `FabricLivyHelper.LivySession` (REST submit/poll, statement lifecycle, log URL on failure). Fixed token scope strings (`https://database.windows.net/.default` and `.../powerbi/api/.default`) and added `notebookutils.credentials` fallback. Switched python model write to `df.write.synapsesql(...)` with 3-part name.
**Why:** End users shouldn't have to look up the SQL endpoint URL in the Fabric portal — the adapter can derive it from the workspace + DW name. This is foundational for the fork's Python-model and workspace-name workflows.
**Upstream:** Upstream `FabricCredentials` still requires `host: str` (no `workspace_id`/`lakehouse_id`). `FabricConnectionManager` has no REST integration, no `get_host`, no Livy session helper, and no API workflow.

### bc113f82 — 2025-04-17 — INFRA: re-add `FABRIC_TEST_ENDPOINT` → `host` in `conftest.py` so CI keeps working alongside the new `workspace_id` path.

### 633f046d — 2025-05-21 — BUG_FIX
**Message:** fix token syntax
**What:** Introduced `FABRIC_SPARK_CREDENTIAL_SCOPE = "pbi"` constant; corrected references to non-existent `SYNAPSE_CREDENTIAL_SCOPE` → `SYNAPSE_SPARK_CREDENTIAL_SCOPE`; switched `synapse`/`fabric` authentication branches to their proper Spark scopes; replaced broken `from notebookutils import mssparkutils` import with `from notebookutils import credentials`.
**Why:** Multiple `AttributeError`s in the scope-selection logic from prior commits; the `mssparkutils` symbol doesn't exist in the fabric notebook runtime.
**Upstream:** Not applicable (token provider file does not exist upstream).

### 41e0e3fd — 2025-05-21 — INFRA: nightly-build BASE_VERSION bumped 1.9.4 → 1.9.6.

### 673f69b9 — 2025-05-21 — INFRA: change `authors` in `pyproject.toml` from "Pradeep Srikakolapu" to "Sam Debruyn".

### bb376b06 — 2025-05-21 — BUG_FIX
**Message:** fix scope selection for fabric auth
**What:** Reordered `get_token_scope` so the `synapse`/`fabric` authentication checks run *before* the URL-based heuristics that need `credentials.host` (which can be None when only `workspace_id` is provided).
**Why:** Prior order would call `credentials.host.lower()` on `None` for the spark notebook auth flows. The reorder also makes auth-type explicit selection win over host-substring guessing.
**Upstream:** Not applicable (no FabricTokenProvider upstream).

### 8c3dbabb — 2025-05-21 — BUG_FIX
**Message:** use provided scope if provided
**What:** `get_token` now honors `self.credentials.scope` before falling back to `get_token_scope()`.
**Notes:** Buggy — references `credentials.scope` which doesn't exist; fixed in 772d2100 below.

### 772d2100 — 2025-05-21 — BUG_FIX
**Message:** fix attr call
**What:** Replaced `self.credentials.scope` with `self.credentials.token_scope` (the actual field on `FabricCredentials`).
**Notes:** Fixes the typo introduced in 8c3dbabb.

### 160463ac — 2025-05-21 — BUG_FIX
**Message:** fix authentication attr call
**What:** Replaced `self.authentication.lower()` (which doesn't exist as an attribute of `FabricTokenProvider`) with `self.credentials.authentication.lower()` in the two new branches of `get_token_scope`.
**Notes:** Fixes an `AttributeError` introduced in bb376b06.

### 5ad65126 — 2025-08-06 — BUG_FIX
**Message:** require alias for limits and subs
**What:** Set `FabricRelation.require_alias = True` (was `False`).
**Why:** dbt-core's `--empty` and ref-subquery handling require the derived-table alias; without it, T-SQL throws "incorrect syntax near …".
**Upstream:** Upstream `dbt/adapters/fabric/fabric_relation.py` also has `require_alias: bool = True` — the fork was catching up with an upstream change rather than introducing one.

### a1f32a80 — 2025-08-07 — NEW_FEATURE
**Message:** Add workspace_name to FabricCredentials and implement workspace ID retrieval
**What:** Added a `workspace_name` credential field plus a `get_workspace_id()` API call against `https://api.powerbi.com/v1.0/myorg/groups?$filter=name eq '<name>'`. Rewrote `get_warehouse_connection_string()` to look in warehouses first, then lakehouses, returning the SQL endpoint from either. Connection string is no longer keyed by `database` — it grabs any item in the workspace (all items in a workspace share the SQL endpoint URL).
**Why:** Users typically know the workspace *name* from the Fabric portal, not the GUID; making `workspace_id` optional removes a copy-paste step. Also enables the adapter to find SQL endpoints for Lakehouses (not just Warehouses).
**Upstream:** Upstream `FabricCredentials` has no `workspace_id` *or* `workspace_name`; no API resolution at all.

### f88b30c1 — 2025-08-07 — INFRA: `ruff format` on `fabric_connection_manager.py`.

### 7da9694a — 2025-08-07 — BUG_FIX
**Message:** Add support for workspace_name in FabricConnectionManager host resolution
**What:** `get_host()` now triggers the REST resolver when *either* `workspace_id` or `workspace_name` is set (was only `workspace_id`).
**Why:** Follow-up to a1f32a80 — the resolver knows how to handle both, but the dispatch in `get_host` only checked one.

### 1d276c76 — 2025-08-07 — BUG_FIX
**Message:** add support for workspace_name in token provider
**What:** `get_token_scope` returns `FABRIC_CREDENTIAL_SCOPE` when `host is None` and *either* `workspace_id` or `workspace_name` is set.
**Why:** Same parity fix as 7da9694a, in the token provider's scope-selection path.

### 69231eb0 — 2025-09-11 — NEW_FEATURE
**Message:** add support for getting tokens using SPs
**What:** Added `tenant_id` to `FabricCredentials`; imported `ClientSecretCredential`; refactored `get_token` to (a) short-circuit and return a cached token when it has >300s remaining, (b) handle `activedirectoryserviceprincipal` by constructing a `ClientSecretCredential(client_id, client_secret, tenant_id)` to fetch tokens for the requested scope (not just for pyodbc).
**Why:** Previously SP auth flowed only through pyodbc/ODBC; the new REST flows (workspace resolution, Livy) need a token via Python too. Without this, SP users can't use any of the API-driven features.
**Upstream:** Upstream `FabricCredentials` has `tenant_id` but the `AZURE_AUTH_FUNCTIONS` map has no entry for `activedirectoryserviceprincipal` — pyodbc handles SP auth natively, but there's no Python-callable equivalent because upstream has no REST features.

### 9d65b372 — 2025-09-11 — BUG_FIX
**Message:** do not use our token in pyodbc if it's not an Azure token
**What:** Added `used_for_pyodbc=True` flag so the SP branch wouldn't fetch a token when pyodbc was the consumer (pyodbc handles SP auth natively).
**Notes:** Reverted in next commit; the gating logic moved into a new `get_sql_token`/`get_api_token` split (0e779bdc).

### 9fed7d65 — 2025-09-11 — REVERT_OR_MODIFY
**Message:** Revert "do not use our token in pyodbc if it's not an Azure token"
**What:** Reverted 9d65b372.
**Why:** The flag-based approach was replaced by an explicit two-method API in 0e779bdc.

### 0e779bdc — 2025-09-11 — DBT_NATIVE_REWRITE
**Message:** resilient token fetching for API or SQL
**What:** Moved the auth helpers (`get_cli_access_token`, `get_auto_access_token`, etc.) out of the class as module-level functions; split `get_token` into `get_api_token()` and `get_sql_token(scope=None)`, with shared `_get_token(scope, usage_is_sql)` that knows: API calls always need `FABRIC_CREDENTIAL_SCOPE`; SQL calls with non-Azure auth (e.g. SP) must skip our token cache (returns None so pyodbc does its own auth); SP auth is only used for API consumers. Switched all callers (`get_warehouse_connection_string`, `LivySession._access_token`, `get_pyodbc_attributes`) to the new explicit methods.
**Why:** Embedding "which scope" and "is SP auth allowed" inside one polymorphic method became unmaintainable; two named methods make the call sites self-documenting and remove the need for the SP-pyodbc flag.
**Upstream:** Not applicable (no FabricTokenProvider upstream).

### 9c3ac010 — 2025-09-25 — BUG_FIX
**Message:** add support for varchar(max)
**What:** Replaced every hardcoded `varchar(8000)` / `VARCHAR(8000)` with `varchar(max)` / `VARCHAR(MAX)` in `FabricColumn.TYPE_LABELS`, `FabricColumn.string_type`, `fabric__snapshot_hash_arguments`, `fabric__hash`, and the `tsql_utils_surrogate_key_col_type` default in `dbt_package_support/dbt_utils/sql/surrogate_key.sql`.
**Why:** `varchar(8000)` silently truncates strings longer than 8000 characters — a real data-loss bug for hash inputs, surrogate keys, snapshot hash columns, and any inferred string column. Fabric Warehouse supports `varchar(MAX)` natively.
**Upstream:** Upstream `FabricColumn.TYPE_LABELS` still has `"STRING": "VARCHAR(8000)"`, `"VARCHAR": "VARCHAR(8000)"`, `"NVARCHAR": "VARCHAR(8000)"`; `string_type` defaults to `8000`; `string_size` returns `8000` when `char_size is None`. Active silent-truncation footgun in upstream.

### df1b5b6c — 2025-09-30 — NEW_FEATURE
**Message:** support SQL MERGE
**What:** Added `"merge"` to `valid_incremental_strategies`; changed `fabric__get_incremental_default_sql` to dispatch to `get_merge_sql` (later corrected to `get_incremental_merge_sql` in 73a8c9af) when `unique_key` is set.
**Why:** Delete+insert is wasteful for warehouse workloads; native `MERGE` is supported by Fabric Warehouse and is the dbt-canonical incremental strategy.
**Upstream:** Upstream now also has `"merge"` in `valid_incremental_strategies` and a `fabric__get_incremental_merge_sql` macro — they have caught up since this fork commit landed.

### 955ab2e3 — 2025-09-30 — BUG_FIX
**Message:** fix microbatch merge
**What:** In `fabric__get_incremental_microbatch_sql`, when `unique_key` is present, delegate to `dbt.get_incremental_merge_sql` instead of falling through to the delete+insert path.
**Why:** Microbatch with a `unique_key` should upsert (merge), not just delete-and-insert, to match user expectations and dbt-core semantics.
**Upstream:** Upstream `fabric__get_incremental_microbatch_sql` still has no unique-key shortcut — always does the delete+insert flow.

### ac4bc560 — 2025-10-04 — INFRA: relaxed dev pin constraints (`==` → `>=`/`<` ranges) for pytest, dbt-core, dbt-tests-adapter, ruff; regenerated `uv.lock`.

### fe3d3281 — 2025-10-04 — BUG_FIX
**Message:** for pooling to work, we'd need odbcversion set to 3.8
**What:** Added `pyodbc.odbcversion = "3.8"` next to `pyodbc.pooling = True` in `FabricConnectionManager.connect`.
**Why:** pyodbc's connection pooling silently no-ops unless `odbcversion` is also set to "3.8"; without it, each connection is freshly created.
**Upstream:** Upstream sets `pyodbc.pooling = credentials.pooling if credentials.pooling is not None else True` but never sets `odbcversion` — pooling is effectively broken there.

### 0b4b1bf2 — 2025-10-04 — REFACTOR
**Message:** integrate upstream typing changes
**What:** Expanded `FabricColumn.TYPE_LABELS` to mirror the larger upstream type map (BINARY, CHAR, DATETIME2, MONEY, NCHAR, NVARCHAR, SMALLMONEY, TIME, TINYINT, VARBINARY, VARCHAR) while keeping VARCHAR/NVARCHAR/STRING at `VARCHAR(MAX)`; added `is_string()` and `is_numeric()` to match upstream API.
**Why:** Pull in the type-handling improvements upstream made, without losing the `MAX` fix from 9c3ac010.

### 32a4155a — 2025-10-04 — REFACTOR
**Message:** integrate upstream "--empty" flag changes
**What:** Added `AS` keyword before the alias in `FabricRelation.render_limited` (both the `where 1=0` and `top` paths), matching upstream.

### 7b1427f1 — 2025-10-04 — REFACTOR
**Message:** integrate upstream changes on incremental constraints
**What:** In `fabric__create_incremental` (table path), call `build_model_constraints(target_relation)` after dropping the temp view, matching upstream's incremental-constraints support.

### a5a90ec5 — 2025-10-04 — INFRA
**Message:** update to test with dbt-core 1.10
**What:** Bumped `dbt-core` upper bound from `<1.10.0` to `<1.11.0`; trimmed `tests/functional/adapter/test_sources.py` to drop the deprecated "space in name" source case (dbt-core 1.10 forbids spaces in source names).

### 47f3ac74 — 2025-10-04 — TEST
**Message:** fix empty test
**What:** Removed the local `model_sql`/`models` override in `TestFabricEmpty`; the base class now suffices.

### 812e2d6b — 2025-10-04 — TEST
**Message:** fix empty inline SQL test
**What:** Added `model_inline_sql` and a `models` fixture override to `TestFabricEmptyInlineSourceRef` (alias source explicitly to satisfy `require_alias=True`).

### 73a8c9af — 2025-10-04 — BUG_FIX
**Message:** fix incremental merge default strategy
**What:** Changed `fabric__get_incremental_default_sql` from `get_merge_sql(arg_dict)` to `get_incremental_merge_sql(arg_dict)`.
**Why:** `get_merge_sql` is the low-level SQL builder; `get_incremental_merge_sql` is the dispatch wrapper that handles all the incremental_predicates/delete_condition/delete_not_matched_by_source plumbing. The earlier commit (df1b5b6c) used the wrong macro and silently dropped those features.
**Notes:** Bug introduced in df1b5b6c (same batch).

### 7af4d5e3 — 2025-10-04 — TEST
**Message:** fix microbatch test
**What:** Dropped a stray alias `a` from a single test SQL string to align with `require_alias` expectations.

### 2e7e1f2f — 2025-10-04 — INFRA
**Message:** simplify test setup
**What:** Removed the second case-insensitive-DWH matrix entry from CI; trimmed `test.env.sample` (workspace_name based, dropped lakehouse_id); switched conftest to `workspace_name`; raised default retries 2→3, threads 1→20, added `login_timeout`/`query_timeout`; dropped the `FABRIC_TEST_DWH_CI_NAME` machinery in `test_caching.py` (caching tests now run against the default DWH).

### 62f047cc — 2025-10-04 — INFRA
**Message:** skip grants tests by default due to broken Fabric SP support
**What:** Added `--with-grants` pytest option and a `grants` marker that auto-skips unless the flag is passed; marked all grants tests; switched CI to use `FABRIC_TEST_WORKSPACE_NAME` and stopped passing the SP-based `DBT_TEST_USER_1/2/3` secrets.
**Why:** Fabric's SP grant support is broken (cannot reliably GRANT to SPs); skipping in CI prevents spurious failures while keeping the tests available locally with `--with-grants`.

### df29b7c0 — 2025-10-04 — INFRA: `ruff format` on `tests/conftest.py`.

### e5a3c370 — 2025-10-04 — INFRA: removed the duplicate `ci07` matrix entry (same python_version + msodbc_version as ci06).

### 4825c916 — 2025-10-04 — INFRA
**Message:** remove support for Python 3.9
**What:** Bumped Python lower bound, removed 3.9 from CI matrix, regenerated `uv.lock`. Enables PEP 604 unions, modern typing, etc. (the cause of the c8483dbf compat fix at the start of this batch).

### 21facd52 — 2025-10-04 — INFRA: CI matrix now passes `FABRIC_TEST_WORKSPACE_ID` (literal GUID); conftest accepts both `workspace_id` and `workspace_name`.

### 4e6b0f7e — 2025-10-05 — INFRA: switched CI back to `FABRIC_TEST_HOST` (from a secret); conftest reads `FABRIC_TEST_HOST` for `host`.

### f63cebfe — 2025-10-05 — REFACTOR
**Message:** introduce api client to isolate API calls
**What:** Created `src/dbt/adapters/fabric/fabric_api_client.py` containing `FabricApiClient` with `get_workspace_id`, `get_warehouse_connection_string`, `get_fabric_token_provider` — all moved out of `FabricConnectionManager`. The connection manager now multi-inherits from `SQLConnectionManager` + `FabricApiClient` and additionally caches `_workspace_id` and `_warehouse_connection_string` at the class level (so REST is hit at most once per process). Added `.vscode/settings.json` (single-key Python envs config).
**Why:** REST-API plumbing was bloating the connection manager and made it harder to reuse the API client from the Livy helper or future utilities. Extracting it gives a clean seam and free memoization.

### 6277687f — 2025-10-05 — NEW_FEATURE
**Message:** link api helper to fetch lakehouse
**What:** Added `get_lakehouse_id` to `FabricApiClient` that resolves a lakehouse ID via the Fabric REST API by `lakehouse_name`, plus a `lakehouse_name` credential and `lakehouse`/`workspace` aliases.
**Why:** Enable Python model execution to target a Lakehouse without forcing users to look up GUIDs.
**Upstream:** Upstream `FabricCredentials` (`dbt/adapters/fabric/fabric_credentials.py`) has no `lakehouse_id` or `lakehouse_name` field at all — there is no FabricApiClient and no lakehouse resolution path.

### 830ae67e — 2025-10-05 — NEW_FEATURE
**Message:** complete python support
**What:** Hooked `FabricLivyHelper` into the lakehouse/workspace API client; implemented `generate_python_submission_response`; injected the warehouse SQL endpoint into the Python harness so `spark.read.synapsesql` resolves; unskipped Python model tests; passed lakehouse vars through CI/conftest.
**Why:** Make `materialized: python` actually work end-to-end against Fabric (Livy + SynapseSQL connector).
**Upstream:** Upstream has no Python model support whatsoever — `generate_python_submission_response` did not exist, there is no Livy helper, and `python` is not a supported materialization. `git ls-tree -r upstream/main | grep python` shows only `.python-version`.

### 95ab823b — 2025-10-05 — DBT_NATIVE_REWRITE
**Message:** reuse sessions if possible
**What:** `LivySession` now lists existing Fabric Livy sessions named `dbt-fabric` in `idle|starting|running` state and reuses them instead of starting a fresh one per model; consolidates URL helpers; correctly reports statement success/error from `output.status`.
**Why:** Spinning up a new Livy session per Python model is expensive (~minutes) and was the prior behaviour; reusing the session is required for realistic adoption.
**Upstream:** Upstream has no Livy/Python infrastructure at all.

### 3f1eb0ec — 2025-10-05 — TEST
**Message:** add skip markers for incremental Python models and PySpark tests
**What:** Re-skipped `TestPythonIncrementalTestsFabric` and `TestPySparkTestsFabric` with explicit reasons after the previous commit had unskipped them.

### a9c20a52 — 2025-10-05 — DOCS
**Message:** clean up docs
**What:** Removed Microsoft-internal `SECURITY.MD` and a nightly-build workflow inherited from the Microsoft repo; trimmed CONTRIBUTING down to the fork's workflow.

### e3cbc5ef — 2025-10-05 — DOCS
**Message:** update readme
**What:** Rewrote README for the fork: rebrands to `dbt-fabric-samdebruyn`, positions as a maintained/extended fork, removes Microsoft CoC reference, adds acknowledgements section.

### e5ede38e — 2025-10-05 — INFRA: fix pypi project URLs after rename to `dbt-fabric-samdebruyn`.

### 65390837 — 2025-10-05 — INFRA: add GitHub Sponsors `.github/FUNDING.yml`.

### ca3df4c7 — 2025-10-05 — DOCS
**Message:** add docs
**What:** Added mkdocs-material configuration (`mkdocs.yml`), initial `docs/index.md`, a placeholder `overrides/partials/integrations/analytics/custom.html`, and a Cloudflare Pages build script. Wires mkdocs into pyproject extras and lockfile.

### 41436810 — 2025-10-05 — INFRA: move docs build artefacts (cloudflare_pages.sh, requirements.txt) into a dedicated `docs_build/` folder.

### b652384c — 2025-10-05 — INFRA: change CF Pages output directory.

### 63dee533 — 2025-10-05 — DOCS: add docs site link to README; gitignore `site/`; add `site` extra.

### 22998e1d — 2025-10-05 — DOCS
**What:** Added contributing.md and license.md docs pages and a Swetrix analytics snippet (later removed in bdc83cfa).

### e659e7f0 — 2025-10-05 — DOCS: add dbt + Fabric brand logos and a Code of Conduct mention with dbt signature mark.

### f94e192d — 2025-10-05 — DOCS: fix logo URLs in README/docs/mkdocs.

### 6252f8b2 — 2025-10-05 — DOCS
**Message:** add config page
**What:** Adds three docs pages: `installation.md` (driver setup), `compatibility.md`, and a 343-line `configuration.md` documenting every credential and aliasing rule. None of these exist upstream.

### e214c9ae — 2025-10-05 — DOCS
**Message:** add feature comparison page to documentation
**What:** Adds a 95-line `feature-comparison.md` enumerating fork vs upstream feature delta — this is the contribution case in user-facing form.

### e332b540 — 2025-10-05 — DOCS: small README link fix.

### 456b7c58 — 2025-10-05 — INFRA: add explicit `permissions:` to lint-format workflow (least-privilege hardening).

### 3953b0eb — 2025-10-06 — DOCS: add "drop-in replacement for `dbt-fabric`" note to README.

### bdc83cfa — 2025-10-18 — INFRA: remove Swetrix analytics from docs build (rolling back the analytics snippet added in 22998e1d).
**Notes:** Modifies 22998e1d from this same batch.

### b8803211 — 2026-02-06 — INFRA: drop support for Python 3.10 (`pyproject.toml`, regenerated `uv.lock`).

### b4a5919e — 2026-02-06 — REFACTOR
**Message:** simpler typing in Python
**What:** Mechanical conversion of `typing.Optional[X]` / `typing.List[X]` to PEP 604 `X | None` / built-in generics across adapter modules.

### 6a18ea77 — 2026-02-06 — BUG_FIX
**Message:** fix for nvarchar column types
**What:** In `fabric__get_columns_in_relation`, halves `c.max_length` for `nchar|nvarchar|sysname` (SQL Server stores nchar lengths in bytes); also adds `fabric_base_api_uri` and `powerbi_base_api_uri` credential overrides and switches to PEP 604 typing in credentials.
**Why:** Without the fix, `nvarchar(50)` columns are reported as character length 100 (bytes), corrupting `get_columns_in_relation` results and any downstream contract/constraint checks.
**Upstream:** Upstream eventually applied the same divide-by-two fix in `dbt/include/fabric/macros/adapters/columns.sql` (commit `253c453`), so the column-length bug is no longer present upstream. The credential base-URI override fields, however, are not in upstream.

### af65b5e3 — 2026-02-06 — ANTI_PATTERN_REMOVED
**Message:** move all API calls into a single API client
**What:** Refactors `FabricApiClient` from a bag of `@classmethod` + class-level mutable caches into a proper instance class (`create()` factory, instance-scoped caches). Pulls Livy session management out of `fabric_livy_helper.py` and the warehouse-connection-string lookup out of the connection manager, centralising every Fabric REST call in one place. Adds `_cached_warehouses` / `_cached_lakehouses` / `_livy_session_id` and a `_warehouse_snapshot_operations` map to support async operations.
**Why:** Removes global mutable state (the previous design stored credentials/token-provider as class attributes — broken under multiple projects/profiles in one process) and removes the copy-pasted Livy URL plumbing from `fabric_livy_helper.py`.
**Upstream:** Upstream has no FabricApiClient; equivalent REST calls live inside `dbt/adapters/fabric/warehouse_snapshots.py` (its own `WarehouseSnapshotManager` class) and `fabric_connection_manager.py` uses a module-global `_snapshot_manager` for snapshot orchestration, plus `atexit.register` to fire end-of-run logic — the exact anti-patterns this refactor removes.

### 8c854a49 — 2026-02-06 — INFRA: bump GitHub Actions matrix to Python 3.11–3.14 (3.14 rolled back in 292b6fd4).

### fc57b152 — 2026-02-06 — INFRA: ruff formatting only.

### 3b56351e — 2026-02-06 — BUG_FIX
**Message:** import snapshot hard deletes fix
**What:** In `fabric__snapshot_staging_table`, when `strategy.hard_deletes == 'new_record'`, filters out previously-hard-deleted records when selecting current snapshot rows for the merge — without it the merge would re-resurrect deleted rows.
**Why:** Bug carried over from dbt-spark/dbt-postgres; without this filter, every snapshot run after a hard-delete cycle reactivates the deleted record.
**Upstream:** Upstream also has this fix in `dbt/include/fabric/macros/materializations/snapshots/helpers.sql` (commit `dbe7a77` "Addressing hard_delete issues with snapshot…"), so this is no longer a fork-only fix.

### d8f71643 — 2026-02-06 — INFRA: routine package bumps in `pyproject.toml` and `uv.lock`.

### 7fccebe7 — 2026-02-07 — DBT_NATIVE_REWRITE
**Message:** add on run start/end hooks for warehouse snapshots
**What:** Adds `create_or_update_fabric_warehouse_snapshot(snapshot_name, description=none)` macro that delegates to a new `@available` adapter method, which calls the consolidated `FabricApiClient`. Implements warehouse-snapshot create/update via the LRO (Location header) pattern, including `wait_and_get_snapshot_id_from_operation`. Adds a functional test that wires the macro into a real dbt project as `on-run-start`/`on-run-end` hooks (the dbt-native way).
**Why:** Replace the upstream design that hijacks connection lifecycle with `atexit` + a module-level `_snapshot_manager` global, with a dbt-native flow: macro → `@available` adapter method → user-controlled `on-run-start`/`on-run-end` hooks.
**Upstream:** `upstream/main:dbt/adapters/fabric/fabric_connection_manager.py` literally `import atexit`, declares `_snapshot_manager = None` global, and at line 602 does `atexit.register(lambda: _run_end_action(result))` to schedule end-of-run snapshot updates. That bypasses dbt-core's normal lifecycle and runs even when the process is killed/crashed; the fork moves all of it into proper macro hooks.

### a462eb8e — 2026-02-07 — INFRA: switch the CI workspace name and corresponding env var.

### a8110438 — 2026-02-07 — INFRA: bump base Debian in CI Dockerfile (reverted two commits later).

### 76c4a4f8 — 2026-02-07 — BUG_FIX
**Message:** add rate limiting support
**What:** Adds `_api_request` helper to `FabricApiClient` that centralises every REST call, handles HTTP 429 by sleeping `Retry-After` and recursing, and raises a uniform `DbtRuntimeError` on non-2xx. Replaces every per-method `requests.get/post/patch` + status-code check with `_api_get/_api_post/_api_patch`.
**Why:** Fabric's REST APIs throttle aggressively; without 429 handling, dbt runs would fail spuriously when several models/snapshots fire calls in quick succession. Also removes ~30 lines of repeated status-check boilerplate.
**Upstream:** `upstream/main:dbt/adapters/fabric/warehouse_snapshots.py` uses `response.raise_for_status()` with no 429 backoff — same throttling vulnerability is present.

### b9d47abd — 2026-02-07 — REVERT_OR_MODIFY: reverts a8110438 (Debian bump in CI).
**Notes:** Same-batch revert.

### 931ec016 — 2026-02-07 — INFRA: ruff formatting only.

### 292b6fd4 — 2026-02-07 — INFRA: remove Python 3.14 from supported matrix because upstream deps don't ship 3.14 wheels yet.
**Notes:** Partially reverts 8c854a49 from this same batch.

### 412b4732 — 2026-02-07 — NEW_FEATURE
**Message:** clean up snapshots after run
**What:** Adds `delete_warehouse_snapshot(snapshot_name)` to FabricApiClient and an optional `description` parameter to the create/update API (and to the user-facing macro). The functional test fixture now uses `delete_warehouse_snapshot` for setup/teardown.
**Why:** Round-trip cleanup so test runs (and user pipelines that want temporary snapshots) don't leak snapshots into the workspace; descriptions make snapshots self-documenting.
**Upstream:** `upstream/main:dbt/adapters/fabric/warehouse_snapshots.py` defines `delete_warehouse_snapshot(snapshot_id)` as `return True` — a stub that pretends to delete but does nothing.

### 2a1ed5a0 — 2026-02-07 — TEST
**Message:** Add Fabric API client and credentials fixtures; update snapshot handling
**What:** Promotes `credentials`, `fabric_token_provider`, and `fabric_api_client` to class-scoped conftest fixtures, simplifies the snapshot test, and asserts the snapshot exists with the expected `displayName` and `description` after the run.

### e51b3bec — 2026-02-07 — NEW_FEATURE
**Message:** build Docker image for mssql-python
**What:** Splits `CI.Dockerfile` into `base` / `msodbc` / `mssql-python` stages, adds a `mssql-python` target installing `libltdl7`, `libkrb5-3`, `libgssapi-krb5-2`, and adds `mssql-python` to the Docker publish matrix.
**Why:** Future move from `pyodbc` to Microsoft's native `mssql-python` driver requires a different system-package baseline (no ODBC, but needs Kerberos libs).
**Upstream:** Upstream still uses `pyodbc` exclusively and ships only ODBC-based CI images.

### e31a0094 — 2026-02-07 — BUG_FIX
**Message:** fix: correct syntax for installing libgssapi-krb5-2 in Dockerfile
**What:** Adds the missing `\` line continuation after `libgssapi-krb5-2` so `apt-get autoremove` is part of the same RUN command.
**Notes:** Fixes a syntax error in e51b3bec from this same batch.

### 30e7593a — 2026-02-17 — INFRA: merge `upstream/main` (Microsoft's `main`) into `forked-version`; resolves conflicts in workflows, version file, table macros, conftest, and several test files.

### 99634f42 — 2026-02-17 — INFRA: another `upstream/main` merge into `forked-version` (more conflicts in pre-commit, columns macro, adapter, relation, etc).

### 4bfd382f — 2026-02-17 — INFRA: third upstream merge (release workflow, incremental_strategies, warehouse_snapshots conflicts).

### e649af80 — 2026-02-17 — INFRA: fourth upstream merge (conftest, warehouse_snapshots).

### 08d36bcb — 2026-02-17 — INFRA: regenerate `uv.lock` after upstream merge.

### 1afcfa1a — 2026-02-17 — DOCS
**Message:** update docs
**What:** Adds four new docs pages: `authentication.md` (245 lines), `python-models.md` (102 lines), `warehouse-snapshots.md` (150 lines), and updates `feature-comparison.md` with the latest fork-vs-upstream delta. Wires them into mkdocs nav.

### ba75719e — 2026-02-20 — TEST
**Message:** enable alter test now that this is supported
**What:** Removed `pytest.skip` for `test_run_incremental_sync_all_columns` in `TestIncrementalOnSchemaChangeFabric` now that Fabric supports `ALTER TABLE` drop columns.
**Why:** Fabric DW added support for dropping columns via ALTER TABLE; previously skipped because Fabric did not allow it.

### 7cd33eaa — 2026-02-20 — BUG_FIX
**Message:** enable validate_sql to work in dbt_utils
**What:** Rewrote `fabric__validate_sql` to wrap the user SQL between separate `SET SHOWPLAN_XML ON` and `OFF` statements instead of a single multi-statement string, and removed the `@pytest.mark.skip` on `TestValidateSqlMethodFabric`.
**Why:** The previous implementation issued `SET SHOWPLAN_ALL ON; <sql>; SET SHOWPLAN_ALL OFF;` as one statement, which fails on Fabric. Splitting into individual statements and using SHOWPLAN_XML makes `dbt_utils.validate_sql` functional.
**Upstream:** No `validate_sql.sql` macro exists in `upstream/main` under `dbt/include/fabric/macros/utils/`, so `dbt_utils.validate_sql` simply doesn't work on the upstream adapter.

### 012ca5d6 — 2026-02-20 — BUG_FIX
**Message:** avoid unnamed column warning for get_intervals_between
**What:** Added a `fabric__get_intervals_between` macro that aliases the datediff column as `diff` instead of leaving it unnamed.
**Why:** `dbt_utils.get_intervals_between` relies on calling `dbt.get_intervals_between`; without an alias, Fabric's query produces an unnamed column warning.
**Upstream:** No `date_spine.sql` in `upstream/main` under `dbt/include/fabric/macros/utils/`.

### 245e899a — 2026-02-20 — INFRA: add dependabot automerge workflow + trim trailing newline in integration-tests.yml

### 4aa51492 — 2026-02-21 — INFRA: bump test timeouts in `tests/conftest.py`

### bc7105df — 2026-02-21 — NEW_FEATURE
**Message:** implement array_append
**What:** Added `fabric__array_append` macro using `JSON_MODIFY(... 'append $', new_element)` and reworked `fabric__array_construct` to support an `as_json` argument and empty input lists. Unskipped `TestArrayAppendFabric`.
**Why:** `dbt_utils.array_append` was unsupported. JSON_MODIFY provides a clean T-SQL implementation.
**Upstream:** Upstream has `array_construct.sql` only — no `array_append.sql` exists. Upstream's `fabric__array_construct` also doesn't handle empty inputs or JSON return type.

### d1fded1e — 2026-02-21 — NEW_FEATURE
**Message:** implement array_concat
**What:** Added `fabric__array_concat` macro that handles empty arrays and concatenates two JSON arrays via string surgery. Unskipped `TestArrayConcatFabric`.
**Why:** `dbt_utils.array_concat` was unsupported. T-SQL has no native JSON array concat.
**Upstream:** No `array_concat.sql` in `upstream/main`.

### 32f9572e — 2026-02-21 — REFACTOR
**Message:** format incremental mat
**What:** Reformatted the incremental materialization macro (whitespace + comments).

### 257c8999 — 2026-02-21 — DBT_NATIVE_REWRITE
**Message:** refactor incremental materialization logic and unskipped tests for Python models
**What:** Replaced the upstream pattern of dropping the target and recreating with a dbt-native intermediate-relation + backup swap pattern using `make_intermediate_relation`, `make_backup_relation`, `drop_relation_if_exists`, and `rename_relation`. Also moved `pre/post_hooks(inside_transaction=False)` outside the transaction (proper dbt semantics) and moved `build_model_constraints` outside the materialization body. Unskipped `TestPythonIncrementalTestsFabric` and `TestPySparkTestsFabric`.
**Why:** Dropping and recreating the target is unsafe (data loss if creation fails); the dbt-native swap pattern (used by dbt-postgres et al.) gives atomic-like semantics. Also unblocks Python incremental models.
**Upstream:** Upstream `dbt/include/fabric/macros/materializations/models/incremental/incremental.sql` still drops the target with `adapter.drop_relation(target_relation)` before re-creating it: `-- Dropping target relation if exists / {{ adapter.drop_relation(target_relation) }} / {%- call statement('main') -%} / {{ get_create_table_as_sql(False, target_relation, sql)}}`.

### 9fce9846 — 2026-02-21 — INFRA: package updates

### b9bd8243 — 2026-02-21 — INFRA: dbt-core update to 1.11

### b0c35576 — 2026-02-21 — REVERT_OR_MODIFY
**Message:** restore skip on other dataframe types
**What:** Re-added `@pytest.mark.skip` to `TestPySparkTestsFabric`.
**Notes:** Modifies 257c8999 in this batch (which had unskipped it).

### aef2872e — 2026-02-21 — TEST
**Message:** add more tests from dbt-adapter-tests update
**What:** Added `TestMergeExcludeColumnsFabric`, `TestFabricStoreTestFailuresLimit`, `TestFabricUnitTestQuotedReservedWordColumnNames`, and removed a stale `--TODO` comment from `fabric__alter_relation_add_remove_columns`.

### 679d9915 — 2026-02-21 — TEST
**Message:** enhance incremental materialization logic and add tests for bad strategy handling
**What:** Hoisted `incremental_predicates` and `strategy_sql_macro_func` to top of macro (strategy validated even on first run). Added `TestIncrementalBadStrategyFabric` and a (skipped) `TestGetCatalogForSingleRelationFabric`.

### 47a008b9 — 2026-02-21 — TEST
**Message:** add tests for persist docs functionality in Fabric with skip markers
**What:** Added persist_docs tests, all skipped because Fabric does not support `COMMENT ON`.

### 95cf08d3 — 2026-02-21 — TEST
**Message:** add new test TestFabricShowSqlHeader
**What:** Imports `BaseShowSqlHeader` for completeness (no new class).

### e78e1af0 — 2026-02-21 — TEST
**Message:** add new test for sample mode functionality in Fabric
**What:** Added `TestSampleModeTestFabric` overriding `input_model_sql` to use `DATETIME2(6)` casts.

### 6cd55d6a — 2026-02-21 — ANTI_PATTERN_REMOVED
**Message:** remove unnecessary check in relation drop
**What:** Removed the dead `elif relation.type == 'table'` branch (assigning unused `object_id_type`) and the `raise_not_implemented` else-branch from `fabric__get_drop_sql`.
**Why:** Branches were dead — `object_id_type` is never referenced; the actual drop is `EXEC('DROP {{ relation.type }} IF EXISTS ...')`. The else-branch prevented dropping function relations.
**Upstream:** Upstream `dbt/include/fabric/macros/adapters/relation.sql` still contains the dead branches.

### 4ab425e7 — 2026-02-21 — BUG_FIX
**Message:** create_or_replace_clone should drop pre-existing clones
**What:** Added `{{ get_drop_sql(target_relation) }}` inside `fabric__create_or_replace_clone` so the clone DDL works when the target already exists. Added `TestFabricClonePossible` and `TestFabricCloneSameSourceAndTarget` tests.
**Why:** `CREATE TABLE ... AS CLONE OF ...` fails if target exists.
**Upstream:** Upstream `clone.sql` only calls `adapter.drop_relation(target_relation)` in the materialization wrapper, not in the macro itself — calling `fabric__create_or_replace_clone` directly (as `BaseClonePossible` does) fails.

### 213c5465 — 2026-02-21 — TEST
**Message:** add tests for pre and post hooks functionality in Fabric
**What:** Added `TestPrePostModelHooksFabric`, `TestPrePostModelHooksInConfigWithCountFabric`, `TestPrePostRunHooksFabric` with Fabric-specific column types.

### 5226156539 — 2026-02-21 — ANTI_PATTERN_REMOVED
**Message:** set query tag to adapter name by default
**What:** Removed a spurious `{{ log(config.get('query_tag','dbt-fabric')) }}` call that fired on every macro invocation and renamed the default label to `dbt-fabric-samdebruyn`.
**Why:** The log call was debug leftover that spammed dbt logs on every SQL statement.
**Upstream:** Upstream still has `{{ log (config.get('query_tag','dbt-fabric'))}}` at the top of `fabric__apply_label`.

### faac4b31 — 2026-02-21 — TEST
**Message:** add more snapshots tests from upstream
**What:** Added 940 lines of snapshot config and snapshot new-record-mode tests.

### 9a136583 — 2026-02-21 — NEW_FEATURE
**Message:** add scalar function support
**What:** Added `function` as a Fabric relation type, added `fabric__scalar_function_sql` / `..._create_replace_signature_sql` / `..._body_sql` / `..._formatted_scalar_function_args_sql` macros, merged the duplicate `list_relations_without_caching`/`get_relation_without_caching` queries into one CTE that also lists scalar functions, added a comprehensive functions test suite.
**Why:** Add dbt 1.11 scalar function (UDF) support for Fabric DW.
**Upstream:** Upstream `policies.py` has no `Function` enum value and `metadata.sql` has separate macros that only union tables+views, no function awareness.

### a9b3a866 — 2026-02-22 — TEST
**Message:** fix tests after changing label
**What:** Updated constraints tests for the new `dbt-fabric-samdebruyn` label; added (skipped) `TestPythonEmptyTestsFabric` and `TestPythonSampleTestsFabric`.

### 2c96f574 — 2026-02-22 — NEW_FEATURE
**Message:** add support for default args in scalar funcs
**What:** Extended `fabric__formatted_scalar_function_args_sql` to emit `@arg type = default` when `arg.default_value` is set; added `TestSqlUDFDefaultArgSupportFabric`.

### aa258587 — 2026-02-22 — INFRA: set `cancel-in-progress: false` on integration test workflows

### b701d180 — 2026-02-22 — INFRA: ruff format

### 2b6110aa — 2026-02-22 — BUG_FIX
**Message:** fix default value check for scalar functions
**What:** Switched `arg.default_value is not none` to `arg.get('default_value', none)` and added `fabric__scalar_function_volatility_sql` that warns instead of erroring on unknown volatility.
**Why:** `arg.default_value` raises if the key is missing; `.get()` is safe. Volatility is a no-op in T-SQL.
**Notes:** Bugfix for code introduced in 2c96f574 of this batch.

### d05ffcd8 — 2026-02-22 — REFACTOR
**Message:** refactor comments to use block syntax for clarity
**What:** Switched inline `--` SQL comments to Jinja `{# #}` block comments in snapshot helpers/macros.

### ca100f1c — 2026-02-22 — TEST
**Message:** fix python model tests
**What:** Unskipped `TestPythonEmptyTestsFabric` and `TestPythonSampleTestsFabric` with `FabricInputModel` fixture supplying T-SQL-compatible event_time data.

### e317baa1 — 2026-02-22 — BUG_FIX
**Message:** Made sure Livy sessions are reused and add test for concurrent usage
**What:** Three fixes in `fabric_api_client.py`: (1) the existing-session lookup was reading `response.json().get("value", [])` but the API returns `items` → no existing session was ever found; (2) wrapped session-lookup-and-create in a `threading.Lock` so concurrent threads share one session instead of each creating its own; (3) bumped Livy session/statement polling timeouts to 10/60 minutes. Added `TestConcurrentPythonModelsPerformance` exercising 10 parallel Python models.
**Why:** Wrong JSON key prevented session reuse; missing lock caused N sessions per N threads → quota exhaustion.
**Upstream:** N/A — FabricLivy infrastructure is fork-only.

### 940cc049 — 2026-02-22 — INFRA: delete `dependabot_automerge.yml`, rename CI workflow

### 1e437574 — 2026-02-23 — DOCS: add dbt Core 1.11 + scalar function support to feature-comparison.md

### 0b8e93a0 — 2026-02-23 — DOCS: typo fix in feature-comparison.md

### fd6402f4 — 2026-02-22 — NEW_FEATURE
**Message:** setup integration testing for DE adapter
**What:** Scaffolds the FabricSpark adapter: adds `dbt-spark` optional dependency group `[spark]`, creates `src/dbt/adapters/fabricspark/__version__.py`, `src/dbt/include/fabricspark/__init__.py`, `src/dbt/include/fabricspark/dbt_project.yml`, splits tests into `tests/fabric/` and `tests/fabricspark/`, exposes `FabricApiClient` from the `fabric` package, parametrises conftest by adapter type, wires CI to run both DW and DE jobs.
**Why:** Begin supporting Fabric Lakehouse / Spark as an adapter target.
**Upstream:** Upstream has no FabricSpark adapter — no `dbt/adapters/fabricspark/`, no `dbt/include/fabricspark/`, no `[spark]` extra.

### 03094937 — 2026-02-23 — NEW_FEATURE
**Message:** working Spark sql commands
**What:** Initial working FabricSpark adapter: extracts common base classes (`BaseFabricConnectionManager`, `BaseFabricCredentials`, `BaseFabricAdapter`); adds `fabric_livy_session.py`; adds `fabricspark_adapter.py`, `fabricspark_connection.py`, `fabricspark_connection_manager.py`, `fabricspark_credentials.py`, `fabricspark_cursor.py`, `fabricspark_relation.py`; initial `tests/fabricspark/adapter/test_basic.py`.
**Upstream:** Entirely fork-only.

### 8710c415 — 2026-02-23 — INFRA: include `with-spark` branch in lint-format workflow

### 57c4c295 — 2026-02-23 — BUG_FIX
**Message:** use busy live sessions if possible
**What:** Added `"busy"` to the list of acceptable Livy session states when looking up an existing session, and inverted lock order to double-checked locking.
**Why:** Previously, an actively-running session (`busy`) was treated as unavailable, causing a new parallel session to be created; busy sessions are usable because Livy queues additional statements.
**Upstream:** N/A — fork-only.

### 2b3113c6 — 2026-02-23 — BUG_FIX
**Message:** make login_timeout always have a value
**What:** Changed `FabricCredentials.login_timeout` from `int | None = 0` to `int = 0`.
**Why:** Downstream code passes the value into pyodbc which expects an int.
**Upstream:** Upstream `fabric_credentials.py` has the same `login_timeout: int | None` typing.

### 2211d4e1 — 2026-02-23 — DBT_NATIVE_REWRITE
**Message:** clean up connection managers
**What:** Deleted the custom `add_query` reimplementation in `FabricConnectionManager` (manually calling `fire_event(ConnectionUsed)`, `fire_event(SQLQuery)`, `fire_event(SQLQueryStatus)`, re-implementing the cursor binding loop) and replaced it with a thin override that only converts datetimes to ISO strings then delegates to `super().add_query()`. Moved `add_begin_query`/`add_commit_query` no-op implementations into the shared `BaseFabricConnectionManager` (DRY). Inlined `pyodbc` import into methods that need it. Improved `get_response` to parse `statement id:` from cursor messages and populate `query_id`.
**Why:** The custom `add_query` duplicated logic that `SQLConnectionManager.add_query` already provides via dbt-adapters, and skipped retry/error pathways.
**Upstream:** Upstream `dbt/adapters/fabric/fabric_connection_manager.py` still has the entire custom `add_query` (line 630+) and an `atexit.register` snapshot manager (line 602).

### 6400f324 — 2026-02-23 — NEW_FEATURE
**Message:** share config in conftest and custom livy session name
**What:** Made the Livy session name user-configurable via `livy_session_name` credential (default `dbt-fabric-samdebruyn`); added it to the connection key so different sessions use different connections; refactored conftest to share common credential settings between adapters.

### 169a8968 — 2026-02-23 — NEW_FEATURE
**Message:** Enhance Fabric integration: add environment variables for tests, improve Livy session handling, and implement cursor functionalities
**What:** Substantial expansion of the FabricSpark cursor (description/rowcount/fetchmany/fetchall) and rework of LivySession statement-result handling; added FabricSpark base adapter macro `fabricspark/macros/adapters.sql`.

### 5784378b — 2026-02-23 — REFACTOR
**Message:** cursor impl complete
**What:** One-line tweak to `fabricspark_cursor.py`.

### 643330cb — 2026-02-24 — REFACTOR
**Message:** Refactor LivySubmissionResult and LivySessionResult classes for improved error handling and clarity in submission responses
**What:** Converted `LivySessionResult` from a regular class with manual `__init__` to a `@dataclass`; introduced `LivySubmissionResult` (dataclass subclass of `PythonSubmissionResult`) with `success` and `error_message` fields; `generate_python_submission_response` now passes `query_id` and the actual error message through to the AdapterResponse.

### b08a8cc2 — 2026-02-24 — TEST
**Message:** Add test for invalid incremental strategy in TestIncrementalBadStrategySpark
**What:** Overrode `test_incremental_invalid_strategy` to assert the FabricSpark-specific error message.

### a06a2e27 — 2026-02-24 — BUG_FIX
**Message:** Fix json_data initialization in LivySessionResult to use field default_factory
**What:** Replaced `json_data: dict[str, Any] | None = {}` with `field(default_factory=dict)` in the `LivySessionResult` dataclass.
**Why:** Mutable default arguments in dataclasses cause shared state between instances.
**Notes:** Bug fix for code introduced in 643330cb of this batch.

### 83d5b7b — 2026-02-24 — NEW_FEATURE
**Message:** Add value conversion methods to FabricSparkCursor for Spark SQL types
**What:** Adds `_convert_value` and `_convert_row` to `FabricSparkCursor` that map Livy's JSON payload schema types to proper Python types (int, float, Decimal, bool, date, datetime, bytes) so DB-API consumers receive typed values instead of strings.
**Why:** Livy returns everything as JSON strings; without typed conversion downstream dbt code and tests would see strings where they expect dates/numbers.
**Upstream:** Upstream has no FabricSpark adapter at all (`fabricspark/` does not exist under `upstream/main`).

### 2a15ff7 — 2026-02-24 — INFRA: bump test `query_timeout` from 60s to 300s in conftest.

### c9dc049 — 2026-02-24 — NEW_FEATURE
**Message:** Add FabricSparkRelationType and update dbt_project.yml; enhance tests for materialized views
**What:** Defines a `FabricSparkRelationType` StrEnum (Table, CTE, MaterializedView, Ephemeral, External, PointerTable, Function) and wires it into `FabricSparkRelation`; sets `+materialized: materialized_view` as the FabricSpark default in the included `dbt_project.yml`; adds stub `create`/`drop` macros for materialized views; expands the BaseSimpleMaterializations test to cover materialized-lake-view swap.
**Why:** Establish materialized-lake-view as a first-class relation type and default materialization for the new FabricSpark adapter.
**Upstream:** No FabricSpark in upstream.

### 1678fdc — 2026-02-25 — NEW_FEATURE
**Message:** Enhance Fabric connection managers and macros for materialized views
**What:** (a) Adds explicit no-op transaction methods (`begin`, `commit`, `_rollback`, `commit_if_has_connection`) to `BaseFabricConnectionManager`. (b) Forces `_message="OK"` when adapter returns an empty message in both Fabric and FabricSpark `get_response`. (c) Adds full `materialized_view` materialization (intermediate/backup swap, grants, hooks, refresh path), a `fabricspark__get_materialized_view_configuration_changes` helper that diffs `SHOW CREATE MATERIALIZED LAKE VIEW`, and a Fabric-specific `spark__drop_relation` override that emits `drop materialized lake view`.
**Why:** Make materialized lake views work end-to-end (create / drop / alter / configuration-change detection) and ensure transaction calls from dbt-core become no-ops on Fabric. Empty `_message` previously broke logging that expected a string.
**Upstream:** No FabricSpark. The Fabric connection manager in upstream does not set a fallback "OK" message (`dbt/adapters/fabric/fabric_connection_manager.py` returns whatever the cursor emitted, which can be empty).

### f394aef — 2026-02-25 — TEST
**Message:** add dbt test harness for fabricspark
**What:** Adds 58 FabricSpark test stub files mirroring the Fabric harness (`test_basic.py` extensions, `test_constraints`, `test_grants`, `test_python_model`, full `utils/` set, etc.) — bodies are mostly `pass` to wire up the harness.
**Why:** Bootstrap the dbt-tests-adapter coverage matrix for FabricSpark before adapting each test case.

### 193f0f1 — 2026-02-27 — INFRA: drop `with-spark` branch from CI triggers; FabricSpark work merged into main fork branch.

### 0a018f8 — 2026-02-08 — DBT_NATIVE_REWRITE
**Message:** mssql-python version
**What:** Replaces the entire `pyodbc` driver path with Microsoft's native `mssql-python` package. Removes the custom `CI.Dockerfile` (ODBC Driver 18 install), drops `driver` credential field, drops `Pooling`, `SQL_ATTR_TRACE`, `APP=...`, `pyodbc.pooling = True`, `pyodbc.odbcversion = "3.8"`, "Windows Login" and "SQL Authentication" branches; rewrites the token provider to return mssql-python-style `attrs_before`. Updates docs and pyproject accordingly.
**Why:** Eliminates an out-of-process ODBC dependency (no system driver install needed), removes a large amount of pyodbc-specific tuning, and aligns with the Microsoft-maintained pure-Python driver. This is the central change that makes the fork installable via plain `pip` on any platform without ODBC binaries.
**Upstream:** Upstream still uses pyodbc + ODBC Driver 18. `upstream/main:dbt/adapters/fabric/fabric_connection_manager.py` imports `pyodbc` and the upstream `pyproject.toml`/setup still depends on it.

### 4a4b6d9 — 2026-02-08 — BUG_FIX
**Message:** prepare for mssql-python sqltype fix
**What:** Changes `self.connections.data_type_code_to_name(column_type_code)` to `column_type_code.type_code` in `FabricAdapter.get_column_schema_from_query` to match an upcoming change in mssql-python's `cursor.description`.
**Why:** Pre-emptive accommodation of a planned mssql-python change.
**Notes:** Reverted by 1a7207b inside this same batch.

### 1a7207b — 2026-02-17 — REVERT_OR_MODIFY
**Message:** Revert "prepare for mssql-python sqltype fix"
**What:** Reverts 4a4b6d9 because the planned mssql-python change did not land in the form anticipated.
**Notes:** Reverts 4a4b6d9 from this same batch.

### 954faac — 2026-02-27 — INFRA: bump `mssql-python` floor to `>=1.4.0`.

### b645e7a — 2026-02-27 — DBT_NATIVE_REWRITE
**Message:** Update authentication method and clean up imports in Fabric adapter
**What:** Changes the default `authentication` value on `BaseFabricCredentials` from `"auto"` to the actual mssql-python value `"ActiveDirectoryDefault"`; moves the `mssql_python` import out of module scope into the connection-manager methods that need it; cleans typing; removes the `"authentication": "auto"` test override in conftest now that the default does the right thing.
**Why:** Stop pretending there's a custom "auto" mode and just use the driver's documented default identity, simplifying both the credentials surface and the token provider call paths.
**Upstream:** Upstream still relies on the pyodbc-specific authentication tokens and conditional handling.

### 044e4d7 — 2026-02-27 — INFRA: add Python 3.14 to the integration-test matrix.

### 5a94f78 — 2026-02-28 — INFRA: bump `requires-python` lower bound to allow Python 3.14; updates `uv.lock` accordingly.

### 581a734 — 2026-02-28 — TEST
**Message:** Add tests for current timestamp functionality in FabricSpark adapter
**What:** Wires `BaseCurrentTimestamps` plus a custom-expected-SQL fixture into `tests/fabricspark/adapter/utils/test_timestamps.py`.
**Why:** Cover `current_timestamp` macro behavior on FabricSpark.

### 8646ee9 — 2026-02-28 — TEST
**Message:** Add comprehensive tests for listagg functionality in FabricSpark adapter
**What:** Subclasses `BaseListagg` and adds seeds plus expected-output fixtures in `tests/fabricspark/adapter/utils/test_listagg.py`.
**Why:** Cover `listagg` on FabricSpark.

### 7f29dbf — 2026-02-28 — TEST
**Message:** Add pytest fixtures for float and int type tests in FabricSpark adapter
**What:** Adds seeds + expected-types fixtures to the FabricSpark `test_data_types.py` subclasses for float and int types.

### 4a5752b — 2026-02-28 — REFACTOR: drop unused `BaseCurrentTimestamp` import from `test_current_timestamp.py`.

### cccd66d — 2026-02-28 — TEST: add seeds fixture for `BaseLastDay` in FabricSpark.

### d2cc7cb — 2026-02-28 — TEST: add seeds fixture for `BaseSplitPart` in FabricSpark.

### 546fdad — 2026-02-28 — REVERT_OR_MODIFY
**Message:** Revert "allow Python 3.14"
**What:** Reverts the requires-python bump from 5a94f78 — Python 3.14 not yet practical for dependencies.
**Notes:** Reverts 5a94f78 from this same batch.

### fb31c03 — 2026-02-28 — REVERT_OR_MODIFY
**Message:** Revert "tests with Python 3.14"
**What:** Reverts the CI matrix addition from 044e4d7.
**Notes:** Reverts 044e4d7 from this same batch.

### df44b2d — 2026-02-28 — DBT_NATIVE_REWRITE
**Message:** Refactor materialized view logic and add refresh macro for lake views
**What:** Removes the special "no_op" path (`if build_sql == ''`) in the materialized_view materialization — always run pre/post hooks and the main statement. Adds `fabricspark__refresh_materialized_view(relation) -> refresh materialized lake view ...`.
**Why:** Align with the standard dbt materialized-view materialization shape and provide a real refresh implementation rather than a no-op fallback.
**Upstream:** No FabricSpark in upstream.

### e17d0a4 — 2026-02-28 — NEW_FEATURE
**Message:** implement relation type fetching
**What:** Adds `_namespace_to_parts` (parses `workspace.database.schema` backtick form) and `_build_spark_relation_list` to `FabricSparkAdapter`; inspects the `information` block from `show table extended` and assigns `FabricSparkRelationType.MaterializedView` when it contains `Type: MATERIALIZED_LAKE_VIEW`; otherwise Table. Adds `information` and `workspace` fields to `FabricSparkRelation`.
**Why:** Needed for catalog/list-relations to distinguish materialized lake views from regular Delta tables; dbt-spark's own logic does not know about Fabric-specific MATERIALIZED_LAKE_VIEW.
**Upstream:** No FabricSpark in upstream.

### b32853b — 2026-02-28 — DBT_NATIVE_REWRITE
**Message:** use get_catalog from Base instead of Spark
**What:** Delegates `get_catalog` to `BaseAdapter.get_catalog` instead of inheriting `SparkAdapter`'s implementation; declares `SchemaMetadataByRelations` capability so dbt-core uses the relation-batched path.
**Why:** SparkAdapter's `get_catalog` issues per-database queries that don't fit Fabric's workspace/lakehouse/schema layout; the base implementation works once capabilities and `list_relations_without_caching` are correctly overridden.
**Upstream:** No FabricSpark in upstream.

### 41f2bf0 — 2026-02-28 — NEW_FEATURE
**Message:** refactor adapter to allow databases
**What:** Treats Fabric workspace as catalog and the lakehouse as database. Adds `FabricSparkColumn` (extends SparkColumn with `table_catalog`); overrides `list_schemas` to extract just the schema from the 3-part namespace; rewrites `get_catalog` to use namespace-parallel `submit_connected` futures and then column-parallel futures, mirroring the BaseAdapter pattern; overrides `parse_describe_extended` to set `table_catalog`; adds `get_relation` override; adds `fabricspark__list_relations_without_caching` (`show table extended in {db} like '*'`), `fabricspark__generate_database_name`, `fabricspark__drop_relation`, and a metadata.sql file. Also propagates a Livy error case where `run_statement` returns a `LivySessionResult` instead of an int by raising `DbtDatabaseError`.
**Why:** Fabric Lakehouses are addressable as 3-part `workspace.database.schema`; the upstream Spark adapter assumes 2-part `schema.table` and would produce empty/broken catalogs against Fabric.
**Upstream:** No FabricSpark in upstream.

### a6bbb86 — 2026-02-28 — REFACTOR
**Message:** Refactor FabricSparkAdapter and FabricSparkRelation to enhance relation type handling and streamline catalog fetching
**What:** Adds `FabricSparkRelation.try_translate_type` to translate `MATERIALIZED_LAKE_VIEW`/`MANAGED` strings to enum values; reuses it in `parse_describe_extended`; extracts a reusable `get_catalog_by_relations` helper and calls it from `get_catalog`; swaps capability `GetCatalogForSingleRelation` (later reverted) back to `SchemaMetadataByRelations`.
**Why:** Cleaner separation; reuse of the by-relations path between full catalog and single-relation catalog.
**Notes:** Pure internal restructure of code added in 41f2bf0.

### 5f53a2a — 2026-02-28 — TEST: skip `TestGetCatalogForSingleRelationSpark` with reason "Capability not implemented in FabricSpark."

### 811f2d1 — 2026-03-01 — NEW_FEATURE
**Message:** Enhance FabricSpark relation handling and add materialized view macros
**What:** Marks `FabricSparkRelation` materialized views as replaceable, marks tables + materialized views as renameable; specializes the materialization macro to `adapter='fabricspark'`; reworks the build-SQL decision tree (create directly when missing, create-and-swap when existing relation is a different type, refresh otherwise); adds `fabricspark__get_rename_materialized_view_sql`, `fabricspark__rename_relation`, `fabricspark__drop_table`, `fabricspark__get_rename_table_sql`.
**Why:** Required to support the rename-and-swap branch of the standard dbt materialized-view lifecycle; dbt-spark does not provide these macros.

### 614e7cc — 2026-03-01 — BUG_FIX
**Message:** Skip processing for temporary views in FabricSparkAdapter
**What:** In `_build_spark_relation_list`, skip rows whose namespace is null/empty (temporary views) instead of trying to parse them with `_namespace_to_parts` (which would raise "Unexpected namespace format").
**Why:** `show table extended` includes session-scoped temporary views with an empty namespace; without this guard `dbt list`/catalog crashes whenever any temp view exists in the Livy session.

### a024a65 — 2026-03-01 — REFACTOR
**Message:** Clarify comment for skipping temporary views in FabricSparkAdapter
**What:** Cosmetic: ` # temporary view` → `  # temporary view` (double space before `#`) to satisfy ruff.

### 5fec7f0 — 2026-05-13 — DOCS: initial 440-line `CLAUDE.md` describing fork architecture, TDD workflow, dispatch system, etc.

### e427b58 — 2026-05-14 — DOCS: expand `CLAUDE.md` with documentation-website details and the Spark SQL vs T-SQL limitations table.

### 8b0dcc2 — 2026-05-14 — TEST
**Message:** Add extra tests for catalog columns in dbt-fabric adapter
**What:** Adds `tests/fabric/adapter/test_catalog_columns.py` with seven assertions about column presence, sequential indexes, and correct types (int/varchar/decimal/bit/datetime2) in `docs generate` output.
**Why:** Regression tests for the catalog macro's column metadata, in preparation for adding row-count stats (commit a3f0dc7).

### 7ecc158 — 2026-05-14 — TEST
**Message:** Add regression test for split_part scalar subexpression (microsoft/dbt-fabric#358)
**What:** Adds `tests/fabric/adapter/test_split_part.py` exercising `dbt.split_part` twice in a single SELECT.
**Why:** Documents and locks in that the fork's `fabric__split_part` (a derived-table subquery) works in the scalar-subexpression context where upstream issue #358 was reported. Upstream (`upstream/main:dbt/include/fabric/macros/utils/split_part.sql`) is similar, suggesting the issue is implementation-flow specific. Test commit only — no production code change.

### 7e32009 — 2026-05-14 — TEST
**Message:** Add regression test for model.timing in on-run-end context (microsoft/dbt-fabric#366)
**What:** Adds `tests/fabric/adapter/test_timing.py` asserting that `result.timing` contains both `compile` and `execute` entries with non-None timestamps, and that the data is reachable via `run_results.json` and the `on-run-end` Jinja context.
**Why:** Per the commit message, upstream reports empty timing data; the fork's connection manager preserves it. Test commit only — no production code change.

### 136ad4f — 2026-05-14 — INFRA/DOCS: add `docs_build/site` and `.claude` to `.gitignore`; tweak CLAUDE.md test-run guidance.

### 24f369f — 2026-05-14 — INFRA
**Message:** Migrate documentation from mkdocs-material to Zensical (#61)
**What:** Removes `mkdocs.yml`, adds `zensical.toml`, switches `pyproject.toml` deps from `mkdocs-material` to `zensical`, updates the Cloudflare Pages deploy script.
**Why:** Tooling switch for the docs site.

### a3f0dc7 — 2026-05-14 — NEW_FEATURE
**Message:** Add approximate row count statistics to catalog generation (#58)
**What:** Adds four `stats:row_count:*` columns to both branches of `fabric__get_catalog` (full and single-relation), populated via `objectpropertyex(tv.object_id, 'Cardinality')`. Result shows up as a row-count box on every BASE TABLE in `dbt docs`.
**Why:** Zero-config visibility of table sizes in the dbt docs catalog.
**Upstream:** Upstream's `dbt/include/fabric/macros/adapters/catalog.sql` selects `null as column_comment` and stops there — no stats columns.

### 1f018582 — 2026-05-14 — BUG_FIX
**Message:** Fix rows_affected reporting -1 for table materializations (#57)
**What:** In `FabricConnectionManager.execute`, move `response = self.get_response(cursor)` to *after* the `while cursor.nextset()` loop so `cursor.rowcount` reflects the final INSERT/CTAS statement instead of an intermediate CREATE VIEW that has rowcount -1.
**Why:** Table materializations were always reporting -1 rows affected.
**Upstream:** Upstream has the same fix at `dbt/adapters/fabric/fabric_connection_manager.py:786-788` ("This fixes rows_affected being -1 for table materializations"), but only after this fork's PR was made — so the fork drove the upstream change.

### b24bdb3 — 2026-05-14 — NEW_FEATURE
**Message:** Add CLUSTER BY support for Fabric DW tables (#59)
**What:** Adds `cluster_by` config option to `FabricConfigs`; adds `build_cluster_by_clause(temporary)` dispatch wrapper plus `fabric__build_cluster_by_clause` that bracket-quotes columns (with `]` escaped as `]]`) and renders `WITH (CLUSTER BY (...))`. Wires it into both the contracts-enforced and plain `fabric__create_table_as` branches; skips when temporary. Adds docs page and 5 integration tests covering single, multi, no-cluster, contract, and incremental usage.
**Why:** Fabric DW automatic clustering is documented at Microsoft Learn but not exposed by the upstream adapter.
**Upstream:** Upstream `FabricConfigs` and `create_table_as.sql` have no `cluster_by` field or clause.

### f0f70031 — 2026-05-14 — INFRA
**Message:** Test infrastructure improvements (#55)
**What:** Adds `--isolated` pytest flag that provisions temporary Fabric DW + Lakehouse items per test session via `tests/isolated_items.py` (155 lines) for multi-agent parallelism; deep-merges `dbt_project_yml` so the FabricSpark `+materialized: materialized_view` default isn't clobbered; replaces unbounded recursive retry with a 10-iteration iterative loop in `_request`; per-item timeout tracking in `wait_for_all`; raises if 202 Accepted lacks a `Location` header; adds `FabricStoreTestFailuresMixin`; refactors timing assertions; adds retry logic for transient snapshot-isolation errors in DW tests; adds `tests/unit/__init__.py`.

### 91a4728 — 2026-05-14 — INFRA: ruff import-sort fixes for `test_split_part.py` and `test_timing.py`.

### cd887943 — 2026-05-14 — INFRA: bump dependencies for CVEs (requests, dbt-common, pytest, urllib3, cryptography, python-dotenv, PyJWT, deepdiff).

### 1dae9ae — 2026-05-14 — INFRA
**Message:** Fix Cloudflare Pages build by removing unsupported -d flag (#69)
**What:** `zensical build` doesn't accept `-d`; use `site_dir` in `zensical.toml` instead.

### 414835b — 2026-05-14 — BUG_FIX
**Message:** Fix T-SQL identifier quoting to use brackets (#56)
**What:** Adds `FabricAdapter.quote()`, `FabricColumn.quoted`, `FabricRelation.quoted()` that wrap identifiers in `[ ]` and escape literal `]` as `]]`. Rewrites `fabric__get_columns_in_relation`, `fabric__alter_relation_add_remove_columns`, `fabric__get_use_database_sql`, `fabric__create_table_as` (contract listColumns), and `fabric__create_columns` (snapshot helper) to use bracket quoting with `]`→`]]` escapes. Adds 9 unit tests for `get_use_database_sql` and 2 integration tests for reserved-word column names (`[order]`, `[select]`, `[group]`, `[table]`) including `on_schema_change='append_new_columns'`.
**Why:** Upstream uses bracket quoting in `quote()` but does NOT escape `]`; downstream macros mix double-quote and bracket forms. Reserved-word columns silently break; identifiers containing `]` would terminate the bracket prematurely (potential T-SQL injection vector).
**Upstream:** `upstream/main:dbt/adapters/fabric/fabric_adapter.py:37` defines `quote` as `"[{}]".format(identifier)` with no escaping. Upstream `columns.sql` uses unescaped `[{{ column.name }}]`. Upstream has no `FabricColumn.quoted` or `FabricRelation.quoted` override.

### 68d82279 — 2026-05-14 — DOCS: add `docs/roadmap.md` (339 lines) and link from `feature-comparison.md` and `zensical.toml` nav.

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

### 91b47d68 — 2026-05-15 — TEST
**Message:** Fix FabricSpark listagg test (#110)
**What:** Enables the FabricSpark listagg test by importing the shared `fixture_listagg.models__test_listagg_yml` and fixing the yml key that previously pointed at the SQL content.
**Why:** Test was misconfigured (YAML key pointed at SQL content); inherited `spark__listagg` from dbt-spark works correctly via `dependencies=["spark"]`.

### 7bfbf943 — 2026-05-15 — BUG_FIX
**Message:** Fix FabricSpark column type tests (#108)
**What:** Adds Spark-name-aware `is_string`, `is_integer`, `is_numeric` overrides on `FabricSparkColumn` so dtype names like `string`, `int`, `decimal(p,s)` are correctly classified; also overrides the column-types test model with CAST-based Spark SQL.
**Why:** Base `Column` only recognises PG-style names so any code path checking column type kind would mis-classify on Spark. Fixing it in Python (not Jinja workaround) means all callers benefit.
**Upstream:** Upstream has no FabricSpark adapter at all, so the bug does not surface there. The pattern of fixing type recognition in Python rather than via a custom `is_type` macro is a general dbt-native improvement.

### 0857efc1 — 2026-05-15 — ANTI_PATTERN_REMOVED
**Message:** Use MERGE for snapshots, remove apply_label(), add --with-python flag (#142)
**What:** (1) Deletes the custom `fabric__snapshot_merge_sql` macro (30 lines of UPDATE+INSERT) so dbt falls through to the default MERGE-based `default__snapshot_merge_sql`, only wrapping with the required trailing semicolon. (2) Removes the `apply_label()` helper macro and all callers in `catalog.sql`, `columns.sql`, `metadata.sql`, `relation.sql`, `merge.sql`, `create_table_as.sql`, `seeds/helpers.sql`. (3) Adds `--with-python` pytest flag so Python model tests opt-in (matches `--with-grants`).
**Why:** The OPTION (LABEL) hint added no observable value; bundling the label with `;` coupled labeling to statement termination and forced custom overrides everywhere. Switching snapshots to native MERGE both simplifies code and uses a single atomic statement.
**Upstream:** `upstream/main:dbt/include/fabric/macros/materializations/snapshots/snapshot_merge.sql` still contains the UPDATE+INSERT 2-statement pattern with `apply_label()` interspersed. Upstream uses `apply_label()` across catalog.sql, columns.sql, metadata.sql, relation.sql, and incremental merge.sql.

### 789d8915 — 2026-05-16 — TEST
**Message:** Fix FabricSpark alias tests (#102)
**What:** Drops a custom `cast.sql` macro from the test fixture so global `string_literal` dispatches to `fabricspark__string_literal` (already adapter-correct).
**Why:** Fixture macros dispatched via `macro_namespace='test'` skip adapter macros; relying on global dispatch (`macro_namespace='dbt'`) lets the existing adapter macro be reached.

### ccd5149f — 2026-05-16 — TEST
**Message:** Fix FabricSpark catalog relation type tests (#103)
**What:** Parametrizes test cases with lowercase Spark enum values (`table`, `materialized_view`); removes a redundant duplicate model.
**Why:** Base test asserts uppercase SQL-standard relation type names; Spark uses lowercase.

### fc0a7342 — 2026-05-16 — TEST
**Message:** Override test_different_dataframes to exclude unsupported koalas_df (#96)
**What:** Excludes the koalas_df case from `test_different_dataframes` for FabricSpark.
**Why:** Koalas isn't available in the Fabric Spark runtime.

### 076f2ab1 — 2026-05-16 — TEST
**Message:** Fix FabricSpark basic tests with materialized_view overrides (#97)
**What:** Replaces `view` materializations with `materialized_view`, implements expected_catalog overrides for FabricSpark in TestDocsGenerateSpark / TestDocsGenReferencesSpark.
**Why:** FabricSpark targets schema-enabled Lakehouses where Spark SQL views are not yet supported, so MLVs are the materialization of choice; catalogs lack stats/owner since DESCRIBE TABLE EXTENDED doesn't expose them.

### 255a75be — 2026-05-16 — TEST
**Message:** Fix FabricSpark simple copy tests (#106)
**What:** Replaces view models with materialized_view, overrides test helpers to use `SHOW TABLES`, fixes profile target passthrough; uses delta + merge for incremental in this test.
**Why:** Default append strategy uses `INSERT INTO TABLE` which fails on FabricSpark with `REQUIRES_SINGLE_PART_NAMESPACE`.

### b54aac10 — 2026-05-16 — BUG_FIX
**Message:** Fix FabricSpark constraint tests and skip NOT NULL enforcement (#115)
**What:** Adds `fabricspark__alter_column_set_constraints` macro that warns and skips `NOT NULL` instead of issuing an `ALTER TABLE CHANGE COLUMN ... SET NOT NULL` (which Fabric Lakehouse Delta doesn't accept). Adjusts constraint test expectations.
**Why:** Fabric Lakehouse Delta does not support adding NOT NULL via ALTER (unlike Databricks Delta which dbt-spark targets); without this override, all constraint DDL fails.
**Upstream:** No FabricSpark adapter exists upstream. dbt-spark's macro (which gets inherited) assumes Databricks behaviour.

### c27fb4a2 — 2026-05-16 — TEST
**Message:** Fix FabricSpark seed tests (#104)
**What:** Replaces PostgreSQL types with Spark types in seed test fixtures, splits multi-statement SQL, handles bigint inference, fixes seed-with-dots edge case, replaces 3-class workaround with a single class using Spark-compatible DROP cleanup.
**Why:** Base fixtures assume PG; harness's `clear_test_schema` uses T-SQL.

### b6601d01 — 2026-05-16 — TEST
**Message:** Fix FabricSpark unit testing tests (#95)
**What:** Overrides unit-testing fixtures with Spark types, uses `table` materialization for the types test to avoid MLV_SCHEMA_MISMATCH, overrides reserved-word identifier quoting with backticks.
**Why:** Default fixtures use PG types and double-quoted identifiers.

### 70390d9e — 2026-05-16 — TEST
**Message:** Fix FabricSpark relation type change test (#93)
**What:** Cycles through materialized_view/table/incremental instead of view/table/incremental.
**Why:** Schema-enabled Lakehouses don't yet support Spark SQL views; the test would never pass.

### 6aa023c8 — 2026-05-16 — INFRA
**Message:** Add Livy session lifecycle management for CI runs (#147)
**What:** Pytest session-scoped fixture pre-creates one Livy session and deletes it on teardown; CI re-uses it instead of creating one per test class.
**Why:** Fabric enforces a 3-session concurrency cap; per-class sessions exhaust it under parallel execution.

### c181357d — 2026-05-16 — NEW_FEATURE
**Message:** Add Microsoft Purview integration for dbt metadata sync (#66)
**What:** Adds a complete Purview metadata sync subsystem: `PurviewClient` (Atlas/Purview REST), `PurviewSync` (model/column/lineage extraction), `purview_types.py` (TypedDicts), a `purview_sync` macro for both Fabric and FabricSpark, custom Purview type definitions (`dbt_metadata`, `dbt_transformation`, `fabric_warehouse_schema/table/column`, `fabric_lakehouse_table_column`), `persist_docs` integration, bulk single-call metadata push, tag→label sync, source/lineage graph, stale-lineage cleanup, lazy type registration, and full unit + integration test coverage.
**Why:** Enables `{{ purview_sync() }}` in `on-run-end` hooks so dbt projects can push descriptions, tags, business metadata, and lineage to Microsoft Purview without paid Purview scans on the Fabric workspace.
**Upstream:** No equivalent in upstream `microsoft/dbt-fabric` — Purview support is entirely new.

### ee83a005 — 2026-05-16 — NEW_FEATURE
**Message:** Port upstream: add token_credential authentication method (#80)
**What:** Adds `token_credential` auth — user supplies any `azure.core.credentials.TokenCredential` by dotted import path with optional kwargs. Wires it into the centralised `FabricTokenProvider`.
**Why:** Custom OAuth flows, token brokers, and non-standard Workload Identity setups need pluggable credentials. Port adapted from `microsoft/dbt-fabricspark@6cadd464`.
**Upstream:** `microsoft/dbt-fabric` does not have this auth method. (It exists in `microsoft/dbt-fabricspark` but is implemented differently — direct credential instantiation per adapter.)

### dc6c24c9 — 2026-05-16 — NEW_FEATURE
**Message:** Add FabricSpark incremental materialization (#63)
**What:** Adds full FabricSpark `incremental` materialization (`incremental.sql` + `incremental_strategies.sql`). Defaults to `merge` when `unique_key` set; detects MLV→incremental switches and drops the MLV first; uses real staging tables (not temp views) to dodge `REQUIRES_SINGLE_PART_NAMESPACE`; strips database component from `INSERT INTO`; uses `MERGE INTO ... ON false` for append (since `INSERT INTO TABLE` breaks 3-part names). Includes inline Jinja comments noting where it deviates from dbt-spark.
**Why:** dbt-spark's inherited incremental relies on Databricks-style temp views and 2-part names — both unusable in Fabric Lakehouse.
**Upstream:** Upstream has no FabricSpark adapter.

### eeed9ec1 — 2026-05-16 — BUG_FIX
**Message:** Use FabricCredentials instead of FabricSparkCredentials in Livy session fixture (#148)
**What:** Fixture constructs `FabricCredentials` (base class) rather than `FabricSparkCredentials`.
**Why:** Avoids hard dependency on the optional `spark` extra in the test fixture itself.

### 55c34792 — 2026-05-16 — INFRA
**Message:** Fix test collection failure when spark extra is not installed (#149)
**What:** Adds `pytest_ignore_collect` hook that uses `importlib.util.find_spec` to skip FabricSpark tests when the extra is missing, and fails fast when `--de` is requested without it.
**Why:** Prevents pytest collection errors in environments without the optional spark dependency.

### be106c92 — 2026-05-16 — BUG_FIX
**Message:** Fix singleton pollution causing TestWarehouseSnapshots to fail (#151)
**What:** The session-scoped Livy fixture had been caching a `FabricApiClient` keyed off the lakehouse on `BaseFabricConnectionManager`; DW tests inheriting the singleton saw the wrong database. Final fix: the fixture no longer caches *anything* on the connection manager — it only pre-warms a Livy session by name, and each adapter creates its own client/token provider with its own credentials.
**Why:** Cross-adapter singleton pollution caused wrong-database lookups in mixed test runs. Modifies the singleton-related changes from earlier commit 6aa023c8 in this batch.
**Notes:** Modifies 6aa023c8 in the same batch.

### 0eea9621 — 2026-05-16 — BUG_FIX
**Message:** Add Lakehouse integration test for Purview sync (#150)
**What:** Adds Lakehouse integration test for `_create_lakehouse_table` path; fixes URL-encoding round-trip bug in `get_entity_by_qualified_name` (qualifiedNames with `%252F` were being corrupted by parse_qs/urlencode), and adds `purview_sync` macro for FabricSpark (was missing entirely).
**Why:** Coverage gap exposed both a real encoding bug and the fact FabricSpark users couldn't call `purview_sync` at all.
**Upstream:** Neither bug exists upstream because Purview integration is fork-only (see c181357d).

### f1c0a512 — 2026-05-16 — DBT_NATIVE_REWRITE
**Message:** Add automatic query retry for transient snapshot isolation errors (#152)
**What:** Defaults `add_query()` to retry on `mssql_python.OperationalError`/`InternalError` up to 3 attempts via dbt-adapters' built-in retry plumbing. Removes the `FabricStoreTestFailuresMixin` test-level workaround.
**Why:** Microsoft's guidance for sys.tables/sys.columns is retry; pushing this into the connection manager benefits end users — not just tests.
**Upstream:** `upstream/main:dbt/adapters/fabric/fabric_connection_manager.py` has `retry_limit: int = 1` with no retryable exceptions, so production users still see flaky metadata queries.

### 9f986a92 — 2026-05-16 — INFRA
**Message:** Remove custom Docker containers from CI (#154)
**What:** Removes `.github/CI.Dockerfile` and `publish-docker.yml` entirely; CI now installs `libltdl7` on `ubuntu-latest` directly since `mssql-python` bundles its ODBC driver.
**Why:** Simpler, no image to publish/maintain.

### c29e9b56 — 2026-05-16 — NEW_FEATURE
**Message:** Add workload_identity authentication for federated credentials (#155)
**What:** Adds `workload_identity` auth using Azure SDK's `ClientAssertionCredential`; tokens can come from either an HTTP URL (optional auth header) or a re-read file path. CI switched off `azure/login` + `AzureCliCredential` to use GitHub OIDC directly.
**Why:** Provider-agnostic federated auth (GitHub Actions OIDC, Kubernetes service tokens, etc.) without azure-specific tooling on the runner.
**Upstream:** `microsoft/dbt-fabric` does not implement `workload_identity` — auth options are limited to CLI/MSI/SP/ActiveDirectoryDefault.

### 1e9d9b70 — 2026-05-16 — INFRA: Merge upstream/main (ours strategy)

### 50a06bec — 2026-05-16 — INFRA: Merge pull request #156 (ours-merge of upstream)

### 7f91d041 — 2026-05-16 — BUG_FIX
**Message:** Fix DE tests failing due to missing auth in livy_session_lifecycle fixture (#157)
**What:** Extracts `_auth_kwargs_from_env()` helper and passes auth fields into the fixture's `FabricCredentials`; otherwise it silently fell back to DefaultAzureCredential which can't authenticate in CI without `az login`.
**Why:** Test infrastructure fix for the lifecycle introduced in 6aa023c8.
**Notes:** Modifies 6aa023c8 / eeed9ec1 in the same batch.

### d67812c8 — 2026-05-16 — INFRA
**Message:** Add unit tests workflow (#158)
**What:** Adds `.github/workflows/unit-tests.yml` running across Python 3.11/3.12/3.13 on PR + push.

### 82c4aa0f — 2026-05-16 — DOCS
**Message:** Remove roadmap page from documentation (#159)
**What:** Removes `docs/roadmap.md`, related comparison entry, and nav.

### c28eb1ec — 2026-05-16 — DOCS
**Message:** Add detailed upstream comparison pages to docs (#160)
**What:** Adds `docs/comparison-dbt-fabric.md` and `docs/comparison-dbt-fabricspark.md`, rewrites `feature-comparison.md` (categorisation, Maturity/Quality section, concrete numbers like 41 community-package overrides across 6 packages).
**Why:** Explicit, evidence-based positioning vs Microsoft's repos.

### 86ea1c76 — 2026-05-16 — INFRA
**Message:** Add devcontainer for cloud development environments (#165)
**What:** Adds `.devcontainer/devcontainer.json` (Python 3.13, uv, az CLI, gh, libltdl7, libkrb5-3, libgssapi-krb5-2), updates CONTRIBUTING.md.

### 27c65566 — 2026-05-16 — INFRA: Remove dbt Power User extension from devcontainer (#186)

### 9125426d — 2026-05-16 — BUG_FIX
**Message:** Fix FabricSpark TestMetadataWithEmptyFlag parse-time crash (#164)
**What:** Overrides the test's model to call `alter_relation_add_remove_columns` without drops (Spark macro raises CompilationError at parse time when drops are passed) and uses `adapter.Relation.create()` instead of `ref()` for DDL on `--empty` flag (subquery substitution breaks DESCRIBE EXTENDED/ALTER TABLE).
**Why:** Tests ERROR at parse time, hiding the underlying bug. The fix shows users a real-world recipe — use `adapter.Relation.create()` for DDL paths under `--empty`.

### 5a60ef1c — 2026-05-16 — BUG_FIX
**Message:** Fix FabricSpark snapshots failing with `character varying` type error (#185)
**What:** Adds `FabricSparkColumn.string_type()` returning `string` (was inheriting base which returns `character varying(N)`) and sets `Column = FabricSparkColumn` on the adapter (previously fell back to `SparkColumn` via MRO). Also drops `TypeAlias` indirection that was being used for the Column/Relation attrs.
**Why:** Without the Column class registration, all snapshot DDL generated PG-style `character varying` types and failed at execution.
**Upstream:** Upstream has no FabricSpark adapter so the bug doesn't exist there. The pattern matters because it's a class of bug that hits any subclass adapter that forgets to bind `Column =`/`Relation =` explicitly.

### 7cf0773f — 2026-05-16 — TEST
**Message:** Add unit tests for FabricCredentials serialization and auth normalization (#195)
**What:** Adds unit coverage for credential auth normalisation (auto→ActiveDirectoryDefault, windows_login override, alias resolution, unique_field fallback).

### 83067433 — 2026-05-16 — TEST
**Message:** Add unit tests for FabricConnectionManager utility functions (#204)
**What:** 23 tests for `bool_to_connection_string_arg`, `byte_array_to_datetime`, `data_type_code_to_name`, `get_response`.

### 3a7e081c — 2026-05-16 — TEST
**Message:** Add unit tests for FabricAdapter pure methods (#192) (#199)
**What:** 206-line unit test suite covering FabricAdapter pure methods.

### 995594bc — 2026-05-16 — TEST
**Message:** Add unit tests for FabricColumn and FabricRelation (#197)

### 2938b103 — 2026-05-16 — INFRA
**Message:** Replace PR trigger with /test-dw on-demand command (#198)
**What:** DW integration tests no longer run on every PR — opt-in via `/test-dw [filter]` PR comment (matches existing `/test-de` pattern); always includes `--with-python`.
**Why:** Avoid burning Fabric capacity / hitting the 3-Livy-session limit on every PR.

### 8060d37f — 2026-05-16 — BUG_FIX
**Message:** Add unit tests for FabricApiClient and fix snapshot API URL casing (#201)
**What:** Adds 660 lines of unit tests for `FabricApiClient`; fixes 4 URL paths from `warehousesnapshots` (lowercase) to `warehouseSnapshots` (camelCase) as the Fabric REST API requires; also documents the empty-`properties` and 202 LRO behaviour.
**Why:** Unit tests exposed that warehouse snapshot endpoints were hitting the wrong URL path. Existing snapshot operations were either broken or working only because of forgiving API behavior at the time.
**Upstream:** Upstream has no `fabric_api_client.py` (this whole client is fork-only), so the URL casing bug is fork-only — but it's worth noting because it proves the rewrite/maintenance value: writing actual tests caught the bug.
**Notes:** Direct example of a TEST commit exposing a real BUG, both in one PR.

### 2260bab3 — 2026-05-16 — INFRA: Add Microsoft Learn MCP server configuration (#212)

### a9246e99 — 2026-05-16 — NEW_FEATURE
**Message:** Add statistics config option for Fabric Data Warehouse (#196)
**What:** Adds `statistics` (list of column names) and `statistics_sample_percent` model configs for `table`, `incremental`, and `snapshot` materializations. Generates `CREATE STATISTICS dbt_stats__<md5(table__col)>` with `FULLSCAN` by default, optional `WITH SAMPLE n PERCENT`; respects table existence to skip the IF EXISTS branch on first run; escapes single quotes; uses md5 hash to avoid identifier-length collisions.
**Why:** Manual statistics are the recommended way to give Fabric DW's optimizer reliable histograms; declarative model-level config beats per-project hooks.
**Upstream:** No statistics config exists in `microsoft/dbt-fabric`.

### 9a8f090d — 2026-05-16 — TEST
**Message:** Add unit tests for FabricSparkAdapter helper methods (#205)
**What:** 232-line suite covering `_namespace_to_parts`, `try_translate_type`, `_build_spark_relation_list`, column type checks, `data_type_code_to_name`.

### 25faac00 — 2026-05-16 — BUG_FIX
**Message:** Improve FabricSparkCursor PEP 249 compliance (#209)
**What:** (1) `__exit__` now returns False instead of True, so exceptions inside `with cursor:` blocks no longer get silently swallowed. (2) Closed-cursor guard — all data ops raise `DbtDatabaseError` after `close()`. (3) `setinputsizes`/`setoutputsize` become spec-compliant no-ops. (4) `cancel()` silently returns on closed cursor instead of raising.
**Why:** Real PEP 249 / DB-API 2.0 compliance; the exception-swallowing in `__exit__` was the most dangerous of these.
**Upstream:** Upstream has no FabricSpark cursor (no FabricSpark adapter), but `dbt-spark` (which FabricSpark inherits from) has not fixed `__exit__` swallowing exceptions either. This is the kind of latent bug fork analysis is meant to surface.

### bff925e8 — 2026-05-16 — BUG_FIX
**Message:** Add unit tests for LivySession and detect fatal session states (#203)
**What:** (1) Adds class constants `_FATAL_SESSION_STATES = {dead, killed, error, shutting_down}` and raises immediately if the session enters any of them — previously waited until timeout. (2) Expands terminal statement states to include `cancelled`/`cancelling`. (3) Provides a fallback error message when a cancelled statement has no `output.evalue`. (4) 434 lines of unit tests.
**Why:** Without fatal-state detection, dead Livy sessions blocked dbt for the full session timeout; cancelled statements produced "Error executing SQL statement: None".
**Upstream:** Upstream has no Livy session handling (no FabricSpark adapter).

### b350cc5b — 2026-05-16 — DOCS
**Message:** Clarify database vs lakehouse config with tabs (#216)
**What:** Documentation tabs distinguishing DW (`database` = warehouse) vs Lakehouse (`database` = lakehouse) config.

### c797e7c3 — 2026-05-16 — INFRA
**Message:** Extend ruff lint rules with F, E, W, UP, B, SIM, C4 (#214)
**What:** Adds pyflakes, pycodestyle, pyupgrade, bugbear, simplify, and flake8-comprehensions ruff rules; fixes all existing violations across src and tests (35 files touched).

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

### 4efb1562 — 2026-05-18 — DOCS: Drop "Open coordination points" section from `_toolbox/PR_DESCRIPTION.md` (-13 lines).

### 211ec6ca — 2026-05-18 — DOCS: Drop "Coordination" subsection from migration path section in `_toolbox/PR_DESCRIPTION.md` (-4 lines).

### d1661d1e — 2026-05-18 — DOCS: Drop "Proposed maintenance model" section from `_toolbox/PR_DESCRIPTION.md` (-15 lines).

### 805789c5 — 2026-05-18 — DOCS: Drop fabricspark migration subsection pending real migration story (-4 lines).

### 72a7c702 — 2026-05-18 — DOCS: Drop entire "Migration path" section from `_toolbox/PR_DESCRIPTION.md` (-8 lines).

### 5b438fa3 — 2026-05-18 — DOCS: Rewrite PR description in Sam's blog voice (112+/108-).

### c2da8b3f — 2026-05-18 — DOCS: Tighten PR description — drop H3 sprawl, single customer mention, no unkept promises (51+/217- net reduction).

### 4348e15b — 2026-05-18 — DOCS: Restore evidence details dropped during tightening (5+/5-).

### 3a4de332 — 2026-05-18 — DOCS: Update DW adapter status to current v1.10.0 / v1.9.10 (both 18 May 2026).

### 46ac285e — 2026-05-18 — DOCS: Drop one-sided "no upper bound" criticism in DW paragraph.

### 85ba7cde — 2026-05-18 — DOCS: Soften Python-matrix criticism; keep dbt-core matrix as the real point.

### 5f0ec295 — 2026-05-18 — DOCS: Update fabricspark to v1.12.2 (six in eight days); drop empty meta-line; reframe pin-range critique.

### c2d65f07 — 2026-05-18 — DOCS: Drop empty "verifiable on PyPI and GitHub" meta-line.

### b8ece9f7 — 2026-05-18 — DOCS: Make own dbt-core matrix claim honest (1+/1-).

### 64d478a0 — 2026-05-18 — DOCS: Apply same softening to fabricspark passages (2+/2-).

### aebe99f6 — 2026-05-18 — DOCS: Drop redundant fabricspark release table (-12 lines).

### 88fc464f — 2026-05-18 — DOCS: Reframe release-pace as positive activity, not as critique.

### 4a1dd9e7 — 2026-05-18 — DOCS: Consolidate CI critique into a single symmetric paragraph.

### 391aa6af — 2026-05-18 — DOCS: Add atexit usage note in dbt-fabric v1.10.0; name the AI+staffing pattern.

### 18c12a09 — 2026-05-18 — DOCS: Clarify pro-AI stance in the pattern section.

### 16555ed2 — 2026-05-18 — DOCS: Drop "three things have to come out of it" sentence from intro.

### 441c5695 — 2026-05-18 — DOCS: Add user-impact phrasing to the first four "What's broken" items.

### fc810a8e — 2026-05-18 — DOCS: Restructure "What's broken" section; fix incorrect mssql_python claim about upstream.

### 9e2fb07e — 2026-05-18 — DOCS: Acknowledge close() pyodbc fix may also be unverified.

### 5b5a1846 — 2026-05-18 — DOCS: Reorder "What's broken"; strengthen dbt-native framing; add dbt doc links throughout.

### e17489ba — 2026-05-18 — DOCS: Add "Headline features" section up front — Purview, Python models, community packages.

### 3b4cb372 — 2026-05-18 — DOCS: Drop Livy session reuse from headline features (upstream has it); add own-docs links.

### e4bd7634 — 2026-05-18 — DOCS: Rewrite "Why this stays maintainable long-term" with a stronger dbt-spark argument.

### 36e0d067 — 2026-05-18 — DOCS: Strengthen "shared auth and API" argument with concrete drift evidence.

### 7eef8b13 — 2026-05-18 — DOCS: Soften intro — drop "serious reset" and accurately attribute fork maintenance to Sam alone.

### 74400a17 — 2026-05-18 — DOCS: Use "community" in intro instead of personal attribution.

### de31ff1c — 2026-05-18 — DOCS: Reframe community-packages entry — compatibility work is the main contribution, testing keeps it honest.

### 066b5612 — 2026-05-18 — DOCS: Drop cluster_by from upstream-doesn't-have list (upstream has it too); remove filler closing line.

### a0b13e6c — 2026-05-18 — DOCS: Drop weak "current situation" section; move criticism into "What's broken".

### 3842c7ec — 2026-05-18 — DOCS: Refine PR_DESCRIPTION — trim, anonymize, sharpen sharing argument.

### 71379288 — 2026-05-18 — DOCS: Drop Livy session reuse bullet from end-user list.

### f54655f6 — 2026-05-18 — DOCS: Fix headline count — three big ones, not two.

### 54de6672 — 2026-05-18 — DOCS: Consistency and accuracy pass on PR_DESCRIPTION (14+/14-).

### f46d3844 — 2026-05-18 — DOCS: Add "why fork instead of contribute upstream" paragraph.

### f19e22c7 — 2026-05-18 — DOCS: Restructure — lift pitch + provenance into intro.

