# dbt-fabric

A dbt adapter for Microsoft Fabric, maintained as a fork of [microsoft/dbt-fabric](https://github.com/microsoft/dbt-fabric). Published to PyPI as `dbt-fabric-samdebruyn`.

This adapter supports two Microsoft Fabric compute engines:

- **Fabric** (adapter type `fabric`) — Fabric Data Warehouse, uses T-SQL
- **FabricSpark** (adapter type `fabricspark`) — Fabric Lakehouse / Data Engineering, uses Spark SQL via Livy sessions

## Quick reference

```shell
uv sync                              # Set up venv + install all deps (editable mode)
uv run pytest                        # Run all integration tests (needs test.env + Fabric)
uv run pytest --dw                   # Run only Fabric (T-SQL) tests
uv run pytest --de                   # Run only FabricSpark tests
uv run pytest --dw --isolated        # Fabric tests with isolated DW (for multi-agent)
uv run pytest --de --isolated        # FabricSpark tests with isolated Lakehouse
uv run pytest --with-grants          # Include GRANT/authorization tests
uv run pytest -k "TestClassName"     # Run a specific test class
uv run ruff format --check .         # Check formatting
uv run ruff format .                 # Auto-format
uv run ruff check .                  # Lint
uv run ruff check --fix .            # Lint with auto-fix
uv run zensical serve                 # Local docs preview at http://127.0.0.1:8000
uv run zensical build --strict       # Build docs and fail on warnings
```

## Documentation website

The project has a documentation website at https://dbt-fabric.debruyn.dev, built with Zensical. Source files live in `docs/`, configuration in `zensical.toml`, and theme overrides in `overrides/`.

The docs cover everything that is specific to this dbt adapter compared to other dbt adapters: installation, configuration, authentication, feature guides (Python models, warehouse snapshots), and a comparison with Microsoft's upstream `dbt-fabric`. When adding or changing adapter-specific behavior, update the relevant docs page. If a new feature has no existing page, add one under the appropriate nav section in `zensical.toml`.

Current nav structure:

- **Home** — Overview, comparison with upstream dbt-fabric, contributing, license
- **Installation & configuration** — Installing the adapter, compatibility matrix, configuration options
- **Feature guides** — Authentication, Python models, warehouse snapshots

## Architecture

### How dbt adapters work

dbt uses a plugin system where adapters translate dbt's abstract operations into database-specific SQL. An adapter consists of:

1. **Python adapter classes** — Define how to connect, execute queries, fetch metadata, and manage relations. These extend base classes from `dbt-adapters`.
2. **Jinja SQL macros** — Define how dbt operations (CREATE TABLE, incremental merge, snapshot, etc.) are expressed in the target SQL dialect. dbt's dispatch system selects the right macro based on adapter name.
3. **Plugin registration** — Each adapter registers itself via `AdapterPlugin` in `__init__.py`, pointing to its adapter class, credentials class, and macro directory.

### Dispatch system

dbt selects macros by adapter name prefix. When dbt needs `dateadd`, it looks for `fabric__dateadd` (or `fabricspark__dateadd`). If no adapter-specific version exists, it falls back to `default__dateadd`.

Macros call dispatch explicitly:

```jinja
{% macro dateadd(datepart, interval, from_date_or_timestamp) %}
    {{ return(adapter.dispatch('dateadd', 'dbt')(datepart, interval, from_date_or_timestamp)) }}
{% endmacro %}

{% macro fabric__dateadd(datepart, interval, from_date_or_timestamp) %}
    dateadd({{ datepart }}, {{ interval }}, cast({{ from_date_or_timestamp }} as datetime2(6)))
{% endmacro %}
```

### Class hierarchy

```
Fabric (T-SQL):
  FabricAdapter → BaseFabricAdapter → SQLAdapter (from dbt-adapters)
  FabricConnectionManager → BaseFabricConnectionManager → SQLConnectionManager

FabricSpark:
  FabricSparkAdapter → (BaseFabricAdapter, SparkAdapter)
  FabricSparkConnectionManager → BaseFabricConnectionManager
```

`BaseFabricAdapter` provides shared functionality for Python model execution via Fabric Livy sessions. `FabricSparkAdapter` inherits from both this base and dbt-spark's `SparkAdapter`.

### Plugin registration

Each adapter has an `__init__.py` that registers the plugin:

- `src/dbt/adapters/fabric/__init__.py` — Registers `FabricAdapter` with `FabricCredentials`
- `src/dbt/adapters/fabricspark/__init__.py` — Registers `FabricSparkAdapter` with `FabricSparkCredentials`, declares `dependencies=["spark"]`

The FabricSpark adapter requires the optional `spark` dependency group: `pip install dbt-fabric-samdebruyn[spark]`.

## Code organization

```
src/
  dbt/
    adapters/
      fabric/                         # Fabric (T-SQL) adapter Python code
        __init__.py                   # Plugin registration
        __version__.py                # Version (updated by CI on release)
        base_fabric_adapter.py        # Shared base: Python/Livy submission
        base_connection_manager.py    # Shared base: connection management
        base_credentials.py           # Shared base: credential fields
        fabric_adapter.py             # T-SQL adapter implementation
        fabric_connection_manager.py  # T-SQL connection management (mssql-python)
        fabric_credentials.py         # T-SQL credential handling
        fabric_relation.py            # Relation types and rendering
        fabric_column.py              # Column type mapping (T-SQL types)
        fabric_configs.py             # Model configuration
        fabric_token_provider.py      # Azure token acquisition
        fabric_api_client.py          # Fabric REST API client
        fabric_livy_session.py        # Livy session management
        fabric_livy_helper.py         # Livy helper utilities
        relation_configs/             # Advanced relation configuration
      fabricspark/                    # FabricSpark adapter Python code
        __init__.py                   # Plugin registration
        __version__.py                # Version (separate from fabric)
        fabricspark_adapter.py        # Spark adapter implementation
        fabricspark_connection_manager.py
        fabricspark_connection.py     # Spark connection handling
        fabricspark_cursor.py         # Spark cursor implementation
        fabricspark_credentials.py
        fabricspark_relation.py       # Spark relation types (incl. MaterializedView)
        fabricspark_column.py         # Spark column types
    include/
      fabric/                         # Fabric (T-SQL) macros
        dbt_project.yml               # Macro package config
        macros/
          adapters/                    # Core adapter operations (catalog, columns, schema, etc.)
          materializations/            # Table, view, incremental, snapshot, seed macros
            models/incremental/        # Merge, delete+insert, append, microbatch strategies
            models/table/              # CREATE TABLE, clone, python models
            models/view/               # CREATE VIEW
            snapshots/                 # Snapshot strategies and helpers
            seeds/                     # Seed loading helpers
            tests/                     # Test helpers
            functions/                 # Scalar function support
          utils/                       # Cross-database functions (dateadd, hash, concat, etc.)
          dbt_package_support/         # Compatibility macros for community packages
            dbt_utils/                 # dbt-utils overrides
            dbt_date/                  # dbt-date overrides
            dbt_expectations/          # dbt-expectations overrides
            dbt_audit_helper/          # dbt-audit-helper overrides
      fabricspark/                     # FabricSpark macros (minimal, inherits from dbt-spark)
        dbt_project.yml               # Sets default materialization to materialized_view
        macros/
          adapters/metadata.sql        # Spark catalog metadata
          materializations/            # Materialized lake view
          relations/                   # Drop, rename, materialized_view CRUD
          get_custom_name/             # Database name generation
tests/
  conftest.py                         # Shared fixtures, adapter type detection, CLI flags
  isolated_items.py                   # FabricTestItemManager for --isolated mode
  unit/                               # Unit tests (no Fabric connection needed)
  fabric/                             # Fabric (T-SQL) integration tests
    adapter/                          # ~20 test modules
  fabricspark/                        # FabricSpark integration tests
    adapter/                          # ~15 test modules
```

## Development workflow (TDD)

Development follows a strict test-driven loop using `dbt-tests-adapter` base classes:

1. **Add a base test class** — Find the relevant base class in `dbt.tests.adapter.*` and create a subclass in the appropriate test directory (`tests/fabric/` or `tests/fabricspark/`). Start with a bare `pass` body.
2. **Run the test** — `uv run pytest -k "TestClassName" --dw` (or `--de` for FabricSpark). Expect it to fail.
3. **Diagnose the failure** — Read the error. Common causes:
   - Missing macro: dbt can't find `fabric__some_macro` → implement it in `src/dbt/include/fabric/macros/`
   - SQL syntax error: the default macro generates SQL that Fabric doesn't support → override the macro with Fabric-compatible SQL
   - Wrong types: Fabric uses `datetime2(6)` not `timestamp`, `varchar` not `text` → override the test fixture
   - Unsupported feature: Fabric genuinely can't do this → skip with `@pytest.mark.skip("reason")`
   - Python adapter method missing or wrong → fix the adapter class
4. **Debug the failure** — See "Debugging test failures" below for how to use logs and the generated dbt project.
5. **Fix and re-run** — Implement the minimal fix (macro, fixture override, adapter method), then re-run the failing test.
5. **Regression check** — After each fix, run the full test suite for that adapter to catch regressions:
   ```shell
   uv run pytest --dw   # all Fabric tests
   uv run pytest --de   # all FabricSpark tests
   ```
6. **Repeat** — Go back to step 1 for the next base test class.

This loop is the core development method. Every feature and fix starts with a failing test. Never skip the regression check after a fix — changes to macros and adapter methods can have broad impact.

### Debugging test failures

The test harness creates a temporary dbt project and profile for each test class. Both are valuable for understanding failures.

**Logs** — Each test class gets its own log directory under `logs/` in the project root, named by the test's unique prefix (e.g., `logs/test17723817511604948531/`). The prefix is printed in pytest output:

```
=== Test logs_dir: /path/to/dbt-fabric/logs/test17723817511604948531
```

Read the dbt log file inside that directory to see the exact SQL that was generated and sent to Fabric, along with any errors returned by the database.

**Generated dbt project** — The harness creates a full dbt project in a temp directory (via pytest's `tmpdir_factory`). The path is printed in pytest output:

```
=== Test project_root: /private/var/folders/.../project0/
```

This temp project contains the compiled SQL models, seeds, macros, `dbt_project.yml`, and `profiles.yml` that the test actually used. When a test fails, read these files to see:
- What SQL was compiled (look in `target/compiled/` and `target/run/`)
- What models and macros were active
- What the profile and connection config looked like

**Debugging workflow:**

1. Run the failing test with `-v -s` to see all output including log and project paths:
   ```shell
   uv run pytest -k "TestClassName" --dw -v -s
   ```
2. Read the dbt log to find the exact SQL error from Fabric.
3. If the SQL is wrong, check the compiled SQL in the temp project's `target/compiled/` directory.
4. Trace the compiled SQL back to the macro that generated it.
5. Fix the macro or adapter method, re-run.

### Lessons learned

During the TDD loop, pay attention to recurring failure patterns. When the same type of fix comes up multiple times, extract the pattern and add it to this section. This keeps the knowledge base growing and prevents re-discovering the same solutions.

Update this section by adding entries as patterns emerge. Format: short description of the pattern, what causes it, and the standard fix.

- **FabricSpark: `'view' is not a valid FabricSparkRelationType`** — dbt's default materialization is `view`, but Fabric Lakehouse with schemas doesn't support Spark SQL views. This comes up in two ways: (1) a test's `project_config_update` provides a `models` key that used to overwrite the `+materialized: materialized_view` default via shallow dict merge — now fixed with deep merge in `conftest.py`; (2) base test classes from dbt-tests-adapter have explicit `config(materialized="view")` in their model SQL fixtures, which bypasses the project-level default entirely. Fix for (2): override the test's `models` fixture to replace `view` with `materialized_view`. Use `materialized_view` when the test is about read-only derived data (closest equivalent to a view), and `table` when the test needs DML or other table-specific behavior.

- **FabricSpark: `PARSE_SYNTAX_ERROR` with `'...'::text` cast** — dbt-tests-adapter's alias test fixtures use PostgreSQL-style `'{{ s }}'::text` cast syntax in their `string_literal` macro, which Spark SQL does not support. Fix: override the `macros` fixture to provide a Spark-compatible `string_literal` macro that uses plain `'{{ s }}'` without the `::text` cast. See `tests/fabricspark/adapter/test_aliases.py` for the pattern. Note: the adapter provides `fabricspark__string_literal` for production use (dispatched via `'dbt'` namespace), but test fixtures dispatch with `macro_namespace='test'` which doesn't search adapter macros — per-test overrides are still needed.

- **FabricSpark: clone materialization falls back to view** — dbt's default clone materialization (and spark's) falls back to `this.incorporate(type='view')` when `can_clone_table()` returns False. Since FabricSpark has no `View` relation type, this fails. Fix: override the `macros` fixture to provide a `fabricspark` clone materialization that falls back to `materialized_view` instead. Clone tests also need `file_format='delta'` in snapshot config (spark requires delta/iceberg/hudi, not parquet). See `tests/fabricspark/adapter/test_dbt_clone.py`.

- **Fabric DW: transient snapshot isolation errors in concurrent test runs** — When the full DW test suite runs in parallel, concurrent DDL from other test classes can cause snapshot isolation failures in `sys.tables`/`sys.views` metadata queries. This is not a code bug — it's infrastructure contention. Fix: retry `check_relation_types` calls with a short delay. See `tests/fabric/adapter/test_store_test_failures.py`.

- **FabricSpark: hooks tests need setUp/check_hooks overrides** — dbt-tests-adapter's hook base classes (`BaseTestPrePost`, `BasePrePostRunHooks`) expect `seed_model.sql`/`seed_run.sql` data files and validate postgres-specific values. FabricSpark needs: (1) mixin classes (`SparkRunModelFile`, `SparkHooksChecks`) that override `setUp` to create hook tables inline with `STRING` type (not `TEXT`) and override `check_hooks` to validate `target_type == "fabricspark"`; (2) `SparkPrePostHooksFixtures` that replaces `VACUUM` statements and removes `"transaction": False` flags (Spark doesn't support `COMMIT`/`BEGIN`); (3) `get_ctx_vars` override to use backtick-quoted column names (Spark SQL treats double-quoted identifiers as string literals). See `tests/fabricspark/adapter/test_hooks.py` for the full pattern.

