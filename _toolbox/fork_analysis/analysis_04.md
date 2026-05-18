### c8483dbf — 2025-04-07 — BUG_FIX
**Message:** fix python 3.9 compat
**What:** Replaced `AccessToken | None` (PEP 604 union) with `Optional[AccessToken]` in `fabric_token_provider.py` so the file parses under Python 3.9.
**Why:** Earlier batch refactor introduced a `X | Y` annotation; the project still claimed `python>=3.9` support, where PEP 604 unions are syntax errors.
**Upstream:** Not applicable — upstream has no separate `fabric_token_provider.py` (token handling is inline in `fabric_connection_manager.py`); this is a fork-only file.

### 40ac03c6 — 2025-04-07 — INFRA: nightly-build base version corrected from 1.9.5 → 1.9.4.

### d0e551c5 — 2025-04-07 — REFACTOR
**Message:** add a base class for package tests
**What:** Extracted `BaseDbtPackageTests` in `tests/functional/packages/base_package_test.py` and refactored `TestDbtUtils` to inherit from it (parametrized via `package_name`, `package_repo`, `package_revision`, `models_config`, `seeds_config`, `tests_config` fixtures).
**Why:** Lays groundwork for adding integration tests against many community packages (dbt-date, dbt-expectations, audit-helper, etc.) without duplicating dispatch/profile boilerplate.

### ad8d2c3e — 2025-04-07 — REFACTOR
**Message:** add timezone var
**What:** Set `vars: {dbt_date:time_zone: UTC}` in the base package test project config.
**Why:** dbt-date requires a `time_zone` var to be set; failing to set it breaks every package that depends on it.

### 55e34683 — 2025-04-07 — REFACTOR
**Message:** add dbt utils dispatching to every package
**What:** Made `BaseDbtPackageTests` auto-add `dbt-labs/dbt_utils@1.3.0` as a package and add a `dbt_utils` dispatch entry whenever the test target is not `dbt_utils` itself; dropped the unused `dbt_fabric` namespace from `search_order`.
**Why:** Many community packages depend on `dbt_utils` macros, but our adapter-specific overrides must take precedence — they need a dispatch entry, not just installation.

### b1e8f997 — 2025-04-07 — INFRA: add empty `tests/__init__.py` to make `tests` an importable package (fixes "module not found" when importing helpers).

### 47b4510f — 2025-04-07 — BUG_FIX
**Message:** cache tokens by scope
**What:** Replaced the single class-level `_token: AccessToken | None` cache with `_tokens: dict[str, AccessToken]` keyed by scope; converted the auth helpers to `@staticmethod` taking an explicit `scope` argument; `get_token(scope=None)` now uses per-scope cache lookup; also exported `FabricLivyHelper`, `FabricRelation`, `FabricTokenProvider` from the package `__init__`.
**Why:** A single cached token is fine for one consumer (pyodbc), but the fork uses multiple scopes (SQL endpoint scope, Fabric/PBI API scope, Livy scope). The shared cache served the wrong token to the wrong consumer.
**Upstream:** `dbt/adapters/fabric/fabric_connection_manager.py` still has `global _TOKEN` (single token) — only ever cached at `AZURE_CREDENTIAL_SCOPE` (`get_pyodbc_attrs_before_credentials` ignores scope). Upstream never needed a multi-scope cache because it has no API-calling features.

### 799d09a3 — 2025-04-17 — NEW_FEATURE
**Message:** add requests dependency and update Fabric classes for improved connection handling
**What:** Added `requests>=2.32.3` as a runtime dep. Introduced workspace/lakehouse-id-based connection: new `workspace_id` and `lakehouse_id` credential fields, made `host` optional, added `FabricConnectionManager.get_warehouse_connection_string()` that calls the Fabric REST API to resolve the SQL connection string from `workspace_id` + `database`, and `get_host()` that picks `host` or falls back to the REST resolver. Built out `FabricLivyHelper.LivySession` (REST submit/poll, statement lifecycle, log URL on failure). Fixed token scope strings (`https://database.windows.net/.default` and `.../powerbi/api/.default`) and added `notebookutils.credentials` fallback. Switched python model write to `df.write.synapsesql(...)` with 3-part name.
**Why:** End users shouldn't have to look up the SQL endpoint URL in the Fabric portal — the adapter can derive it from the workspace + DW name. This is foundational for the fork's Python-model and workspace-name workflows.
**Upstream:** Upstream `FabricCredentials` still requires `host: str` (no `workspace_id`/`lakehouse_id`). `FabricConnectionManager` has no REST integration, no `get_host`, no Livy session helper, and no API workflow.

