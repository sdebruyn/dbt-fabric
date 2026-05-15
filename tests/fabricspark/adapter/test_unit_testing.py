import pytest

from dbt.tests.adapter.unit_testing.test_case_insensitivity import BaseUnitTestCaseInsensivity
from dbt.tests.adapter.unit_testing.test_invalid_input import BaseUnitTestInvalidInput
from dbt.tests.adapter.unit_testing.test_quoted_reserved_word_column_names import (
    BaseUnitTestQuotedReservedWordColumnNames,
)
from dbt.tests.adapter.unit_testing.test_types import BaseUnitTestingTypes


@pytest.mark.skip("TODO: FabricSpark unit test data type handling differs from standard adapters")
class TestFabricSparkUnitTestingTypes(BaseUnitTestingTypes):
    pass


class TestFabricSparkUnitTestCaseInsensivity(BaseUnitTestCaseInsensivity):
    pass


class TestFabricSparkUnitTestInvalidInput(BaseUnitTestInvalidInput):
    pass


@pytest.mark.skip(
    "TODO: FabricSpark quoted reserved word column names need Spark SQL compatible quoting"
)
class TestFabricSparkUnitTestQuotedReservedWordColumnNames(
    BaseUnitTestQuotedReservedWordColumnNames,
):
    pass
