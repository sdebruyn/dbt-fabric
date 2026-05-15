import pytest

from dbt.tests.adapter.persist_docs import fixtures
from dbt.tests.adapter.persist_docs.test_persist_docs import (
    BasePersistDocs,
    BasePersistDocsColumnMissing,
    BasePersistDocsCommentOnQuotedColumn,
)


class TestPersistDocsFabricSpark(BasePersistDocs):
    @pytest.fixture(scope="class")
    def models(self):
        return {
            "no_docs_model.sql": fixtures._MODELS__NO_DOCS_MODEL,
            "table_model.sql": fixtures._MODELS__TABLE,
            "view_model.sql": """
{{ config(materialized='materialized_view') }}
select 2 as id, 'Bob' as name
""",
        }


class TestPersistDocsColumnMissingFabricSpark(BasePersistDocsColumnMissing):
    pass


class TestPersistDocsCommentOnQuotedColumnFabricSpark(BasePersistDocsCommentOnQuotedColumn):
    pass