### bc113f82 — 2025-04-17 — INFRA: re-add `FABRIC_TEST_ENDPOINT` → `host` in `conftest.py` so CI keeps working alongside the new `workspace_id` path.

### 633f046d — 2025-05-21 — BUG_FIX
**Message:** fix token syntax
**What:** Introduced `FABRIC_SPARK_CREDENTIAL_SCOPE = "pbi"` constant; corrected references to non-existent `SYNAPSE_CREDENTIAL_SCOPE` → `SYNAPSE_SPARK_CREDENTIAL_SCOPE`; switched `synapse`/`fabric` authentication branches to their proper Spark scopes; replaced broken `from notebookutils import mssparkutils` import with `from notebookutils import credentials`.
**Why:** Multiple `AttributeError`s in the scope-selection logic from prior commits; the `mssparkutils` symbol doesn't exist in the fabric notebook runtime.
**Upstream:** Not applicable (token provider file does not exist upstream).

### 41e0e3fd — 2025-05-21 — INFRA: nightly-build BASE_VERSION bumped 1.9.4 → 1.9.6.

### 673f69b9 — 2025-05-21 — INFRA: change `authors` in `pyproject.toml` from "Pradeep Srikakolapu" to "Sam Debruyn".

### bb376b06 — 2025-05-21 — BUG_FIX
**Message:** fix scope selection for fabric auth
**What:** Reordered `get_token_scope` so the `synapse`/`fabric` authentication checks run *before* the URL-based heuristics that need `credentials.host` (which can be None when only `workspace_id` is provided).
**Why:** Prior order would call `credentials.host.lower()` on `None` for the spark notebook auth flows. The reorder also makes auth-type explicit selection win over host-substring guessing.
**Upstream:** Not applicable (no FabricTokenProvider upstream).

### 8c3dbabb — 2025-05-21 — BUG_FIX
**Message:** use provided scope if provided
**What:** `get_token` now honors `self.credentials.scope` before falling back to `get_token_scope()`.
**Notes:** Buggy — references `credentials.scope` which doesn't exist; fixed in 772d2100 below.

### 772d2100 — 2025-05-21 — BUG_FIX
**Message:** fix attr call
**What:** Replaced `self.credentials.scope` with `self.credentials.token_scope` (the actual field on `FabricCredentials`).
**Notes:** Fixes the typo introduced in 8c3dbabb.

