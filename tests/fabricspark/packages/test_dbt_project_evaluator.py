import pytest

from tests.packages.base_package_test import BaseDbtPackageTests


class TestDbtProjectEvaluator(BaseDbtPackageTests):
    @pytest.fixture(scope="class")
    def package_name(self) -> str:
        return "dbt_project_evaluator"

    @pytest.fixture(scope="class")
    def package_repo(self) -> str:
        return "https://github.com/sdebruyn/dbt-project-evaluator"

    @pytest.fixture(scope="class")
    def package_revision(self) -> str:
        return "feature/fabric-support"

    @pytest.fixture(scope="class")
    def packages(self, package_repo, package_revision, dbt_utils_version):
        return {
            "packages": [
                {"git": package_repo, "revision": package_revision},
                {"package": "dbt-labs/dbt_utils", "version": dbt_utils_version},
            ]
        }

    @pytest.fixture(scope="class")
    def project_vars(self):
        return {
            "max_depth_dag": 9,
        }
