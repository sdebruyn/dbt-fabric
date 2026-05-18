# Batch 07 analysis

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
