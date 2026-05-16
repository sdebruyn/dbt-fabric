import pytest

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
    def packages(
        self,
        package_name: str,
        package_repo: str,
        package_revision: str,
        dbt_utils_version: str,
        dbt_date_repo: str,
        dbt_date_revision: str,
    ):
        return {
            "packages": [
                {"git": package_repo, "revision": package_revision},
                {
                    "git": package_repo,
                    "revision": package_revision,
                    "subdirectory": "integration_tests",
                },
                {"package": "dbt-labs/dbt_utils", "version": dbt_utils_version},
                {"git": dbt_date_repo, "revision": dbt_date_revision},
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
