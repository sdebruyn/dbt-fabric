# Contribute `dbt-fabric` to the Fabric Toolbox

This PR adds `tools/dbt-fabric/`: one dbt adapter for both Microsoft Fabric compute engines (Data Warehouse and Lakehouse) in a single Python package.

I wrote most of the code that's now in [`microsoft/dbt-fabric`](https://github.com/microsoft/dbt-fabric). When Microsoft adopted the repository I kept maintaining a fork because customers were asking for things the official repo wasn't shipping. That fork ([`dbt-fabric-samdebruyn`](https://pypi.org/project/dbt-fabric-samdebruyn/) on PyPI) is what multiple organizations are running in production today.

I'm not happy with the state of either Microsoft adapter today. I'm writing this as an invitation, not as an attack. Both repos need a serious reset, and the only way I see to do that is to bring the community back into the maintenance loop: Fabric product team, CAT team, and the people who've kept the fork alive. Three things have to come out of it: a release cadence that actually follows dbt-core, a maintenance model with explicit roles, and a place that the customers who already migrated can stay on.

---

## What does the current situation look like?

Everything below is verifiable on PyPI and GitHub at the time of writing.

`microsoft/dbt-fabric` (Data Warehouse adapter) is on v1.10.0, released 18 May 2026 alongside v1.9.10 the same day. The PyPI classifier list says Python 3.8–3.12, with 3.13 still missing even though it's been GA for over a year. The dependency is `dbt-core>=1.10.0` with no upper bound. Integration tests now do run on PRs (good). The Python test matrix is narrow (integration on 3.11, unit on 3.10 and 3.11) and could be broadened, though that's a minor point — Python version regressions in a dbt adapter are rare.

`microsoft/dbt-fabricspark` (Lakehouse adapter) shipped six releases in eight days (10–17 May 2026):

| Version | Release date |
|---|---|
| v1.10.0 | 10 May 2026 |
| v1.10.1 | 11 May 2026 |
| v1.11.0 | 15 May 2026 |
| v1.12.0 | 17 May 2026 |
| v1.12.1 | 17 May 2026 |
| v1.12.2 | 17 May 2026 |

The version numbers suggest dbt-core 1.10, 1.11, and 1.12 are all supported, but the PyPI manifest of v1.12.2 still says `dbt-core>=1.8.0` with no upper bound. In the dbt adapter ecosystem the convention is that `<adapter>==1.X.Y` means "compatible with `dbt-core==1.X.*`" — Snowflake, Postgres, Spark, and BigQuery encode that as a tight per-release dependency range (e.g. `dbt-core>=1.10.0,<1.11.0`) and ship a matching adapter for each new dbt-core minor. A floor that's two minors behind the adapter version doesn't give that signal: if you install `dbt-fabricspark==1.12.2` and you're on dbt-core 1.8, pip will let you, with no warning.

Functions (the dbt-core 1.11 scalar-function feature) are also not supported in either official adapter, even though 1.11 has been out for about six months. If you use SQL UDFs in dbt on Snowflake or BigQuery and you want to do the same on Fabric, you can't.

---

## What's broken in the official adapters

**Global mutable state in `microsoft/dbt-fabricspark`.** Module-level and class-level globals hold authentication tokens, Livy session handles, connection managers, and relation configuration. See `singleton_livy.py` and `concurrent_livy.py`. Consequence: data races in multi-threaded dbt runs (dbt defaults to more than 1 thread). This contribution uses instance encapsulation throughout.

**`atexit` handlers for session cleanup.** Both `singleton_livy.py` and `concurrent_livy.py` register `atexit` handlers at module import time. Handler execution order is undefined; networking and logging may already be torn down when the handler runs; and the handler gets registered just by importing the module, even if no session was ever created. The high-concurrency variant adds a second `atexit` handler with a global `_active_sessions` set, which makes the global-state problem worse, not better.

**Exception swallowing.** `LivySession.__exit__` (livysession.py:489–495) and `LivyCursor.__exit__` (livysession.py:855–859) both `return True`. That suppresses every exception raised inside a `with` block using these objects. Database errors, timeouts, `KeyboardInterrupt`, all silently dropped.

**Regex bug in SQL sanitization.** `_getLivySQL()` passes `re.DOTALL` as the `count` argument to `re.sub` instead of `flags=re.DOTALL`. So instead of multiline matching, it silently caps comment-stripping to 16 replacements. Subtle, but production-affecting.

**Dead code and copy-paste artifacts.**

- Thrift exception handling in `connections.py:97–113` references `thrift_resp.status.errorMessage` — a pattern from dbt-spark, which talks Apache Thrift. This adapter talks Livy over HTTP. The path is dead.
- AWS logging config in `connections.py:39–46` sets `botocore` and `boto3` to DEBUG at import time. Inherited from a Spark/Databricks ancestor. There are no AWS dependencies in the package.
- A hardcoded 2028 timestamp in `livysession.py:194–198`: the `int_tests` auth path creates a token with `expires_on = 1845972874`, bypassing all token-refresh logic.
- `_parse_retry_after` is duplicated verbatim between `livysession.py` and `mlv_api.py`, both using the deprecated `datetime.utcnow()`.
- `get_headers()` has a `tokenPrint` parameter that logs the full bearer token when set to `True`. Never called with `True`. Dead parameter, latent security risk.

**Inconsistent coding style.** camelCase (`tokenPrint`, `accessToken`, `_submitLivyCode`, `_getLivySQL`) mixed with snake_case all over the codebase. Pre-3.9 typing aliases (`Dict`, `List`, `Optional`, `Union`) still in use even though the package targets Python 3.13. Not aesthetic complaints — signals about review and refactor discipline.

**Inadequate review.** [PR #315](https://github.com/microsoft/dbt-fabric/pull/315) on `microsoft/dbt-fabric` adds `timeout=getattr(credentials, "login_timeout", None)` to every `get_token()` call. This does nothing: `login_timeout` doesn't exist on `FabricCredentials`, and `get_token()` in `azure-identity` doesn't accept a `timeout` argument anyway. The PR description looks AI-generated. Code that does nothing should not be getting merged.

The v1.9.10 release ([issue #362](https://github.com/microsoft/dbt-fabric/issues/362), May 2026) is a different version of the same problem. It's a response to a real, well-documented user report (`list_<schema>` taking 8–20 minutes when another dbt run is active on the same warehouse). The reporter is careful, explicitly flagging their root-cause guess as hypothesis: *"though we have not been able to confirm the exact mechanism"*. The fix wraps `FabricAdapter.list_relations_without_caching` in a custom retry with exponential back-off — duplicating a mechanism that's already in the same file. `SQLConnectionManager.add_query` in `dbt-adapters` takes `retryable_exceptions` and `retry_limit`. Two screens up in the same connection manager, the project's own `add_query` override is already calling it with `retry_limit=3` and `mssql_python.OperationalError` registered. Anyone reading the diff would notice. The PR description follows the same AI-generated pattern as #315. (The same release also adds a `close()` override that skips `ROLLBACK` on autocommit connections, attributed to pyodbc-level contention. I haven't measured pyodbc, so I'm not calling that part wrong. On `mssql-python` I measured `rollback()` at ≤0.1 ms under load, so there's nothing for me to port there.)

**Warehouse snapshots wired into the connection lifecycle.** The warehouse-snapshot feature in `microsoft/dbt-fabric` is implemented as hooks inside `open()` of the connection manager, plus `atexit` handlers. That couples a user-facing feature to Python runtime internals and to connection-manager lifecycle methods that aren't designed as hook points. Not part of dbt's stable adapter interface. This contribution exposes warehouse snapshots as a Jinja macro you can call from `on-run-start` / `on-run-end`. That's the documented, supported way to do this in dbt.

**Fabric-only config keys on the `incremental` materialization.** The v1.9.10 release also extends the `merge` incremental strategy with two new model-level configs invented by the maintainers: `delete_condition` and `delete_not_matched_by_source`. They're wired into `dbt/include/fabric/macros/materializations/models/incremental/incremental.sql` and dispatched through a new `fabric__get_incremental_merge_sql` macro. Neither config exists in `dbt-core` or `dbt-adapters`. No other reference adapter (Snowflake, BigQuery, Postgres, Redshift, Spark) exposes anything equivalent.

The `incremental` materialization is part of dbt's user-facing API contract. Its config keys are how thousands of models in production projects describe themselves. Adding adapter-private knobs has three consequences. A model written for Fabric stops being portable — a user moving to Snowflake (or back) has to rewrite the config block, even though the same merge-with-delete semantics could be done with a `post-hook` or with `merge_update_columns` / `merge_exclude_columns`. Validation has to be reimplemented in Jinja: three compile-time exception branches in the materialization enforce that the new keys only apply to `merge` and that they're mutually exclusive. And it sets the precedent that Fabric needs its own knobs — the first adapter-private config on a stable materialization is the hardest one to push back on, and after that every next one is easier. Extensions go in macros and hooks. They don't go on the materializations dbt-core ships. A maintainer who feels the pull to add `delete_condition` to `incremental` is signalling that they're thinking of the adapter as a standalone product, not as a citizen of the dbt ecosystem.

**Six releases in eight days.** v1.10.0 → v1.10.1 → v1.11.0 → v1.12.0 → v1.12.1 → v1.12.2 on `microsoft/dbt-fabricspark` between 10 and 17 May 2026, with the PyPI manifest of v1.12.2 still saying just `dbt-core>=1.8.0`. The version number says 1.12, the dependency floor says 1.8, and there's no upper bound. That's not how the reference adapters version: a release advertised as supporting dbt-core 1.X is typically pinned to `dbt-core>=1.X,<1.(X+1)`.

---

## How this contribution is different

The architecture is built around shared abstractions instead of duplicating everything per adapter type:

```
BaseFabricCredentials → FabricCredentials (T-SQL) / FabricSparkCredentials (Spark)
BaseFabricConnectionManager → FabricConnectionManager (mssql-python) / FabricSparkConnectionManager (Livy)
BaseFabricAdapter → FabricAdapter / FabricSparkAdapter (also extends SparkAdapter from dbt-spark)

Shared: FabricTokenProvider, FabricApiClient, PurviewClient + PurviewSync
```

Compared to upstream: `microsoft/dbt-fabric` is flat (no inheritance, no shared abstractions), and `microsoft/dbt-fabricspark` is a standalone `SQLAdapter` without a `dbt-spark` dependency, so it reimplements everything dbt-spark provides and automatically misses anything new it ships.

Inheriting from `dbt-spark` means improvements, bug fixes, and new materializations in dbt-spark land in this FabricSpark adapter automatically — much less maintenance burden per dbt-core release. Instance encapsulation makes the adapter thread-safe without separate synchronization logic. Capability declarations (`SchemaMetadataByRelations`, `TableLastModifiedMetadata`) let dbt-core pick the optimized paths on its own, no monkey-patching.

Everything from the "What's broken" section is avoided by construction: no module-level mutable state, no `atexit` handlers, no exception swallowing, modern Python typing (PEP 604 unions, no `typing.Union`/`Optional`), consistent snake_case. The integration test suite has about 444 test classes (vs ~117 for `microsoft/dbt-fabric` and ~141 for `microsoft/dbt-fabricspark`), runs continuously against real Fabric infrastructure, and runs across Python 3.11/3.12/3.13 × dbt-core 1.9/1.10/1.11/1.12. dbt-core upgrades follow a documented checklist in `CONTRIBUTING.md` ("Upgrading dbt-core support"), and a release only ships when the matching dbt-core minor's tests pass. Versioning convention is strict: `dbt-fabric==1.X.Y` means tested against `dbt-core>=1.X,<1.(X+1)`. Build stack is `hatchling` + `uv`.

---

## Everything goes through dbt's existing mechanisms

The one principle running through this whole adapter: every feature uses dbt's existing mechanisms instead of building parallel ones. Examples.

**Warehouse snapshots** are a macro `{{ create_or_update_fabric_warehouse_snapshot(name, description) }}`, callable from any Jinja context (`on-run-start`, `on-run-end`, `post-hook`, `dbt run-operation`). Because it's a macro, you get dynamic names through Jinja, per-model snapshot timing through `post-hook`, environment-driven names through `env_var()`. Same mental model Snowflake, BigQuery, and Postgres users have used for years.

**External tables** go through dbt's [dispatch system](https://docs.getdbt.com/reference/dbt-jinja-functions/dispatch) to override the Fabric plugin of the `dbt-external-tables` package, instead of upstream's standalone `openrowset_source()` macro. The result: external files are regular sources, `{{ source('my_external', 'sales') }}`. They show up in the lineage graph, freshness checking works out of the box, and `dbt run-operation stage_external_sources` is the standard interface.

**`cluster_by`** is a standard model config option (`{{ config(cluster_by=['customer_id', 'order_date']) }}`), identical to Snowflake and BigQuery. Works on tables, on incremental models, and on models with contract enforcement. Generated DDL is a clean `WITH (CLUSTER BY (...))` clause, no post-hook tricks.

**Manual statistics** through model config (`{{ config(statistics=['col1', 'col2'], statistics_sample_percent=50) }}`), idempotent (`CREATE STATISTICS` first run, `UPDATE STATISTICS` after). The naming convention `dbt_stats__<md5_hash>` avoids collisions with Fabric's auto-generated `_WA_Sys_*` statistics — a detail you only think to add after you've debugged the collision in production.

**Catalog statistics** show up automatically in `dbt docs generate` output. Implemented as an override of the catalog query using `OBJECTPROPERTYEX(object_id, 'Cardinality')`. No config, no extra commands.

**Microsoft Purview integration** is the macro `{{ purview_sync() }}`, callable from `on-run-end` or as a `dbt run-operation`. It respects dbt's standard [`persist_docs`](https://docs.getdbt.com/reference/resource-configs/persist_docs) configuration: `persist_docs: false` skips the model, `relation: true, columns: false` syncs only what you asked for. Lineage is built from `ref()` and `source()`. End users don't have to learn a separate model.

**Authentication** is a single `FabricTokenProvider` across both adapter types. Configuration goes through the standard `authentication` profile key. Workload identity uses the same top-level credential fields as every other method, no separate profile section. Custom `TokenCredential` classes plug in via `credential_class` and `credential_kwargs`, the same way `azure-identity` users already extend the SDK.

**Python models** use the standard `model(dbt, spark)` API. Same signature, same `dbt.ref()` / `dbt.source()` semantics, same `dbt.config.get()` pattern. Developer experience matches dbt-spark exactly.

**Livy session reuse** is a deep Fabric optimization: the FabricSpark adapter derives a deterministic session tag from `(workspace_id, lakehouse_id)`, so a second `dbt run` against the same workspace/lakehouse reattaches to the still-warm session. Spark cold-start (typically over 2 minutes) doesn't happen on subsequent runs — first-statement latency drops under 1 second. The kind of thing you only think to build after you've waited for the cold-start one too many times. Direct production impact: Spark capacity isn't reprovisioned for no reason.

**PEP 249 cursor** parses Spark JSON results into standard Python types via a [PEP 249](https://peps.python.org/pep-0249/) compatible cursor, so dbt talks to the Lakehouse exactly like any other database.

**Limitations documentation** lists per platform (Data Warehouse, Lakehouse) which dbt features don't work and why, organized into "Unsupported dbt features", "SQL dialect limitations", "DDL limitations", and "Incremental model limitations". Every limitation has either a workaround or a reference to the underlying Fabric constraint. Not a feature in itself — a diagnostic signal that the maintainer knows the engines well enough to map the gaps honestly.

**Community packages** are tested with per-package compatibility documentation: dbt-utils (1.3.3), dbt-date (0.17.2), dbt-codegen (0.14.1), dbt-expectations (0.10.10), dbt-audit-helper (0.13.0), dbt-external-tables (0.11.0), dbt-profiler (1.0.0). For each one, `docs/packages/<package>.md` lists which macros work, which don't, which tests run, and the tested version.

---

## What end users get out of this

- One `pip install dbt-fabric` for both engines, instead of two separate packages with overlapping dependencies and version-conflict risk.
- No external ODBC driver installation. `mssql-python` bundles ODBC Driver 18 and unixODBC, removing a common installation hurdle on macOS and in containers.
- Functions (dbt 1.11 scalar functions) supported on both adapter types where the platform allows.
- Python models on both engines via PySpark, using dbt's standard `model(dbt, spark)` API.
- Microsoft Purview integration via API, `persist_docs`-aware. No Purview scan configuration, no scan-capacity costs.
- 11 authentication methods, including workload identity (federated OIDC for CI/CD) and custom `TokenCredential` classes, all configured through standard dbt profile keys.
- Auto host-resolution from the workspace name. No hardcoded SQL endpoint per environment.
- Manual statistics declaratively manageable through a model config. No post-hook tricks.
- Catalog statistics in `dbt docs generate` without configuration.
- `cluster_by` as a standard model config option, identical to Snowflake and BigQuery.
- High-concurrency Livy session reuse, with measurable cost savings on Spark capacity.
- Compatible with seven community packages, each with its own compatibility matrix.
- Transparent limitations documentation, so customers can decide in advance what will and won't work for their use case.
