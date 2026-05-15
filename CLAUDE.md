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

When linking to Microsoft Learn pages (anywhere in docs, code comments, or markdown), always append the MVP tracking parameter: `?WT.mc_id=MVP_310840` (or `&WT.mc_id=MVP_310840` if the URL already has query parameters).

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

### Overriding community package macros via dispatch

Community packages like dbt-external-tables ship their own `fabric__*` macros (e.g., Synapse-style `CREATE EXTERNAL TABLE`). To override these with adapter-internal macros (e.g., our OPENROWSET-based implementation), users configure dispatch in `dbt_project.yml`:

```yaml
dispatch:
  - macro_namespace: dbt_external_tables
    search_order: ['dbt', 'dbt_external_tables']
```

The key insight is that `'dbt'` is the `GLOBAL_PROJECT_NAME` constant in dbt-core. When `get_from_package("dbt", macro_name)` is called during dispatch, it searches the `global_project_namespace` — which contains all adapter-internal macros (everything under `src/dbt/include/fabric/macros/`). This means putting `'dbt'` first in the `search_order` makes dbt find our `fabric__create_external_table` before the package's version.

When adding override macros for a community package:
1. Place the override macros in `src/dbt/include/fabric/macros/dbt_package_support/<package_name>/`
2. Only override leaf macros that the package dispatches to — don't override orchestration macros that already use dispatched calls
3. Document the required `dispatch` config in the docs page for that feature

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

### `@available` decorator

Adapter methods decorated with `@available` become callable from Jinja macros via `adapter.method_name()`. Use this when adding a new Python method that macros need to call. Example: `create_or_update_warehouse_snapshot` in `FabricAdapter` is `@available` so the snapshot macro can invoke it. There's also `@available.parse(lambda *a, **k: ...)` for methods that need a parse-time stub (e.g., `get_column_schema_from_query` returns `[]` during parsing).

### Capability declaration

Each adapter declares which dbt features it supports via `_capabilities: CapabilityDict`. dbt checks these to decide whether to use optimized code paths. Current declarations:

- **Fabric**: `SchemaMetadataByRelations` (Full), `TableLastModifiedMetadata` (Full)
- **FabricSpark**: `TableLastModifiedMetadata` (Full), `SchemaMetadataByRelations` (Full)

When adding support for a new dbt capability (e.g., `FastRelationLookup`), add it to the adapter's `_capabilities` dict with the appropriate `Support` level (`Full`, `Partial`, or `NotImplemented`).

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

## Branching and worktrees

**Every change to the codebase — no matter how small — must happen on a feature branch, never directly on `main`.** Use a git worktree (or `isolation: "worktree"` when spawning agents) so the main working directory stays clean and on `main`. This applies to all changes: code, macros, tests, documentation, and CLAUDE.md itself.

Workflow for every change:

1. Create a worktree on a new branch:
   ```shell
   git worktree add ../dbt-fabric-<short-name> -b <branch-name>
   cp test.env ../dbt-fabric-<short-name>/
   ```
2. Make changes, run ruff, commit.
3. Push and create a PR:
   ```shell
   git push -u origin <branch-name>
   gh pr create --title "..." --body "..."
   ```
4. Clean up the worktree:
   ```shell
   git worktree remove ../dbt-fabric-<short-name>
   ```

**When your work is done, always push and open a PR.** Don't leave committed work sitting on a local branch — the PR is the deliverable.

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

### PR scope

Each pull request covers exactly one logical change. A logical change is the smallest unit that makes sense on its own: a single bug fix, a single test adaptation, a single new feature, or a single refactor. Implementation code and its corresponding test belong in the same PR (they are one logical unit), but unrelated changes — even if they share a theme — go in separate PRs.

**Why:** Small, isolated PRs are easier to review, can be merged and reverted independently, and reduce merge conflicts when multiple agents work in parallel. A PR that bundles 20 test files forces the reviewer to context-switch between unrelated changes and makes partial merges impossible.

**How to split:** When adapting N test files for a new adapter feature, create N PRs (one per test file) unless two files are tightly coupled (e.g., a macro change and the test that exercises it). When fixing M bugs, create M PRs. When in doubt, split further rather than grouping.

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

During the TDD loop, pay attention to recurring failure patterns. When the same type of fix comes up multiple times, extract the general principle and add it to this section. Entries should describe broad, reusable patterns -- not individual bug fixes or specific test classes. Each entry should help someone fix a *class* of problems, not one specific problem.

Integration tests should mimic real-world usage as closely as possible. Set up dbt the way an end user would -- configure `dbt_project.yml`, profiles, models, and seeds naturally. Don't build in assumptions or shortcuts to target a specific code path; let dbt's normal execution flow reach the code under test.

