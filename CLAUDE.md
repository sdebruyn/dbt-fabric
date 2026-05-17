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

For coordinating parallel agents to fix multiple test failures, use the `multi-agent` skill.

## Testing

### Test architecture

Tests use [dbt-tests-adapter](https://github.com/dbt-labs/dbt-adapters), dbt's official adapter test harness. It provides base test classes for standard adapter behavior. Our tests inherit from these base classes and override fixtures where Fabric's SQL dialect differs. See any test file in `tests/fabric/adapter/` or `tests/fabricspark/adapter/` for the pattern.

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

For adding integration tests for community dbt packages, use the `community-package-tests` skill. See `tests/fabric/packages/base_package_test.py` for the `BaseDbtPackageTests` base class and existing tests in the same directory for examples.

## CI/CD

GitHub Actions workflows in `.github/workflows/`:

| Workflow | Trigger | What it does |
|---|---|---|
| `lint-format.yml` | PR, push | `ruff format --check` + `ruff check` |
| `integration-tests-dw.yml` | PR, push, manual, weekly (Sun 02:00 UTC) | DW tests: Python 3.14 only on PR/push/manual, full matrix (3.11/3.12/3.13/3.14) on weekly schedule |
| `integration-tests-de.yml` | Weekly (Sun 01:00 UTC), PR comment (`/test-de`), manual | DE tests: weekly full run on main + on-demand per PR via `/test-de <filter>` or `gh workflow run` |
| `release-version.yml` | Tag `v*` | Update version, build, publish to PyPI |

CI authenticates to Azure via OIDC (federated credentials, no secrets stored). Tests run on `ubuntu-latest` runners with `libltdl7` installed (required by mssql-python's bundled ODBC driver).

## Releasing

1. Create and push a git tag: `git tag v1.2.3 && git push origin v1.2.3`
2. The `release-version.yml` workflow automatically:
   - Updates `__version__.py` in both adapter packages
   - Builds with `uv build`
   - Publishes to PyPI with `uv publish`

## Code style

- **Formatter/linter**: ruff (config in `pyproject.toml`)
- **Line length**: 99
- **Python target**: 3.11 (ruff target-version, must match minimum supported Python)
- **Quote style**: double quotes
- **Lint rules**: isort (`I`) + no commented-out code (`ERA`)
- **No comments in code** unless the _why_ is non-obvious
- **Always run ruff before committing**: `uv run ruff format .` and `uv run ruff check --fix .` must pass before every commit
- **PEP 604 union syntax**: use `X | Y` instead of `typing.Union[X, Y]` — the minimum supported Python is 3.11 (PEP 604 requires 3.10+) and there are no `from typing import Union` imports
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
