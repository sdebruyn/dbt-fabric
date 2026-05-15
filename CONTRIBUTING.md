# Development of the adapter

We recommend creating a virtual environment to develop the adapter. At the time of writing, [`uv`](https://docs.astral.sh/uv/) is a very popular tool to work with Python packages and environments. Installation should be pretty straightforward ([docs](https://docs.astral.sh/uv/getting-started/installation/)).

Throughout the rest of this guide, we'll assume you're using `uv`. `uv` is a drop-in replacement for `pip` with greater performance and additional features. You can of course use any other tool you prefer.

Uv is super simple to use and only requires you to run a single command to do the following:

1. Create a virtual environment
1. Install all dependencies
1. Install the adapter in an editable mode
1. Install the development dependencies

```shell
uv sync
```

To run anything inside the virtual environment, use `uv run ...`. Otherwise, you can [activate the virtual environment](https://docs.astral.sh/uv/pip/environments/#using-a-virtual-environment) before running any commands.

## Testing

The integration tests require a Fabric Data Warehouse. Tell our tests how they should connect to your data warehouse by creating a file called `test.env` in the root of the project.
You can use the provided `test.env.sample` as a base.

```shell
cp test.env.sample test.env
```

You can use the following command to run the integration tests:

```shell
uv run pytest
```

## Upgrading dbt-core support

When a new dbt-core minor version is released (e.g. 1.11 → 1.12), the adapter needs to be updated to support it. This is a systematic process:

### 1. Research what changed

Check these sources for changes that affect adapters:

* **[dbt-core release notes](https://github.com/dbt-labs/dbt-core/releases)** — new features, breaking changes, behavior flags
* **[dbt-adapters commits](https://github.com/dbt-labs/dbt-adapters/commits/main/dbt-adapters)** — new macros, adapter methods, dispatch changes
* **[dbt-tests-adapter commits](https://github.com/dbt-labs/dbt-adapters/commits/main/dbt-tests-adapter)** — new test classes to adopt
* **Reference adapters** — check what [Snowflake](https://github.com/dbt-labs/dbt-adapters/commits/main/dbt-snowflake), [Postgres](https://github.com/dbt-labs/dbt-adapters/commits/main/dbt-postgres), and [Spark](https://github.com/dbt-labs/dbt-adapters/commits/main/dbt-spark) implemented for the new version

Focus on:

* New dispatchable macros (search for `adapter.dispatch` in the diff)
* New base adapter methods or changed signatures
* New behavior flags (search for `behavior` in `dbt/adapters/base/impl.py`)
* New test classes in `dbt/tests/adapter/`

### 2. Bump version pins

In `pyproject.toml`, update the `dbt-core` upper bound in the dev dependency group. Also check if `dbt-adapters`, `dbt-tests-adapter`, or `dbt-common` need bumping.

### 3. Inventory new test classes

List all new `Base*` test classes in `dbt-tests-adapter`. For each one:

* **Already covered?** — check if we already have a subclass in `tests/fabric/` or `tests/fabricspark/`
* **Add it** — create a subclass with `pass` body in the appropriate test directory
* **Override fixtures** — if the default SQL uses syntax incompatible with T-SQL or Spark SQL, override the relevant fixture (see existing tests for patterns)
* **Skip if impossible** — if Fabric genuinely cannot support the feature, skip with a reason: `@pytest.mark.skip("reason")`

### 4. Implement missing macros and adapter methods

If the global project added new dispatchable macros with a `default__` that raises "not implemented", check if our adapter needs them. Look at what the reference adapters implemented.

### 5. Verify

Run the full test suite against the new dbt-core version:

```shell
uv sync
uv run pytest --dw -v   # Fabric (T-SQL)
uv run pytest --de -v   # FabricSpark
```

Fix failures using the standard TDD loop described in `CLAUDE.md`.

### 6. Update documentation

* Add the new dbt-core version to `docs/compatibility.md`
* Update any feature guides if new adapter features were added

## CI/CD

We use Docker images that have all the things we need to test the adapter in the CI/CD workflows.
The Dockerfile is located in the *.github* directory and pushed to GitHub Packages to this repo.
There is one tag per supported Python version.

All CI/CD pipelines are using GitHub Actions. The following pipelines are available:

* `publish-docker`: publishes the image we use in all other pipelines.
* `integration-tests`: runs the integration tests.
* `release-version`: publishes the adapter to PyPI.
* `lint-format`: runs `ruff` to check and format the code.

## Releasing a new version

Ceate a git tag named `v<version>` and push it to GitHub.
A GitHub Actions workflow will be triggered to build the package and push it to PyPI. 
