import pytest

from tests.packages.base_package_test import BaseDbtPackageTests


class TestDbtUtils(BaseDbtPackageTests):
    @pytest.fixture(scope="class")
    def models_config(self):
        return {
            "dbt_utils_integration_tests": {
                "sql": {
                    "test_groupby": {"+enabled": False},
                    "test_get_relations_by_prefix_and_union": {"+enabled": False},
                    "test_get_relations_by_pattern": {"+enabled": False},
                }
            }
        }

    @pytest.fixture(scope="class")
    def seeds_config(self):
        return {
            "dbt_utils_integration_tests": {
                "schema_tests": {
                    "data_test_equality_floats_a": {"+enabled": False},
                    "data_test_equality_floats_b": {"+enabled": False},
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
