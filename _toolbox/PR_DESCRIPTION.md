# Contribute `dbt-fabric` to the Fabric Toolbox

## TL;DR

This PR adds `tools/dbt-fabric/`: one dbt adapter for both Microsoft Fabric compute engines, Data Warehouse and Lakehouse, in a single Python package. I wrote most of the code that originally became `microsoft/dbt-fabric`, and I've been maintaining a fork ever since because customers needed features and stability the official repo wasn't shipping. The fork ([`dbt-fabric-samdebruyn`](https://pypi.org/project/dbt-fabric-samdebruyn/) on PyPI) is already running in production at multiple organizations. This PR is the obvious next step: bring it back to a place where it can be maintained jointly by the Fabric product team, the CAT team, and the community.

## Personal context and motivation

I wrote most of the code that's now in [`microsoft/dbt-fabric`](https://github.com/microsoft/dbt-fabric). When Microsoft adopted the repository I kept working on my fork because customers were asking for things the official repo wasn't shipping.

I'm not happy about the state of either Microsoft adapter today. I'm writing this as an invitation, not as an attack. Both repos need a serious reset, and I think the only way to do that is to bring the community back into the maintenance loop: Fabric product team, CAT team, and the people who've kept the fork alive for the last year.

### Who's actually running this?

At conferences and in one-on-one conversations, multiple customers have told me they switched from `microsoft/dbt-fabric` to my fork because it was the more stable option. That's not a sales pitch, it's just something I keep hearing. The interim PyPI package keeps getting adopted because there's demand for a dbt adapter for Fabric that actually works in production.

I'll attach a separate document listing organizations currently running this in production, with consent. For those that prefer not to be named, I'll describe them by sector and size.

### What this test suite has caught

The test suite I maintain is significantly broader than either of Microsoft's. It runs Python 3.11, 3.12, and 3.13 across dbt-core 1.9, 1.10, 1.11, and 1.12, on both engines, against real Fabric infrastructure. That breadth keeps catching bugs that are still present in the official adapters today.

So the test suite isn't just a regression net for whatever I add next. It's been finding production-impacting issues retroactively. I'll attach a separate document with 5–10 concrete examples: a short description of each bug, the fix in this fork, and the current status upstream (open issue / closed without a fix / never reported).

### Goal of this PR

So why this PR, beyond just moving code over? Three things the current situation doesn't have:

1. A predictable release cadence tied to dbt-core, with the versioning convention actually followed.
2. A maintenance model with explicit roles for Microsoft (product team and CAT team) and for community contributors.
3. A way to keep the customers who already migrated. They're not going to come back to something less stable than what they're running today.

---

## What does the current situation look like?

Everything below is verifiable on PyPI and GitHub at the time of writing.

### `microsoft/dbt-fabric` (Data Warehouse adapter)

- Latest release: v1.9.9 on 30 March 2026.
- The PyPI classifier list still says Python 3.8–3.11. No 3.12, no 3.13.
- The dependency is `dbt-core>=1.8.0` with no upper bound. So installing on any current dbt-core version is a gamble. A user on dbt-core 1.12 has no way to know whether `dbt-fabric==1.9.9` has been tested against it.
- No public evidence of integration tests on PRs.
- No multi-Python or multi-dbt-core test matrix.

### `microsoft/dbt-fabricspark` (Lakehouse adapter)

Five releases in seven days (10–17 May 2026):

| Version | Release date |
|---|---|
| v1.10.0 | 10 May 2026 |
| v1.10.1 | 11 May 2026 |
| v1.11.0 | 15 May 2026 |
| v1.12.0 | 17 May 2026 |
| v1.12.1 | 17 May 2026 |

The version numbers suggest dbt-core 1.10, 1.11, and 1.12 are all supported, but the PyPI manifest just says `dbt-core>=1.8.0` with no upper bound, and there's no public evidence of CI runs against the implied minors.

### What versioning is supposed to mean

In the dbt adapter ecosystem, `<adapter>==1.X.Y` is supposed to mean "tested and guaranteed against `dbt-core==1.X.*`". The reference adapters, Snowflake, Postgres, Spark, BigQuery, follow this strictly. A release only goes out once the matching dbt-core minor is actually covered by the test suite. Rapid version bumps without a visible test matrix per dbt-core minor break that contract. If you're running dbt-core 1.12 and you install `dbt-fabricspark==1.12.1`, you don't actually have a guarantee that this combination has been validated.

### Functions (dbt-core 1.11 scalar functions)

Functions, the dbt-core 1.11 scalar-function feature, are not supported in either official adapter. dbt-core 1.11 has been out for about six months. If you're using SQL UDFs in dbt on Snowflake or BigQuery and you want to do the same on Fabric, you can't.

---

## Concrete quality issues in the official adapters

This isn't a list of grievances. It's the evidence behind the claim that a reset is needed. Every item below has a file path, a line number, or a PR link, so you can verify any of it independently.

### Global mutable state in `microsoft/dbt-fabricspark`

Module-level and class-level globals hold authentication tokens, Livy session handles, connection managers, and relation configuration. See `singleton_livy.py` and `concurrent_livy.py`. The consequence: data races in multi-threaded dbt runs. dbt defaults to more than 1 thread. This contribution uses instance encapsulation throughout, no module-level mutable state.

### `atexit` handlers for session cleanup

Both `singleton_livy.py` and `concurrent_livy.py` register `atexit` handlers at module import time. Three problems with that. Handler execution order is undefined. Networking and logging may already be torn down by the time the handler runs. And the handler gets registered just by importing the module, even if no session was ever created. The high-concurrency variant adds a second `atexit` handler with a global `_active_sessions` set, which makes the global-mutable-state problem worse, not better. This contribution does all session lifecycle through dbt's standard connection-manager `close()` path.

### Exception swallowing

`LivySession.__exit__` (livysession.py:489–495) and `LivyCursor.__exit__` (livysession.py:855–859) both `return True`. That suppresses every exception raised inside any `with` block that uses these objects. Database errors, timeouts, `KeyboardInterrupt`, all silently dropped. This contribution propagates exceptions normally.

### Regex bug in SQL sanitization

`_getLivySQL()` passes `re.DOTALL` as the `count` argument to `re.sub` instead of `flags=re.DOTALL`. So instead of multiline matching, it silently caps comment-stripping to 16 replacements. Subtle, but production-affecting.

### Dead code and copy-paste artifacts

- Thrift exception handling in `connections.py:97–113` references `thrift_resp.status.errorMessage`. That's a pattern from dbt-spark, which talks to Apache Thrift. This adapter talks Livy over HTTP. The code path is dead.
- AWS logging config in `connections.py:39–46` sets `botocore` and `boto3` to DEBUG at import time. Inherited from a Spark/Databricks ancestor. There are no AWS dependencies in the package.
- A hardcoded 2028 timestamp in `livysession.py:194–198`: the `int_tests` auth path creates a token with `expires_on = 1845972874`, bypassing all token-refresh logic.
- `_parse_retry_after` is duplicated verbatim between `livysession.py` and `mlv_api.py`, both using the deprecated `datetime.utcnow()`.
- `get_headers()` has a `tokenPrint` parameter that logs the full bearer token when set to `True`. It's never called with `True`. Dead parameter, latent security risk.

### Inconsistent coding style

camelCase (`tokenPrint`, `accessToken`, `_submitLivyCode`, `_getLivySQL`) is mixed with snake_case all over the codebase. Pre-3.9 typing aliases (`Dict`, `List`, `Optional`, `Union`) are still in use, even though the package targets Python 3.13. These aren't aesthetic complaints. They're signals about review and refactor discipline.

### Inadequate review on `microsoft/dbt-fabric`

[PR #315](https://github.com/microsoft/dbt-fabric/pull/315) adds `timeout=getattr(credentials, "login_timeout", None)` to every `get_token()` call in the connection manager. This does nothing.

- `login_timeout` doesn't exist on `FabricCredentials`, so `getattr` always returns `None`.
- `get_token()` in `azure-identity` doesn't accept a `timeout` argument. It silently disappears into `**kwargs`.

The PR description for #315 looks AI-generated, with structured headers and numbered references. Code that does nothing should not be getting merged. The pattern says reviewer attention is thin, and that problem only gets worse as more low-signal changes accumulate.

The v1.9.10 release ([issue #362](https://github.com/microsoft/dbt-fabric/issues/362), May 2026) is a response to a real, well-documented user report: `list_<schema>` was taking 8–20 minutes when another dbt run was active on the same warehouse. The user is careful. They describe exactly what they observed (the metadata read hangs while another session is doing DDL) and explicitly call the rest hypothesis ("we have not been able to confirm the exact mechanism").

The fix that landed for this addresses the real complaint by duplicating something that's already in the same file. `FabricAdapter.list_relations_without_caching` got wrapped in a custom retry with exponential back-off. But `dbt-adapters` already has this. `SQLConnectionManager.add_query` takes `retryable_exceptions` and `retry_limit`. Two screens up in the same connection manager, the project's own `add_query` override is already calling it with `retry_limit=3` and `mssql_python.OperationalError` registered. Anyone reading the diff next to the existing code would notice. And the PR description follows the same AI-generated patterns as #315.

(The same release also adds a `close()` override that skips `ROLLBACK` on autocommit connections, attributed to pyodbc-level contention. I haven't measured pyodbc, so I'm not going to call that part wrong. I've only measured the `mssql-python` path: `rollback()` is ≤0.1 ms there under load, so there's nothing for me to port.)

### Warehouse snapshots via connection lifecycle hooks

The warehouse-snapshot feature in `microsoft/dbt-fabric` is implemented as hooks inside `open()` of the connection manager, plus `atexit` handlers. That couples a user-facing feature to Python runtime internals (`atexit`) and to connection-manager lifecycle methods that aren't designed as hook points. They're not part of dbt's stable adapter interface, and they can break across dbt-core releases. This contribution exposes warehouse snapshots as a Jinja macro you can call from `on-run-start` / `on-run-end`. That's the documented, supported way to do this kind of thing in dbt.

### Fabric-only config keys on the `incremental` materialization

The v1.9.10 release also extends the `merge` incremental strategy with two new model-level configs that the maintainers invented: `delete_condition` and `delete_not_matched_by_source`. You can see them in `dbt/include/fabric/macros/materializations/models/incremental/incremental.sql`, dispatched through a new `fabric__get_incremental_merge_sql` macro. Neither config exists in `dbt-core` or `dbt-adapters`. No other reference adapter (Snowflake, BigQuery, Postgres, Redshift, Spark) exposes anything equivalent.

Why does this matter? The `incremental` materialization is part of dbt's user-facing API contract. Its config keys are how thousands of models in production projects describe themselves. Extending it with adapter-private knobs has three consequences.

A model written for Fabric stops being portable. A user moving from Fabric to Snowflake (or back) has to rewrite the config block, even though the same merge-with-delete semantics could be done with a `post-hook` or with the standard `merge_update_columns` / `merge_exclude_columns` keys that dbt-core already has.

Validation has to be reimplemented in Jinja. The two new config keys come with three compile-time exception branches in the materialization to enforce that they only apply to `incremental_strategy: 'merge'` and that they're mutually exclusive. That logic wouldn't exist if the feature were a macro or a hook.

And it sets the precedent that Fabric needs its own knobs. The first adapter-private config on a stable materialization is the hardest one to push back on. After that, every next one is easier. This is how an adapter drifts from feeling dbt-native to feeling like a SQL wrapper with a parallel config language.

The general principle: extensions go in macros and hooks. They don't go on the materializations dbt-core ships. A maintainer who feels the pull to add `delete_condition` to `incremental` is signalling that they're thinking of the adapter as a standalone product, not as a citizen of the dbt ecosystem.

### Versioning-convention violation in `microsoft/dbt-fabricspark`

Five releases in one week: v1.10.0 → v1.10.1 → v1.11.0 → v1.12.0 → v1.12.1. The PyPI manifest just says `dbt-core>=1.8.0`. No upper bound. No minor-version mapping. That's the opposite of how the dbt ecosystem versions adapters. A customer can't tell which combination of `dbt-fabricspark` and `dbt-core` is actually safe. Version bumps without a visible test matrix per dbt-core minor look more like reputation management than a compatibility guarantee.

---

## How this contribution avoids these problems

Point by point.

- No module-level mutable state. Everything lives on instance-bound objects, managed through dbt's standard connection-manager `close()` path.
- No `atexit` handlers. Cleanup goes through the documented connection lifecycle.
- No exception swallowing. Errors propagate normally.
- Modern Python typing: PEP 604 union syntax (`X | Y`), no `typing.Union` or `typing.Optional` legacy imports.
- Consistent snake_case throughout.
- About 444 integration test classes (vs ~117 for `microsoft/dbt-fabric` and ~141 for `microsoft/dbt-fabricspark`, exact counts to be re-verified at submission). Run against real Fabric infrastructure.
- The test harness as a bug detector, not just a regression net. Because it's broader than both upstreams and runs continuously, it keeps surfacing bugs that the official adapters still have. The attached bug-fix list demonstrates this. For maintenance over years, a larger test net is the single most important precondition.
- Multi-Python CI matrix: 3.11, 3.12, 3.13.
- Multi-dbt-core CI matrix: each release is actually tested against the matching dbt-core minor.
- Systematic process for dbt-core upgrades, documented in `CONTRIBUTING.md` under "Upgrading dbt-core support". A version bump follows a checklist: inventory new dispatchable macros, new adapter methods, new `Base*` test classes, document lessons learned, and only tag when the suite passes.
- Warehouse snapshots through dbt's native hooks. Stable API, no runtime internals.
- Capability declarations (`SchemaMetadataByRelations`, `TableLastModifiedMetadata`) so dbt picks the optimized paths on its own without monkey-patching internals.
- Modern build stack: `hatchling` and `uv`. Faster and more reproducible than `setuptools` + `pip`.
- Versioning convention strictly followed: `dbt-fabric==1.X.Y` is tested and guaranteed against `dbt-core>=1.X,<1.(X+1)`.

---

## Everything goes through dbt's existing mechanisms

The one design principle running through this whole adapter: every feature uses dbt's existing mechanisms instead of building parallel ones. This isn't accidental. It comes from years of using dbt in production and knowing exactly where things hurt when an integration doesn't feel native.

Some examples.

### Warehouse snapshots — `on-run-start` / `on-run-end` / `post-hook`

A single macro: `{{ create_or_update_fabric_warehouse_snapshot(name, description) }}`. Callable from any Jinja context. Because it's a macro, you get a bunch of things for free. Dynamic snapshot names with Jinja: `'snapshot_' ~ modules.datetime.datetime.now().strftime('%Y%m%d')`. Per-model snapshot timing through `post-hook`. Environment-variable-driven names with `env_var()`. This is how Snowflake, BigQuery, and Postgres users have been orchestrating side effects in dbt for years. There's no new mental model.

### External tables — dbt's dispatch system + `{{ source() }}` lineage

Upstream goes with a standalone `openrowset_source()` macro that sits outside dbt's source system. This contribution uses dbt's [dispatch system](https://docs.getdbt.com/reference/dbt-jinja-functions/dispatch) to override the Fabric plugin of the `dbt-external-tables` package. The result: external files are modeled as regular sources, `{{ source('my_external', 'sales') }}`. They show up in the lineage graph. Freshness checking works out of the box. `dbt run-operation stage_external_sources` is the standard interface users of other warehouses already know.

### `cluster_by` — standard model config

```sql
{{ config(materialized='table', cluster_by=['customer_id', 'order_date']) }}
```

Syntactically identical to Snowflake and BigQuery. Works on tables, on incremental models, and on models with contract enforcement. The generated DDL is a clean `WITH (CLUSTER BY ([...]))` clause. No DDL injection. No post-hook tricks.

### Manual statistics — declarative model config

```sql
{{ config(statistics=['col1', 'col2'], statistics_sample_percent=50) }}
```

Idempotent: `CREATE STATISTICS` on the first run, `UPDATE STATISTICS` after that. The naming convention `dbt_stats__<md5_hash>` avoids collisions with Fabric's auto-generated `_WA_Sys_*` statistics. That's a detail you only think to add after you've debugged the collision in production.

### Catalog statistics — zero-config enrichment

Row counts show up automatically in `dbt docs generate` output. No configuration required. It's implemented as a clean override of the catalog query using `OBJECTPROPERTYEX(object_id, 'Cardinality')`. No extra macros. No extra commands.

### Microsoft Purview integration — `persist_docs`-aware

The macro `{{ purview_sync() }}` is callable from `on-run-end` or as a `dbt run-operation`. It respects dbt's standard [`persist_docs`](https://docs.getdbt.com/reference/resource-configs/persist_docs) configuration. Models with `persist_docs: false` are skipped entirely. Models with granular `relation: true, columns: false` only get the corresponding parts synced. Lineage is built from dbt's `ref()` and `source()` graph. End users don't have to learn a separate mental model. It's just dbt.

### Authentication — extends dbt's standard credential pattern

A single `FabricTokenProvider` covers both adapter types. Everything goes through the standard `authentication` profile key. Workload identity (federated OIDC) is configured with the same top-level credential fields as every other method, there's no separate profile section. Custom `TokenCredential` classes plug in via `credential_class` and `credential_kwargs`, which is exactly how `azure-identity` users already extend the SDK.

### Python models — standard `model(dbt, spark)` API

```python
def model(dbt, spark):
    source_df = dbt.ref("my_upstream_model")
    return source_df.withColumn("full_name", ...)
```

Same signature, same `dbt.ref()` / `dbt.source()` semantics, same `dbt.config.get()` access pattern. The developer experience matches dbt-spark exactly.

### High-concurrency Livy session reuse — deep Fabric optimization

The FabricSpark adapter derives a deterministic session tag from `(workspace_id, lakehouse_id)`. So when you run `dbt run` again against the same workspace and lakehouse, the adapter reattaches to the still-warm Livy session that's already there. Spark cold-start, typically over 2 minutes, doesn't happen on the subsequent runs. First-statement latency drops under 1 second. This is the kind of optimization you only think to build after you've personally waited for the cold-start one too many times. The production impact is real: Spark capacity isn't reprovisioned for no reason, so it costs less.

### PEP 249 cursor — Lakehouse feels like every other database

The FabricSpark cursor parses Spark JSON results into standard Python types via a [PEP 249](https://peps.python.org/pep-0249/) cursor. So dbt interacts with the Lakehouse exactly the same way it interacts with any other database. No Spark-specific deviations in connection management.

### Transparent limitations documentation

The [limitations page](https://microsoft.github.io/fabric-toolbox/dbt-fabric/limitations/) lists per platform (Data Warehouse and Lakehouse) exactly which dbt features don't work and why. It's organized into "Unsupported dbt features", "SQL dialect limitations", "DDL limitations", and "Incremental model limitations". Every limitation has either a workaround or a reference to the underlying Fabric platform constraint. That's not really a feature in itself. It's a diagnostic signal: the maintainer knows the engines well enough to map the gaps honestly.

### Community package compatibility with depth

Seven community packages are tested, each with its own compatibility documentation:

- dbt-utils (1.3.3)
- dbt-date (0.17.2)
- dbt-codegen (0.14.1)
- dbt-expectations (0.10.10)
- dbt-audit-helper (0.13.0)
- dbt-external-tables (0.11.0)
- dbt-profiler (1.0.0)

For each one, `docs/packages/<package>.md` lists which macros work, which don't, which tests run, and the version that was tested. That goes beyond "it works". It's a compatibility matrix, which is what data teams actually need to plan production rollouts.

---

## Architectural comparison

### This contribution

```
BaseFabricCredentials (abstract)
  ├── FabricCredentials          (T-SQL specific)
  └── FabricSparkCredentials     (Spark specific)

BaseFabricConnectionManager (abstract)
  ├── FabricConnectionManager      (mssql-python, T-SQL)
  └── FabricSparkConnectionManager (Livy sessions, Spark SQL)

BaseFabricAdapter (abstract: Python models, Purview sync)
  ├── FabricAdapter        (T-SQL DDL, constraints, warehouse snapshots)
  └── FabricSparkAdapter   (also extends SparkAdapter from dbt-spark)

Shared services:
  FabricTokenProvider   (unified authentication for both adapter types)
  FabricApiClient       (Fabric REST API: workspaces, warehouses, lakehouses, Livy, snapshots)
  PurviewClient + PurviewSync  (metadata sync, custom Purview types)
```

### `microsoft/dbt-fabric`

Flat structure, no inheritance. `FabricCredentials`, `FabricConnectionManager`, `FabricAdapter`, `WarehouseSnapshotManager`, all standalone, nothing shared.

### `microsoft/dbt-fabricspark`

A standalone `FabricSparkAdapter(SQLAdapter)` without a `dbt-spark` dependency. It has to reimplement everything that dbt-spark provides. And it automatically misses anything new that dbt-spark ships.

### Why this architecture

- Shared abstractions between DW and Lakehouse eliminate duplication. One auth stack. One Fabric API client. One Python-model submission path.
- Inheriting from `dbt-spark` means improvements, bug fixes, and new materializations in dbt-spark land in this FabricSpark adapter automatically. The maintenance burden per dbt-core release is significantly smaller.
- Instance encapsulation makes the adapter thread-safe by default. No separate synchronization logic.
- Capability declarations let dbt-core pick the optimized paths on its own. No monkey-patching of dbt internals required.

---

## What end users get out of this

All of this comes back to the dbt-native theme. For end users, that means:

- One `pip install dbt-fabric` for both engines, instead of two separate packages with overlapping dependencies and a version-conflict risk.
- No external ODBC driver installation. `mssql-python` bundles ODBC Driver 18 and unixODBC, which removes a common installation hurdle on macOS and inside containers.
- Functions (dbt 1.11 scalar functions) supported on both adapter types where the platform allows.
- Python models on both engines via PySpark, using dbt's standard `model(dbt, spark)` API.
- Microsoft Purview integration via API, `persist_docs`-aware. No Purview scan configuration, no scan-capacity costs.
- 11 authentication methods, including workload identity (federated OIDC for CI/CD) and custom `TokenCredential` classes, all configured through standard dbt profile keys.
- Auto host-resolution from the workspace name. No hardcoded SQL endpoint per environment.
- Manual statistics declaratively manageable through a model config. No post-hook tricks.
- Catalog statistics in `dbt docs generate` without configuration.
- `cluster_by` as a standard model config option, identical to Snowflake and BigQuery.
- High-concurrency Livy session reuse, for measurable cost savings on Spark capacity.
- Compatible with seven community packages, each with its own per-package compatibility matrix.
- Transparent limitations documentation, so customers can decide in advance what will and won't work for their use case.
