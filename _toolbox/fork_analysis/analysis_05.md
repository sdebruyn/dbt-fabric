### 6277687f — 2025-10-05 — NEW_FEATURE
**Message:** link api helper to fetch lakehouse
**What:** Added `get_lakehouse_id` to `FabricApiClient` that resolves a lakehouse ID via the Fabric REST API by `lakehouse_name`, plus a `lakehouse_name` credential and `lakehouse`/`workspace` aliases.
**Why:** Enable Python model execution to target a Lakehouse without forcing users to look up GUIDs.
**Upstream:** Upstream `FabricCredentials` (`dbt/adapters/fabric/fabric_credentials.py`) has no `lakehouse_id` or `lakehouse_name` field at all — there is no FabricApiClient and no lakehouse resolution path.

### 830ae67e — 2025-10-05 — NEW_FEATURE
**Message:** complete python support
**What:** Hooked `FabricLivyHelper` into the lakehouse/workspace API client; implemented `generate_python_submission_response`; injected the warehouse SQL endpoint into the Python harness so `spark.read.synapsesql` resolves; unskipped Python model tests; passed lakehouse vars through CI/conftest.
**Why:** Make `materialized: python` actually work end-to-end against Fabric (Livy + SynapseSQL connector).
**Upstream:** Upstream has no Python model support whatsoever — `generate_python_submission_response` did not exist, there is no Livy helper, and `python` is not a supported materialization. `git ls-tree -r upstream/main | grep python` shows only `.python-version`.

### 95ab823b — 2025-10-05 — DBT_NATIVE_REWRITE
**Message:** reuse sessions if possible
**What:** `LivySession` now lists existing Fabric Livy sessions named `dbt-fabric` in `idle|starting|running` state and reuses them instead of starting a fresh one per model; consolidates URL helpers; correctly reports statement success/error from `output.status`.
**Why:** Spinning up a new Livy session per Python model is expensive (~minutes) and was the prior behaviour; reusing the session is required for realistic adoption.
**Upstream:** Upstream has no Livy/Python infrastructure at all.

### 3f1eb0ec — 2025-10-05 — TEST
**Message:** add skip markers for incremental Python models and PySpark tests
**What:** Re-skipped `TestPythonIncrementalTestsFabric` and `TestPySparkTestsFabric` with explicit reasons after the previous commit had unskipped them.

### a9c20a52 — 2025-10-05 — DOCS
**Message:** clean up docs
**What:** Removed Microsoft-internal `SECURITY.MD` and a nightly-build workflow inherited from the Microsoft repo; trimmed CONTRIBUTING down to the fork's workflow.

### e3cbc5ef — 2025-10-05 — DOCS
**Message:** update readme
**What:** Rewrote README for the fork: rebrands to `dbt-fabric-samdebruyn`, positions as a maintained/extended fork, removes Microsoft CoC reference, adds acknowledgements section.

### e5ede38e — 2025-10-05 — INFRA: fix pypi project URLs after rename to `dbt-fabric-samdebruyn`.

### 65390837 — 2025-10-05 — INFRA: add GitHub Sponsors `.github/FUNDING.yml`.

### ca3df4c7 — 2025-10-05 — DOCS
**Message:** add docs
**What:** Added mkdocs-material configuration (`mkdocs.yml`), initial `docs/index.md`, a placeholder `overrides/partials/integrations/analytics/custom.html`, and a Cloudflare Pages build script. Wires mkdocs into pyproject extras and lockfile.

### 41436810 — 2025-10-05 — INFRA: move docs build artefacts (cloudflare_pages.sh, requirements.txt) into a dedicated `docs_build/` folder.

### b652384c — 2025-10-05 — INFRA: change CF Pages output directory.

### 63dee533 — 2025-10-05 — DOCS: add docs site link to README; gitignore `site/`; add `site` extra.

### 22998e1d — 2025-10-05 — DOCS
**What:** Added contributing.md and license.md docs pages and a Swetrix analytics snippet (later removed in bdc83cfa).

### e659e7f0 — 2025-10-05 — DOCS: add dbt + Fabric brand logos and a Code of Conduct mention with dbt signature mark.

### f94e192d — 2025-10-05 — DOCS: fix logo URLs in README/docs/mkdocs.

### 6252f8b2 — 2025-10-05 — DOCS
**Message:** add config page
**What:** Adds three docs pages: `installation.md` (driver setup), `compatibility.md`, and a 343-line `configuration.md` documenting every credential and aliasing rule. None of these exist upstream.

### e214c9ae — 2025-10-05 — DOCS
**Message:** add feature comparison page to documentation
**What:** Adds a 95-line `feature-comparison.md` enumerating fork vs upstream feature delta — this is the contribution case in user-facing form.

### e332b540 — 2025-10-05 — DOCS: small README link fix.

### 456b7c58 — 2025-10-05 — INFRA: add explicit `permissions:` to lint-format workflow (least-privilege hardening).

