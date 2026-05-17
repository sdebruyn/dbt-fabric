import pytest

from dbt.tests.util import run_dbt
from tests.packages.base_package_test import BaseDbtPackageTests


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
    def models_config(self):
        return {
            "dbt_profiler_integration_tests": {
                # STRUCT type does not exist in Spark SQL on Fabric (BigQuery-only)
                "profile_struct": {"+enabled": False},
            }
        }

    def test_package(self, project, dbt_core_bug_workaround):
        run_dbt(["deps"])
        run_dbt(["build"])
        run_dbt(["run", "--select", "profile_over_time"])
