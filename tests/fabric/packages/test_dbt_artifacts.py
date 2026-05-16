from typing import Any

import pytest

from dbt.tests.util import run_dbt
from tests.fabric.packages.base_package_test import BaseDbtPackageTests


class TestDbtArtifacts(BaseDbtPackageTests):
    @pytest.fixture(scope="class")
    def package_name(self) -> str:
        return "dbt_artifacts"

    @pytest.fixture(scope="class")
    def package_repo(self) -> str:
        return "https://github.com/brooklyn-data/dbt_artifacts"

    @pytest.fixture(scope="class")
    def package_revision(self) -> str:
        return "2.10.1"

    @pytest.fixture(scope="class")
    def packages(
        self, package_name: str, package_repo: str, package_revision: str
    ) -> dict[str, list]:
        return {
            "packages": [
                {"git": package_repo, "revision": package_revision},
                {
                    "git": package_repo,
                    "revision": package_revision,
                    "subdirectory": "integration_test_project",
                },
            ]
        }

    @pytest.fixture(scope="class")
    def models_config(self) -> dict[str, Any]:
        return {
            "dbt_fabric": {
                "dbt_artifacts": {"+enabled": True, "+materialized": "table"},
            },
            "artifacts_integration_tests": {
                "+persist_docs": {"relation": False, "columns": False},
            },
        }

    @pytest.fixture(scope="class")
    def seeds_config(self) -> dict[str, Any]:
        return {
            "artifacts_integration_tests": {
                "freshness": {"+column_types": {"load_timestamp": "datetime2(6)"}}
            }
        }

    @pytest.fixture(scope="class")
    def project_vars(self) -> dict[str, Any]:
        return {
            "dbt_artifacts_exclude_all_results": True,
        }

    @pytest.fixture(scope="class")
    def extra_dispatches(self) -> list[dict[str, Any]]:
        return [
            {
                "macro_namespace": "dbt_artifacts",
                "search_order": ["test_dbt_package", "dbt", "dbt_artifacts"],
            },
        ]

    @pytest.fixture(scope="class")
    def project_config_update(
        self,
        package_name: str,
        models_config: dict,
        seeds_config: dict,
        tests_config: dict,
        project_vars: dict,
        extra_dispatches: list,
    ) -> dict[str, Any]:
        dispatches = [
            {
                "macro_namespace": package_name,
                "search_order": ["test_dbt_package", "dbt", package_name],
            },
            {
                "macro_namespace": "dbt_utils",
                "search_order": ["test_dbt_package", "dbt", "dbt_utils"],
            },
        ]
        dispatches.extend(extra_dispatches)

        return {
            "name": "test_dbt_package",
            "vars": project_vars,
            "dispatch": dispatches,
            "seeds": seeds_config,
            "models": models_config,
            "tests": tests_config,
            "on-run-end": ["{{ fabric__upload_results(results) }}"],
        }

    def test_package(self, project, dbt_core_bug_workaround):
        run_dbt(["deps"])
        run_dbt(["seed"])
        run_dbt(["run"])
        run_dbt(["test"])
