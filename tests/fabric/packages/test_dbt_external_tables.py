import json
import os
import urllib.parse

import pytest
import requests
from azure.identity import AzureCliCredential

from dbt.tests.util import relation_from_name, run_dbt
from tests.packages.base_package_test import BaseDbtPackageTests

TEST_CSV_CONTENT = (
    "id,name,amount,sale_date\n"
    "1,Widget A,19.99,2024-01-15\n"
    "2,Widget B,29.99,2024-02-20\n"
    "3,Gadget C,49.50,2024-03-10\n"
    "4,Gadget D,99.00,2024-04-05\n"
    "5,Widget E,14.75,2024-05-12"
)

TEST_JSONL_CONTENT = "\n".join(
    json.dumps(row)
    for row in [
        {"id": 1, "name": "Widget A", "amount": 19.99, "sale_date": "2024-01-15"},
        {"id": 2, "name": "Widget B", "amount": 29.99, "sale_date": "2024-02-20"},
        {"id": 3, "name": "Gadget C", "amount": 49.50, "sale_date": "2024-03-10"},
        {"id": 4, "name": "Gadget D", "amount": 99.00, "sale_date": "2024-04-05"},
        {"id": 5, "name": "Widget E", "amount": 14.75, "sale_date": "2024-05-12"},
    ]
)

_onelake_urls_cache = None


def _get_onelake_urls():
    """Resolve workspace/lakehouse IDs, upload test files, return dict of OneLake URLs."""
    global _onelake_urls_cache
    if _onelake_urls_cache is not None:
        return _onelake_urls_cache

    workspace_name = os.getenv("FABRIC_TEST_WORKSPACE_NAME")
    lakehouse_name = os.getenv("FABRIC_TEST_LAKEHOUSE_NAME")
    if not workspace_name or not lakehouse_name:
        return None

    try:
        credential = AzureCliCredential()
        pbi_token = credential.get_token("https://analysis.windows.net/powerbi/api/.default").token
        pbi_headers = {
            "Authorization": f"Bearer {pbi_token}",
            "Accept": "application/json",
        }

        query = urllib.parse.quote_plus(f"name eq '{workspace_name}'")
        resp = requests.get(
            f"https://api.powerbi.com/v1.0/myorg/groups?$filter={query}",
            headers=pbi_headers,
        )
        resp.raise_for_status()
        workspaces = resp.json().get("value", [])
        if not workspaces:
            return None
        workspace_id = workspaces[0]["id"]

        resp = requests.get(
            f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/lakehouses",
            headers=pbi_headers,
        )
        resp.raise_for_status()
        lakehouses = resp.json().get("value", [])
        lh = next((lh for lh in lakehouses if lh["displayName"] == lakehouse_name), None)
        if not lh:
            return None
        lakehouse_id = lh["id"]

        storage_token = credential.get_token("https://storage.azure.com/.default").token
        headers = {"Authorization": f"Bearer {storage_token}"}
        base = (
            f"https://onelake.dfs.fabric.microsoft.com"
            f"/{workspace_id}/{lakehouse_id}/Files/dbt-test"
        )

        _upload_file(headers, f"{base}/sample.csv", TEST_CSV_CONTENT.encode())
        _upload_file(headers, f"{base}/sample.jsonl", TEST_JSONL_CONTENT.encode())

        _onelake_urls_cache = {
            "csv_url": f"{base}/sample.csv",
            "jsonl_url": f"{base}/sample.jsonl",
        }
        return _onelake_urls_cache
    except Exception:
        return None


def _upload_file(headers, url, data):
    """Upload a file to OneLake via the DFS REST API (create, append, flush)."""
    requests.put(f"{url}?resource=file", headers=headers)
    requests.patch(
        f"{url}?action=append&position=0",
        headers={**headers, "Content-Type": "application/octet-stream"},
        data=data,
    )
    requests.patch(f"{url}?action=flush&position={len(data)}", headers=headers)


def _skip_without_lakehouse():
    urls = _get_onelake_urls()
    if not urls:
        pytest.skip("No lakehouse available for OPENROWSET end-to-end test")
    return urls


