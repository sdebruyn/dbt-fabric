import pytest

from dbt.tests.util import run_dbt
from tests.fabric.packages.base_package_test import BaseDbtPackageTests

EXCLUDED_MODELS = [
    "timeseries_data",
    "timeseries_data_extended",
    "timeseries_data_grouped",
    "timeseries_hourly_data_extended",
]

EXCLUDED_TESTS = [
    "expect_column_values_to_match_regex",
    "expect_column_values_to_not_match_regex",
    "expect_column_values_to_match_regex_list",
    "expect_column_values_to_not_match_regex_list",
    "expect_column_to_exist",
    "expect_column_values_to_have_consistent_casing",
    "expect_compound_columns_to_be_unique",
    "expect_column_most_common_value_to_be_in_set",
]


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
        excludes = []
        for model in EXCLUDED_MODELS:
            excludes.extend(["--exclude", f"{model}+"])
        for test in EXCLUDED_TESTS:
            excludes.extend(["--exclude", f"test_name:{test}"])
        run_dbt(["build"] + excludes)
