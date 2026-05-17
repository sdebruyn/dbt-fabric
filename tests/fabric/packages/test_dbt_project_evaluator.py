import re
from pathlib import Path

import pytest

from dbt.tests.util import run_dbt
from tests.fabric.packages.base_package_test import BaseDbtPackageTests

_TSQL_REPLACEMENTS = [
    ("where false", "where 1=0"),
    ("cast(True as ", "cast(1 as "),
    ("cast(False as ", "cast(0 as "),
    ("cast(True as boolean)", "cast(1 as BIT)"),
    ("as boolean)", "as BIT)"),
    (") as database,", ") as [database],"),
    (") as database\n", ") as [database]\n"),
    (") as schema,", ") as [schema],"),
    (") as schema\n", ") as [schema]\n"),
    ("coalesce(is_enabled, True) = True", "coalesce(is_enabled, cast(1 as bit)) = cast(1 as bit)"),
    ("unioned_with_calc.database,", "unioned_with_calc.[database],"),
    ("unioned_with_calc.schema,", "unioned_with_calc.[schema],"),
    ("not is_excluded", "is_excluded = 0"),
    ("not parent_is_excluded", "parent_is_excluded = 0"),
    ("not child_is_excluded", "child_is_excluded = 0"),
    (" || ", " + "),
    ("then true", "then 1"),
    ("else false", "else 0"),
    ("when database is NULL", "when [database] is NULL"),
    ('["database",', '["[database]",'),
    ('["schema",', '["[schema]",'),
    (', "schema",', ', "[schema]",'),
    (", FALSE)", ", cast(0 as bit))"),
]

_TSQL_REGEX_REPLACEMENTS = [
    (
        r"\}\}(\|\|'_')",
        r"}} + '_'",
    ),
    (
        r"regexp_replace\(file_path,'\.(.*)',''\)",
        r"right(file_path, charindex('/', reverse(file_path)) - 1)",
    ),
    (
        r"^(\s+)(.+?(?:\s+(?:like|and|or)\s+|[=<>!]).+?)\s+as\s+(is_\{\{[^}]+\}\}|is_test_\w+|is_public),\s*$",
        r"\1case when \2 then cast(1 as bit) else cast(0 as bit) end as \3,",
    ),
    (
        r"^(\s+)((?:\w+\.)?(?:is_\w+|has_\w+))\s+as\s+(is_\{\{[^}]+\}\}|is_test_\w+|is_public),\s*$",
        r"\1case when \2 = 1 then cast(1 as bit) else cast(0 as bit) end as \3,",
    ),
    (
        r"^(\s+(?:where|and|or|when)\s+)((?:\w+\.)?(?:is_\w+|has_\w+))\s*$",
        r"\1\2 = 1",
    ),
    (
        r"\(\s*\n\s+all_graph_resources\.resource_type = 'test'\s*\n\s+and models\.is_primary_relationship\s*\n\s+\) as is_primary_test_relationship",
        r"case when all_graph_resources.resource_type = 'test' and models.is_primary_relationship = 1 then cast(1 as bit) else cast(0 as bit) end as is_primary_test_relationship",
    ),
]

_DIRECTORY_PATTERN_OVERRIDE = """\
{% macro get_dbtreplace_directory_pattern() %}
  left(file_path, len(file_path) - charindex('/', reverse(file_path)))
{% endmacro %}
"""


def _patch_package_for_tsql(package_dir):
    package_dir = Path(str(package_dir))
    for sql_file in package_dir.rglob("*.sql"):
        text = sql_file.read_text()
        patched = text
        for old, new in _TSQL_REPLACEMENTS:
            patched = patched.replace(old, new)
        for pattern, replacement in _TSQL_REGEX_REPLACEMENTS:
            patched = re.sub(pattern, replacement, patched, flags=re.MULTILINE)
        if patched != text:
            sql_file.write_text(patched)

    directory_macro = package_dir / "macros" / "get_directory_pattern.sql"
    if directory_macro.exists():
        text = directory_macro.read_text()
        text = re.sub(
            r"\{%\s*macro get_dbtreplace_directory_pattern\(\)\s*%\}.*?\{%\s*endmacro\s*%\}",
            _DIRECTORY_PATTERN_OVERRIDE.strip(),
            text,
            flags=re.DOTALL,
        )
        directory_macro.write_text(text)


class TestDbtProjectEvaluator(BaseDbtPackageTests):
    @pytest.fixture(scope="class")
    def package_name(self) -> str:
        return "dbt_project_evaluator"

    @pytest.fixture(scope="class")
    def package_repo(self) -> str:
        return "https://github.com/dbt-labs/dbt-project-evaluator"

    @pytest.fixture(scope="class")
    def package_revision(self) -> str:
        return "v1.2.4"

    @pytest.fixture(scope="class")
    def packages(self, package_repo, package_revision, dbt_utils_version):
        return {
            "packages": [
                {"git": package_repo, "revision": package_revision},
                {"package": "dbt-labs/dbt_utils", "version": dbt_utils_version},
            ]
        }

    @pytest.fixture(scope="class")
    def seeds_config(self):
        col_type = "varchar(8000)"
        return {
            "dbt_project_evaluator": {
                "dbt_project_evaluator_exceptions": {
                    "+column_types": {
                        "fct_name": col_type,
                        "column_name": col_type,
                        "id_to_exclude": col_type,
                        "comment": col_type,
                    }
                }
            }
        }

    @pytest.fixture(scope="class")
    def project_vars(self):
        return {
            "max_depth_dag": 9,
        }

    def test_package(self, project, dbt_core_bug_workaround):
        run_dbt(["deps"])
        _patch_package_for_tsql(project.project_root / "dbt_packages" / "dbt_project_evaluator")
        run_dbt(["build"])
