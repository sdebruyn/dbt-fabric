from dbt.tests.adapter.empty.test_empty import (
    BaseTestEmpty,
    BaseTestEmptyInlineSourceRef,
    MetadataWithEmptyFlag,
)


class TestFabricSparkEmpty(BaseTestEmpty):
    pass


class TestFabricSparkEmptyInlineSourceRef(BaseTestEmptyInlineSourceRef):
    pass


class TestMetadataWithEmptyFlagFabricSpark(MetadataWithEmptyFlag):
    pass
