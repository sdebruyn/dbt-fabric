import pytest

from dbt.tests.adapter.utils.test_escape_single_quotes import BaseEscapeSingleQuotesQuote


@pytest.mark.skip(
    "TODO: FabricSpark escape_single_quotes macro needs Spark-compatible implementation"
)
class TestEscapeSingleQuotesQuoteFabricSpark(BaseEscapeSingleQuotesQuote):
    pass
