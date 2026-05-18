### 99b9986e — 2025-03-26 — INFRA: part 1 of project modernization — replaced setup.py/Makefile/dev_requirements.txt with `pyproject.toml` + `uv.lock`, added `.python-version`, dropped `.pre-commit-config.yaml`, `CHANGELOG.md`, `pytest.ini`, `MANIFEST.in`; moved `devops/CI.Dockerfile` to `.github/CI.Dockerfile`; updated CI workflows.
**Upstream:** Still uses `setup.py`, `Makefile`, `dev_requirements.txt`, `.pre-commit-config.yaml`, `pytest.ini`, `MANIFEST.in`, `devops/CI.Dockerfile`, and a build-system-only `pyproject.toml`.

### ce0554fe — 2025-03-26 — INFRA: clean up configs — moved adapter package from `dbt/` to `src/dbt/` (src layout), trimmed `requirements-dev.txt`, refined ruff config in `pyproject.toml`.
**Upstream:** Still uses flat `dbt/` layout.

### fbb08c44 — 2025-03-26 — INFRA: ruff fmt — apply ruff formatting across the codebase after move to src layout.

### 17259ce0 — 2025-03-26 — INFRA: add less checks — removed several ruff rule categories from `pyproject.toml` (slimmer enforced ruleset).

### e134bdbf — 2025-03-26 — DBT_NATIVE_REWRITE
**Message:** simplify testing
**What:** Collapsed the multi-profile (`--profile`/`PROFILE_NAME`) conftest into a single environment-driven `dbt_profile_target` fixture; removed the `_profile_*` helper functions and the `skip_by_profile_type` autouse fixture; removed `skip_profile`/`only_with_profile` pytest markers.
**Why:** Five hand-rolled profile variants (`ci_azure_cli`, `ci_azure_auto`, `ci_azure_environment`, `user_azure`, `integration_tests`) and the marker-based skip plumbing are scaffolding the harness shouldn't need — env vars + the standard `dbt_profile_target_update` fixture cover the same surface with far less code.
**Upstream:** `tests/conftest.py` upstream still defines `pytest_addoption("--profile")`, five `_profile_*` helpers, the marker-driven `skip_by_profile_type` autouse fixture, and registers `skip_profile`/`only_with_profile` markers in `pyproject.toml`. Roughly 100 lines of indirection the fork removed.

### 4daecf5a — 2025-03-26 — INFRA: test warnings — tighten `filterwarnings` in `pyproject.toml`.

### ac162d96 — 2025-03-26 — INFRA: update docker imgs — refactor `publish-docker.yml` actions/tags.

### 36261378 — 2025-03-26 — INFRA: simpler publishing — simplify `release-version.yml` workflow.

### 4fbece14 — 2025-03-26 — INFRA: fix unit test flow — tweak `unit-tests.yml`.

### abe0bfb5 — 2025-03-26 — INFRA: fix current tests — restructure `integration-tests-azure.yml`, removing legacy steps.

### 68630a73 — 2025-03-26 — INFRA: debian img — switch CI Dockerfile base image to Debian.

### c702e421 — 2025-03-26 — INFRA: cleanup docs — rename `integration-tests-azure.yml` to `integration-tests.yml`; trim `CONTRIBUTING.md`.

### deeed954 — 2025-03-26 — INFRA: clean up more things — also fixes filename typo `test_snpashot_configs.py` → `test_snapshot_configs.py`.

### ba675aac — 2025-03-26 — INFRA: Merge PR #1 (project-modernization-2025) — aggregate merge of the above modernization commits.

### 51d5c80f — 2025-03-26 — INFRA: forked project name — rename PyPI package to fork-specific name and bump version.

### 8bd8bbec — 2025-03-26 — INFRA: target 'forked-version' branch in workflows + expand Python matrix.

### 886382a4 — 2025-03-26 — INFRA: casing — case fix in `CI.Dockerfile`.

### b8bf180d — 2025-03-26 — INFRA: simplify docker img — reduce `CI.Dockerfile` from 23 to 7 lines.

### d6c2153c — 2025-03-26 — INFRA: merge project-modernization-2025 into forked-version.

### 19c4ad70 — 2025-03-26 — INFRA: fix platforms for docker.

### c6c47aff — 2025-03-26 — INFRA: merge project-modernization-2025 into forked-version.

### 27d17011 — 2025-03-26 — INFRA: fix unit test ci — simplify `unit-tests.yml`.

### c05c7193 — 2025-03-26 — INFRA: merge project-modernization-2025 into forked-version.

### 0148b809 — 2025-03-29 — INFRA: bump version to alpha.

### 82ab328b — 2025-03-29 — INFRA: version from tag — generate adapter version from git tag in release workflow.

