# Batch 06 analysis

**Summary:** 46 commits from Feb 20 – Feb 24, 2026. Distribution: **TEST: 12**, **INFRA: 9**, **NEW_FEATURE: 8**, **BUG_FIX: 8**, **REFACTOR: 4**, **DBT_NATIVE_REWRITE: 2**, **ANTI_PATTERN_REMOVED: 2**, **DOCS: 2**, **REVERT_OR_MODIFY: 1**.

Most impactful items: (1) bootstrap of the entire FabricSpark adapter (`fd6402f4`, `03094937`) — extracts shared `BaseFabricConnectionManager`/`BaseFabricCredentials`/`BaseFabricAdapter`, introduces Livy session handling, cursor, connection manager — none of which exists in upstream. (2) `2211d4e1` (DBT_NATIVE_REWRITE) deletes Fabric's custom `add_query` reimplementation and delegates to `SQLConnectionManager.add_query`; upstream still has the duplicated code plus `atexit.register`. (3) `257c8999` (DBT_NATIVE_REWRITE) replaces upstream drop-and-recreate incremental full-refresh path with dbt-native intermediate/backup rename swap. (4) `e317baa1` (BUG_FIX) fixes wrong JSON key (`"value"` vs `"items"`) that broke Livy session reuse + adds missing thread lock. (5) `5226156539` (ANTI_PATTERN_REMOVED) removes a `log()` call that spammed dbt logs on every macro invocation — still present upstream.

One in-batch revert chain: `257c8999` unskipped `TestPySparkTestsFabric`, then `b0c35576` re-skipped it. One self-fix chain inside scalar functions: `2c96f574` added default-args support, then `2b6110aa` fixed the `arg.default_value` lookup. One self-fix in dataclasses: `643330cb` introduced `json_data: dict | None = {}` mutable default, `a06a2e27` fixed it with `field(default_factory=dict)`.

---

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
