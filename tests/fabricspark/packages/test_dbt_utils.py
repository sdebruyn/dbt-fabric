import pytest

from tests.packages.base_package_test import BaseDbtPackageTests


class TestDbtUtils(BaseDbtPackageTests):
    @pytest.fixture(scope="class")
    def models_config(self):
        return {
            "dbt_utils_integration_tests": {
                "sql": {
                    "test_groupby": {"+enabled": False},
                    "test_urls": {"+enabled": False},
                    "test_unpivot_bool": {"+enabled": False},
                }
            }
        }

    @pytest.fixture(scope="class")
    def macros(self):
        return {
            "limit_zero.sql": """
{% macro default__limit_zero() %}
  {{ return('limit 0') }}
{% endmacro %}"""
        }

    @pytest.fixture(scope="class")
    def package_name(self) -> str:
        return "dbt_utils"

    @pytest.fixture(scope="class")
    def package_repo(self) -> str:
        return "https://github.com/dbt-labs/dbt-utils"

    @pytest.fixture(scope="class")
    def package_revision(self, dbt_utils_version) -> str:
        return dbt_utils_version