When a test fails, always investigate before skipping. The macro inheritance chain has multiple layers to check: **dbt-adapters** (base implementations of all macros and adapter classes) → **dbt-spark** (SparkAdapter and its macro overrides, which FabricSpark inherits from) → **dbt-fabric** (our adapter-specific overrides). Before implementing a new macro or skipping a test, check whether dbt-adapters has a default and whether dbt-spark or dbt-databricks already solved the same problem -- the fix may already exist upstream. Only skip a test after running test queries against Fabric to confirm the feature is genuinely unsupported in Microsoft Fabric's variant of Spark.

- **Base test fixtures assume PostgreSQL syntax** -- dbt-tests-adapter base classes are written for PostgreSQL. Their SQL fixtures commonly contain PG-specific syntax that fails on both Fabric and Spark: `::text` casts, `TEXT`/`INTEGER`/`TIMESTAMP WITHOUT TIME ZONE` types, double-quoted identifiers, multi-statement strings separated by `;`, and `VACUUM`/`BEGIN`/`COMMIT` transaction commands. Fix: override the relevant fixture (`models`, `seeds`, `macros`, or `seeds__expected_sql`) to replace PG syntax with the target dialect. For FabricSpark: use `STRING` not `TEXT`, `TIMESTAMP` not `TIMESTAMP WITHOUT TIME ZONE`, `INT`/`BIGINT` not `INTEGER`, backtick-quoted identifiers not double-quoted, and split multi-statement SQL into individual executions. For Fabric (T-SQL): use `varchar`/`datetime2(6)` and bracket-quoted identifiers. Note that test fixture macros dispatched with `macro_namespace='test'` do not search adapter macros -- per-test overrides via the `macros` fixture are required even when the adapter provides a production version.

- **Base test classes hardcode `view` as materialization or relation type** -- Many base classes use `config(materialized="view")` in model SQL, `store_failures_as="view"` in test configs, or fall back to `view` in materialization logic (e.g., clone). Since FabricSpark has no `View` relation type, all of these fail. Fix: override fixtures and test methods to replace `view` with `materialized_view` (for read-only derived data) or `table` (for DML-heavy tests). This applies anywhere a base class references views -- models, schema.yml, project config, expected relation types, and materialization macros. Note: the `conftest.py` project-level default (`+materialized: materialized_view`) only applies when `config()` is not explicitly set in the model SQL, so fixture-level overrides are often still needed.

- **Spark's `spark_catalog` rejects 3-part names in certain DML statements** -- `INSERT INTO TABLE` and some other DML trigger `REQUIRES_SINGLE_PART_NAMESPACE` with 3-part names (`database.schema.table`), even though `CREATE TABLE`, `MERGE INTO`, and `CREATE OR REPLACE MATERIALIZED LAKE VIEW` handle 3-part names fine. Additionally, if *any* temporary view exists in the Livy session, even normally-working 3-part DML breaks. Fix: strip the database component with `.include(database=false)` in affected macros, drop the `TABLE` keyword from `INSERT INTO`, avoid temporary views (use real staging tables instead), and override parent macros that call DML helpers without `adapter.dispatch()`. When `INSERT INTO` cannot be fixed, `MERGE INTO ... ON false WHEN NOT MATCHED THEN INSERT *` is a workaround.

- **Delta Lake DDL has stricter limitations than T-SQL** -- Delta tables in Fabric Lakehouse do not support `DEFAULT` clauses in `ALTER TABLE ADD COLUMN`, and dropping a source table does not automatically drop dependent materialized views (no cascading drops). Fix: strip `DEFAULT ...` from column definitions in test helpers. For features that appear unsupported (e.g., `CREATE FUNCTION`), first verify by running test queries against Fabric and checking how dbt-spark/dbt-databricks handle it -- Fabric's Spark variant may support more than expected. Only skip after confirming the limitation with actual queries.

- **Test infrastructure helpers assume T-SQL** -- Several test harness methods (`project.get_tables_in_schema()`, `clear_test_schema`, `project.run_sql()` with raw DDL) use T-SQL system views (`sys.tables`, `sys.views`) or T-SQL DDL syntax that does not exist in Spark SQL. Fix: override the test method to use Spark equivalents (`SHOW TABLES IN`, `SHOW VIEWS IN`, etc.). Check dbt-spark's test suite for existing overrides of the same helpers. When a base class assumes inter-test schema cleanup that Spark cannot perform (e.g., drop and recreate schema), split the test class into separate classes with one test each.

- **Base test assertions compare compiled SQL strings** -- Some base test classes assert exact compiled SQL strings (e.g., expecting `create view` with double-quoted identifiers). These assertions are testing dbt core internals (CTE inlining, SQL formatting), not adapter behavior. Since Fabric and FabricSpark generate different DDL and quoting, these assertions always fail. Fix: override the test method to keep functional assertions (run, check_relations_equal) and drop the SQL string comparison.

- **Base test classes override connection fixtures with PG credentials** -- Some base classes override `dbt_profile_target` with hardcoded PostgreSQL connection details. When inheriting from these classes, re-override `dbt_profile_target` to pass through the conftest fixture: `@pytest.fixture(scope="class") def dbt_profile_target(self, dbt_profile_target): return dbt_profile_target`.

