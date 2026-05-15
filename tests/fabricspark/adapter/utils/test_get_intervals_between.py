import pytest

from dbt.tests.adapter.utils.test_get_intervals_between import BaseGetIntervalsBetween


@pytest.mark.skip(
    "TODO: FabricSpark get_intervals_between macro needs Spark-compatible implementation"
)
class TestGetIntervalsBetweenFabricSpark(BaseGetIntervalsBetween):
    pass
