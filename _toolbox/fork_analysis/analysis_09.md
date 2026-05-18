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