- **FabricSpark: catalog relation types use lowercase** — FabricSpark's catalog returns relation types as lowercase enum values (`"table"`, `"materialized_view"`) rather than the uppercase SQL-standard names (`"BASE TABLE"`, `"MATERIALIZED VIEW"`) that other adapters use. When overriding `CatalogRelationTypes` for FabricSpark, use lowercase expected values.

- **FabricSpark: base class `dbt_profile_target` override** — Some base test classes (e.g., `BaseSimpleCopyUppercase`) override `dbt_profile_target` with postgres-specific credentials. FabricSpark tests inheriting from these classes must re-override `dbt_profile_target` to pass through the conftest fixture: `@pytest.fixture(scope="class") def dbt_profile_target(self, dbt_profile_target): return dbt_profile_target`.

- **FabricSpark: `seeds__expected_sql` multi-statement and type errors** — dbt-tests-adapter's seed test `setUp` fixture runs `seeds__expected_sql` which contains (1) PostgreSQL types (`TEXT`, `TIMESTAMP WITHOUT TIME ZONE`, `INTEGER`) and (2) multiple SQL statements separated by semicolons. Spark SQL fails on both: wrong types and multi-statement execution. Fix: replace types (`TEXT`→`STRING`, `TIMESTAMP WITHOUT TIME ZONE`→`TIMESTAMP`, `INTEGER`→`INT`), strip double quotes from column names (Spark uses backticks), and split on `;` to execute each statement separately via a `run_sql_statements()` helper. Also note Spark infers untyped integer columns as `bigint`, not `int` — use `bigint` in `properties__schema_yml` for seed_id type checks. See `tests/fabricspark/adapter/test_simple_seed.py`.

