import pytest
from jinja2 import Environment

MACRO_TEMPLATE = """\
{%- macro fabric__get_use_database_sql(database) -%}
  {%- if database is not none -%}
    USE [{{database | replace('"', '') | replace('[', '') | replace(']', '')}}];
  {%- endif -%}
{%- endmacro -%}
{{ fabric__get_use_database_sql(test_database) }}"""


@pytest.fixture
def jinja_env():
    return Environment()


def _render(jinja_env, database):
    template = jinja_env.from_string(MACRO_TEMPLATE)
    return template.render(test_database=database).strip()


def test_plain_database_name(jinja_env):
    assert _render(jinja_env, "my_database") == "USE [my_database];"


def test_double_quoted_database_name(jinja_env):
    assert _render(jinja_env, '"my_database"') == "USE [my_database];"


def test_bracket_quoted_database_name(jinja_env):
    assert _render(jinja_env, "[my_database]") == "USE [my_database];"


def test_bracket_and_double_quoted_database_name(jinja_env):
    assert _render(jinja_env, '"[my_database]"') == "USE [my_database];"


def test_none_database_returns_empty(jinja_env):
    assert _render(jinja_env, None) == ""


def test_database_with_spaces(jinja_env):
    assert _render(jinja_env, "my database") == "USE [my database];"


def test_database_with_brackets_and_spaces(jinja_env):
    assert _render(jinja_env, "[my database]") == "USE [my database];"
