import pytest

from tests.packages.base_package_test import BaseDbtPackageTests


class TestDbtAuditHelper(BaseDbtPackageTests):
    @pytest.fixture(scope="class")
    def package_name(self) -> str:
        return "audit_helper"

    @pytest.fixture(scope="class")
    def package_repo(self) -> str:
        return "https://github.com/dbt-labs/dbt-audit-helper"

    @pytest.fixture(scope="class")
    def package_revision(self) -> str:
        return "0.13.0"

    @pytest.fixture(scope="class")
    def models_config(self):
        return {
            "audit_helper_integration_tests": {
                "unit_test_placeholder_models": {
                    "unit_test_struct_model_a": {"+enabled": False},
                    "unit_test_struct_model_b": {"+enabled": False},
                },
                "unit_test_wrappers": {"+enabled": False},
                "data_tests": {
                    "compare_and_classify_query_results": {"+enabled": False},
                    "compare_all_columns_where_clause": {"+enabled": False},
                    # Macro works (run_query fetches metadata separately, view
                    # builds with correct VALUES), but the equality test fails:
                    # upstream seed CSV has UPPERCASE headers while the model
                    # outputs lowercase, and Fabric's BIN2 collation is
                    # case-sensitive for identifiers.
                    "compare_relation_columns": {"+enabled": False},
                },
            }
        }

    @pytest.fixture(scope="class")
    def project_vars(self):
        return {
            "compare_queries_summarize": True,
            "primary_key_columns_var": ["col1"],
            "columns_var": ["col1"],
            "event_time_var": None,
            "quick_are_queries_identical_cols": ["col1"],
        }
