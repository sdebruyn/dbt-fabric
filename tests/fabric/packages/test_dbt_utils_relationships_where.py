import pytest

from dbt.tests.util import run_dbt

_PACKAGES_YML = """
packages:
  - package: dbt-labs/dbt_utils
    version: 1.3.3
""".strip()


_PARENT_CSV = """id
1
2
3
""".strip()


_CHILD_PASS_CSV = """id,parent_id
10,1
11,2
12,3
""".strip()


_CHILD_PASS_FILTERED_CSV = """id,parent_id
20,1
21,2
22,99
""".strip()


_CHILD_FAIL_CSV = """id,parent_id
30,1
31,2
32,99
""".strip()


_SCHEMA_YML = """
version: 2

seeds:
  - name: rw_parent
    columns:
      - name: id

  - name: rw_child_pass
    columns:
      - name: parent_id
        data_tests:
          - dbt_utils.relationships_where:
              arguments:
                to: ref('rw_parent')
                field: id

  - name: rw_child_pass_filtered
    columns:
      - name: parent_id
        data_tests:
          - dbt_utils.relationships_where:
              arguments:
                to: ref('rw_parent')
                field: id
                from_condition: parent_id <> 99
                to_condition: id in (1, 2)

  - name: rw_child_fail
    columns:
      - name: parent_id
        data_tests:
          - dbt_utils.relationships_where:
              arguments:
                to: ref('rw_parent')
                field: id
""".strip()


class TestRelationshipsWhere:
    """Focused integration test for dbt_utils.relationships_where on Fabric (T-SQL).

    Confirms both default conditions (`from_condition`/`to_condition` defaulting to
    `1=1` upstream) and custom conditions work against Fabric without the legacy
    adapter-specific override. Covers pass (clean FKs), pass-via-filter (bad FK
    but excluded by conditions), and fail (bad FK with default conditions).
    """

    @pytest.fixture(scope="class")
    def packages(self):
        return _PACKAGES_YML

    @pytest.fixture(scope="class")
    def project_config_update(self):
        return {
            "name": "test_relationships_where",
            "dispatch": [
                {
                    "macro_namespace": "dbt_utils",
                    "search_order": ["test_relationships_where", "dbt", "dbt_utils"],
                }
            ],
        }

    @pytest.fixture(scope="class")
    def seeds(self):
        return {
            "rw_parent.csv": _PARENT_CSV,
            "rw_child_pass.csv": _CHILD_PASS_CSV,
            "rw_child_pass_filtered.csv": _CHILD_PASS_FILTERED_CSV,
            "rw_child_fail.csv": _CHILD_FAIL_CSV,
            "schema.yml": _SCHEMA_YML,
        }

    def test_relationships_where(self, project, dbt_core_bug_workaround):
        run_dbt(["deps"])
        run_dbt(["seed"])

        run_dbt(["test", "--select", "rw_child_pass"])
        run_dbt(["test", "--select", "rw_child_pass_filtered"])
        run_dbt(["test", "--select", "rw_child_fail"], expect_pass=False)
