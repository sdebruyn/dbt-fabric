import pytest

from dbt.tests.util import run_dbt
from tests.fabric.packages.base_package_test import BaseDbtPackageTests


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
                    "compare_all_columns_with_summary": {"+enabled": False},
                    "compare_all_columns_without_summary": {"+enabled": False},
                    "compare_all_columns_concat_pk_with_summary": {"+enabled": False},
                    "compare_all_columns_concat_pk_without_summary": {"+enabled": False},
                    "compare_all_columns_with_summary_and_exclude": {"+enabled": False},
                    "compare_all_columns_where_clause": {"+enabled": False},
                    "compare_which_columns_differ": {"+enabled": False},
                    "compare_which_columns_differ_exclude_cols": {"+enabled": False},
                    "compare_relation_columns": {"+materialized": "table"},
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

    def test_package(self, project, dbt_core_bug_workaround):
        run_dbt(["deps"])
        run_dbt(["seed"])
        run_dbt(["run"])
        run_dbt(["test"])
