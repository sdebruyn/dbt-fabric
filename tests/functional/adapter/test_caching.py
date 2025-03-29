import os

import pytest

from dbt.tests.adapter.caching.test_caching import (
    BaseCachingLowercaseModel,
    BaseCachingSelectedSchemaOnly,
    BaseCachingUppercaseModel,
    BaseNoPopulateCache,
)


class TestCachingLowerCaseModel(BaseCachingLowercaseModel):
    pass


class TestCachingUppercaseModel(BaseCachingUppercaseModel):
    @pytest.fixture(scope="class")
    def dbt_profile_target_update(self):
        dwh_name = os.getenv("FABRIC_TEST_DWH_CI_NAME")

        if dwh_name is None:
            pytest.skip("FABRIC_TEST_DWH_CI_NAME not set")

        return {
            "database": dwh_name,
        }


class TestCachingSelectedSchemaOnly(BaseCachingSelectedSchemaOnly):
    pass


class TestNoPopulateCache(BaseNoPopulateCache):
    pass
