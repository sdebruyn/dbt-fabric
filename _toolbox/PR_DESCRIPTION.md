# Contribute `dbt-fabric` to the Fabric Toolbox

This PR adds `tools/dbt-fabric/`: one dbt adapter for both Microsoft Fabric compute engines (Data Warehouse and Lakehouse) in a single Python package.

I wrote most of the code that's now in [`microsoft/dbt-fabric`](https://github.com/microsoft/dbt-fabric). When Microsoft adopted the repository I kept maintaining a fork because customers were asking for things the official repo wasn't shipping. That fork ([`dbt-fabric-samdebruyn`](https://pypi.org/project/dbt-fabric-samdebruyn/) on PyPI) is what multiple organizations are running in production today.

I'm bringing it to the toolbox because the toolbox's multi-contributor model — the Fabric product team, the CAT team, and the community sharing maintenance — fits a dbt adapter better than a single-maintainer setup. The dbt ecosystem moves quickly (new dbt-core minors, community-package releases, [`dbt-tests-adapter`](https://github.com/dbt-labs/dbt-adapters/tree/main/dbt-tests-adapter) `Base*` classes every cycle), and a shared codebase under the toolbox is better positioned to keep up.

---

## What this gives users today

**One `pip install dbt-fabric` and both Fabric engines work.** No separate `dbt-fabricspark` package, no system ODBC driver to install: the bundled [`mssql-python`](https://github.com/microsoft/mssql-python) driver handles the Data Warehouse side and ships ODBC Driver 18 + unixODBC inside the wheel.

On top of that, a long list of features the official adapters don't ship:

**[Microsoft Purview](https://learn.microsoft.com/en-us/purview/) integration via API.** A `{{ purview_sync() }}` macro that pushes model and column documentation, plus [`ref()`](https://docs.getdbt.com/reference/dbt-jinja-functions/ref) and [`source()`](https://docs.getdbt.com/reference/dbt-jinja-functions/source) lineage, directly into Purview through the REST API. [`persist_docs`](https://docs.getdbt.com/reference/resource-configs/persist_docs)-aware: models marked `persist_docs: false` are skipped, granular `relation: true, columns: false` only syncs what you asked for. No Purview scan configuration needed.

**[Python models](https://docs.getdbt.com/docs/build/python-models) on both engines.** Standard `model(dbt, spark)` API with PySpark on both Data Warehouse and Lakehouse. `microsoft/dbt-fabric` doesn't support Python models at all; `microsoft/dbt-fabricspark` only supports them on the Lakehouse.

**Compatibility with nine community packages, continuously tested.** [dbt-utils](https://github.com/dbt-labs/dbt-utils), [dbt-date](https://github.com/godatadriven/dbt-date), [dbt-codegen](https://github.com/dbt-labs/dbt-codegen), [dbt-expectations](https://github.com/metaplane/dbt-expectations), [dbt-audit-helper](https://github.com/dbt-labs/dbt-audit-helper), [dbt-external-tables](https://github.com/dbt-labs/dbt-external-tables), [dbt-profiler](https://github.com/data-mie/dbt-profiler), [dbt-artifacts](https://github.com/brooklyn-data/dbt_artifacts), and [dbt-project-evaluator](https://github.com/dbt-labs/dbt-project-evaluator) ship Postgres- or Snowflake-flavoured macros that fail on Fabric. This contribution writes the adapter-specific overrides through dbt's [dispatch](https://docs.getdbt.com/reference/dbt-jinja-functions/dispatch) system and runs an integration test for each package on every PR. Neither official adapter ships overrides or tests for any of these.

And the rest:

- Warehouse snapshots as a callable Jinja macro (`{{ create_or_update_fabric_warehouse_snapshot(...) }}`) usable from [`on-run-start`/`on-run-end`](https://docs.getdbt.com/reference/project-configs/on-run-start-on-run-end), any [`post-hook`](https://docs.getdbt.com/reference/resource-configs/pre-hook-post-hook), or [`dbt run-operation`](https://docs.getdbt.com/reference/commands/run-operation).
- [`dbt-external-tables`](https://github.com/dbt-labs/dbt-external-tables) compatibility via dispatch, so `OPENROWSET`-backed files are regular [`source()`](https://docs.getdbt.com/reference/dbt-jinja-functions/source) references in the lineage graph.
- [`cluster_by`](https://docs.getdbt.com/reference/resource-configs/snowflake-configs#using-cluster_by) as a standard model config.
- [Manual statistics as model config](https://dbt-fabric.debruyn.dev/statistics/).
- Catalog statistics in [`dbt docs generate`](https://docs.getdbt.com/reference/commands/cmd-docs) output.
- [Functions](https://docs.getdbt.com/docs/build/functions) (dbt-core 1.11 scalar functions) on both engines.
- [Workload identity](https://learn.microsoft.com/en-us/entra/workload-id/workload-identity-federation) (federated OIDC for CI/CD).
- 11 authentication methods through standard dbt [profile keys](https://docs.getdbt.com/docs/core/connect-data-platform/profiles.yml), plus custom [`TokenCredential`](https://learn.microsoft.com/en-us/python/api/azure-core/azure.core.credentials.tokencredential?view=azure-python) classes.
- One shared `FabricTokenProvider` covering both adapter types, so the same profile structure works for DW and Lakehouse.
- [Auto host-resolution from the workspace name](https://dbt-fabric.debruyn.dev/configuration/#host).
- A PEP 249–compliant cursor for Spark JSON results.

Every PR runs against real Fabric, and every release ships after the full integration suite has gone green.

---

## What's broken in the official adapters

I tried contributing some of these fixes back to `microsoft/dbt-fabric` first; most didn't land. The fork carried what the upstream couldn't absorb fast enough, and the gap has compounded since.

> **Note (will be replaced on filing):** the links currently point at issue drafts on the `to-toolbox` branch of [the fork](https://github.com/sdebruyn/dbt-fabric). They will be re-pointed at the actual upstream tickets once filed.

### `microsoft/dbt-fabric` — 20 issues

- [#01 — `varchar(8000)` silently truncates long-text string columns](https://github.com/sdebruyn/dbt-fabric/blob/to-toolbox/_toolbox/upstream_issues/dbt-fabric/01-varchar-8000-silent-truncation.md)
- [#02 — Case-sensitive Fabric Warehouses broken (missing `_make_match_kwargs` override)](https://github.com/sdebruyn/dbt-fabric/blob/to-toolbox/_toolbox/upstream_issues/dbt-fabric/02-case-sensitive-dwh-broken.md)
- [#03 — `apply_grants` re-issues GRANTs on every run; query misses Entra-principal grants](https://github.com/sdebruyn/dbt-fabric/blob/to-toolbox/_toolbox/upstream_issues/dbt-fabric/03-apply-grants-misses-entra-principals.md)
- [#04 — Pre/post hooks fail because dbt-adapters' default `run_hooks` emits `commit;`](https://github.com/sdebruyn/dbt-fabric/blob/to-toolbox/_toolbox/upstream_issues/dbt-fabric/04-pre-post-hooks-fail-with-commit.md)
- [#05 — CTAS via `EXEC('...')` silently breaks on embedded apostrophes](https://github.com/sdebruyn/dbt-fabric/blob/to-toolbox/_toolbox/upstream_issues/dbt-fabric/05-exec-ctas-wrapper-breaks-on-apostrophes.md)
- [#06 — `get_response` returns hardcoded `"OK"`, discards cursor messages + statement IDs](https://github.com/sdebruyn/dbt-fabric/blob/to-toolbox/_toolbox/upstream_issues/dbt-fabric/06-get-response-drops-warnings-and-statement-id.md)
- [#07 — `FabricAdapter.quote()` doesn't escape `]` — T-SQL injection vector](https://github.com/sdebruyn/dbt-fabric/blob/to-toolbox/_toolbox/upstream_issues/dbt-fabric/07-identifier-quoting-not-escaped.md)
- [#08 — `pyodbc` pooling silently disabled; the right fix is landing the `mssql-python` PR](https://github.com/sdebruyn/dbt-fabric/blob/to-toolbox/_toolbox/upstream_issues/dbt-fabric/08-pyodbc-pooling-silently-disabled.md)
- [#09 — `fabric__get_use_database_sql` emits invalid `USE [None];` from `drop_schema_named`](https://github.com/sdebruyn/dbt-fabric/blob/to-toolbox/_toolbox/upstream_issues/dbt-fabric/09-use-none-emitted-when-database-is-none.md)
- [#10 — Incremental `--full-refresh` drop-then-recreate risks data loss on creation failure](https://github.com/sdebruyn/dbt-fabric/blob/to-toolbox/_toolbox/upstream_issues/dbt-fabric/10-incremental-full-refresh-data-loss-risk.md)
- [#11 — `fabric__get_incremental_microbatch_sql` ignores `unique_key`](https://github.com/sdebruyn/dbt-fabric/blob/to-toolbox/_toolbox/upstream_issues/dbt-fabric/11-microbatch-ignores-unique-key.md)
- [#12 — Custom `fabric__snapshot_merge_sql` UPDATE+INSERT instead of native MERGE](https://github.com/sdebruyn/dbt-fabric/blob/to-toolbox/_toolbox/upstream_issues/dbt-fabric/12-snapshot-merge-uses-update-plus-insert.md)
- [#13 — `delete_warehouse_snapshot` is a `return True` stub](https://github.com/sdebruyn/dbt-fabric/blob/to-toolbox/_toolbox/upstream_issues/dbt-fabric/13-delete-warehouse-snapshot-is-noop-stub.md)
- [#14 — `apply_label` macro emits debug `log()` on every call; should use `query_header`](https://github.com/sdebruyn/dbt-fabric/blob/to-toolbox/_toolbox/upstream_issues/dbt-fabric/14-apply-label-emits-debug-log-on-every-call.md)
- [#15 — `check_for_nested_cte` macro parses SQL in Jinja (categorically wrong)](https://github.com/sdebruyn/dbt-fabric/blob/to-toolbox/_toolbox/upstream_issues/dbt-fabric/15-check-for-nested-cte-false-positives.md)
- [#16 — PR #315 `login_timeout=getattr(...)` is a no-op on every call site](https://github.com/sdebruyn/dbt-fabric/blob/to-toolbox/_toolbox/upstream_issues/dbt-fabric/16-login-timeout-parameter-is-noop.md)
- [#17 — Warehouse snapshots coupled to `atexit` + `open()` should be a Jinja macro](https://github.com/sdebruyn/dbt-fabric/blob/to-toolbox/_toolbox/upstream_issues/dbt-fabric/17-warehouse-snapshots-via-atexit-and-connection-lifecycle.md)
- [#18 — Adapter-private `delete_condition` / `delete_not_matched_by_source` on `incremental`](https://github.com/sdebruyn/dbt-fabric/blob/to-toolbox/_toolbox/upstream_issues/dbt-fabric/18-incremental-private-config-keys.md)
- [#19 — v1.9.10 retry wrapper at wrong layer (use `add_query`'s `retryable_exceptions`)](https://github.com/sdebruyn/dbt-fabric/blob/to-toolbox/_toolbox/upstream_issues/dbt-fabric/19-list-relations-retry-at-wrong-layer.md)
- [#20 — Module-level `_TOKEN` global — thread-safety and lifecycle issues](https://github.com/sdebruyn/dbt-fabric/blob/to-toolbox/_toolbox/upstream_issues/dbt-fabric/20-module-level-token-global.md)

### `microsoft/dbt-fabricspark` — 8 issues

- [#01 — Six `__exit__` methods return `True` (silent exception swallowing)](https://github.com/sdebruyn/dbt-fabric/blob/to-toolbox/_toolbox/upstream_issues/dbt-fabricspark/01-exit-methods-return-true-swallow-exceptions.md)
- [#02 — Hardcoded `expires_on = 1845972874` (year 2028) bypasses token refresh](https://github.com/sdebruyn/dbt-fabric/blob/to-toolbox/_toolbox/upstream_issues/dbt-fabricspark/02-hardcoded-2028-token-expiry.md)
- [#04 — `_getLivySQL`: `re.DOTALL` passed as positional `count` caps comment-stripping at 16](https://github.com/sdebruyn/dbt-fabric/blob/to-toolbox/_toolbox/upstream_issues/dbt-fabricspark/04-getlivysql-regex-bug.md)
- [#06 — Livy session cleanup bypasses dbt's `close()` lifecycle and uses `atexit`](https://github.com/sdebruyn/dbt-fabric/blob/to-toolbox/_toolbox/upstream_issues/dbt-fabricspark/06-atexit-handlers-leak-livy-sessions.md)
- [#07 — Dead Thrift exception handler from dbt-spark ancestry](https://github.com/sdebruyn/dbt-fabric/blob/to-toolbox/_toolbox/upstream_issues/dbt-fabricspark/07-thrift-dead-code.md)
- [#08 — Proposal: inherit from `dbt-spark` instead of being a standalone `SQLAdapter`](https://github.com/sdebruyn/dbt-fabric/blob/to-toolbox/_toolbox/upstream_issues/dbt-fabricspark/08-inherit-from-dbt-spark.md)
- [#09 — `botocore`/`boto3` DEBUG logging at module import time](https://github.com/sdebruyn/dbt-fabric/blob/to-toolbox/_toolbox/upstream_issues/dbt-fabricspark/09-aws-logging-debug-at-import.md)
- [#10 — `_parse_retry_after` duplicated 4× with deprecated `datetime.utcnow()`](https://github.com/sdebruyn/dbt-fabric/blob/to-toolbox/_toolbox/upstream_issues/dbt-fabricspark/10-parse-retry-after-duplicated.md)

### The pattern behind them

Several of these issues are recent PRs that reinvent a dbt-native primitive that already does the job, with PR descriptions that read as AI-generated. AI raises the floor on output volume; it doesn't raise the floor on judgement, and judgement is what review is for. I use AI heavily in [the fork](https://github.com/sdebruyn/dbt-fabric) — the problem here is the missing review step, not the tool.

The structural cause is that Microsoft has staffed this adapter as a sideline of a product role, not as an engineering project: no second pair of eyes on PRs, no dbt-domain technical lead. PyPI ownership reflects this — both packages are published under a personal account rather than a Microsoft organisational identity (compare `azure-core`, `azure-identity`, owned by `Microsoft Corporation <azpysdkhelp@microsoft.com>`). The fix is to put the adapter somewhere it can get sustained engineering attention and community review, with package ownership at the organisational level.

---

## Why this stays maintainable long-term

The maintenance cost of a dbt adapter scales with two things: how much you reimplement that dbt's ecosystem already gives you, and how many private mechanisms you have to keep in sync with dbt-core across releases. The architecture here keeps both close to zero.

**The Lakehouse adapter inherits from [`dbt-spark`](https://github.com/dbt-labs/dbt-adapters/tree/main/dbt-spark).** `dbt-spark` ships the Spark materializations, incremental strategies, Spark-aware column type handling, constraint handling, the Spark Python-model API, and a `SparkAdapter` base class. Spark-based adapters inherit from it and write only the parts specific to their engine — [`dbt-databricks`](https://github.com/databricks/dbt-databricks) does this.

`microsoft/dbt-fabricspark` doesn't. It's a standalone `SQLAdapter`, so every macro, materialization, type rule, incremental strategy, and Python-model path has to be implemented and maintained by hand. Every dbt-spark release silently widens the gap. Python's [multiple inheritance](https://docs.python.org/3/tutorial/classes.html#multiple-inheritance) lets the FabricSpark adapter extend `SparkAdapter` *and* a shared `BaseFabricAdapter` at the same time, getting the dbt-spark machinery and the cross-adapter Fabric code in one class.

**One auth stack, one Fabric API client, and one Livy session layer across both adapters.** Auth, Fabric REST API access, workspace resolution, profile validation, and Livy session handling are the same problem on both engines — the Lakehouse runs everything through Livy, and the Data Warehouse needs the same Livy machinery for Python models.

`microsoft/dbt-fabric` and `microsoft/dbt-fabricspark` each maintain their own token logic, API client, workspace resolution, and profile validation, and they're already out of sync. The DW adapter uses `workspace_id` / `workspace_name` / `access_token` (snake_case). The Lakehouse adapter uses `workspaceid` / `lakehouseid` / `accessToken` (camelCase). The default auth method differs (`ActiveDirectoryDefault` vs `CLI`). A user running both can't share a profile structure. Every auth-related change has to be implemented twice.

This contribution has one [`FabricTokenProvider`](https://dbt-fabric.debruyn.dev/authentication/) covering all 11 auth methods for both adapter types. One `FabricApiClient` for workspaces, warehouses, lakehouses, Livy, and snapshots. One Python-model submission path. One profile schema. A bug fix is a one-place change.

```
BaseFabricCredentials → FabricCredentials (T-SQL) / FabricSparkCredentials (Spark)
BaseFabricConnectionManager → FabricConnectionManager (mssql-python) / FabricSparkConnectionManager (Livy)
BaseFabricAdapter → FabricAdapter / FabricSparkAdapter (also extends SparkAdapter from dbt-spark)

Shared: FabricTokenProvider, FabricApiClient, PurviewClient + PurviewSync
```

**Test suite built on [`dbt-tests-adapter`](https://github.com/dbt-labs/dbt-adapters/tree/main/dbt-tests-adapter).** Every dbt-core minor ships new `Base*` test classes that codify what an adapter needs to do to be compatible. Bumping `dbt-tests-adapter` is how this adapter picks up coverage for new dbt-core features automatically. About 430 adapter test classes here plus an extra ~110 community-package tests, all running against real Fabric. PRs run on Python 3.13; the full Python 3.11/3.12/3.13 matrix runs weekly.

**Capability declarations** (`SchemaMetadataByRelations`, `TableLastModifiedMetadata`) let dbt-core pick the optimised code paths on its own. Declaring a new capability when dbt-core adds one is a one-line change.

**Whole classes of silent-failure bugs eliminated by construction.** No module-level mutable state, so race conditions can't happen the way they do in the "What's broken" section. No `atexit` handlers, so cleanup follows dbt's documented connection-manager `close()` path. No exception swallowing, so errors propagate normally.

**Versioning and dependency hygiene.** Tight `dbt-core>=1.9.6,<1.13.0` range with an explicit upper bound. dbt-core upgrades follow a documented checklist in `CONTRIBUTING.md` (inventory new dispatchable macros, new adapter methods, new `Base*` test classes; only tag when the suite passes). Modern build stack (`hatchling` + `uv`) and Python typing (PEP 604 unions, no `typing.Union`/`Optional`).

---

## Everything goes through dbt's existing mechanisms

Every feature uses dbt's existing mechanisms instead of building parallel ones.

**Warehouse snapshots** are a macro `{{ create_or_update_fabric_warehouse_snapshot(name, description) }}`, callable from any Jinja context: [`on-run-start`/`on-run-end`](https://docs.getdbt.com/reference/project-configs/on-run-start-on-run-end), any [`post-hook`](https://docs.getdbt.com/reference/resource-configs/pre-hook-post-hook), or [`dbt run-operation`](https://docs.getdbt.com/reference/commands/run-operation). Dynamic names through Jinja, per-model snapshot timing through `post-hook`, environment-driven names through [`env_var()`](https://docs.getdbt.com/reference/dbt-jinja-functions/env_var).

**External tables** use dbt's [dispatch system](https://docs.getdbt.com/reference/dbt-jinja-functions/dispatch) to override the Fabric plugin of the [`dbt-external-tables`](https://github.com/dbt-labs/dbt-external-tables) package. External files become regular [`source()`](https://docs.getdbt.com/reference/dbt-jinja-functions/source) references that show up in the lineage graph, work with [source freshness](https://docs.getdbt.com/docs/build/sources#snapshotting-source-data-freshness), and respond to `dbt run-operation stage_external_sources`.

**`cluster_by`** is a standard [model config](https://docs.getdbt.com/reference/model-configs) option (`{{ config(cluster_by=['customer_id', 'order_date']) }}`), identical to Snowflake and BigQuery. Generated DDL is a clean `WITH (CLUSTER BY (...))` clause.

**Manual statistics** through model config (`{{ config(statistics=['col1', 'col2'], statistics_sample_percent=50) }}`), idempotent (`CREATE STATISTICS` first run, `UPDATE STATISTICS` after).

**Catalog statistics** populate [`dbt docs generate`](https://docs.getdbt.com/reference/commands/cmd-docs) output automatically via an override of the catalog query using `OBJECTPROPERTYEX(object_id, 'Cardinality')`.

**Microsoft Purview integration** is the macro `{{ purview_sync() }}`, callable from [`on-run-end`](https://docs.getdbt.com/reference/project-configs/on-run-start-on-run-end) or as a [`dbt run-operation`](https://docs.getdbt.com/reference/commands/run-operation). It respects [`persist_docs`](https://docs.getdbt.com/reference/resource-configs/persist_docs) (`persist_docs: false` skips the model, `relation: true, columns: false` syncs only what you asked for). Lineage is built from [`ref()`](https://docs.getdbt.com/reference/dbt-jinja-functions/ref) and [`source()`](https://docs.getdbt.com/reference/dbt-jinja-functions/source).

**Authentication** is a single `FabricTokenProvider` across both adapter types, configured through the standard `authentication` [profile](https://docs.getdbt.com/docs/core/connect-data-platform/profiles.yml) key. Workload identity uses the same top-level credential fields as every other method. Custom `TokenCredential` classes plug in via `credential_class` and `credential_kwargs`, the same way [`azure-identity`](https://learn.microsoft.com/en-us/python/api/azure-identity/azure.identity?view=azure-python) users already extend the SDK.

**Python models** use the standard [`model(dbt, spark)`](https://docs.getdbt.com/docs/build/python-models) API: same signature, same `dbt.ref()` / `dbt.source()` semantics, same `dbt.config.get()` pattern.

**PEP 249 cursor** parses Spark JSON results into standard Python types via a [PEP 249](https://peps.python.org/pep-0249/) compatible cursor.

**Community packages.** Adapter-specific override macros via [dispatch](https://docs.getdbt.com/reference/dbt-jinja-functions/dispatch) for every macro that breaks on T-SQL or Spark, with integration tests on every PR: dbt-utils (1.3.3), dbt-date (0.17.2), dbt-codegen (0.14.1), dbt-expectations (0.10.10), dbt-audit-helper (0.13.0), dbt-external-tables (0.11.0), dbt-profiler (1.0.0), dbt-artifacts (2.10.1, Lakehouse only), dbt-project-evaluator (1.2.4, Lakehouse only).