def _build_csv_sources_yml(csv_url):
    return f"""
version: 2
sources:
  - name: test_external
    schema: dbo
    tables:
      - name: sample_csv
        external:
          location: "{csv_url}"
          file_format: csv
          options:
            header_row: "true"
            fieldterminator: ","
            parser_version: "2.0"
        columns:
          - name: id
            data_type: int
          - name: name
            data_type: "varchar(100)"
          - name: amount
            data_type: "decimal(10,2)"
          - name: sale_date
            data_type: date
      - name: sample_csv_auto
        external:
          location: "{csv_url}"
          options:
            header_row: "true"
            fieldterminator: ","
            parser_version: "2.0"
        columns:
          - name: id
            data_type: int
          - name: name
            data_type: "varchar(100)"
          - name: amount
            data_type: "decimal(10,2)"
          - name: sale_date
            data_type: date
"""


def _build_jsonl_sources_yml(jsonl_url):
    return f"""
version: 2
sources:
  - name: test_external
    schema: dbo
    tables:
      - name: sample_jsonl
        external:
          location: "{jsonl_url}"
          file_format: jsonl
        columns:
          - name: id
            data_type: int
          - name: name
            data_type: "varchar(100)"
          - name: amount
            data_type: "decimal(10,2)"
          - name: sale_date
            data_type: date
"""


csv_model_sql = """
{{ config(materialized='table') }}
select id, name, amount, sale_date
from {{ source('test_external', 'sample_csv') }}
"""

csv_auto_model_sql = """
{{ config(materialized='table') }}
select id, name, amount, sale_date
from {{ source('test_external', 'sample_csv_auto') }}
"""

jsonl_model_sql = """
{{ config(materialized='table') }}
select id, name, amount, sale_date
from {{ source('test_external', 'sample_jsonl') }}
"""


class BaseExternalTableTest(BaseDbtPackageTests):
    @pytest.fixture(scope="class")
    def package_name(self) -> str:
        return "dbt_external_tables"

    @pytest.fixture(scope="class")
    def package_repo(self) -> str:
        return "https://github.com/dbt-labs/dbt-external-tables"

    @pytest.fixture(scope="class")
    def package_revision(self) -> str:
        return "0.11.0"

    @pytest.fixture(scope="class")
    def packages(self, package_repo: str, package_revision: str):
        return {
            "packages": [
                {"git": package_repo, "revision": package_revision},
            ]
        }

    def test_package(self, project, dbt_core_bug_workaround):
        run_dbt(["deps"])
        run_dbt(["run-operation", "stage_external_sources"])
        results = run_dbt(["run"])
        for r in results:
            assert r.status == "success"
        self.verify_data(project)

    def verify_data(self, project):
        raise NotImplementedError


class TestExternalTableCSV(BaseExternalTableTest):
    @pytest.fixture(scope="class")
    def models(self):
        urls = _skip_without_lakehouse()
        return {
            "sources.yml": _build_csv_sources_yml(urls["csv_url"]),
            "csv_data.sql": csv_model_sql,
            "csv_auto_data.sql": csv_auto_model_sql,
        }

    def verify_data(self, project):
        relation = relation_from_name(project.adapter, "csv_data")
        result = project.run_sql(f"select count(*) from {relation}", fetch="one")
        assert result[0] == 5

        result = project.run_sql(
            f"select id, name, amount from {relation} where id = 1", fetch="one"
        )
        assert result[0] == 1
        assert result[1] == "Widget A"
        assert float(result[2]) == pytest.approx(19.99)

        relation = relation_from_name(project.adapter, "csv_auto_data")
        result = project.run_sql(f"select count(*) from {relation}", fetch="one")
        assert result[0] == 5


class TestExternalTableJSONL(BaseExternalTableTest):
    @pytest.fixture(scope="class")
    def models(self):
        urls = _skip_without_lakehouse()
        return {
            "sources.yml": _build_jsonl_sources_yml(urls["jsonl_url"]),
            "jsonl_data.sql": jsonl_model_sql,
        }

    def verify_data(self, project):
        relation = relation_from_name(project.adapter, "jsonl_data")
        result = project.run_sql(f"select count(*) from {relation}", fetch="one")
        assert result[0] == 5

        result = project.run_sql(f"select id, name from {relation} where id = 1", fetch="one")
        assert result[0] == 1
        assert result[1] == "Widget A"
