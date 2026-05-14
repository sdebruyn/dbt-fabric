import pytest

from dbt.tests.adapter.utils.test_null_compare import BaseMixedNullCompare, BaseNullCompare


class TestMixedNullCompareFabricSpark(BaseMixedNullCompare):
    pass


@pytest.mark.skip("TODO: FabricSpark null_compare macro needs Spark-compatible implementation")
class TestNullCompareFabricSpark(BaseNullCompare):
    pass
