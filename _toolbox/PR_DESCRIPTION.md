# Contribute `dbt-fabric` to the Fabric Toolbox

This PR adds `tools/dbt-fabric/`: one dbt adapter for both Microsoft Fabric compute engines (Data Warehouse and Lakehouse) in a single Python package.

I wrote most of the code that's now in [`microsoft/dbt-fabric`](https://github.com/microsoft/dbt-fabric). When Microsoft adopted the repository I kept maintaining a fork because customers were asking for things the official repo wasn't shipping. That fork ([`dbt-fabric-samdebruyn`](https://pypi.org/project/dbt-fabric-samdebruyn/) on PyPI) is what multiple organizations are running in production today.

I'm bringing it to the toolbox because the toolbox's multi-contributor model — the Fabric product team, the CAT team, and the community sharing maintenance — fits a dbt adapter better than a single-maintainer setup does. More co-owners, more reviewers, more eyes on PRs. The dbt ecosystem also moves quickly — new dbt-core minors, new community-package releases, new [`dbt-tests-adapter`](https://github.com/dbt-labs/dbt-adapters/tree/main/dbt-tests-adapter) `Base*` classes every cycle — and a shared codebase under the toolbox is better positioned to keep up with that cadence than any individual maintainer can be.

---

## What this gives users today

**One `pip install dbt-fabric` and both Fabric engines work.** No separate `dbt-fabricspark` package to manage, no system ODBC driver to install: the bundled [`mssql-python`](https://github.com/microsoft/mssql-python) driver handles the Data Warehouse side and ships with ODBC Driver 18 + unixODBC inside the wheel. That alone removes the most common installation hurdle on macOS and in containers, where pulling the right ODBC driver is the step new users get stuck on most often.

On top of that, a long list of features the official adapters don't ship:

**[Microsoft Purview](https://learn.microsoft.com/en-us/purview/) integration via API.** A `{{ purview_sync() }}` macro that pushes model and column documentation, plus dbt's [`ref()`](https://docs.getdbt.com/reference/dbt-jinja-functions/ref) and [`source()`](https://docs.getdbt.com/reference/dbt-jinja-functions/source) lineage, directly into Purview through the REST API. [`persist_docs`](https://docs.getdbt.com/reference/resource-configs/persist_docs)-aware: models marked `persist_docs: false` are skipped, granular `relation: true, columns: false` only syncs what you asked for. No Purview scan configuration needed on the user side.

**[Python models](https://docs.getdbt.com/docs/build/python-models) on both engines.** Standard `model(dbt, spark)` API with PySpark on both the Data Warehouse and the Lakehouse sides, using the same signature and semantics every dbt-spark user already knows. `microsoft/dbt-fabric` doesn't support Python models at all. `microsoft/dbt-fabricspark` ships a Python-model path, but only on its own; the Data Warehouse engine has no Python-model story upstream.

**Community packages made compatible with Fabric, and continuously tested to keep them that way.** Nine popular dbt community packages — [dbt-utils](https://github.com/dbt-labs/dbt-utils), [dbt-date](https://github.com/godatadriven/dbt-date), [dbt-codegen](https://github.com/dbt-labs/dbt-codegen), [dbt-expectations](https://github.com/metaplane/dbt-expectations), [dbt-audit-helper](https://github.com/dbt-labs/dbt-audit-helper), [dbt-external-tables](https://github.com/dbt-labs/dbt-external-tables), [dbt-profiler](https://github.com/data-mie/dbt-profiler), [dbt-artifacts](https://github.com/brooklyn-data/dbt_artifacts), and [dbt-project-evaluator](https://github.com/dbt-labs/dbt-project-evaluator) — don't fully work on Fabric out of the box. They ship Postgres- or Snowflake-flavoured macros that fail on Fabric's T-SQL or Spark dialects. This contribution writes the adapter-specific overrides through dbt's [dispatch](https://docs.getdbt.com/reference/dbt-jinja-functions/dispatch) system, with per-package compatibility documentation listing which macros work, which don't, and the exact version that was validated. Integration tests then run against each package on real Fabric infrastructure on every PR — that's what keeps the compatibility honest as both Fabric and the packages release new versions. Neither official adapter ships compatibility overrides or tests against any of these packages.

And the rest:

- Warehouse snapshots as a callable Jinja macro (`{{ create_or_update_fabric_warehouse_snapshot(...) }}`) usable from [`on-run-start`/`on-run-end`](https://docs.getdbt.com/reference/project-configs/on-run-start-on-run-end), any [`post-hook`](https://docs.getdbt.com/reference/resource-configs/pre-hook-post-hook), or [`dbt run-operation`](https://docs.getdbt.com/reference/commands/run-operation).
- [`dbt-external-tables`](https://github.com/dbt-labs/dbt-external-tables) compatibility via dispatch, so `OPENROWSET`-backed files are regular [`source()`](https://docs.getdbt.com/reference/dbt-jinja-functions/source) references that show up in the lineage graph and work with `dbt run-operation stage_external_sources`.
- [`cluster_by`](https://docs.getdbt.com/reference/resource-configs/snowflake-configs#using-cluster_by) as a standard model config option, identical to Snowflake and BigQuery.
- [Manual statistics as model config](https://dbt-fabric.debruyn.dev/statistics/) — declarative, no post-hook tricks.
- Catalog statistics in [`dbt docs generate`](https://docs.getdbt.com/reference/commands/cmd-docs) output, automatically.
- [Functions](https://docs.getdbt.com/docs/build/functions) (dbt-core 1.11 scalar functions) on both engines.
- [Workload identity](https://learn.microsoft.com/en-us/entra/workload-id/workload-identity-federation) (federated OIDC for CI/CD pipelines).
- 11 authentication methods through standard dbt [profile keys](https://docs.getdbt.com/docs/core/connect-data-platform/profiles.yml), plus custom [`TokenCredential`](https://learn.microsoft.com/en-us/python/api/azure-core/azure.core.credentials.tokencredential?view=azure-python) classes.
- One shared `FabricTokenProvider` covering both adapter types, so the same profile structure works for DW and Lakehouse.
- [Auto host-resolution from the workspace name](https://dbt-fabric.debruyn.dev/configuration/#host) — no hardcoded SQL endpoint per environment.
- A PEP 249–compliant cursor for Spark JSON results, so dbt talks to the Lakehouse exactly like any other database.

Every PR runs against real Fabric, every release ships after the full integration suite has gone green, and all the bugs documented in the next section are already fixed.

---

## What's broken in the official adapters

I tried contributing some of these fixes back to `microsoft/dbt-fabric` first; most didn't land. The fork carried what the upstream couldn't absorb fast enough, and the gap has compounded since.

I've filed [20 issues against `microsoft/dbt-fabric`](#) and [8 against `microsoft/dbt-fabricspark`](#). Each ticket has its own reproduction, evidence, and suggested fix.

> **Note (will be replaced on filing):** the links currently point at issue drafts on the `to-toolbox` branch of [the fork](https://github.com/sdebruyn/dbt-fabric). They will be re-pointed at the actual upstream tickets once filed against `microsoft/dbt-fabric` and `microsoft/dbt-fabricspark`.

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

Looking across the list: PR #315 ships a parameter that does nothing. The v1.9.10 retry wrapper adds an adapter-method retry layer where `add_query`'s built-in `retryable_exceptions` was the right hook. The v1.9.10 `delete_condition` config invents adapter-private knobs on a dbt-core [materialization](https://docs.getdbt.com/docs/build/materializations). The v1.10.0 `atexit` warehouse snapshots reinvent [`on-run-end`](https://docs.getdbt.com/reference/project-configs/on-run-start-on-run-end). Each is code that *looks* sophisticated but ignores a dbt-native primitive that already does the job. Combined with PR descriptions that read as AI-generated, the symptom is clear: AI-assisted code is landing without review from someone with the dbt expertise to spot that the wheel was already there.

To be clear: I'm strongly *in favour* of AI-assisted development. Used well, it lets a small team keep up with the dbt-core release cadence, catch repetitive issues across both adapters at once, and ship fixes faster than a human-only workflow ever could. I use it heavily in [the fork](https://github.com/sdebruyn/dbt-fabric). The problem isn't that AI was involved. The problem is that the suggestions weren't filtered through someone who knows where dbt's extension points already live — so they landed as parallel mechanisms, dead parameters, and Fabric-only knobs instead of fixes that fit the ecosystem. AI raises the floor on output volume; it doesn't raise the floor on judgement, and judgement is what review is for.

A related factor is the size of the upstream CI matrices, which is part of what lets the per-PR drift above accumulate. A broader matrix and end-to-end runs against real Fabric on every PR would catch most of these earlier — which is something a multi-contributor codebase under the toolbox is well positioned to set up.

The structural cause is that Microsoft has staffed this adapter as a sideline of an existing product role, not as an engineering project. There's no second pair of eyes on PRs and no dbt-domain technical lead in the loop. Even the PyPI ownership reflects this: both `dbt-fabric` and `dbt-fabricspark` are published under a personal account rather than under a Microsoft organisational identity. Compare with the Azure SDK packages (`azure-core`, `azure-identity`) which list `Microsoft Corporation <azpysdkhelp@microsoft.com>` and are uploaded under a shared corporate account. If the individual PyPI account becomes unavailable for any reason — employee transition, account compromise, vacation during a security incident — Microsoft has no direct path to push a fix. Customers running these packages in production have no escalation route within Microsoft beyond filing a GitHub issue. This isn't about the individual maintainer — swapping one Microsoft employee for another doesn't fix it. The fix is to put the adapter somewhere it can get sustained engineering attention and community review, with package ownership at the organisational level. That's what this PR proposes.

---

## Why this stays maintainable long-term

The maintenance cost of a dbt adapter scales with two things: how much you reimplement that dbt's ecosystem already gives you, and how many private mechanisms you have to keep in sync with dbt-core across releases. The architecture here is designed to keep both as close to zero as possible.

**Stand on the shoulders of giants: the Lakehouse adapter inherits from [`dbt-spark`](https://github.com/dbt-labs/dbt-adapters/tree/main/dbt-spark).**

`dbt-spark` is years of refinement and battle-testing. The package ships the [Spark materializations](https://github.com/dbt-labs/dbt-adapters/tree/main/dbt-spark/src/dbt/include/spark/macros/materializations) (table, view, incremental, snapshot, materialized view), all the Spark-flavoured [incremental strategies](https://docs.getdbt.com/docs/build/incremental-strategy) (`merge`, `append`, `insert_overwrite`, `microbatch`), Spark-aware column type handling, constraint handling, the Spark [Python model](https://docs.getdbt.com/docs/build/python-models) API, and an opinionated `SparkAdapter` base class that codifies how a Spark engine plugs into dbt. The whole point of the package is to be inherited from. Spark-based adapters are supposed to write the parts that are specific to their engine — connection layer, auth, engine quirks — and get the rest for free.

This isn't a theoretical pattern. [`dbt-databricks`](https://github.com/databricks/dbt-databricks), Databricks' own production adapter, depends on `dbt-spark>=1.10.0,<1.11.0` in [its `pyproject.toml`](https://github.com/databricks/dbt-databricks/blob/main/pyproject.toml) and declares `class DatabricksAdapter(SparkAdapter):` in [`dbt/adapters/databricks/impl.py:230`](https://github.com/databricks/dbt-databricks/blob/main/dbt/adapters/databricks/impl.py). Databricks doesn't reimplement Spark adapter behaviour because that's not where their value lies — their value is in the Databricks-specific extensions on top. Whatever Microsoft's competitive position on Databricks is, the engineering pattern Databricks uses for *their* dbt adapter is the one to copy: build on top of the shared foundation, ship only the platform-specific bits.

`microsoft/dbt-fabricspark` doesn't have a `dbt-spark` dependency. It's a standalone `SQLAdapter`. So every single one of those hundreds of macros, every materialization, every type-handling rule, every incremental strategy, every Python-model path has to be implemented and maintained by hand. Every dbt-spark release that ships a fix or a new feature silently widens the gap. Every new dbt-core minor that adds a `Base*` test class for Spark needs a manual port of whatever dbt-spark did to satisfy it. The maintenance treadmill compounds: a year of dbt-spark improvements that this contribution inherits for free is a year of work upstream has to do manually (and largely doesn't), which is exactly why a comparable feature set isn't there.

The reference Spark adapter inherits from `dbt-spark`. Databricks inherits from `dbt-spark`. There is no engineering case for the standalone approach — it *guarantees* ongoing maintenance pain on `microsoft/dbt-fabricspark` regardless of who maintains it. Python's [multiple inheritance](https://docs.python.org/3/tutorial/classes.html#multiple-inheritance) lets the FabricSpark adapter extend `SparkAdapter` *and* a shared `BaseFabricAdapter` at the same time, getting the dbt-spark machinery and the cross-adapter Fabric code in one class.

**One auth stack, one Fabric API client, and one Livy session layer across both adapters, instead of two parallel codebases.** Auth, Fabric REST API access, workspace resolution, profile validation, and Livy session handling are the same problem on both Data Warehouse and Lakehouse — the Lakehouse runs everything through Livy, and the Data Warehouse needs the same Livy machinery for [Python models](https://docs.getdbt.com/docs/build/python-models).

`microsoft/dbt-fabric` and `microsoft/dbt-fabricspark` each maintain their own token acquisition logic, their own Fabric API client, their own workspace resolution, their own profile validation, and they're already out of sync. The DW adapter uses `workspace_id` / `workspace_name` / `access_token` (snake_case, dbt-conventional). The Lakehouse adapter uses `workspaceid` / `lakehouseid` / `accessToken` (camelCase, different defaults). The default auth method differs (`ActiveDirectoryDefault` vs `CLI`). A user running both can't share a profile structure. A bug fixed in one repo's token-acquisition path doesn't carry over to the other. Every new auth method has to be implemented twice. Every Fabric API endpoint that gets added or changed has to be wrapped twice. This is the same compounding cost as the dbt-spark situation — two maintenance treadmills running in parallel instead of one shared codebase.

This contribution has one [`FabricTokenProvider`](https://dbt-fabric.debruyn.dev/authentication/) covering all 11 auth methods for both adapter types. One `FabricApiClient` for workspaces, warehouses, lakehouses, Livy, and snapshots. One Python-model submission path. One profile schema, derived from one base. A bug fix is a one-place change. New auth methods land for both adapters at once.

```
BaseFabricCredentials → FabricCredentials (T-SQL) / FabricSparkCredentials (Spark)
BaseFabricConnectionManager → FabricConnectionManager (mssql-python) / FabricSparkConnectionManager (Livy)
BaseFabricAdapter → FabricAdapter / FabricSparkAdapter (also extends SparkAdapter from dbt-spark)

Shared: FabricTokenProvider, FabricApiClient, PurviewClient + PurviewSync
```

**Test suite built on [`dbt-tests-adapter`](https://github.com/dbt-labs/dbt-adapters/tree/main/dbt-tests-adapter), dbt's official adapter test harness.** Every dbt-core minor ships new `Base*` test classes that codify what an adapter needs to do to be compatible. Bumping `dbt-tests-adapter` is how this adapter picks up coverage for new dbt-core features automatically. Without it, "compatibility with dbt-core 1.12" is a manual research project rather than a CI signal. About 430 adapter test classes here (vs ~125 for `microsoft/dbt-fabric` and ~150 for `microsoft/dbt-fabricspark`), plus an extra ~110 community-package tests, all running against real Fabric infrastructure. PRs run on Python 3.13; the full Python 3.11/3.12/3.13 matrix runs on a weekly schedule.

**Capability declarations** (`SchemaMetadataByRelations`, `TableLastModifiedMetadata`) let dbt-core pick the optimised code paths on its own. When dbt-core adds a new capability in a future release, declaring it is a one-line change. The alternative — hooking into private dbt-core internals — breaks every time dbt-core touches them, which is exactly the maintenance treadmill `dbt-tests-adapter` and capabilities exist to eliminate.

**Whole classes of silent-failure bugs eliminated by construction.** No module-level mutable state, so race conditions can't happen the way they do in the "What's broken" section. No `atexit` handlers, so cleanup follows dbt's documented connection-manager `close()` path. No exception swallowing, so errors propagate normally. The code paths to defend against future regressions are smaller because the underlying mistakes aren't possible to make.

**Versioning and dependency hygiene that signal what's actually tested.** Tight `dbt-core>=1.9.6,<1.13.0` range with an explicit upper bound. dbt-core upgrades follow a documented checklist in `CONTRIBUTING.md` ("Upgrading dbt-core support") — inventory new dispatchable macros, new adapter methods, new `Base*` test classes, record lessons learned, only tag when the suite passes. Modern build stack (`hatchling` + `uv`) for faster CI and reproducible installs. Modern Python typing (PEP 604 unions, no `typing.Union`/`Optional`), consistent snake_case. None of these individually shift the maintenance equation by much; together they're the difference between a codebase a new contributor can land a PR in and one they walk away from.

---

## Everything goes through dbt's existing mechanisms

The one principle running through this whole adapter: every feature uses dbt's existing mechanisms instead of building parallel ones. Examples.

**Warehouse snapshots** are a macro `{{ create_or_update_fabric_warehouse_snapshot(name, description) }}`, callable from any Jinja context: [`on-run-start` / `on-run-end`](https://docs.getdbt.com/reference/project-configs/on-run-start-on-run-end), any [`post-hook`](https://docs.getdbt.com/reference/resource-configs/pre-hook-post-hook), or [`dbt run-operation`](https://docs.getdbt.com/reference/commands/run-operation). Because it's a macro, you get dynamic names through Jinja, per-model snapshot timing through `post-hook`, environment-driven names through [`env_var()`](https://docs.getdbt.com/reference/dbt-jinja-functions/env_var). Same mental model Snowflake, BigQuery, and Postgres users have used for years.

**External tables** go through dbt's [dispatch system](https://docs.getdbt.com/reference/dbt-jinja-functions/dispatch) to override the Fabric plugin of the [`dbt-external-tables`](https://github.com/dbt-labs/dbt-external-tables) package, instead of upstream's standalone `openrowset_source()` macro. The result: external files are regular [`source()`](https://docs.getdbt.com/reference/dbt-jinja-functions/source) references, `{{ source('my_external', 'sales') }}`. They show up in the lineage graph, [source freshness](https://docs.getdbt.com/docs/build/sources#snapshotting-source-data-freshness) works out of the box, and `dbt run-operation stage_external_sources` is the standard interface.

**`cluster_by`** is a standard [model config](https://docs.getdbt.com/reference/model-configs) option (`{{ config(cluster_by=['customer_id', 'order_date']) }}`), identical to Snowflake and BigQuery. Works on tables, on [incremental models](https://docs.getdbt.com/docs/build/incremental-models), and on models with [contract enforcement](https://docs.getdbt.com/reference/resource-configs/contract). Generated DDL is a clean `WITH (CLUSTER BY (...))` clause, no post-hook tricks.

**Manual statistics** through model config (`{{ config(statistics=['col1', 'col2'], statistics_sample_percent=50) }}`), idempotent (`CREATE STATISTICS` first run, `UPDATE STATISTICS` after).

**Catalog statistics** show up automatically in [`dbt docs generate`](https://docs.getdbt.com/reference/commands/cmd-docs) output. Implemented as an override of the catalog query using `OBJECTPROPERTYEX(object_id, 'Cardinality')`. No config, no extra commands.

**Microsoft Purview integration** is the macro `{{ purview_sync() }}`, callable from [`on-run-end`](https://docs.getdbt.com/reference/project-configs/on-run-start-on-run-end) or as a [`dbt run-operation`](https://docs.getdbt.com/reference/commands/run-operation). It respects dbt's standard [`persist_docs`](https://docs.getdbt.com/reference/resource-configs/persist_docs) configuration: `persist_docs: false` skips the model, `relation: true, columns: false` syncs only what you asked for. Lineage is built from [`ref()`](https://docs.getdbt.com/reference/dbt-jinja-functions/ref) and [`source()`](https://docs.getdbt.com/reference/dbt-jinja-functions/source). End users don't have to learn a separate model.

**Authentication** is a single `FabricTokenProvider` across both adapter types. Configuration goes through the standard `authentication` [profile](https://docs.getdbt.com/docs/core/connect-data-platform/profiles.yml) key. Workload identity uses the same top-level credential fields as every other method, no separate profile section. Custom `TokenCredential` classes plug in via `credential_class` and `credential_kwargs`, the same way [`azure-identity`](https://learn.microsoft.com/en-us/python/api/azure-identity/azure.identity?view=azure-python) users already extend the SDK.

**Python models** use the standard [`model(dbt, spark)`](https://docs.getdbt.com/docs/build/python-models) API. Same signature, same `dbt.ref()` / `dbt.source()` semantics, same `dbt.config.get()` pattern. Developer experience matches dbt-spark exactly.

**Livy session reuse** is shared between both adapters too. Python models on the Data Warehouse run through the same Livy machinery as everything on the Lakehouse, so the warm-session logic in `BaseFabricAdapter` benefits both — one implementation, one place to fix bugs, one place to extend.

**PEP 249 cursor** parses Spark JSON results into standard Python types via a [PEP 249](https://peps.python.org/pep-0249/) compatible cursor, so dbt talks to the Lakehouse exactly like any other database.

**Limitations documentation** lists per platform (Data Warehouse, Lakehouse) which dbt features don't work and why, organized into "Unsupported dbt features", "SQL dialect limitations", "DDL limitations", and "Incremental model limitations". Every limitation has either a workaround or a reference to the underlying Fabric constraint. Not a feature in itself — a diagnostic signal that the maintainer knows the engines well enough to map the gaps honestly.

**Community packages** are made Fabric-compatible — adapter-specific override macros via [dispatch](https://docs.getdbt.com/reference/dbt-jinja-functions/dispatch) for every macro that breaks on T-SQL or Spark — and then continuously tested per-package: dbt-utils (1.3.3), dbt-date (0.17.2), dbt-codegen (0.14.1), dbt-expectations (0.10.10), dbt-audit-helper (0.13.0), dbt-external-tables (0.11.0), dbt-profiler (1.0.0), dbt-artifacts (2.10.1, Lakehouse only), dbt-project-evaluator (1.2.4, Lakehouse only). For each one, `docs/packages/<package>.md` lists which macros work, which don't, which tests run, and the tested version.