- **FabricSpark: seed full-refresh cascade drop tests fail** — Tests like `test_simple_seed_full_refresh_flag` and `BaseSeedConfigFullRefreshOn` assume dropping a seed table cascades to drop dependent models (views). Fabric materialized views are not automatically dropped when their source table is recreated. Fix: skip these tests with reason "Dropping a seed table does not cascade to materialized views in Fabric". Same pattern as the Fabric T-SQL adapter.

- **FabricSpark: `BaseSimpleSeedEnabledViaConfig` tests conflict in same class** — The three test methods (`test_simple_seed_with_disabled`, `test_simple_seed_selection`, `test_simple_seed_exclude`) assume a clean schema between each test (via `clear_test_schema` which drops and recreates the schema). FabricSpark can't drop schemas this way, and the `clear_test_schema` fixture is overridden to no-op. Fix: split into three test classes with one non-skipped test each, same pattern as the Fabric T-SQL adapter.

- **FabricSpark: `store_failures_as="view"` is invalid** — dbt's `store_test_failures_tests` base classes use `store_failures_as="view"` in test SQL configs and `schema.yml` fixtures, then verify stored results are views via `check_relation_types`. Since `FabricSparkRelationType` has no `View` type, this causes `invalid value 'view'` errors at runtime. Fix: override `tests`, `models` (for `schema.yml`), `project_config_update`, and test methods to replace all `store_failures_as="view"` with `store_failures_as="table"` and update expected `TestResult` types from `"view"` to `"table"`. See `tests/fabricspark/adapter/test_store_test_failures.py`.

