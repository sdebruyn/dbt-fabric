import pytest

from dbt.tests.util import run_dbt
from tests.fabric.packages.base_package_test import BaseDbtPackageTests


class TestDbtExpectations(BaseDbtPackageTests):
    @pytest.fixture(scope="class")
    def package_name(self) -> str:
        return "dbt_expectations"

    @pytest.fixture(scope="class")
    def package_repo(self) -> str:
        return "https://github.com/metaplane/dbt-expectations"

    @pytest.fixture(scope="class")
    def package_revision(self) -> str:
        return "0.10.10"

    @pytest.fixture(scope="class")
    def packages(self, package_name: str, package_repo: str, package_revision: str):
        return {
            "packages": [
                {"git": package_repo, "revision": package_revision},
                {
                    "git": package_repo,
                    "revision": package_revision,
                    "subdirectory": "integration_tests",
                },
                {"package": "dbt-labs/dbt_utils", "version": "1.3.0"},
            ]
        }

    @pytest.fixture(scope="class")
    def project_vars(self):
        return {"dbt_date:time_zone": "UTC"}

    @pytest.fixture(scope="class")
    def extra_dispatches(self):
        return [
            {
                "macro_namespace": "dbt_date",
                "search_order": ["test_dbt_package", "dbt", "dbt_date"],
            },
        ]

    def test_package(self, project, dbt_core_bug_workaround):
        run_dbt(["deps"])
        run_dbt(["run"])
        run_dbt(["test"])
