import pytest

from dbt.adapters.exceptions.compilation import ApproximateMatchError
from dbt.adapters.fabricspark.fabricspark_relation import (
    FabricSparkIncludePolicy,
    FabricSparkQuotePolicy,
    FabricSparkRelation,
    FabricSparkRelationType,
)


class TestFabricSparkQuotePolicy:
    def test_database_and_schema_quoting_enabled(self):
        policy = FabricSparkQuotePolicy()
        assert policy.database is True
        assert policy.schema is True
        assert policy.identifier is False

    def test_relation_default_quote_policy(self):
        r = FabricSparkRelation.create(
            database="DBTTest",
            schema="TestSchema",
            identifier="my_model",
            type=FabricSparkRelationType.Table,
        )
        assert r.quote_policy.database is True
        assert r.quote_policy.schema is True


class TestFabricSparkIncludePolicy:
    def test_database_included(self):
        policy = FabricSparkIncludePolicy()
        assert policy.database is True
        assert policy.schema is True
        assert policy.identifier is True

    def test_relation_default_include_policy(self):
        r = FabricSparkRelation.create(
            database="my_lakehouse",
            schema="dbo",
            identifier="my_model",
            type=FabricSparkRelationType.Table,
        )
        assert r.include_policy.database is True


class TestFabricSparkRelationRendering:
    def test_renders_three_part_name(self):
        r = FabricSparkRelation.create(
            database="my_lakehouse",
            schema="dbo",
            identifier="my_model",
            type=FabricSparkRelationType.Table,
        )
        rendered = str(r)
        assert rendered == "`my_lakehouse`.`dbo`.my_model"

    def test_mixed_case_preserved_in_rendering(self):
        r = FabricSparkRelation.create(
            database="DBTTest",
            schema="TestSchema",
            identifier="my_model",
            type=FabricSparkRelationType.Table,
        )
        rendered = str(r)
        assert "`DBTTest`" in rendered
        assert "`TestSchema`" in rendered

    def test_identifier_not_quoted_by_default(self):
        r = FabricSparkRelation.create(
            database="DBTTest",
            schema="TestSchema",
            identifier="my_model",
            type=FabricSparkRelationType.Table,
        )
        rendered = str(r)
        assert "my_model" in rendered
        assert "`my_model`" not in rendered

    def test_without_identifier_renders_database_and_schema(self):
        r = FabricSparkRelation.create(
            database="my_lakehouse",
            schema="dbo",
            identifier="my_model",
            type=FabricSparkRelationType.Table,
        )
        without_id = r.without_identifier()
        rendered = str(without_id)
        assert "`my_lakehouse`" in rendered
        assert "`dbo`" in rendered
        assert "my_model" not in rendered


class TestFabricSparkRelationCasePreservation:
    def test_matches_preserves_case_when_quoted(self):
        r = FabricSparkRelation.create(
            database="DBTTest",
            schema="TestSchema",
            identifier="my_model",
            type=FabricSparkRelationType.Table,
        )
        assert r.matches(
            database="DBTTest",
            schema="TestSchema",
            identifier="my_model",
        )

    def test_lowered_search_raises_approximate_match_error(self):
        """With quote_policy.database/schema=True, matches() uses exact
        case-sensitive comparison. Lowercased search terms will not
        exact-match mixed-case stored values but will approximate-match,
        raising ApproximateMatchError instead of silently returning True."""
        r = FabricSparkRelation.create(
            database="DBTTest",
            schema="TestSchema",
            identifier="my_model",
            type=FabricSparkRelationType.Table,
            dbt_created=True,
        )
        with pytest.raises(ApproximateMatchError):
            r.matches(
                database="dbttest",
                schema="testschema",
                identifier="my_model",
            )
