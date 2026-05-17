import pytest

from dbt.tests.util import run_dbt
from tests.packages.base_package_test import BaseDbtPackageTests


class TestDbtDate(BaseDbtPackageTests):
    @pytest.fixture(scope="class")
    def package_name(self) -> str:
        return "dbt_date"

    @pytest.fixture(scope="class")
    def package_repo(self, dbt_date_repo) -> str:
        return dbt_date_repo

    @pytest.fixture(scope="class")
    def package_revision(self, dbt_date_revision) -> str:
        return dbt_date_revision

    @pytest.fixture(scope="class")
    def project_vars(self):
        return {"dbt_date:time_zone": "America/Los_Angeles"}

    @pytest.fixture(scope="class")
    def extra_dispatches(self):
        return [
            {
                "macro_namespace": "dbt_date_integration_tests",
                "search_order": [
                    "test_dbt_package",
                    "dbt",
                    "dbt_date_integration_tests",
                ],
            }
        ]

    def test_package(self, project, dbt_core_bug_workaround):
        run_dbt(["deps"])
        # Upstream test_dates.yml has an expression_is_true test that renders
        # cast('to_date(...)' as date) — nested single quotes cause a Spark
        # PARSE_SYNTAX_ERROR. This is an upstream fixture bug, not an adapter issue.
        run_dbt(
            ["build", "--exclude", "test_name:expression_is_true"],
        )
