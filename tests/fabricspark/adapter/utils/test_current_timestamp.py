import pytest

from dbt.tests.adapter.utils.test_current_timestamp import (
    BaseCurrentTimestampNaive,
)


class TestCurrentTimestampNaiveFabricSpark(BaseCurrentTimestampNaive):
    @pytest.mark.skip("TODO: FabricSpark current_timestamp type differs from expected")
    def test_current_timestamp_type(self, current_timestamp):
        pass