- **FabricSpark: base test SQL string comparisons fail** — Some base test classes (e.g., `BaseEphemeralMulti`, `BaseEphemeralNested`) compare exact compiled SQL strings, expecting `create view` with double-quoted identifiers. FabricSpark generates `create or replace materialized lake view` with backtick-quoted identifiers instead. Fix: override the test method to keep only the functional assertions (seed, run, check_relations_equal) and drop the SQL string comparison. The string comparison tests dbt core CTE inlining, not adapter behavior. See `tests/fabricspark/adapter/test_ephemeral.py`.

- **FabricSpark: `INSERT INTO TABLE` fails with 3-part names** — Spark's `INSERT INTO TABLE \`lh\`.\`schema\`.\`table\`` triggers `REQUIRES_SINGLE_PART_NAMESPACE` because `spark_catalog` doesn't support multi-part namespaces for this statement. Other DML (`CREATE TABLE`, `MERGE INTO`, `CREATE OR REPLACE MATERIALIZED LAKE VIEW`) handles 3-part names fine. Fix: override `get_insert_into_sql` and `get_insert_overwrite_sql` in `src/dbt/include/fabricspark/macros/materializations/incremental.sql` to strip the database component with `.include(database=false)` and drop the `TABLE` keyword. See `fabricspark__get_insert_into_sql`.

