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
