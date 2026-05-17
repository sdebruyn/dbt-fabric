import pytest

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
    def models_config(self):
        return {
            "dbt_profiler_integration_tests": {
                "profile_struct": {"+enabled": False},
                "profile_over_time": {"+enabled": False},
            }
        }

    @pytest.fixture(scope="class")
    def seeds_config(self):
        return {
            "dbt_profiler_integration_tests": {"+column_types": {"date_nullable": "datetime2(6)"}}
        }