- **FabricSpark: temporary views break DML with 3-part names** — When a temporary view exists in a Livy session, *all* DML with 3-part names fails with `REQUIRES_SINGLE_PART_NAMESPACE` — including `MERGE INTO` and `INSERT INTO`. The root cause is `create_table_as(True, ...)` which creates a temporary view for the staging data. Fix: use `create_table_as(False, ...)` to create a real table for staging, then drop it after the incremental DML. The `dbt_spark_get_incremental_sql` macro must also be overridden since spark's version calls `get_insert_into_sql` directly without `adapter.dispatch()`, so `fabricspark__` prefixed overrides are never found. The append strategy uses `MERGE INTO ... ON false WHEN NOT MATCHED THEN INSERT *` instead of `INSERT INTO ... SELECT` to avoid the namespace error entirely.

- **FabricSpark: incremental on existing materialized view** — When switching a model from `materialized_view` to `incremental`, the incremental materialization must detect and drop the existing materialized lake view before creating the table. Add `existing_relation.is_materialized_view` to the drop-and-recreate condition alongside `existing_relation.is_view`.

- **FabricSpark: incremental default strategy should be `merge` with unique_key** — dbt-spark defaults to `append` strategy, which ignores `unique_key`. Tests (and real usage) that set `unique_key` expect deduplication via MERGE INTO. Fix: in the FabricSpark incremental materialization, default to `merge` when `unique_key` is set: `config.get('incremental_strategy') or ('merge' if unique_key else 'append')`.

- **FabricSpark: constraint tests need Spark-compatible types** — `BaseConstraintsColumnsEqual` uses PostgreSQL types (`TEXT`, `timestamptz`, `text[]`, `json`, `::` casts) in its `data_types` fixture. Fix: create a `FabricSparkConstraintsTypesMixin` that overrides `string_type="string"`, `int_type="INT"`, and provides a Spark-compatible `data_types` list (only `int`, `string`, `boolean`, `timestamp`, `decimal`). DDL enforcement and rollback tests require adapter-specific `expected_sql` overrides — skip with TODO if not yet implemented.

- **FabricSpark: UDFs/UDAFs not supported** — Fabric Lakehouse doesn't support `CREATE FUNCTION` via Spark SQL. Tests that expect function creation succeed should be skipped. Tests that expect error validation (e.g., `ErrorForUnsupportedType`, `PythonUDFNotSupported`) pass as-is since the adapter rejects them before SQL execution.

- **FabricSpark: `project.get_tables_in_schema()` uses T-SQL** — The conftest `project` fixture's `get_tables_in_schema` method queries `sys.tables`/`sys.views` which doesn't exist in Spark SQL. Fix: override the test method and use `SHOW TABLES IN \`schema_name\`` instead. The result rows have table name at index 1. See `tests/fabricspark/adapter/test_simple_copy.py`.

- **FabricSpark: tests with raw DDL SQL fail** — Base tests that create objects via `project.run_sql()` with T-SQL DDL (e.g., `create materialized view`, `create view`) will fail on Spark. Fix: skip these tests with a descriptive reason.

- **FabricSpark: snapshot `file_format` check fails** — dbt-spark's snapshot materialization requires `file_format` to be `delta`, `iceberg`, or `hudi` (default is `parquet`). Fabric Lakehouse is always Delta, so this check is unnecessary. Fix: the `fabricspark` adapter has its own snapshot materialization in `src/dbt/include/fabricspark/macros/materializations/snapshots/snapshot.sql` that skips the file format check. It also uses a real table (not a view) for the staging relation since FabricSpark doesn't support views, and provides `fabricspark__snapshot_merge_sql`, `fabricspark__snapshot_hash_arguments`, `fabricspark__snapshot_string_as_time`, `fabricspark__create_columns`, and `fabricspark__post_snapshot`.