### 3953b0eb — 2025-10-06 — DOCS: add "drop-in replacement for `dbt-fabric`" note to README.

### bdc83cfa — 2025-10-18 — INFRA: remove Swetrix analytics from docs build (rolling back the analytics snippet added in 22998e1d).
**Notes:** Modifies 22998e1d from this same batch.

### b8803211 — 2026-02-06 — INFRA: drop support for Python 3.10 (`pyproject.toml`, regenerated `uv.lock`).

### b4a5919e — 2026-02-06 — REFACTOR
**Message:** simpler typing in Python
**What:** Mechanical conversion of `typing.Optional[X]` / `typing.List[X]` to PEP 604 `X | None` / built-in generics across adapter modules.

### 6a18ea77 — 2026-02-06 — BUG_FIX
**Message:** fix for nvarchar column types
**What:** In `fabric__get_columns_in_relation`, halves `c.max_length` for `nchar|nvarchar|sysname` (SQL Server stores nchar lengths in bytes); also adds `fabric_base_api_uri` and `powerbi_base_api_uri` credential overrides and switches to PEP 604 typing in credentials.
**Why:** Without the fix, `nvarchar(50)` columns are reported as character length 100 (bytes), corrupting `get_columns_in_relation` results and any downstream contract/constraint checks.
**Upstream:** Upstream eventually applied the same divide-by-two fix in `dbt/include/fabric/macros/adapters/columns.sql` (commit `253c453`), so the column-length bug is no longer present upstream. The credential base-URI override fields, however, are not in upstream.

### af65b5e3 — 2026-02-06 — ANTI_PATTERN_REMOVED
**Message:** move all API calls into a single API client
**What:** Refactors `FabricApiClient` from a bag of `@classmethod` + class-level mutable caches into a proper instance class (`create()` factory, instance-scoped caches). Pulls Livy session management out of `fabric_livy_helper.py` and the warehouse-connection-string lookup out of the connection manager, centralising every Fabric REST call in one place. Adds `_cached_warehouses` / `_cached_lakehouses` / `_livy_session_id` and a `_warehouse_snapshot_operations` map to support async operations.
**Why:** Removes global mutable state (the previous design stored credentials/token-provider as class attributes — broken under multiple projects/profiles in one process) and removes the copy-pasted Livy URL plumbing from `fabric_livy_helper.py`.
**Upstream:** Upstream has no FabricApiClient; equivalent REST calls live inside `dbt/adapters/fabric/warehouse_snapshots.py` (its own `WarehouseSnapshotManager` class) and `fabric_connection_manager.py` uses a module-global `_snapshot_manager` for snapshot orchestration, plus `atexit.register` to fire end-of-run logic — the exact anti-patterns this refactor removes.

### 8c854a49 — 2026-02-06 — INFRA: bump GitHub Actions matrix to Python 3.11–3.14 (3.14 rolled back in 292b6fd4).

### fc57b152 — 2026-02-06 — INFRA: ruff formatting only.

### 3b56351e — 2026-02-06 — BUG_FIX
**Message:** import snapshot hard deletes fix
**What:** In `fabric__snapshot_staging_table`, when `strategy.hard_deletes == 'new_record'`, filters out previously-hard-deleted records when selecting current snapshot rows for the merge — without it the merge would re-resurrect deleted rows.
**Why:** Bug carried over from dbt-spark/dbt-postgres; without this filter, every snapshot run after a hard-delete cycle reactivates the deleted record.
**Upstream:** Upstream also has this fix in `dbt/include/fabric/macros/materializations/snapshots/helpers.sql` (commit `dbe7a77` "Addressing hard_delete issues with snapshot…"), so this is no longer a fork-only fix.

### d8f71643 — 2026-02-06 — INFRA: routine package bumps in `pyproject.toml` and `uv.lock`.

### 7fccebe7 — 2026-02-07 — DBT_NATIVE_REWRITE
**Message:** add on run start/end hooks for warehouse snapshots
**What:** Adds `create_or_update_fabric_warehouse_snapshot(snapshot_name, description=none)` macro that delegates to a new `@available` adapter method, which calls the consolidated `FabricApiClient`. Implements warehouse-snapshot create/update via the LRO (Location header) pattern, including `wait_and_get_snapshot_id_from_operation`. Adds a functional test that wires the macro into a real dbt project as `on-run-start`/`on-run-end` hooks (the dbt-native way).
**Why:** Replace the upstream design that hijacks connection lifecycle with `atexit` + a module-level `_snapshot_manager` global, with a dbt-native flow: macro → `@available` adapter method → user-controlled `on-run-start`/`on-run-end` hooks.
**Upstream:** `upstream/main:dbt/adapters/fabric/fabric_connection_manager.py` literally `import atexit`, declares `_snapshot_manager = None` global, and at line 602 does `atexit.register(lambda: _run_end_action(result))` to schedule end-of-run snapshot updates. That bypasses dbt-core's normal lifecycle and runs even when the process is killed/crashed; the fork moves all of it into proper macro hooks.

