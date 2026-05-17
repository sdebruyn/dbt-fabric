import pytest

from dbt.tests.util import run_dbt
from tests.packages.base_package_test import BaseDbtPackageTests


class TestDbtArtifacts(BaseDbtPackageTests):
    @pytest.fixture(scope="class")
    def package_name(self) -> str:
        return "dbt_artifacts"

    @pytest.fixture(scope="class")
    def package_repo(self) -> str:
        return "https://github.com/brooklyn-data/dbt_artifacts"

    @pytest.fixture(scope="class")
    def package_revision(self) -> str:
        return "2.10.1"

    @pytest.fixture(scope="class")
    def packages(
        self,
        package_name: str,
        package_repo: str,
        package_revision: str,
        dbt_utils_version: str,
    ):
        return {
            "packages": [
                {"git": package_repo, "revision": package_revision},
                {
                    "git": package_repo,
                    "revision": package_revision,
                    "subdirectory": "integration_test_project",
                },
                {"package": "dbt-labs/dbt_utils", "version": dbt_utils_version},
            ]
        }

    @pytest.fixture(scope="class")
    def models_config(self):
        return {
            "dbt_artifacts": {
                "+file_format": "delta",
            },
        }

    def test_package(self, project, dbt_core_bug_workaround):
        run_dbt(["deps"])
        run_dbt(
            [
                "build",
                "--exclude",
                "microbatch",
            ],
        )