- **FabricSpark: `DEFAULT` values not supported in `ALTER TABLE ADD COLUMN`** — Delta tables in Fabric Lakehouse don't support `DEFAULT` clauses when adding columns via `ALTER TABLE ADD COLUMN`. The test harness's `add_column` helper uses `varchar(200) default null` which fails. Fix: override the method to strip `default ...` from the column definition and replace `varchar(N)` with `string` for Spark compatibility. See `tests/fabricspark/adapter/test_simple_snapshot.py` for the pattern.

## Multi-agent development

When implementing multiple test classes or fixing many failures at once, use parallel agents to speed up the work. The main conversation acts as coordinator.

### How it works

**Phase 1 — Discover failures**

Run the full test suite for each adapter. Tests run against real Fabric infrastructure and are slow (minutes per test class). Don't wait for the full suite to finish — monitor the output for failures as they arrive and start working on fixes immediately:

```shell
# Run tests in the background
uv run pytest --dw -v &
uv run pytest --de -v &

# Monitor for failures as they come in (use Monitor tool or tail the output)
```

As soon as enough failures have come in to form a work package, start phase 2. The test suite keeps running while workers fix earlier failures.

**Phase 2 — Group by root cause**

Analyze the failures before spawning any agents. Multiple test failures often share a single root cause:
- 5 tests fail on `fabric__dateadd not found` → one missing macro
- 3 tests fail on `VARCHAR` without length → one type mapping issue
- 2 tests fail on `LIMIT` syntax → one SQL dialect difference

Group these into **work packages**. Each work package:
- Has a clear root cause
- Lists all test classes affected
- Targets specific files that need to change (macros, adapter code, test fixtures)

Ensure work packages have **non-overlapping target files** where possible. If two packages need to edit the same file, either merge them into one package or assign them sequentially.

**Phase 3 — Spawn worker agents**

Spawn one agent per work package using `isolation: "worktree"`. Each worker gets a self-contained prompt with:
- The root cause and the failing test classes
- Which files to look at and modify
- The full TDD loop instructions (fix, run affected tests, regression check)
- Instructions to add any recurring patterns to the "Lessons learned" section of CLAUDE.md

Worker prompt template:

```
You are working on dbt-fabric, a dbt adapter for Microsoft Fabric. Read CLAUDE.md first.

Root cause: [description of the root cause]
Failing tests: [list of test classes]
Target files: [which macros/adapter files/test files to modify]

Instructions:
1. Read CLAUDE.md to understand the project and workflow.
2. Read the failing test classes and their base classes to understand what they expect.
3. Implement the fix in the target files.
4. Run ONLY the specific failing test: uv run pytest -k "TestClassName" --dw --isolated -v (or --de --isolated)
   The --isolated flag creates a temporary DW/Lakehouse for your run so you don't conflict with other agents.
5. If you discover a recurring pattern, add it to the "Lessons learned" section of CLAUDE.md.
6. Report back: what you changed, which tests pass/fail, any lessons learned.
```

Spawn agents for independent work packages in parallel (single message, multiple Agent tool calls). Keep dependent work packages sequential.

**Phase 4 — Merge and validate**

After workers complete:
1. Review each worker's changes (the worktree diff).
2. Merge non-conflicting worktrees. If CLAUDE.md was updated by multiple workers, consolidate the lessons learned entries.
3. Run the full test suite on the merged result:
   ```shell
   uv run pytest --dw -v
   uv run pytest --de -v
   ```
4. If new failures appear, go back to phase 2 with the remaining failures.

### Guidelines for the coordinator

- **Don't do the fixing yourself** — your job is to analyze, distribute, and validate. Workers do the implementation.
- **Be specific in prompts** — include file paths, error messages, and the exact test class names. Workers start without context.
- **Start broad, narrow down** — in the first round, tackle the root causes that affect the most tests. Later rounds handle stragglers.
- **Cap workers at 3-4 per round** — more creates merge complexity and potential test infrastructure contention due to Fabric API rate limiting.
- **Track progress** — after each round, note which tests went from failing to passing. If a worker's fix introduces new failures, revert and reassign.
- **Regression checks are the coordinator's job** — after merging worker changes, the coordinator runs the full suite. Workers only run their own specific tests.

### Guidelines for workers

