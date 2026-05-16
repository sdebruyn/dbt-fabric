import pytest

from dbt.tests.util import run_dbt
from tests.fabric.packages.base_package_test import BaseDbtPackageTests

_SAMPLE_MODEL_SQL = """
{{ config(materialized='table') }}

select
    1 as id,
    cast('Alice' as varchar(100)) as name,
    cast(100.50 as decimal(10,2)) as amount,
    cast('2024-01-15 10:00:00' as datetime2(6)) as updated_at
union all
select
    2 as id,
    cast('Bob' as varchar(100)) as name,
    cast(200.75 as decimal(10,2)) as amount,
    cast('2024-02-20 11:30:00' as datetime2(6)) as updated_at
union all
select
    3 as id,
    cast('Charlie' as varchar(100)) as name,
    cast(50.00 as decimal(10,2)) as amount,
    cast('2024-03-10 09:15:00' as datetime2(6)) as updated_at
"""

_SCHEMA_YML = """
version: 2

models:
  - name: sample_model
    columns:
      - name: id
        data_tests:
          - not_null
          - unique
      - name: name
        data_tests:
          - not_null
          - elementary.column_anomalies:
              timestamp_column: "updated_at"
              column_anomalies:
                - "null_count"
                - "missing_count"
                - "min_length"
                - "max_length"
      - name: amount
        data_tests:
          - not_null
          - elementary.column_anomalies:
              timestamp_column: "updated_at"
              column_anomalies:
                - "null_count"
                - "zero_count"
                - "min"
                - "max"
                - "average"
    data_tests:
      - elementary.volume_anomalies:
          timestamp_column: "updated_at"
      - elementary.freshness_anomalies:
          timestamp_column: "updated_at"
      - elementary.schema_changes
"""


class TestElementary(BaseDbtPackageTests):
    @pytest.fixture(scope="class")
    def package_name(self) -> str:
        return "elementary"

    @pytest.fixture(scope="class")
    def package_repo(self) -> str:
        return "https://github.com/elementary-data/dbt-data-reliability"

    @pytest.fixture(scope="class")
    def package_revision(self) -> str:
        return "0.23.1"

    @pytest.fixture(scope="class")
    def packages(self, package_repo: str, package_revision: str):
        return {
            "packages": [
                {"git": package_repo, "revision": package_revision},
            ]
        }

    @pytest.fixture(scope="class")
    def models(self):
        return {
            "sample_model.sql": _SAMPLE_MODEL_SQL,
            "schema.yml": _SCHEMA_YML,
        }

    @pytest.fixture(scope="class")
    def project_config_update(self, package_name: str):
        return {
            "name": "test_dbt_package",
            "dispatch": [
                {
                    "macro_namespace": package_name,
                    "search_order": ["test_dbt_package", "dbt", package_name],
                },
                {
                    "macro_namespace": "dbt_utils",
                    "search_order": ["test_dbt_package", "dbt", "dbt_utils"],
                },
            ],
            "models": {
                "elementary": {"+schema": "elementary"},
            },
        }

    def test_package(self, project, dbt_core_bug_workaround):
        run_dbt(["deps"])
        run_dbt(["run"])
        run_dbt(["test"])
