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
                    # dbt_date.now() generates T-SQL incompatible date arithmetic
                    "timeseries_data": {"+enabled": False},
                    "timeseries_data_extended": {"+enabled": False},
                    "timeseries_data_grouped": {"+enabled": False},
                    "timeseries_hourly_data_extended": {"+enabled": False},
                }
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

    def test_package(self, project, dbt_core_bug_workaround):
        run_dbt(["deps"])

        excludes = []

        # T-SQL has no native regex support (no REGEXP, REGEXP_LIKE, or similar).
        # These tests cannot be fixed with macro overrides or adapter dispatch.
        for test in (
            "expect_column_values_to_match_regex",
            "expect_column_values_to_not_match_regex",
            "expect_column_values_to_match_regex_list",
            "expect_column_values_to_not_match_regex_list",
        ):
            excludes.extend(["--exclude", f"test_name:{test}"])

        # These tests have T-SQL incompatible SQL but do NOT use adapter.dispatch(),
        # so they cannot be overridden by adapter macros. Project-level macros also
        # cannot shadow them because dbt resolves generic tests defined in a package's
        # schema.yml from the package's own macro namespace, not the root project.
        for test in (
            # Upstream renders Python True/False as SQL literals and uses bare boolean
            # in WHERE. T-SQL has no boolean type.
            "expect_column_to_exist",
            # Upstream uses positional GROUP BY 1. T-SQL does not support positional
            # GROUP BY.
            "expect_column_values_to_have_consistent_casing",
        ):
            excludes.extend(["--exclude", f"test_name:{test}"])

        # This specific test instance sets fail_calc='cast((count(*)=0) as int)' in its
        # schema.yml. T-SQL cannot cast a boolean expression to int. This is a test
        # harness config issue in the upstream integration_tests, not an adapter
        # limitation — the expect_compound_columns_to_be_unique test itself works fine.
        excludes.extend(
            [
                "--exclude",
                "dbt_expectations_expect_compound_columns_to_be_unique_data_test_date_col__col_null__all_values_are_missing",
            ]
        )

        run_dbt(["build"] + excludes)
