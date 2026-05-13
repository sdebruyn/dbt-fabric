import pytest

from dbt.tests.adapter.aliases import fixtures
from dbt.tests.adapter.aliases.test_aliases import (
    BaseAliasErrors,
    BaseAliases,
    BaseSameAliasDifferentDatabases,
    BaseSameAliasDifferentSchemas,
)

# Spark SQL does not support PostgreSQL-style '...'::text casts.
# Override the default__string_literal macro to simply return a string literal.
MACROS__CAST_SQL_SPARK = """
{% macro string_literal(s) -%}
  {{ adapter.dispatch('string_literal', macro_namespace='test')(s) }}
{%- endmacro %}

{% macro default__string_literal(s) %}
    '{{ s }}'
{% endmacro %}
"""


class TestAliasesFabricSpark(BaseAliases):
    @pytest.fixture(scope="class")
    def macros(self):
        return {
            "cast.sql": MACROS__CAST_SQL_SPARK,
            "expect_value.sql": fixtures.MACROS__EXPECT_VALUE_SQL,
        }


class TestAliasErrorsFabricSpark(BaseAliasErrors):
    @pytest.fixture(scope="class")
    def macros(self):
        return {
            "cast.sql": MACROS__CAST_SQL_SPARK,
            "expect_value.sql": fixtures.MACROS__EXPECT_VALUE_SQL,
        }


class TestSameAliasDifferentSchemasFabricSpark(BaseSameAliasDifferentSchemas):
    @pytest.fixture(scope="class")
    def macros(self):
        return {
            "cast.sql": MACROS__CAST_SQL_SPARK,
            "expect_value.sql": fixtures.MACROS__EXPECT_VALUE_SQL,
        }


class TestSameAliasDifferentDatabasesFabricSpark(BaseSameAliasDifferentDatabases):
    @pytest.fixture(scope="class")
    def macros(self):
        return {
            "cast.sql": MACROS__CAST_SQL_SPARK,
            "expect_value.sql": fixtures.MACROS__EXPECT_VALUE_SQL,
        }
