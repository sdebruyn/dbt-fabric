import pytest

from dbt.tests.util import run_dbt
from tests.fabric.packages.base_package_test import BaseDbtPackageTests


class TestDbtCodegen(BaseDbtPackageTests):
    @pytest.fixture(scope="class")
    def package_name(self) -> str:
        return "codegen"

    @pytest.fixture(scope="class")
    def package_repo(self) -> str:
        return "https://github.com/dbt-labs/dbt-codegen"

    @pytest.fixture(scope="class")
    def package_revision(self) -> str:
        return "0.14.1"

    @pytest.fixture(scope="class")
    def packages(self, package_repo, package_revision, dbt_utils_version):
        return {
            "packages": [
                {"git": package_repo, "revision": package_revision},
                {"package": "dbt-labs/dbt_utils", "version": dbt_utils_version},
            ]
        }

    @pytest.fixture(scope="class")
    def models(self):
        return {
            "model_data_a.sql": "select * from {{ ref('data__a_relation') }}",
            "child_model.sql": "select * from {{ ref('model_data_a') }}",
            "schema.yml": _SCHEMA_YML,
            "source.yml": _SOURCE_YML,
        }

    @pytest.fixture(scope="class")
    def seeds(self):
        return {
            "data__a_relation.csv": "col_a,col_b\n1,a\n2,b\n",
            "data__b_relation.csv": "col_a,col_b\n3,c\n4,d\n",
        }

    @pytest.fixture(scope="class")
    def seeds_config(self):
        return {"+schema": "raw_data"}

    @pytest.fixture(scope="class")
    def tests(self):
        return {
            "test_generate_source.sql": _TEST_GENERATE_SOURCE,
            "test_generate_source_some_tables.sql": _TEST_GENERATE_SOURCE_SOME_TABLES,
            "test_generate_model_yaml.sql": _TEST_GENERATE_MODEL_YAML,
            "test_generate_base_model.sql": _TEST_GENERATE_BASE_MODEL,
            "test_generate_model_import_ctes.sql": _TEST_GENERATE_MODEL_IMPORT_CTES,
            "test_generate_unit_test_template.sql": _TEST_GENERATE_UNIT_TEST_TEMPLATE,
        }

    @pytest.fixture(scope="class")
    def macros(self):
        return {
            "create_source_table.sql": _CREATE_SOURCE_TABLE_SQL,
            "assert_equal.sql": _ASSERT_EQUAL_SQL,
        }

    def test_package(self, project, dbt_core_bug_workaround):
        run_dbt(["deps"])
        run_dbt(["seed"])
        run_dbt(["run-operation", "create_source_table"])
        run_dbt(["run"])
        run_dbt(["test"])


_SCHEMA_YML = """
version: 2

models:
  - name: model_data_a
    columns:
      - name: col_a
        description: 'description column "a"'
""".strip()

_SOURCE_YML = """
version: 2

sources:
  - name: codegen_test_source
    schema: "{{ target.schema ~ '__data_source_schema' }}"
    tables:
      - name: codegen_integration_tests__data_source_table
        columns:
          - name: my_integer_col
            description: My Integer Column
          - name: my_bool_col
            description: My Boolean Column
""".strip()

_TEST_GENERATE_SOURCE = """
{% set raw_schema = generate_schema_name('raw_data') %}

{% set actual_source_yaml = codegen.generate_source(raw_schema) %}

{% set expected_source_yaml %}
version: 2

sources:
  - name: {{ raw_schema | trim | lower }}
    tables:
      - name: data__a_relation
      - name: data__b_relation
{% endset %}

{{ assert_equal (actual_source_yaml | trim, expected_source_yaml | trim) }}
""".strip()

_TEST_GENERATE_SOURCE_SOME_TABLES = """
{% set raw_schema = generate_schema_name('raw_data') %}

{% set actual_source_yaml = codegen.generate_source(
    schema_name=raw_schema,
    database_name=target.database,
    table_names=['data__a_relation'],
    generate_columns=True,
    include_descriptions=True,
    include_data_types=False
) %}

{% set expected_source_yaml %}
version: 2

sources:
  - name: {{ raw_schema | trim | lower }}
    description: ""
    tables:
      - name: data__a_relation
        description: ""
        columns:
          - name: col_a
            description: ""
          - name: col_b
            description: ""

{% endset %}

{{ assert_equal (actual_source_yaml | trim, expected_source_yaml | trim) }}
""".strip()