### a462eb8e — 2026-02-07 — INFRA: switch the CI workspace name and corresponding env var.

### a8110438 — 2026-02-07 — INFRA: bump base Debian in CI Dockerfile (reverted two commits later).

### 76c4a4f8 — 2026-02-07 — BUG_FIX
**Message:** add rate limiting support
**What:** Adds `_api_request` helper to `FabricApiClient` that centralises every REST call, handles HTTP 429 by sleeping `Retry-After` and recursing, and raises a uniform `DbtRuntimeError` on non-2xx. Replaces every per-method `requests.get/post/patch` + status-code check with `_api_get/_api_post/_api_patch`.
**Why:** Fabric's REST APIs throttle aggressively; without 429 handling, dbt runs would fail spuriously when several models/snapshots fire calls in quick succession. Also removes ~30 lines of repeated status-check boilerplate.
**Upstream:** `upstream/main:dbt/adapters/fabric/warehouse_snapshots.py` uses `response.raise_for_status()` with no 429 backoff — same throttling vulnerability is present.

### b9d47abd — 2026-02-07 — REVERT_OR_MODIFY: reverts a8110438 (Debian bump in CI).
**Notes:** Same-batch revert.

### 931ec016 — 2026-02-07 — INFRA: ruff formatting only.

### 292b6fd4 — 2026-02-07 — INFRA: remove Python 3.14 from supported matrix because upstream deps don't ship 3.14 wheels yet.
**Notes:** Partially reverts 8c854a49 from this same batch.

### 412b4732 — 2026-02-07 — NEW_FEATURE
**Message:** clean up snapshots after run
**What:** Adds `delete_warehouse_snapshot(snapshot_name)` to FabricApiClient and an optional `description` parameter to the create/update API (and to the user-facing macro). The functional test fixture now uses `delete_warehouse_snapshot` for setup/teardown.
**Why:** Round-trip cleanup so test runs (and user pipelines that want temporary snapshots) don't leak snapshots into the workspace; descriptions make snapshots self-documenting.
**Upstream:** `upstream/main:dbt/adapters/fabric/warehouse_snapshots.py` defines `delete_warehouse_snapshot(snapshot_id)` as `return True` — a stub that pretends to delete but does nothing.

### 2a1ed5a0 — 2026-02-07 — TEST
**Message:** Add Fabric API client and credentials fixtures; update snapshot handling
**What:** Promotes `credentials`, `fabric_token_provider`, and `fabric_api_client` to class-scoped conftest fixtures, simplifies the snapshot test, and asserts the snapshot exists with the expected `displayName` and `description` after the run.

### e51b3bec — 2026-02-07 — NEW_FEATURE
**Message:** build Docker image for mssql-python
**What:** Splits `CI.Dockerfile` into `base` / `msodbc` / `mssql-python` stages, adds a `mssql-python` target installing `libltdl7`, `libkrb5-3`, `libgssapi-krb5-2`, and adds `mssql-python` to the Docker publish matrix.
**Why:** Future move from `pyodbc` to Microsoft's native `mssql-python` driver requires a different system-package baseline (no ODBC, but needs Kerberos libs).
**Upstream:** Upstream still uses `pyodbc` exclusively and ships only ODBC-based CI images.

### e31a0094 — 2026-02-07 — BUG_FIX
**Message:** fix: correct syntax for installing libgssapi-krb5-2 in Dockerfile
**What:** Adds the missing `\` line continuation after `libgssapi-krb5-2` so `apt-get autoremove` is part of the same RUN command.
**Notes:** Fixes a syntax error in e51b3bec from this same batch.

### 30e7593a — 2026-02-17 — INFRA: merge `upstream/main` (Microsoft's `main`) into `forked-version`; resolves conflicts in workflows, version file, table macros, conftest, and several test files.

### 99634f42 — 2026-02-17 — INFRA: another `upstream/main` merge into `forked-version` (more conflicts in pre-commit, columns macro, adapter, relation, etc).

### 4bfd382f — 2026-02-17 — INFRA: third upstream merge (release workflow, incremental_strategies, warehouse_snapshots conflicts).

### e649af80 — 2026-02-17 — INFRA: fourth upstream merge (conftest, warehouse_snapshots).

### 08d36bcb — 2026-02-17 — INFRA: regenerate `uv.lock` after upstream merge.

### 1afcfa1a — 2026-02-17 — DOCS
**Message:** update docs
**What:** Adds four new docs pages: `authentication.md` (245 lines), `python-models.md` (102 lines), `warehouse-snapshots.md` (150 lines), and updates `feature-comparison.md` with the latest fork-vs-upstream delta. Wires them into mkdocs nav.