### a3467b4a — 2025-03-29 — DBT_NATIVE_REWRITE
**Message:** use trusted publishing
**What:** Drop `.pypirc` token bootstrapping from `release-version.yml`; rely on PyPI OIDC trusted publishing.
**Why:** Removes the need to store and rotate a long-lived `PYPI_DBT_FABRIC` API token in GitHub Secrets.
**Upstream:** `microsoft/dbt-fabric` `release-version.yml` still writes a `.pypirc` with `password = ${{ secrets.PYPI_DBT_FABRIC }}` and uploads via `twine upload`. No trusted publisher configured.
**Notes:** Mechanism is INFRA but the security/supply-chain improvement is worth flagging for the contribution case.

### 0b116542 — 2025-03-29 — INFRA: add permissions for token — grant `id-token: write` for OIDC.

### 4d9ede1c — 2025-03-29 — INFRA: use correct container in `integration-tests.yml`.

### 6ae56767 — 2025-03-29 — INFRA: login to azure cli using OIDC — `azure/login@v2` with OIDC federation.
**Notes:** Upstream still authenticates via stored client secrets / older auth flows in `integration-tests-azure.yml`. OIDC removes long-lived Azure secrets from the CI environment.

### 31eadd6f — 2025-03-29 — INFRA: add environment azure for oidc — declare GitHub environment for federated credential trust.

### 21a7e2bf — 2025-03-29 — INFRA: disable subscriptions in azure/login step.

### 0f30d0f3 — 2025-03-29 — INFRA: uv run in integration tests — invoke pytest via `uv run`.

### bb228891 — 2025-03-29 — INFRA: set correct odbc driver in CI.

### 9a1c177c — 2025-03-29 — INFRA: correct ODBC driver version reference in integration tests.

### 20c169c2 — 2025-03-29 — INFRA: secret refs — fix env var names in workflow secrets.

### c333c26b — 2025-03-29 — INFRA: limit concurrency in `integration-tests.yml`.

### 1b8b002c — 2025-03-29 — DOCS: update package references and badges in README.md (point at the fork's PyPI/repo).

### bbfe064c — 2025-03-29 — BUG_FIX
**Message:** add default dbo user in schema creation tests
**What:** In `tests/functional/adapter/test_schema.py`, fall back to `'dbo'` when `DBT_TEST_USER_1` isn't set in the env (both in `schema_authorization` and `_verify_schema_owner`).
**Why:** Without the fallback, the test fixture interpolates an empty string into a GRANT/AUTHORIZATION clause, producing a runtime SQL failure when running locally without the env var set.
**Upstream:** Upstream `tests/functional/adapter/test_schema.py` still uses `env_var('DBT_TEST_USER_1')` and `os.getenv("DBT_TEST_USER_1")` with no default.

### 9d861bc0 — 2025-03-29 — INFRA: add dbt test user to CI — export `DBT_TEST_USER_1` env var in the workflow.

### 0bc7374c — 2025-03-29 — INFRA: fix python version usage in ci.

### 077a2b7c — 2025-03-29 — INFRA: try without concurrency limitation.

### ae91dbdf — 2025-03-29 — INFRA: concurrent tests — re-enable concurrent test execution.

### fa51a13a — 2025-03-29 — TEST
**Message:** add a secondary dwh with case insensitive collation
**What:** Wire up a second Fabric Data Warehouse (case-insensitive collation) via env var `FABRIC_TEST_DWH_CI_NAME` and use it in `TestCachingUppercaseModel` to actually run the case-insensitive cache test instead of skipping it.
**Why:** Upstream blanket-skips the case-insensitivity caching test with the comment "Fabric DW does not support Case Insensivity" — but Fabric *does* support CI collations when the warehouse is provisioned with one. The skip masks a real test that can run with the right fixture.
**Upstream:** `tests/functional/adapter/test_caching.py` upstream still has `@pytest.mark.skip(reason="Fabric DW does not support Case Insensivity.")` on `TestCachingUppercaseModel`. The fork proves the test is runnable with a properly-collated DWH.

### 4c96067e — 2025-03-29 — TEST
**Message:** enable ephemeral tests
**What:** Remove `@pytest.mark.skip(reason="Nested CTE is not supported")` from `TestSingularTestsEphemeralFabric`.
**Why:** The skip's claim ("Nested CTE is not supported") is incorrect — Fabric supports nested CTEs. The test runs.
**Upstream:** Upstream still has the skip on `TestSingularTestsEphemeralFabric` with the same incorrect rationale.

### 8359b9cf — 2025-03-29 — INFRA: set secondary dwh in ci — export `FABRIC_TEST_DWH_CI_NAME` to the workflow env.

### 477d451a — 2025-03-29 — TEST
**Message:** remove skip from ci tests
**What:** Remove the class-level `@pytest.mark.skip` from `TestCachingUppercaseModel` (kept the conditional skip inside the fixture for when the env var is unset).
**Why:** Follow-up to fa51a13a — once the secondary CI-collation DWH is wired into CI, the class no longer needs the blanket skip.
**Upstream:** Upstream still has the blanket class-level skip.
**Notes:** Modifies fa51a13a from same batch; together these two commits convert a permanently-skipped upstream test into a real, running one when the proper fixture warehouse exists.
