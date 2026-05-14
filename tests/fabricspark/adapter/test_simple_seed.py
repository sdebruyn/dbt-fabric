import inspect
from pathlib import Path

import pytest

from dbt.tests.adapter.simple_seed import fixtures, seeds
from dbt.tests.adapter.simple_seed.test_seed import (
    BaseBasicSeedTests,
    BaseSeedConfigFullRefreshOff,
    BaseSeedConfigFullRefreshOn,
    BaseSeedCustomSchema,
    BaseSeedParsing,
    BaseSeedSpecificFormats,
    BaseSeedWithEmptyDelimiter,
    BaseSeedWithUniqueDelimiter,
    BaseSeedWithWrongDelimiter,
    BaseSimpleSeedEnabledViaConfig,
    BaseSimpleSeedWithBOM,
    BaseTestEmptySeed,
)
from dbt.tests.adapter.simple_seed.test_seed_type_override import BaseSimpleSeedColumnOverride
from dbt.tests.util import copy_file, run_dbt

fixed_seeds__expected_sql = (
    seeds.seeds__expected_sql.replace("TIMESTAMP WITHOUT TIME ZONE", "TIMESTAMP")
    .replace("TEXT", "STRING")
    .replace("INTEGER", "INT")
    .replace('"', "")
)

fixed_properties__schema_yml = (
    fixtures.properties__schema_yml.replace("type: timestamp without time zone", "type: timestamp")
    .replace("type: text", "type: string")
    .replace("type: integer", "type: bigint")
)


def run_sql_statements(project, sql):
    for stmt in sql.split(";"):
        stmt = stmt.strip()
        if stmt:
            project.run_sql(stmt)


class FixedSeedSetup:
    @pytest.fixture(scope="class", autouse=True)
    def setUp(self, project):
        run_sql_statements(project, fixed_seeds__expected_sql)


class TestBasicSeedTestsFabricSpark(FixedSeedSetup, BaseBasicSeedTests):
    def test_simple_seed_full_refresh_flag(self, project):
        pytest.skip("Dropping a seed table does not cascade to materialized views in Fabric")


class TestEmptySeedFabricSpark(BaseTestEmptySeed):
    pass


class TestSeedConfigFullRefreshOffFabricSpark(FixedSeedSetup, BaseSeedConfigFullRefreshOff):
    pass


@pytest.mark.skip("Dropping a seed table does not cascade to materialized views in Fabric")
class TestSeedConfigFullRefreshOnFabricSpark(FixedSeedSetup, BaseSeedConfigFullRefreshOn):
    pass


class TestSeedCustomSchemaFabricSpark(FixedSeedSetup, BaseSeedCustomSchema):
    @pytest.mark.skip("TODO: FabricSpark cannot drop and recreate schemas during seed operations")
    def test_simple_seed_with_drop_and_schema(self, project, custom_schema):
        pass


@pytest.mark.skip("TODO: FabricSpark seed parsing test encounters runtime errors")
class TestSeedParsingFabricSpark(FixedSeedSetup, BaseSeedParsing):
    pass


@pytest.mark.skip("Spark SQL interprets dots in seed names as schema separators")
class TestSeedSpecificFormatsFabricSpark(BaseSeedSpecificFormats):
    pass


@pytest.mark.skip("TODO: FabricSpark seed with empty delimiter encounters runtime errors")
class TestSeedWithEmptyDelimiterFabricSpark(FixedSeedSetup, BaseSeedWithEmptyDelimiter):
    pass


class TestSeedWithUniqueDelimiterFabricSpark(FixedSeedSetup, BaseSeedWithUniqueDelimiter):
    pass


class TestSeedWithWrongDelimiterFabricSpark(FixedSeedSetup, BaseSeedWithWrongDelimiter):
    pass


class TestSimpleSeedColumnOverrideFabricSpark(BaseSimpleSeedColumnOverride):
    @pytest.fixture(scope="class")
    def models(self):
        return {
            "schema.yml": fixed_properties__schema_yml,
        }

    @staticmethod
    def seed_enabled_types():
        return {
            "seed_id": "string",
            "birthday": "date",
        }

    @staticmethod
    def seed_tricky_types():
        return {
            "seed_id_str": "string",
            "looks_like_a_bool": "string",
            "looks_like_a_date": "string",
        }


class BaseSimpleSeedEnabledViaConfigFabricSpark(BaseSimpleSeedEnabledViaConfig):
    @pytest.fixture(scope="function")
    def clear_test_schema(self):
        pass


class TestSimpleSeedEnabledViaConfigFabricSparkDisabled(
    BaseSimpleSeedEnabledViaConfigFabricSpark,
):
    @pytest.mark.skip("Tests have to be split up into multiple classes")
    def test_simple_seed_selection(self, clear_test_schema, project):
        super().test_simple_seed_selection(clear_test_schema, project)

    @pytest.mark.skip("Tests have to be split up into multiple classes")
    def test_simple_seed_exclude(self, clear_test_schema, project):
        super().test_simple_seed_exclude(clear_test_schema, project)


class TestSimpleSeedEnabledViaConfigFabricSparkSelection(
    BaseSimpleSeedEnabledViaConfigFabricSpark,
):
    @pytest.mark.skip("Tests have to be split up into multiple classes")
    def test_simple_seed_with_disabled(self, clear_test_schema, project):
        super().test_simple_seed_with_disabled(clear_test_schema, project)

    @pytest.mark.skip("Tests have to be split up into multiple classes")
    def test_simple_seed_exclude(self, clear_test_schema, project):
        super().test_simple_seed_exclude(clear_test_schema, project)


class TestSimpleSeedEnabledViaConfigFabricSparkExclude(
    BaseSimpleSeedEnabledViaConfigFabricSpark,
):
    @pytest.mark.skip("Tests have to be split up into multiple classes")
    def test_simple_seed_with_disabled(self, clear_test_schema, project):
        super().test_simple_seed_with_disabled(clear_test_schema, project)

    @pytest.mark.skip("Tests have to be split up into multiple classes")
    def test_simple_seed_selection(self, clear_test_schema, project):
        super().test_simple_seed_selection(clear_test_schema, project)


class TestSimpleSeedWithBOMFabricSpark(FixedSeedSetup, BaseSimpleSeedWithBOM):
    @pytest.fixture(scope="class", autouse=True)
    def setUp(self, project):
        run_sql_statements(project, fixed_seeds__expected_sql)
        copy_file(
            Path(inspect.getfile(BaseSimpleSeedWithBOM)).parent,
            "seed_bom.csv",
            project.project_root / Path("seeds") / "seed_bom.csv",
            "",
        )
