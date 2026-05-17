import pytest

from dbt.tests.util import run_dbt
from tests.packages.base_package_test import BaseDbtPackageTests


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

        # Upstream guards these tests with `target.type in ['spark']`, but this
        # adapter reports `fabricspark`. The spark__regexp_instr macro ignores
        # is_raw and flags parameters, so these tests produce wrong results.
        for test in (
            "expect_column_values_to_match_regex",
            "expect_column_values_to_not_match_regex",
            "expect_column_values_to_match_regex_list",
            "expect_column_values_to_not_match_regex_list",
        ):
            excludes.extend(["--exclude", f"test_name:{test}"])

        # Upstream generate_series macro hits "upper bound must be positive"
        # compilation error on FabricSpark.
        excludes.extend(
            ["--exclude", "test_name:expect_row_values_to_have_data_for_every_n_datepart"]
        )

        # Static upstream fixture dates are not recent enough for this assertion.
        excludes.extend(["--exclude", "test_name:expect_row_values_to_have_recent_data"])

        run_dbt(["build"] + excludes)
