---
name: community-package-tests
description: Use when adding or modifying integration tests for community dbt packages (dbt-utils, dbt-date, dbt-expectations, dbt-audit-helper, dbt-external-tables). Covers the BaseDbtPackageTests base class, fixture wiring, and patterns for git-based and PyPI packages.
user-invocable: true
---

Integration tests for community dbt packages live in `tests/fabric/packages/`. They use the `BaseDbtPackageTests` base class from `base_package_test.py`, which provides shared fixture wiring and dispatch configuration.

**Base class fixtures:**

| Fixture | Purpose |
|---|---|
| `package_name` | dbt macro namespace (e.g., `dbt_utils`, `dbt_external_tables`) |
| `package_repo` | Git URL to the package repository (e.g., `https://github.com/dbt-labs/dbt-utils`) |
| `package_revision` | Git revision or tag (e.g., `1.3.0`) |
| `packages` | Installs via git + `integration_tests` subdirectory, using `package_repo`/`package_revision` |
| `project_config_update` | Sets up dispatch with `search_order: [test_dbt_package, dbt, <package_name>]` |
| `test_package` | Default flow: `dbt deps` -> `dbt seed` -> `dbt run` |

Subclasses must provide `package_name`, `package_repo`, and `package_revision`.

**Git packages** (have integration_tests subdirectory, e.g., dbt-utils) -- inherit directly from `BaseDbtPackageTests`:

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

**PyPI packages** (e.g., dbt-external-tables) -- create an intermediate base class that overrides `packages` (for PyPI format) and `test_package` (for the package-specific workflow). Concrete test classes then only provide `models` and `verify_data`:

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
