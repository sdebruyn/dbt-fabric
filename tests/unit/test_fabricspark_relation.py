from dbt.adapters.fabricspark.fabricspark_relation import (
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


class TestFabricSparkRelationRendering:
    def test_mixed_case_schema_backtick_quoted(self):
        r = FabricSparkRelation.create(
            database="DBTTest",
            schema="TestSchema",
            identifier="my_model",
            type=FabricSparkRelationType.Table,
        )
        rendered = str(r)
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

    def test_no_approximate_match_error_on_mixed_case(self):
        """When quote_policy.database/schema=True, matches() does exact
        case-sensitive comparison. This prevents ApproximateMatchError
        that would occur if the search terms were lowercased by
        _make_match_kwargs but the stored values kept original case."""
        r = FabricSparkRelation.create(
            database="DBTTest",
            schema="TestSchema",
            identifier="my_model",
            type=FabricSparkRelationType.Table,
            dbt_created=True,
        )
        assert r.matches(
            database="DBTTest",
            schema="TestSchema",
            identifier="my_model",
        )