_TEST_GENERATE_MODEL_YAML = """
{% set actual_model_yaml = codegen.generate_model_yaml(
    model_names=['data__a_relation']
  )
%}

{% set expected_model_yaml %}
version: 2

models:
  - name: data__a_relation
    description: ""
    columns:
      - name: col_a
        data_type: int
        description: ""

      - name: col_b
        data_type: varchar
        description: ""

{% endset %}

{{ assert_equal (actual_model_yaml | trim, expected_model_yaml | trim) }}
""".strip()

_TEST_GENERATE_BASE_MODEL = """
{% set actual_base_model = codegen.generate_base_model(
    source_name='codegen_test_source',
    table_name='codegen_integration_tests__data_source_table'
  )
%}

{% set expected_base_model %}

with source as (

    select * from {{ "{{" }} source('codegen_test_source', 'codegen_integration_tests__data_source_table') {{ "}}" }}

),

renamed as (

    select
        my_integer_col,
        my_bool_col

    from source

)

select * from renamed
{% endset %}

{{ assert_equal (actual_base_model | trim, expected_base_model | trim) }}
""".strip()

_TEST_GENERATE_MODEL_IMPORT_CTES = """
-- depends_on: {{ ref('model_data_a') }}
-- depends_on: {{ ref('child_model') }}

{% set actual_model_yaml = codegen.generate_model_import_ctes(
    model_name='child_model'
  )
%}

{% set expected_model_yaml %}
with model_data_a as (

    select * from {{ "{{" }} ref('model_data_a') {{ "}}" }}

)

select * from model_data_a
{% endset %}

{{ assert_equal (actual_model_yaml | trim, expected_model_yaml | trim) }}
""".strip()

_TEST_GENERATE_UNIT_TEST_TEMPLATE = """
-- depends_on: {{ ref('model_data_a') }}
-- depends_on: {{ ref('child_model') }}

{% set actual_model_yaml = codegen.generate_unit_test_template(
    model_name='child_model',
    inline_columns=False
  )
%}

{% set expected_model_yaml %}
unit_tests:
  - name: unit_test_child_model
    model: child_model

    given:
      - input: ref("model_data_a")
        rows:
          - col_a:\x20
            col_b:\x20

    expect:
      rows:
        - col_a:\x20
          col_b:\x20

{% endset %}

{{ assert_equal (actual_model_yaml | trim, expected_model_yaml | trim) }}
""".strip()

_CREATE_SOURCE_TABLE_SQL = """
{% macro create_source_table() %}

{% set target_schema=api.Relation.create(
    database=target.database,
    schema=target.schema ~ "__data_source_schema"
) %}

{% do adapter.create_schema(target_schema) %}

{% set drop_table_sql %}
drop table if exists {{ target_schema }}.codegen_integration_tests__data_source_table
{% endset %}

{{ run_query(drop_table_sql) }}

{% set create_table_sql %}
create table {{ target_schema }}.codegen_integration_tests__data_source_table
as select
    1 as my_integer_col,
    cast(1 as bit) as my_bool_col
{% endset %}

{{ run_query(create_table_sql) }}

{% endmacro %}
""".strip()

_ASSERT_EQUAL_SQL = """
{% macro _strip_trailing_ws(text) %}
    {% set lines = text.split('\\n') %}
    {% set stripped = [] %}
    {% for line in lines %}
        {% do stripped.append(line.rstrip()) %}
    {% endfor %}
    {{ return(stripped | join('\\n')) }}
{% endmacro %}

{% macro assert_equal(actual_object, expected_object) %}
{% set actual_clean = _strip_trailing_ws(actual_object | string) %}
{% set expected_clean = _strip_trailing_ws(expected_object | string) %}
{% if not execute %}

    {# pass #}

{% elif actual_clean != expected_clean %}

    {% set msg %}
    Expected did not match actual

    -----------
    Actual:
    -----------
    --->{{ actual_clean }}<---

    -----------
    Expected:
    -----------
    --->{{ expected_clean }}<---

    {% endset %}

    {{ log(msg, info=True) }}

    select 'fail' as result

{% else %}

    select top 0 'ok' as result

{% endif %}
{% endmacro %}
""".strip()
