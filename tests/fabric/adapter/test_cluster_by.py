import pytest

from dbt.tests.util import run_dbt

model_single_cluster = """
{{ config(materialized='table', cluster_by='id') }}
select 1 as id, 'blue' as color
"""

model_multi_cluster = """
{{ config(materialized='table', cluster_by=['id', 'color']) }}
select 1 as id, 'blue' as color, cast('2024-01-01' as date) as date_day
"""

model_no_cluster = """
{{ config(materialized='table') }}
select 1 as id, 'blue' as color
"""

model_cluster_contract = """
{{ config(materialized='table', cluster_by=['id', 'color']) }}
select 1 as id, cast('blue' as varchar(100)) as color
"""

model_cluster_contract_schema = """
version: 2
models:
  - name: model_cluster_contract
    config:
      contract:
        enforced: true
    columns:
      - name: id
        data_type: int
      - name: color
        data_type: varchar(100)
"""

model_cluster_incremental = """
{{ config(materialized='incremental', cluster_by=['id'], unique_key='id') }}
select 1 as id, 'blue' as color
"""


class TestClusterBySingleColumn:
    @pytest.fixture(scope="class")
    def models(self):
        return {"model_single.sql": model_single_cluster}

    def test_cluster_by_single(self, project):
        results = run_dbt(["run"])
        assert len(results) == 1
        assert results[0].status == "success"


class TestClusterByMultipleColumns:
    @pytest.fixture(scope="class")
    def models(self):
        return {"model_multi.sql": model_multi_cluster}

    def test_cluster_by_multi(self, project):
        results = run_dbt(["run"])
        assert len(results) == 1
        assert results[0].status == "success"


class TestClusterByNoCluster:
    @pytest.fixture(scope="class")
    def models(self):
        return {"model_no_cluster.sql": model_no_cluster}

    def test_no_cluster_by(self, project):
        results = run_dbt(["run"])
        assert len(results) == 1
        assert results[0].status == "success"


class TestClusterByWithContract:
    @pytest.fixture(scope="class")
    def models(self):
        return {
            "model_cluster_contract.sql": model_cluster_contract,
            "schema.yml": model_cluster_contract_schema,
        }

    def test_cluster_by_with_contract(self, project):
        results = run_dbt(["run"])
        assert len(results) == 1
        assert results[0].status == "success"


class TestClusterByIncremental:
    @pytest.fixture(scope="class")
    def models(self):
        return {"model_cluster_incr.sql": model_cluster_incremental}

    def test_cluster_by_incremental(self, project):
        results = run_dbt(["run"])
        assert len(results) == 1
        assert results[0].status == "success"

        results = run_dbt(["run"])
        assert len(results) == 1
        assert results[0].status == "success"
