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
    (" || ", " + "),
    ("then true", "then 1"),
    ("else false", "else 0"),
    ("when database is NULL", "when [database] is NULL"),
    ('["database",', '["[database]",'),
    ('["schema",', '["[schema]",'),
    (', "schema",', ', "[schema]",'),
    (", FALSE)", ", cast(0 as bit))"),
    (
        "if target.type in ['snowflake','redshift','duckdb','trino']",
        "if target.type in ['snowflake','redshift','duckdb','trino','fabric']",
    ),
    (
        "where model_and_source_joined.keep_row",
        "where model_and_source_joined.keep_row = 1",
    ),
    (
        "is_{{ test.split('.')[1] }} {%- if not loop.last %}",
        "is_{{ test.split('.')[1] }} = 1 {%- if not loop.last %}",
    ),
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
        r"(?<!if )(?<!elif )\bnot\s*\(((?:\w+\.)?(?:\w+_)?(?:is_\w+|has_\w+))\)",
        r"\1 = 0",
    ),
    (
        r"(?<!if )(?<!elif )\bnot\s+((?:\w+\.)?(?:\w+_)?(?:is_\w+|has_\w+))\b",
        r"\1 = 0",
    ),
    (
        r"\(\s*\n(\s+)all_graph_resources\.resource_type = 'test'\s*\n\s+and models\.is_primary_relationship\s*\n\s+\) as is_primary_test_relationship",
        r"case when all_graph_resources.resource_type = 'test' and models.is_primary_relationship = 1 then cast(1 as bit) else cast(0 as bit) end as is_primary_test_relationship",
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
        r"\b(where|and|or|when)\s+((?:\w+\.)?(?:\w+_)?(?:is_\w+|has_\w+))\s+(and|or)\b",
        r"\1 \2 = 1 \3",
    ),
    (
        r"\b(when|and|or)\s+((?:\w+\.)?(?:\w+_)?(?:is_\w+|has_\w+))\s+(then)\b",
        r"\1 \2 = 1 \3",
    ),
    (
        r"^(\s+(?:where|and|or|when)\s+)((?:\w+\.)?(?:\w+_)?(?:is_\w+|has_\w+))\s*$",
        r"\1\2 = 1",
    ),
    (
        r"cast\((sum\(case[\s\S]*?end\s*\))\s*>=\s*1\s+as\s+\{\{\s*dbt\.type_boolean\(\)\s*\}\}\)",
        r"case when \1 >= 1 then cast(1 as {{ dbt.type_boolean() }}) else cast(0 as {{ dbt.type_boolean() }}) end",
    ),
    (
        r"^\s*order by .+$\n?",
        r"",
    ),
]

_DIRECTORY_PATTERN_OVERRIDE = """\
{% macro get_dbtreplace_directory_pattern() %}
  left(file_path, len(file_path) - charindex('/', reverse(file_path)))
{% endmacro %}
"""


def _resolve_group_by_ordinals(text):
    """Replace GROUP BY ordinal positions with actual column names from the SELECT."""
    lines = text.split("\n")
    result = []
    for i, line in enumerate(lines):
        match = re.match(r"^(\s+)group by\s+(.+)$", line)
        if not match or not re.fullmatch(r"[\d,\s]+", match.group(2)):
            result.append(line)
            continue
        indent = match.group(1)
        ordinals = [int(x.strip()) for x in match.group(2).split(",")]
        from_line = None
        select_line = None
        for j in range(i - 1, -1, -1):
            stripped = lines[j].strip().lower()
            if from_line is None and (stripped.startswith("from ") or stripped.startswith("from\t")):
                from_line = j
            elif from_line is not None and stripped.startswith("select"):
                select_line = j
                break
        if select_line is None or from_line is None:
            result.append(line)
            continue
        select_columns = []
        for j in range(select_line + 1, from_line):
            col_line = lines[j].strip().rstrip(",")
            if not col_line or col_line.startswith("--") or col_line.startswith("{%"):
                continue
            if " as " in col_line:
                select_columns.append(col_line.rsplit(" as ", 1)[0].strip())
            else:
                select_columns.append(col_line.strip())
        col_names = []
        for ordinal in ordinals:
            if 1 <= ordinal <= len(select_columns):
                col_names.append(select_columns[ordinal - 1])
            else:
                col_names.append(str(ordinal))
        result.append(f"{indent}group by {', '.join(col_names)}")
    return "\n".join(result)


def _patch_package_for_tsql(package_dir):
    package_dir = Path(str(package_dir))
    for sql_file in package_dir.rglob("*.sql"):
        text = sql_file.read_text()
        patched = text
        for old, new in _TSQL_REPLACEMENTS:
            patched = patched.replace(old, new)
        for pattern, replacement in _TSQL_REGEX_REPLACEMENTS:
            patched = re.sub(pattern, replacement, patched, flags=re.MULTILINE)
        patched = _resolve_group_by_ordinals(patched)
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

    dbt_project_yml = package_dir / "dbt_project.yml"
    if dbt_project_yml.exists():
        text = dbt_project_yml.read_text()
        text = text.replace(
            "if target.type in ['duckdb']",
            "if target.type in ['duckdb','fabric']",
        )
        dbt_project_yml.write_text(text)


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
