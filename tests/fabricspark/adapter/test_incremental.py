import pytest

from dbt.tests.adapter.incremental.test_incremental_merge_exclude_columns import (
    BaseMergeExcludeColumns,
)
from dbt.tests.adapter.incremental.test_incremental_microbatch import BaseMicrobatch
from dbt.tests.adapter.incremental.test_incremental_on_schema_change import (
    BaseIncrementalOnSchemaChange,
)
from dbt.tests.adapter.incremental.test_incremental_predicates import BaseIncrementalPredicates
from dbt.tests.adapter.incremental.test_incremental_unique_id import BaseIncrementalUniqueKey


class TestBaseIncrementalUniqueKeyFabricSpark(BaseIncrementalUniqueKey):
    pass


class TestIncrementalOnSchemaChangeFabricSpark(BaseIncrementalOnSchemaChange):
    @pytest.mark.skip(
        "TODO: DELTA_MERGE_UNRESOLVED_EXPRESSION when appending new columns after column removal"
    )
    def test_run_incremental_append_new_columns(self, project):
        pass

    @pytest.mark.skip("TODO: Apache Spark does not support dropping columns from Delta tables")
    def test_run_incremental_sync_all_columns(self, project):
        pass


@pytest.mark.skip("TODO: FabricSpark does not support delete+insert incremental strategy")
class TestIncrementalPredicatesDeleteInsertFabricSpark(BaseIncrementalPredicates):
    pass


@pytest.mark.skip("TODO: FabricSpark does not support delete+insert incremental strategy")
class TestPredicatesDeleteInsertFabricSpark(BaseIncrementalPredicates):
    pass


class TestMergeExcludeColumnsFabricSpark(BaseMergeExcludeColumns):
    pass


@pytest.mark.skip("TODO: FabricSpark microbatch insert_overwrite needs investigation")
class TestFabricSparkMicrobatch(BaseMicrobatch):
    pass
