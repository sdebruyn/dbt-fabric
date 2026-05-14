import pytest

from dbt.tests.adapter.persist_docs.test_persist_docs import (
    BasePersistDocs,
    BasePersistDocsColumnMissing,
    BasePersistDocsCommentOnQuotedColumn,
)


@pytest.mark.skip("TODO: FabricSpark does not support table/column comments via Spark SQL")
class TestPersistDocsFabricSpark(BasePersistDocs):
    pass


@pytest.mark.skip("TODO: FabricSpark does not support table/column comments via Spark SQL")
class TestPersistDocsColumnMissingFabricSpark(BasePersistDocsColumnMissing):
    pass


@pytest.mark.skip("TODO: FabricSpark does not support table/column comments via Spark SQL")
class TestPersistDocsCommentOnQuotedColumnFabricSpark(BasePersistDocsCommentOnQuotedColumn):
    pass