### 160463ac — 2025-05-21 — BUG_FIX
**Message:** fix authentication attr call
**What:** Replaced `self.authentication.lower()` (which doesn't exist as an attribute of `FabricTokenProvider`) with `self.credentials.authentication.lower()` in the two new branches of `get_token_scope`.
**Notes:** Fixes an `AttributeError` introduced in bb376b06.

### 5ad65126 — 2025-08-06 — BUG_FIX
**Message:** require alias for limits and subs
**What:** Set `FabricRelation.require_alias = True` (was `False`).
**Why:** dbt-core's `--empty` and ref-subquery handling require the derived-table alias; without it, T-SQL throws "incorrect syntax near …".
**Upstream:** Upstream `dbt/adapters/fabric/fabric_relation.py` also has `require_alias: bool = True` — the fork was catching up with an upstream change rather than introducing one.

### a1f32a80 — 2025-08-07 — NEW_FEATURE
**Message:** Add workspace_name to FabricCredentials and implement workspace ID retrieval
**What:** Added a `workspace_name` credential field plus a `get_workspace_id()` API call against `https://api.powerbi.com/v1.0/myorg/groups?$filter=name eq '<name>'`. Rewrote `get_warehouse_connection_string()` to look in warehouses first, then lakehouses, returning the SQL endpoint from either. Connection string is no longer keyed by `database` — it grabs any item in the workspace (all items in a workspace share the SQL endpoint URL).
**Why:** Users typically know the workspace *name* from the Fabric portal, not the GUID; making `workspace_id` optional removes a copy-paste step. Also enables the adapter to find SQL endpoints for Lakehouses (not just Warehouses).
**Upstream:** Upstream `FabricCredentials` has no `workspace_id` *or* `workspace_name`; no API resolution at all.

### f88b30c1 — 2025-08-07 — INFRA: `ruff format` on `fabric_connection_manager.py`.

### 7da9694a — 2025-08-07 — BUG_FIX
**Message:** Add support for workspace_name in FabricConnectionManager host resolution
**What:** `get_host()` now triggers the REST resolver when *either* `workspace_id` or `workspace_name` is set (was only `workspace_id`).
**Why:** Follow-up to a1f32a80 — the resolver knows how to handle both, but the dispatch in `get_host` only checked one.

### 1d276c76 — 2025-08-07 — BUG_FIX
**Message:** add support for workspace_name in token provider
**What:** `get_token_scope` returns `FABRIC_CREDENTIAL_SCOPE` when `host is None` and *either* `workspace_id` or `workspace_name` is set.
**Why:** Same parity fix as 7da9694a, in the token provider's scope-selection path.

### 69231eb0 — 2025-09-11 — NEW_FEATURE
**Message:** add support for getting tokens using SPs
**What:** Added `tenant_id` to `FabricCredentials`; imported `ClientSecretCredential`; refactored `get_token` to (a) short-circuit and return a cached token when it has >300s remaining, (b) handle `activedirectoryserviceprincipal` by constructing a `ClientSecretCredential(client_id, client_secret, tenant_id)` to fetch tokens for the requested scope (not just for pyodbc).
**Why:** Previously SP auth flowed only through pyodbc/ODBC; the new REST flows (workspace resolution, Livy) need a token via Python too. Without this, SP users can't use any of the API-driven features.
**Upstream:** Upstream `FabricCredentials` has `tenant_id` but the `AZURE_AUTH_FUNCTIONS` map has no entry for `activedirectoryserviceprincipal` — pyodbc handles SP auth natively, but there's no Python-callable equivalent because upstream has no REST features.

### 9d65b372 — 2025-09-11 — BUG_FIX
**Message:** do not use our token in pyodbc if it's not an Azure token
**What:** Added `used_for_pyodbc=True` flag so the SP branch wouldn't fetch a token when pyodbc was the consumer (pyodbc handles SP auth natively).
**Notes:** Reverted in next commit; the gating logic moved into a new `get_sql_token`/`get_api_token` split (0e779bdc).

### 9fed7d65 — 2025-09-11 — REVERT_OR_MODIFY
**Message:** Revert "do not use our token in pyodbc if it's not an Azure token"
**What:** Reverted 9d65b372.
**Why:** The flag-based approach was replaced by an explicit two-method API in 0e779bdc.

### 0e779bdc — 2025-09-11 — DBT_NATIVE_REWRITE
**Message:** resilient token fetching for API or SQL
**What:** Moved the auth helpers (`get_cli_access_token`, `get_auto_access_token`, etc.) out of the class as module-level functions; split `get_token` into `get_api_token()` and `get_sql_token(scope=None)`, with shared `_get_token(scope, usage_is_sql)` that knows: API calls always need `FABRIC_CREDENTIAL_SCOPE`; SQL calls with non-Azure auth (e.g. SP) must skip our token cache (returns None so pyodbc does its own auth); SP auth is only used for API consumers. Switched all callers (`get_warehouse_connection_string`, `LivySession._access_token`, `get_pyodbc_attributes`) to the new explicit methods.
**Why:** Embedding "which scope" and "is SP auth allowed" inside one polymorphic method became unmaintainable; two named methods make the call sites self-documenting and remove the need for the SP-pyodbc flag.
**Upstream:** Not applicable (no FabricTokenProvider upstream).

### 9c3ac010 — 2025-09-25 — BUG_FIX
**Message:** add support for varchar(max)
**What:** Replaced every hardcoded `varchar(8000)` / `VARCHAR(8000)` with `varchar(max)` / `VARCHAR(MAX)` in `FabricColumn.TYPE_LABELS`, `FabricColumn.string_type`, `fabric__snapshot_hash_arguments`, `fabric__hash`, and the `tsql_utils_surrogate_key_col_type` default in `dbt_package_support/dbt_utils/sql/surrogate_key.sql`.
**Why:** `varchar(8000)` silently truncates strings longer than 8000 characters — a real data-loss bug for hash inputs, surrogate keys, snapshot hash columns, and any inferred string column. Fabric Warehouse supports `varchar(MAX)` natively.
**Upstream:** Upstream `FabricColumn.TYPE_LABELS` still has `"STRING": "VARCHAR(8000)"`, `"VARCHAR": "VARCHAR(8000)"`, `"NVARCHAR": "VARCHAR(8000)"`; `string_type` defaults to `8000`; `string_size` returns `8000` when `char_size is None`. Active silent-truncation footgun in upstream.

### df1b5b6c — 2025-09-30 — NEW_FEATURE
**Message:** support SQL MERGE
**What:** Added `"merge"` to `valid_incremental_strategies`; changed `fabric__get_incremental_default_sql` to dispatch to `get_merge_sql` (later corrected to `get_incremental_merge_sql` in 73a8c9af) when `unique_key` is set.
**Why:** Delete+insert is wasteful for warehouse workloads; native `MERGE` is supported by Fabric Warehouse and is the dbt-canonical incremental strategy.
**Upstream:** Upstream now also has `"merge"` in `valid_incremental_strategies` and a `fabric__get_incremental_merge_sql` macro — they have caught up since this fork commit landed.

### 955ab2e3 — 2025-09-30 — BUG_FIX
**Message:** fix microbatch merge
**What:** In `fabric__get_incremental_microbatch_sql`, when `unique_key` is present, delegate to `dbt.get_incremental_merge_sql` instead of falling through to the delete+insert path.
**Why:** Microbatch with a `unique_key` should upsert (merge), not just delete-and-insert, to match user expectations and dbt-core semantics.
**Upstream:** Upstream `fabric__get_incremental_microbatch_sql` still has no unique-key shortcut — always does the delete+insert flow.

### ac4bc560 — 2025-10-04 — INFRA: relaxed dev pin constraints (`==` → `>=`/`<` ranges) for pytest, dbt-core, dbt-tests-adapter, ruff; regenerated `uv.lock`.

### fe3d3281 — 2025-10-04 — BUG_FIX
**Message:** for pooling to work, we'd need odbcversion set to 3.8
**What:** Added `pyodbc.odbcversion = "3.8"` next to `pyodbc.pooling = True` in `FabricConnectionManager.connect`.
**Why:** pyodbc's connection pooling silently no-ops unless `odbcversion` is also set to "3.8"; without it, each connection is freshly created.
**Upstream:** Upstream sets `pyodbc.pooling = credentials.pooling if credentials.pooling is not None else True` but never sets `odbcversion` — pooling is effectively broken there.

### 0b4b1bf2 — 2025-10-04 — REFACTOR
**Message:** integrate upstream typing changes
**What:** Expanded `FabricColumn.TYPE_LABELS` to mirror the larger upstream type map (BINARY, CHAR, DATETIME2, MONEY, NCHAR, NVARCHAR, SMALLMONEY, TIME, TINYINT, VARBINARY, VARCHAR) while keeping VARCHAR/NVARCHAR/STRING at `VARCHAR(MAX)`; added `is_string()` and `is_numeric()` to match upstream API.
**Why:** Pull in the type-handling improvements upstream made, without losing the `MAX` fix from 9c3ac010.

### 32a4155a — 2025-10-04 — REFACTOR
**Message:** integrate upstream "--empty" flag changes
**What:** Added `AS` keyword before the alias in `FabricRelation.render_limited` (both the `where 1=0` and `top` paths), matching upstream.

### 7b1427f1 — 2025-10-04 — REFACTOR
**Message:** integrate upstream changes on incremental constraints
**What:** In `fabric__create_incremental` (table path), call `build_model_constraints(target_relation)` after dropping the temp view, matching upstream's incremental-constraints support.

### a5a90ec5 — 2025-10-04 — INFRA
**Message:** update to test with dbt-core 1.10
**What:** Bumped `dbt-core` upper bound from `<1.10.0` to `<1.11.0`; trimmed `tests/functional/adapter/test_sources.py` to drop the deprecated "space in name" source case (dbt-core 1.10 forbids spaces in source names).

### 47f3ac74 — 2025-10-04 — TEST
**Message:** fix empty test
**What:** Removed the local `model_sql`/`models` override in `TestFabricEmpty`; the base class now suffices.

### 812e2d6b — 2025-10-04 — TEST
**Message:** fix empty inline SQL test
**What:** Added `model_inline_sql` and a `models` fixture override to `TestFabricEmptyInlineSourceRef` (alias source explicitly to satisfy `require_alias=True`).

### 73a8c9af — 2025-10-04 — BUG_FIX
**Message:** fix incremental merge default strategy
**What:** Changed `fabric__get_incremental_default_sql` from `get_merge_sql(arg_dict)` to `get_incremental_merge_sql(arg_dict)`.
**Why:** `get_merge_sql` is the low-level SQL builder; `get_incremental_merge_sql` is the dispatch wrapper that handles all the incremental_predicates/delete_condition/delete_not_matched_by_source plumbing. The earlier commit (df1b5b6c) used the wrong macro and silently dropped those features.
**Notes:** Bug introduced in df1b5b6c (same batch).

### 7af4d5e3 — 2025-10-04 — TEST
**Message:** fix microbatch test
**What:** Dropped a stray alias `a` from a single test SQL string to align with `require_alias` expectations.

### 2e7e1f2f — 2025-10-04 — INFRA
**Message:** simplify test setup
**What:** Removed the second case-insensitive-DWH matrix entry from CI; trimmed `test.env.sample` (workspace_name based, dropped lakehouse_id); switched conftest to `workspace_name`; raised default retries 2→3, threads 1→20, added `login_timeout`/`query_timeout`; dropped the `FABRIC_TEST_DWH_CI_NAME` machinery in `test_caching.py` (caching tests now run against the default DWH).

### 62f047cc — 2025-10-04 — INFRA
**Message:** skip grants tests by default due to broken Fabric SP support
**What:** Added `--with-grants` pytest option and a `grants` marker that auto-skips unless the flag is passed; marked all grants tests; switched CI to use `FABRIC_TEST_WORKSPACE_NAME` and stopped passing the SP-based `DBT_TEST_USER_1/2/3` secrets.
**Why:** Fabric's SP grant support is broken (cannot reliably GRANT to SPs); skipping in CI prevents spurious failures while keeping the tests available locally with `--with-grants`.

### df29b7c0 — 2025-10-04 — INFRA: `ruff format` on `tests/conftest.py`.

### e5a3c370 — 2025-10-04 — INFRA: removed the duplicate `ci07` matrix entry (same python_version + msodbc_version as ci06).

### 4825c916 — 2025-10-04 — INFRA
**Message:** remove support for Python 3.9
**What:** Bumped Python lower bound, removed 3.9 from CI matrix, regenerated `uv.lock`. Enables PEP 604 unions, modern typing, etc. (the cause of the c8483dbf compat fix at the start of this batch).

### 21facd52 — 2025-10-04 — INFRA: CI matrix now passes `FABRIC_TEST_WORKSPACE_ID` (literal GUID); conftest accepts both `workspace_id` and `workspace_name`.

### 4e6b0f7e — 2025-10-05 — INFRA: switched CI back to `FABRIC_TEST_HOST` (from a secret); conftest reads `FABRIC_TEST_HOST` for `host`.

### f63cebfe — 2025-10-05 — REFACTOR
**Message:** introduce api client to isolate API calls
**What:** Created `src/dbt/adapters/fabric/fabric_api_client.py` containing `FabricApiClient` with `get_workspace_id`, `get_warehouse_connection_string`, `get_fabric_token_provider` — all moved out of `FabricConnectionManager`. The connection manager now multi-inherits from `SQLConnectionManager` + `FabricApiClient` and additionally caches `_workspace_id` and `_warehouse_connection_string` at the class level (so REST is hit at most once per process). Added `.vscode/settings.json` (single-key Python envs config).
**Why:** REST-API plumbing was bloating the connection manager and made it harder to reuse the API client from the Livy helper or future utilities. Extracting it gives a clean seam and free memoization.
