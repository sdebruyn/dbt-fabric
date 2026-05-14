import json

import pytest

from dbt.tests.adapter.persist_docs import fixtures
from dbt.tests.adapter.persist_docs.test_persist_docs import (
    BasePersistDocs,
    BasePersistDocsColumnMissing,
    BasePersistDocsCommentOnQuotedColumn,
)
from dbt.tests.util import run_dbt

_MODELS__MATERIALIZED_VIEW = """\
{{ config(materialized='materialized_view') }}
select 2 as id, 'Bob' as name
"""


class TestPersistDocsFabricSpark(BasePersistDocs):
    @pytest.fixture(scope="class")
    def models(self):
        return {
            "no_docs_model.sql": fixtures._MODELS__NO_DOCS_MODEL,
            "table_model.sql": fixtures._MODELS__TABLE,
            "view_model.sql": _MODELS__MATERIALIZED_VIEW,
        }

    def test_has_comments_pglike(self, project):
        run_dbt(["docs", "generate"])
        with open("target/catalog.json") as fp:
            catalog_data = json.load(fp)
        assert "nodes" in catalog_data
        assert len(catalog_data["nodes"]) == 4
        table_node = catalog_data["nodes"]["model.test.table_model"]
        self._assert_has_table_comments(table_node)

        view_node = catalog_data["nodes"]["model.test.view_model"]
        self._assert_has_view_comments(view_node)

        no_docs_node = catalog_data["nodes"]["model.test.no_docs_model"]
        self._assert_has_view_comments(no_docs_node, False, False)


class TestPersistDocsColumnMissingFabricSpark(BasePersistDocsColumnMissing):
    pass


class TestPersistDocsCommentOnQuotedColumnFabricSpark(BasePersistDocsCommentOnQuotedColumn):
    pass
