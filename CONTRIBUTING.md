# Contributing to dbt-fabric

## Getting started

We recommend [uv](https://docs.astral.sh/uv/) for managing Python environments and dependencies. A single command sets up everything you need (virtual environment, all dependencies, the adapter in editable mode):

```shell
uv sync
```

Use `uv run ...` to run commands inside the virtual environment, or [activate it](https://docs.astral.sh/uv/pip/environments/#using-a-virtual-environment) first.

## Architecture

dbt uses a plugin system where adapters translate dbt's abstract operations into database-specific SQL. This adapter supports two Microsoft Fabric compute engines:

- **Fabric** (adapter type `fabric`) — Fabric Data Warehouse, uses T-SQL via [mssql-python](https://pypi.org/project/mssql-python/) (no ODBC drivers needed)
- **FabricSpark** (adapter type `fabricspark`) — Fabric Lakehouse / Data Engineering, uses Spark SQL via Livy sessions

An adapter consists of:

1. **Python adapter classes** — Connection management, query execution, metadata retrieval. Located in `src/dbt/adapters/fabric/` and `src/dbt/adapters/fabricspark/`.
2. **Jinja SQL macros** — dbt operations (CREATE TABLE, incremental merge, snapshot, etc.) expressed in the target SQL dialect. Located in `src/dbt/include/fabric/macros/` and `src/dbt/include/fabricspark/macros/`.
3. **Plugin registration** — Each adapter registers via `AdapterPlugin` in its `__init__.py`.

dbt selects the correct macro by adapter name prefix: `fabric__dateadd` for Fabric, `fabricspark__dateadd` for FabricSpark, falling back to `default__dateadd` if no override exists.

### Key SQL dialect differences

| Concept | Fabric (T-SQL) | FabricSpark (Spark SQL) |
|---|---|---|
| Pagination | `SELECT TOP N` | `LIMIT N` |
| String type | `varchar(MAX)` | `string` |
| Timestamp | `datetime2(6)` | `timestamp` |
| Identifier quoting | `[brackets]` | `` `backticks` `` |
| Default materialization | `table` | `materialized_view` (lake view) |
| Connection | mssql-python (TDS) | Livy sessions (HTTP/REST) |

Note: Fabric Lakehouse with schemas does **not** support Spark SQL views — only tables and materialized lake views.

### Community package compatibility

The `src/dbt/include/fabric/macros/dbt_package_support/` directory contains macro overrides that make popular dbt packages (dbt-utils, dbt-date, dbt-expectations, dbt-audit-helper) work with Fabric's T-SQL dialect.

## Testing

Integration tests run against real Microsoft Fabric infrastructure. You need:

1. A Fabric workspace with a Data Warehouse and/or Lakehouse
2. Azure credentials (`az login`)
3. A `test.env` file — copy from `test.env.sample` and fill in your values:
   ```shell
   cp test.env.sample test.env
   ```

Key environment variables:

| Variable | Required for | Description |
|---|---|---|
| `FABRIC_TEST_WORKSPACE_NAME` | Both | Fabric workspace name |
| `FABRIC_TEST_DWH_NAME` | `--dw` | Data Warehouse name |
| `FABRIC_TEST_HOST` | `--dw` | SQL endpoint host |
| `FABRIC_TEST_LAKEHOUSE_NAME` | `--de` | Lakehouse name |
| `FABRIC_TEST_LIVY_SESSION_NAME` | `--de` | Livy session name (optional) |
| `FABRIC_TEST_THREADS` | Both | Parallelism (default: 10) |

### Running tests

```shell
uv run pytest                        # All integration tests
uv run pytest --dw                   # Fabric (T-SQL) tests only
uv run pytest --de                   # FabricSpark tests only
uv run pytest --with-grants          # Include GRANT/authorization tests
uv run pytest -k "TestClassName"     # A specific test class
```

### Test architecture

Tests use [dbt-tests-adapter](https://github.com/dbt-labs/dbt-adapters), dbt's official adapter test harness. It provides base test classes for standard adapter behavior. Our tests inherit from these and override fixtures where Fabric's SQL dialect differs:

```python
from dbt.tests.adapter.basic.test_base import BaseSimpleMaterializations

class TestSimpleMaterializations(BaseSimpleMaterializations):
    pass  # Inherits all test methods, uses the Fabric adapter automatically
```

When Fabric needs different SQL, override the relevant fixture (`models`, `seeds`, `macros`, `project_config_update`, etc.):

```python
class TestIncrementalFabric(BaseIncrementalOnSchemaChange):
    @pytest.fixture(scope="class")
    def models(self):
        return {"model.sql": fabric_specific_sql}
```

The adapter type is detected from the test file path: `tests/fabric/**` → `fabric`, `tests/fabricspark/**` → `fabricspark`.

### Debugging test failures

Each test class gets its own log directory and a temporary dbt project. Both paths are printed in pytest output:

```
=== Test logs_dir: /path/to/dbt-fabric/logs/test17723817511604948531
=== Test project_root: /private/var/folders/.../project0/
```

- **Logs** — The dbt log shows the exact SQL sent to Fabric and any errors returned.
- **Compiled SQL** — Look in the temp project's `target/compiled/` and `target/run/` to see what dbt generated.

Debugging workflow:

1. Run with `-v -s` for full output: `uv run pytest -k "TestClassName" --dw -v -s`
2. Read the dbt log for the SQL error.
3. Check compiled SQL in `target/compiled/`.
4. Trace it back to the macro that generated it, fix, and re-run.

## Code style

- **Formatter/linter**: [ruff](https://docs.astral.sh/ruff/) (config in `pyproject.toml`)
- **Line length**: 99
- **Python target**: 3.13
- **Quote style**: double quotes

Always run before committing:

```shell
uv run ruff format .
uv run ruff check --fix .
```

## CI/CD

GitHub Actions workflows in `.github/workflows/`:

| Workflow | Trigger | What it does |
|---|---|---|
| `lint-format.yml` | PR, push | `ruff format --check` + `ruff check` |
| `integration-tests.yml` | PR, push, weekly | Matrix: Python 3.11/3.12/3.13 x {DW, DE} |
| `publish-docker.yml` | Manual | Build CI Docker image (`.github/CI.Dockerfile`) → ghcr.io |
| `release-version.yml` | Tag `v*` | Update version, build, publish to PyPI |

CI authenticates to Azure via OIDC (federated credentials, no secrets stored). Tests run inside Docker containers with pre-installed `mssql-python` dependencies.

## Releasing

Create a git tag and push it:

```shell
git tag v1.2.3 && git push origin v1.2.3
```

The `release-version.yml` workflow automatically updates `__version__.py` in both adapter packages, builds with `uv build`, and publishes to PyPI.

## Documentation

The documentation website at [dbt-fabric.debruyn.dev](https://dbt-fabric.debruyn.dev) is built with [Zensical](https://zensical.com). Source files live in `docs/`, configuration in `zensical.toml`.

```shell
uv run zensical serve                 # Local preview at http://127.0.0.1:8000
uv run zensical build --strict        # Build and fail on warnings
```

When adding or changing adapter-specific behavior, update the relevant docs page. When linking to Microsoft Learn pages, always append `?WT.mc_id=MVP_310840` (or `&WT.mc_id=MVP_310840` if the URL already has query parameters).