- **Read CLAUDE.md first** — it contains everything you need about the project, architecture, and patterns.
- **Read the base test class** — understand what the test expects before fixing. The fix often becomes obvious from reading the base class SQL.
- **Minimal fixes only** — fix the root cause, don't refactor. If a macro works, don't also clean up unrelated macros.
- **Always use `--isolated`** — every worker must pass `--isolated` when running tests. This creates a temporary DW/Lakehouse for your run so you don't conflict with other agents or the coordinator. Items are automatically cleaned up when your test session ends.
- **Only run your own specific tests** — never run the full test suite. Fabric infrastructure is slow (Livy sessions, rate-limited APIs). Run only the test class you are fixing: `uv run pytest -k "TestClassName" --dw --isolated -v` (or `--de --isolated`). The coordinator handles regression checks after merging.
- **Validate and commit before finishing** — after your fix works, run `uv run ruff format .` and `uv run ruff check --fix .`, then commit only your own changes (not unrelated changes in the repo). Use a descriptive commit message.
- **Report clearly** — list: files changed, tests that now pass, tests that still fail (if any), and any lessons learned.
- **Update CLAUDE.md** — if you find a pattern that will help future work, add it to "Lessons learned". This is part of your job, not optional.

## Testing

### Test architecture

Tests use [dbt-tests-adapter](https://github.com/dbt-labs/dbt-adapters), dbt's official adapter test harness. It provides base test classes for standard adapter behavior. Our tests inherit from these base classes and override fixtures where Fabric's SQL dialect differs.

Typical test pattern:

```python
from dbt.tests.adapter.basic.test_base import BaseSimpleMaterializations

class TestSimpleMaterializations(BaseSimpleMaterializations):
    pass  # Inherits all test methods, uses Fabric adapter automatically
```

When Fabric-specific SQL is needed, override fixtures:

```python
class TestIncrementalFabric(BaseIncrementalOnSchemaChange):
    @pytest.fixture(scope="class")
    def models(self):
        return {"model.sql": fabric_specific_sql}
```

Common fixture overrides:
- `models` — SQL model files (when T-SQL syntax differs from default)
- `seeds` — Seed CSV data or expected SQL (type name replacements)
- `macros` — Test-specific macro overrides
- `project_config_update` — dbt_project.yml settings
- `expected_catalog` — Expected column types in catalog tests
- `dbt_profile_target_update` — Connection profile overrides

### Adapter type detection

`conftest.py` determines the adapter type from the test file's directory path:
- `tests/fabric/**` → adapter type `fabric`
- `tests/fabricspark/**` → adapter type `fabricspark`

This controls which connection profile and dbt_project.yml defaults are used.

### Isolated test infrastructure (`--isolated`)

When multiple agents run tests in parallel, they must not share the same Data Warehouse or Lakehouse — otherwise schema operations, catalog queries, and DDL can collide. The `--isolated` flag solves this by creating temporary Fabric items for each test session.

**How it works:**

1. At session start, `conftest.py` creates a uniquely-named DW (`dbt-test-dw-<uuid>`) and/or Lakehouse (`dbt-test-lh-<uuid>`) via the Fabric REST API using Azure CLI credentials.
2. It waits for provisioning to complete (can take 1-3 minutes).
3. It overrides `FABRIC_TEST_DWH_NAME` and/or `FABRIC_TEST_LAKEHOUSE_NAME` env vars so all tests in the session use the isolated items.
4. At session end (even on failure), it deletes the temporary items.

**Which items are created:**
- `--dw --isolated` → creates only a Data Warehouse
- `--de --isolated` → creates only a Lakehouse (with schemas enabled)
- `--isolated` (no filter) → creates both

**Orphaned items:** if the process is killed with SIGKILL, cleanup won't run. Orphaned items can be identified by the `dbt-test-` name prefix and deleted manually from the Fabric workspace.

**Requirements:** Azure CLI must be logged in (`az login`). The logged-in identity needs permission to create and delete warehouses/lakehouses in the workspace specified by `FABRIC_TEST_WORKSPACE_NAME`.

### Integration tests require real infrastructure

Integration tests connect to actual Microsoft Fabric workspaces. They cannot run locally without:

1. A `test.env` file (copy from `test.env.sample`)
2. Azure credentials (CLI login or service principal)
3. A Fabric workspace with a Data Warehouse and/or Lakehouse

Key environment variables:
- `FABRIC_TEST_WORKSPACE_NAME` — Fabric workspace name
- `FABRIC_TEST_DWH_NAME` — Data Warehouse name (for `--dw`)
- `FABRIC_TEST_LAKEHOUSE_NAME` — Lakehouse name (for `--de`)
- `FABRIC_TEST_HOST` — SQL endpoint host (for `--dw`)
- `FABRIC_TEST_LIVY_SESSION_NAME` — Livy session name (for `--de`, optional)
- `FABRIC_TEST_THREADS` — Parallelism (default: 10)

### Skipping tests

When Fabric doesn't support a feature, skip with a reason:

```python
@pytest.mark.skip("Catalog for single relation does not give any benefits in Fabric")
class TestGetCatalogForSingleRelation(BaseGetCatalogForSingleRelation):
    pass
```

## CI/CD

GitHub Actions workflows in `.github/workflows/`:

| Workflow | Trigger | What it does |
|---|---|---|
| `lint-format.yml` | PR, push | `ruff format --check` + `ruff check` |
| `integration-tests.yml` | PR, push, weekly (Sun 01:00 UTC) | Matrix: Python 3.11/3.12/3.13 x {DW, DE} |
| `publish-docker.yml` | Manual | Build CI Docker images → ghcr.io |
| `release-version.yml` | Tag `v*` | Update version, build, publish to PyPI |

CI authenticates to Azure via OIDC (federated credentials, no secrets stored). Tests run inside Docker containers with pre-installed `mssql-python` dependencies.

## Releasing

1. Create and push a git tag: `git tag v1.2.3 && git push origin v1.2.3`
2. The `release-version.yml` workflow automatically:
   - Updates `__version__.py` in both adapter packages
   - Builds with `uv build`
   - Publishes to PyPI with `uv publish`

## Code style

- **Formatter/linter**: ruff (config in `pyproject.toml`)
- **Line length**: 99
- **Python target**: 3.13
- **Quote style**: double quotes
- **Lint rules**: isort (`I`) + no commented-out code (`ERA`)
- **No comments in code** unless the _why_ is non-obvious
- **Always run ruff before committing**: `uv run ruff format .` and `uv run ruff check --fix .` must pass before every commit

## Key concepts for working on this adapter

### T-SQL vs Spark SQL differences

Fabric (T-SQL) and FabricSpark (Spark SQL) use fundamentally different SQL dialects:

| Concept | Fabric (T-SQL) | FabricSpark (Spark SQL) |
|---|---|---|
| Pagination | `SELECT TOP N` | `LIMIT N` |
| String type | `varchar(MAX)` | `string` |
| Timestamp | `datetime2(6)` | `timestamp` |
| Identifier quoting | `[brackets]` | `` `backticks` `` |
| Default materialization | `table` | `materialized_view` (lake view) |
| Connection | mssql-python (TDS) | Livy sessions (HTTP/REST) |
| Catalog queries | `sys.tables`, `sys.views`, `sys.columns` | `SHOW TABLES`, `SHOW COLUMNS`, `DESCRIBE` |

### No Spark SQL views in Fabric Lakehouse

Microsoft Fabric Lakehouse with schemas enabled does not support Spark SQL views — only tables and materialized lake views. This means:
- `FabricSparkRelationType` has no `View` variant — only `Table`, `MaterializedView`, `CTE`, `Ephemeral`, etc.
- FabricSpark's default materialization is `materialized_view` (set in `dbt_project.yml` and `conftest.py`)
- dbt's default materialization is `view`, which will fail on FabricSpark — every test that uses the default must be configured to use `materialized_view` or `table` instead
- The `conftest.py` fixture `dbt_project_yml` sets `+materialized: materialized_view` for FabricSpark, but this can be lost if a test's `project_config_update` replaces the `models` key (shallow merge)

### Materialized lake views in FabricSpark

FabricSpark's default materialization is `materialized_view`, which creates Fabric "lake views". These support:
- `PARTITIONED BY` clauses
- `TBLPROPERTIES` (Spark table properties)
- `CHECK` constraints with `ON MISMATCH` behavior
- `CREATE OR REPLACE` semantics

### mssql-python driver

The Fabric adapter uses `mssql-python` (not pyodbc) for T-SQL connections. This is a native Python driver for SQL Server/Fabric that doesn't require ODBC drivers on the system.

### Livy sessions

Both adapters use Fabric Livy sessions for Python model execution. The `BaseFabricAdapter` handles session lifecycle, code submission, and result retrieval via the Fabric REST API.

### Community package compatibility

The `dbt_package_support/` directory contains macro overrides that make popular dbt community packages (dbt-utils, dbt-date, dbt-expectations, dbt-audit-helper) work with Fabric's T-SQL dialect. These override specific macros from those packages with Fabric-compatible implementations.

## Upstream relationship

This is a maintained fork of `microsoft/dbt-fabric`. The upstream remote is configured:
- `origin` → `sdebruyn/dbt-fabric` (this fork)
- `upstream` → `microsoft/dbt-fabric` (original)

The fork adds features and fixes not (yet) present in Microsoft's version, including FabricSpark support.
