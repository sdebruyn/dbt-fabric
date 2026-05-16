import pytest

from dbt.tests.util import run_dbt
from tests.fabric.packages.base_package_test import BaseDbtPackageTests


class TestDbtProjectEvaluator(BaseDbtPackageTests):
    @pytest.fixture(scope="class")
    def package_name(self) -> str:
        return "dbt_project_evaluator"

    @pytest.fixture(scope="class")
    def package_repo(self) -> str:
        return "https://github.com/dbt-labs/dbt-project-evaluator"

    @pytest.fixture(scope="class")
    def package_revision(self) -> str:
        return "v1.2.4"

    @pytest.fixture(scope="class")
    def packages(self, package_repo, package_revision):
        return {
            "packages": [
                {"git": package_repo, "revision": package_revision},
                {"package": "dbt-labs/dbt_utils", "version": "1.3.0"},
            ]
        }

    @pytest.fixture(scope="class")
    def project_vars(self):
        return {
            "max_depth_dag": 9,
        }

    def test_package(self, project, dbt_core_bug_workaround):
        run_dbt(["deps"])
        run_dbt(["seed"])
        run_dbt(["run"])
