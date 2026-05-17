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
    def models_config(self):
        return {
            "dbt_expectations_integration_tests": {
                "schema_tests": {
                    # dbt_date.now() generates T-SQL incompatible date arithmetic in these models
                    "timeseries_data": {"+enabled": False},
                    "timeseries_data_extended": {"+enabled": False},
                    "timeseries_data_grouped": {"+enabled": False},
                    "timeseries_hourly_data_extended": {"+enabled": False},
                }
            }
        }

    @pytest.fixture(scope="class")
    def tests_config(self):
        return {
            "dbt_expectations_integration_tests": {
                "expect_column_values_to_match_regex": {"+enabled": False},
                "expect_column_values_to_not_match_regex": {"+enabled": False},
                "expect_column_values_to_match_regex_list": {"+enabled": False},
                "expect_column_values_to_not_match_regex_list": {"+enabled": False},
                "expect_column_to_exist": {"+enabled": False},
                "expect_column_values_to_have_consistent_casing": {"+enabled": False},
                "expect_compound_columns_to_be_unique": {"+enabled": False},
                "expect_column_most_common_value_to_be_in_set": {"+enabled": False},
            }
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
