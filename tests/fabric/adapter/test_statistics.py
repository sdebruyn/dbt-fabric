import pytest

from dbt.tests.util import run_dbt, run_sql_with_adapter

model_stats_specific = """
{{ config(materialized='table', statistics=['id', 'color']) }}
select 1 as id, 'blue' as color, cast('2024-01-01' as date) as date_day
"""

model_stats_all = """
{{ config(materialized='table', statistics=true) }}
select 1 as id, 'blue' as color
"""

model_stats_none = """
{{ config(materialized='table') }}
select 1 as id, 'blue' as color
"""

model_stats_sample = """
{{ config(materialized='table', statistics=['id'], statistics_sample_percent=50) }}
select 1 as id, 'blue' as color
"""

model_stats_single_string = """
{{ config(materialized='table', statistics='id') }}
select 1 as id, 'blue' as color
"""

model_stats_incremental = """
{{ config(materialized='incremental', statistics=['id', 'color'], unique_key='id') }}
select 1 as id, 'blue' as color
"""

seed_snapshot_source_csv = """id,name,updated_at
1,Alice,2024-01-01 00:00:00
2,Bob,2024-01-01 00:00:00
""".lstrip()

snapshot_with_stats_yml = """
snapshots:
  - name: snapshot_with_stats
    relation: "ref('snapshot_source')"
    config:
      strategy: timestamp
      unique_key: id
      updated_at: updated_at
      statistics:
        - id
        - name
"""


def _get_stats_names(project, adapter, table_name):
    schema = project.test_schema
    sql = f"""
        SELECT s.name
        FROM sys.stats s
        WHERE s.object_id = OBJECT_ID(N'{schema}.{table_name}')
          AND s.name LIKE 'stats\\_\\_%' ESCAPE '\\'
        ORDER BY s.name
    """
    result = run_sql_with_adapter(adapter, sql, fetch="all")
    return [row[0] for row in result]


class TestStatisticsSpecificColumns:
    @pytest.fixture(scope="class")
    def models(self):
        return {"model_stats.sql": model_stats_specific}

    def test_statistics_specific_columns(self, project, adapter):
        results = run_dbt(["run"])
        assert len(results) == 1
        assert results[0].status == "success"

        stats = _get_stats_names(project, adapter, "model_stats")
        assert "stats__model_stats__id" in stats
        assert "stats__model_stats__color" in stats
        assert len(stats) == 2


class TestStatisticsAllColumns:
    @pytest.fixture(scope="class")
    def models(self):
        return {"model_stats_all.sql": model_stats_all}

    def test_statistics_all_columns(self, project, adapter):
        results = run_dbt(["run"])
        assert len(results) == 1
        assert results[0].status == "success"

        stats = _get_stats_names(project, adapter, "model_stats_all")
        assert "stats__model_stats_all__id" in stats
        assert "stats__model_stats_all__color" in stats
        assert len(stats) == 2


class TestStatisticsNone:
    @pytest.fixture(scope="class")
    def models(self):
        return {"model_no_stats.sql": model_stats_none}

    def test_no_statistics(self, project, adapter):
        results = run_dbt(["run"])
        assert len(results) == 1
        assert results[0].status == "success"

        stats = _get_stats_names(project, adapter, "model_no_stats")
        assert len(stats) == 0


class TestStatisticsSamplePercent:
    @pytest.fixture(scope="class")
    def models(self):
        return {"model_stats_sample.sql": model_stats_sample}

    def test_statistics_sample_percent(self, project, adapter):
        results = run_dbt(["run"])
        assert len(results) == 1
        assert results[0].status == "success"

        stats = _get_stats_names(project, adapter, "model_stats_sample")
        assert "stats__model_stats_sample__id" in stats
        assert len(stats) == 1


class TestStatisticsSingleString:
    @pytest.fixture(scope="class")
    def models(self):
        return {"model_stats_str.sql": model_stats_single_string}

    def test_statistics_single_string(self, project, adapter):
        results = run_dbt(["run"])
        assert len(results) == 1
        assert results[0].status == "success"

        stats = _get_stats_names(project, adapter, "model_stats_str")
        assert "stats__model_stats_str__id" in stats
        assert len(stats) == 1


class TestStatisticsIncremental:
    @pytest.fixture(scope="class")
    def models(self):
        return {"model_stats_incr.sql": model_stats_incremental}

    def test_statistics_incremental(self, project, adapter):
        results = run_dbt(["run"])
        assert len(results) == 1
        assert results[0].status == "success"

        stats = _get_stats_names(project, adapter, "model_stats_incr")
        assert "stats__model_stats_incr__id" in stats
        assert "stats__model_stats_incr__color" in stats

        results = run_dbt(["run"])
        assert len(results) == 1
        assert results[0].status == "success"

        stats = _get_stats_names(project, adapter, "model_stats_incr")
        assert "stats__model_stats_incr__id" in stats
        assert "stats__model_stats_incr__color" in stats


class TestStatisticsSnapshot:
    @pytest.fixture(scope="class")
    def seeds(self):
        return {"snapshot_source.csv": seed_snapshot_source_csv}

    @pytest.fixture(scope="class")
    def snapshots(self):
        return {"snapshot_with_stats.yml": snapshot_with_stats_yml}

    def test_statistics_snapshot(self, project, adapter):
        run_dbt(["seed"])
        results = run_dbt(["snapshot"])
        assert len(results) == 1
        assert results[0].status == "success"

        stats = _get_stats_names(project, adapter, "snapshot_with_stats")
        assert "stats__snapshot_with_stats__id" in stats
        assert "stats__snapshot_with_stats__name" in stats
        assert len(stats) == 2