- **Concurrent DW test runs cause transient metadata query failures** -- When running the full Fabric (T-SQL) test suite in parallel, concurrent DDL from other test classes can cause snapshot isolation errors on `sys.tables`/`sys.views` queries. This is infrastructure contention, not a code bug. Fix: add retry logic with a short delay to metadata queries that are prone to transient failures.

## Handling PR review comments

When processing review comments on a pull request, follow this workflow for each comment:

1. **Evaluate the comment** — Verify the claim against the actual code or documentation. Determine whether it's valid, partially valid, or not applicable.
2. **Fix if needed** — If the comment is valid (or partially valid), implement the fix. If it's not applicable, prepare a clear explanation of why.
3. **Reply to the comment** — Always reply to every comment on the PR via the GitHub API (`gh api repos/.../pulls/.../comments/{id}/replies`). Explain what was done to resolve it, or why the comment doesn't apply. Be specific: reference the code, the change made, or the reasoning.

Never silently fix comments without replying, and never ignore comments without explaining why they don't apply.

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

**Security**: `test.env` contains real Azure credentials and connection strings. It is in `.gitignore` — never commit it. Treat `test.env.sample` as the authoritative template for which variables are needed. Never hardcode credentials in code or tests.

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

### Community package integration tests

Integration tests for community dbt packages live in `tests/fabric/packages/`. They use the `BaseDbtPackageTests` base class from `base_package_test.py`, which provides shared fixture wiring and dispatch configuration.

**Base class fixtures:**

| Fixture | Purpose |
|---|---|
| `package_name` | dbt macro namespace (e.g., `dbt_utils`, `dbt_external_tables`) |
| `package_repo` | Git URL to the package repository (e.g., `https://github.com/dbt-labs/dbt-utils`) |
| `package_revision` | Git revision or tag (e.g., `1.3.0`) |
| `packages` | Installs via git + `integration_tests` subdirectory, using `package_repo`/`package_revision` |
| `project_config_update` | Sets up dispatch with `search_order: [test_dbt_package, dbt, <package_name>]` |
| `test_package` | Default flow: `dbt deps` → `dbt seed` → `dbt run` |

Subclasses must provide `package_name`, `package_repo`, and `package_revision`.

**Git packages** (have integration_tests subdirectory, e.g., dbt-utils) — inherit directly from `BaseDbtPackageTests`:

```python
class TestDbtUtils(BaseDbtPackageTests):
    @pytest.fixture(scope="class")
    def package_name(self) -> str:
        return "dbt_utils"

    @pytest.fixture(scope="class")
    def package_repo(self) -> str:
        return "https://github.com/dbt-labs/dbt-utils"

    @pytest.fixture(scope="class")
    def package_revision(self) -> str:
        return "1.3.0"
```

**PyPI packages** (e.g., dbt-external-tables) — create an intermediate base class that overrides `packages` (for PyPI format) and `test_package` (for the package-specific workflow). Concrete test classes then only provide `models` and `verify_data`:

```python
class BaseExternalTableTest(BaseDbtPackageTests):
    @pytest.fixture(scope="class")
    def package_name(self) -> str:
        return "dbt_external_tables"

    @pytest.fixture(scope="class")
    def package_repo(self) -> str:
        return "dbt-labs/dbt_external_tables"

    @pytest.fixture(scope="class")
    def package_revision(self) -> str:
        return "0.11.0"

    @pytest.fixture(scope="class")
    def packages(self, package_repo: str, package_revision: str):
        return {"packages": [{"package": package_repo, "version": package_revision}]}

    def test_package(self, project, dbt_core_bug_workaround):
        run_dbt(["deps"])
        run_dbt(["run-operation", "stage_external_sources"])
        results = run_dbt(["run"])
        for r in results:
            assert r.status == "success"
        self.verify_data(project)

    def verify_data(self, project):
        raise NotImplementedError

class TestExternalTableCSV(BaseExternalTableTest):
    @pytest.fixture(scope="class")
    def models(self):
        ...  # sources.yml + model SQL for CSV

    def verify_data(self, project):
        ...  # assert row counts and data values
```

## CI/CD

GitHub Actions workflows in `.github/workflows/`:

| Workflow | Trigger | What it does |
|---|---|---|
| `lint-format.yml` | PR, push | `ruff format --check` + `ruff check` |
| `integration-tests.yml` | PR, push, weekly (Sun 01:00 UTC) | Matrix: Python 3.11/3.12/3.13 x {DW, DE} |
| `publish-docker.yml` | Manual | Build CI Docker image (`.github/CI.Dockerfile`) → ghcr.io |
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
- **PEP 604 union syntax**: use `X | Y` instead of `typing.Union[X, Y]` — the project targets Python 3.13 and has no `from typing import Union` imports
- **Class constants at the top**: group all class-level constants together at the top of the class body, before any methods

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
