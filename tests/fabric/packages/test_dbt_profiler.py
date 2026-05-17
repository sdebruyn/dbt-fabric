import pytest

from dbt.tests.util import run_dbt
from tests.fabric.packages.base_package_test import BaseDbtPackageTests


class TestDbtProfiler(BaseDbtPackageTests):
    @pytest.fixture(scope="class")
    def package_name(self) -> str:
        return "dbt_profiler"

    @pytest.fixture(scope="class")
    def package_repo(self) -> str:
        return "https://github.com/data-mie/dbt-profiler"

    @pytest.fixture(scope="class")
    def package_revision(self) -> str:
        return "1.0.0"

    @pytest.fixture(scope="class")
    def extra_dispatches(self):
        return [
            {
                "macro_namespace": "dbt_expectations",
                "search_order": [
                    "test_dbt_package",
                    "dbt",
                    "dbt_expectations",
                ],
            }
        ]

    @pytest.fixture(scope="class")
    def models_config(self):
        return {
            "dbt_profiler_integration_tests": {
                # STRUCT type does not exist in T-SQL (BigQuery-only)
                "profile_struct": {"+enabled": False},
            }
        }

    @pytest.fixture(scope="class")
    def seeds_config(self):
        return {
            "dbt_profiler_integration_tests": {"+column_types": {"date_nullable": "datetime2(6)"}}
        }

    def test_package(self, project, dbt_core_bug_workaround):
        run_dbt(["deps"])
        results = run_dbt(["build"], expect_pass=False)
        failures = [r for r in results.results if r.status in ("error", "fail")]
        # dbt_expectations.expect_column_to_exist renders Jinja True/False directly in SQL
        # (invalid T-SQL). The test is namespace-qualified in the package yml so a local
        # override cannot take precedence. Upstream: metaplane/dbt-expectations#43
        expected = "expect_column_to_exist"
        unexpected = [f for f in failures if expected not in f.node.unique_id]
        assert not unexpected, f"Unexpected failures: {[f.node.unique_id for f in unexpected]}"

        # Run the incremental model a second time to test the merge/insert path
        run_dbt(["run", "--select", "profile_over_time"])
