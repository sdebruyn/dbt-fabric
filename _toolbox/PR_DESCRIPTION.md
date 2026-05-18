# Contribute `dbt-fabric` to the Fabric Toolbox

## TL;DR

This PR adds `tools/dbt-fabric/` — a production-ready dbt adapter that supports **both** Microsoft Fabric compute engines (Data Warehouse via T-SQL, Lakehouse via Spark SQL) from a single Python package. It is proposed by [Sam Debruyn](https://github.com/sdebruyn), the primary author of the original `dbt-fabric` adapter, as a replacement for both [`microsoft/dbt-fabric`](https://github.com/microsoft/dbt-fabric) and [`microsoft/dbt-fabricspark`](https://github.com/microsoft/dbt-fabricspark). Multiple customers have already migrated to this codebase (via the interim PyPI distribution `dbt-fabric-samdebruyn`) specifically for production stability. The goal: a coordinated restart of Microsoft's dbt-adapter strategy with the community embedded in the maintenance model — Fabric product team, CAT team, and community contributors as co-maintainers.

## Personal context and motivation

I am the original author of most of the code in [`microsoft/dbt-fabric`](https://github.com/microsoft/dbt-fabric). When Microsoft adopted the repository I continued my work through my own fork because customers and the wider dbt community needed production-grade adapter features that the official repo was not shipping.

I sincerely regret the state in which Microsoft has left both adapters. This is not an attack — it is an invitation to put this project back on a sustainable track, together with the Fabric product team, the CAT team, and the community that has been keeping it alive.

### Market validation

At several conferences and in direct conversations, multiple customers have told me that they actively migrated from `microsoft/dbt-fabric` to my fork specifically because of its stability. This is not a marketing claim — it is something I have been told independently on multiple occasions. Customers choose on production reliability, and they are currently voting with their feet. Even the interim distribution `dbt-fabric-samdebruyn` on PyPI sees ongoing adoption purely because the community needs a working dbt adapter for Fabric.

A list of organizations currently running this adapter in production will be attached as a separate document (with their consent). For customers who prefer anonymity, the list will describe them by sector and size (e.g., "Fortune 500 retailer", "European bank").

### Bug-fix track record

Because the test harness I maintain is significantly broader than either of Microsoft's adapter test suites — multi-version Python (3.11/3.12/3.13) × multi-version dbt-core (1.9/1.10/1.11/1.12) × both compute engines, running against real Fabric infrastructure — it has actively surfaced bugs that are still present in `microsoft/dbt-fabric` and `microsoft/dbt-fabricspark`. The test suite is therefore not only a regression-prevention net for future work; it has retroactively raised the production reliability of the adapter as a whole.

A bug-fix track record table will be attached as a separate document, listing 5–10 concrete fixes with: a short description, link to the fix PR/commit in this fork, status check in upstream (open issue, closed without fix, or not yet reported).

### Goal of this PR

Beyond transferring code, this PR proposes a structured restart of Microsoft's dbt-adapter strategy with three properties the current situation lacks:

1. A predictable release cadence tied to dbt-core releases (versioning convention strictly followed).
2. A maintenance model where Microsoft product team, CAT team, and the community all have explicit roles.
3. Retention of the customers who already migrated — who are unlikely to return to a less stable version.

---

## The current situation — objectively documented

All metrics in this section are verifiable on PyPI and GitHub at the time of writing.

### `microsoft/dbt-fabric` (Data Warehouse adapter)

- Latest release: **v1.9.9 on 30 March 2026**.
- PyPI classifier list still declares Python 3.8–3.11 (no 3.12 or 3.13).
- `dbt-core>=1.8.0` without an upper bound — meaning installation on any modern dbt-core version is a gamble; users who depend on `dbt-core==1.12` cannot tell whether `dbt-fabric==1.9.9` is even tested against it.
- No public evidence of automated integration tests on pull requests.
- No multi-Python or multi-dbt-core test matrix.

### `microsoft/dbt-fabricspark` (Lakehouse adapter)

Five releases within seven days (10–17 May 2026):

| Version | Release date |
|---|---|
| v1.10.0 | 10 May 2026 |
| v1.10.1 | 11 May 2026 |
| v1.11.0 | 15 May 2026 |
| v1.12.0 | 17 May 2026 |
| v1.12.1 | 17 May 2026 |

Version numbers suggest support for dbt-core 1.10, 1.11, and 1.12, but the PyPI manifest only declares `dbt-core>=1.8.0` without an upper bound, and there is no public evidence of CI runs against the implied dbt-core minors.

### Versioning convention observation

The dbt adapter ecosystem follows the convention that `<adapter>==1.X.Y` means tested and guaranteed against `dbt-core==1.X.*`. Reference adapters (Snowflake, Postgres, Spark, BigQuery) follow this strictly: each adapter release ships only after its matching dbt-core minor is fully supported by the test suite. The pattern of rapid sequential version bumps without a visible test matrix against each dbt-core minor breaks this convention. Customers running dbt-core 1.12 who install `dbt-fabricspark==1.12.1` have no guarantee that the combination is actually validated.

### Functions (dbt-core 1.11 scalar functions)

Not supported in either official adapter, despite dbt-core 1.11 having been released approximately six months ago. This is a tangible gap for customers using SQL UDFs in their dbt projects on other warehouses.

---

## Concrete quality issues that obstruct maintenance

This section is not a list of grievances. It is evidence material that explains why a restart is needed and why this contribution's architecture is fundamentally more maintainable. Every claim is anchored with a file path, line number, or PR link so it can be independently verified.

### Global mutable state in `microsoft/dbt-fabricspark`

Module-level and class-level globals are used for authentication tokens, Livy session handles, connection managers, and relation configuration. The files involved include `singleton_livy.py` and `concurrent_livy.py`. Concrete consequence: data races in multi-threaded dbt runs (dbt's default `threads` is greater than 1). This contribution uses instance-encapsulation throughout — there is no module-level mutable state.

### `atexit` handlers for session cleanup

Registered at module import time in both `singleton_livy.py` and `concurrent_livy.py`. Consequences: handler execution order is undefined, networking and logging may already be torn down when handlers fire, and the handler is registered simply by importing the module — even if no session was ever created. The high-concurrency implementation adds a second `atexit` handler with a global `_active_sessions` set, compounding the global mutable state problem. This contribution manages all session lifecycle through dbt's standard connection-manager `close()` paths.

### Exception swallowing

`LivySession.__exit__` (livysession.py, lines 489–495) and `LivyCursor.__exit__` (livysession.py, lines 855–859) both `return True`. This suppresses **all** exceptions inside any `with` block using these objects, including database errors, timeouts, and `KeyboardInterrupt`. This contribution propagates exceptions normally.

### Regex bug in SQL sanitization

`_getLivySQL()` passes `re.DOTALL` as the `count` parameter to `re.sub` instead of `flags=re.DOTALL`. This silently limits comment-stripping to 16 replacements rather than enabling multiline matching. A subtle but production-affecting bug.

### Dead code and copy-paste artifacts

- Thrift exception handling in `connections.py` (lines 97–113) — references `thrift_resp.status.errorMessage`, a pattern from Apache Thrift used by dbt-spark. This adapter uses Livy over HTTP, not Thrift; the code path is dead.
- AWS logging configuration in `connections.py` (lines 39–46) — sets `botocore` and `boto3` to DEBUG at import time. Leftovers from a Spark/Databricks ancestor; there are no AWS dependencies in the package.
- Hardcoded 2028 timestamp in `livysession.py` (lines 194–198) — the `int_tests` auth path creates a token with `expires_on = 1845972874`, bypassing all token refresh logic.
- `_parse_retry_after` is duplicated verbatim between `livysession.py` and `mlv_api.py`, both using the deprecated `datetime.utcnow()`.
- `get_headers()` has a `tokenPrint` parameter that logs the full bearer token when set to `True`, but is never called with `True`. Dead parameter, latent security risk.

### Inconsistent coding style

camelCase (`tokenPrint`, `accessToken`, `_submitLivyCode`, `_getLivySQL`) is mixed with snake_case throughout. Pre-3.9 typing aliases (`Dict`, `List`, `Optional`, `Union`) are used despite the package targeting Python 3.13. These are signals about review and refactor discipline, not aesthetic preferences.

### Inadequate review on `microsoft/dbt-fabric`

[PR #315](https://github.com/microsoft/dbt-fabric/pull/315) adds `timeout=getattr(credentials, "login_timeout", None)` to all `get_token()` calls in the connection manager. This is a complete no-op:

- `login_timeout` does not exist as an attribute on `FabricCredentials`, so `getattr` always returns `None`.
- `get_token()` in `azure-identity` does not accept or use a `timeout` keyword argument — it silently disappears into `**kwargs`.

The PR description also follows clearly AI-generated patterns (structured headers, numbered references). Code that does nothing should not be merged. This suggests reviewer attention is limited — a problem that compounds over time as more low-signal changes accumulate.

The v1.9.10 release ([issue #362](https://github.com/microsoft/dbt-fabric/issues/362), May 2026) responds to a well-documented user report of `list_<schema>` taking 8–20 minutes under concurrent dbt runs on the same warehouse. The user is careful about what they actually observed (the metadata read hangs while DDL is active in another session) and explicitly flags everything else as hypothesis ("though we have not been able to confirm the exact mechanism"). One of the two changes that landed addresses the real complaint with code that duplicates a mechanism already present in the same file:

**`FabricAdapter.list_relations_without_caching` is wrapped in a custom retry-with-exponential-back-off.** `dbt-adapters` already provides exactly this on `SQLConnectionManager.add_query` via the `retryable_exceptions` + `retry_limit` arguments. It is not a hidden helper — the same connection manager file already configures it for the project's own `add_query` override, with `retry_limit=3` and `mssql_python.OperationalError` registered. Wrapping the adapter method on top is duplication that a reviewer reading the diff next to the existing connection manager would notice. The PR description also follows the same AI-generated patterns observed in PR #315.

(The release also adds a `close()` override that skips `ROLLBACK` on autocommit connections, attributed to pyodbc-level contention. We have not measured the pyodbc path and take no position on whether that part is justified for the upstream stack — only that on our `mssql-python` driver `rollback()` measures at ≤0.1 ms under live integration-test load, so it is not a fix we need to port.)

### `microsoft/dbt-fabric` warehouse snapshots via connection lifecycle hooks

The warehouse-snapshot feature is implemented as hooks in `open()` of the connection manager plus `atexit` handlers. This couples feature logic to Python runtime internals (`atexit`) and to connection lifecycle methods that are not designed as hook points — they are not part of dbt's stable adapter interface and can break across dbt-core versions. This contribution exposes warehouse snapshots as a Jinja macro callable from dbt's native `on-run-start` / `on-run-end` hooks — the stable, documented, supported mechanism for orchestrating side effects.

### Fabric-only config keys on the `incremental` materialization

The most recent upstream release (`microsoft/dbt-fabric` v1.9.10, May 2026) extends the `merge` incremental strategy with two new model-level configs invented by the maintainers: `delete_condition` and `delete_not_matched_by_source`. They are wired into `dbt/include/fabric/macros/materializations/models/incremental/incremental.sql` and dispatched through a new `fabric__get_incremental_merge_sql` macro. Neither config exists in `dbt-core` or `dbt-adapters`; no other reference adapter (Snowflake, BigQuery, Postgres, Redshift, Spark) exposes anything equivalent under those names.

This is the inverse of the dbt-native harmony principle. The `incremental` materialization is part of dbt's user-facing API contract — its config keys are how thousands of models in production projects are described. Extending it with adapter-private knobs has three concrete downsides:

1. **A model written for Fabric stops being portable.** A user moving from Fabric to Snowflake (or back) must rewrite the model's config block, even though the same merge-with-delete semantics could be expressed as a `post-hook` or via the standard `merge_update_columns` / `merge_exclude_columns` config that dbt-core already supports.
2. **Validation has to be reimplemented in Jinja.** The new config keys come with three compile-time exception branches in the materialization to enforce that they only apply to `incremental_strategy: 'merge'` and are mutually exclusive — logic that would be unnecessary if the feature were expressed through existing dbt primitives.
3. **It sets the precedent that "Fabric needs its own knobs."** Once the first adapter-private config lands on a stable materialization, the cost of saying no to the next one drops. This is how adapter codebases drift from feeling dbt-native to feeling like a thin SQL wrapper with a parallel config language.

The general principle: extensions belong in macros and hooks, not as new config keys on the materializations dbt-core ships. A maintainer who feels the pull to add `delete_condition` to `incremental` is signaling that the adapter is being designed as an isolated artefact rather than as a citizen of the dbt ecosystem.

### Versioning-convention violation in `microsoft/dbt-fabricspark`

Five rapid releases v1.10.0 → v1.10.1 → v1.11.0 → v1.12.0 → v1.12.1 within one week, with the PyPI manifest declaring only `dbt-core>=1.8.0` (no upper bound, no minor-version mapping). This is the opposite of the dbt-ecosystem convention. Customers cannot tell which combination of `dbt-fabricspark` and `dbt-core` is actually safe to use. The pattern — version bumps without a visible test matrix per dbt-core minor — suggests versioning here is reputation management rather than compatibility guarantee.

---

## How this contribution solves the maintenance situation

Point by point:

- **No module-level mutable state.** All lifecycle in instance-bound objects, managed by dbt's standard connection-manager `close()` paths.
- **No `atexit` handlers.** Resource cleanup follows dbt's documented connection lifecycle.
- **No exception swallowing.** Errors propagate normally.
- **Modern Python typing.** PEP 604 union syntax (`X | Y`), no `typing.Union`/`Optional` legacy imports.
- **Consistent snake_case.** Throughout the codebase.
- **Comprehensive integration test suite running against real Fabric infrastructure.** Approximately 444 integration test classes (vs ~117 for `microsoft/dbt-fabric`, ~141 for `microsoft/dbt-fabricspark` — to be verified with live counts at PR submission).
- **Test harness as a bug detector, not only a regression net.** Because the suite is broader than both upstreams and runs continuously against real Fabric infrastructure, it actively finds bugs that are still present in the official adapters. The track record of concrete fixes (attached bug-fix list) demonstrates this. The implication for sustainable maintenance: a larger test net means regressions are caught faster — which is *the* most essential precondition for maintenance over years rather than quarters.
- **Multi-Python matrix in CI.** Tests run on Python 3.11, 3.12, and 3.13.
- **Multi-dbt-core matrix in CI.** Each release is actually tested against the matching dbt-core minor version.
- **Systematic TDD process for dbt-core upgrades.** Documented in `CONTRIBUTING.md` under "Upgrading dbt-core support". Version bumps are not ad-hoc; they follow a checklist that inventories new dispatchable macros, new adapter methods, and new `Base*` test classes, records lessons learned, and only tags a release when all tests pass.
- **Warehouse snapshots via dbt's native hooks.** Stable API, no runtime internals.
- **Capability declarations.** (`SchemaMetadataByRelations`, `TableLastModifiedMetadata`) so dbt can choose optimized code paths without monkey-patching dbt internals.
- **Modern build stack.** `hatchling` and `uv`; faster and more reproducible than `setuptools` + `pip`.
- **Versioning convention strictly followed.** `dbt-fabric==1.X.Y` means tested and guaranteed against `dbt-core>=1.X,<1.(X+1)`.

---

## The unifying theme: dbt-native harmony

The overarching design principle of this contribution is that **every feature uses dbt's existing mechanisms rather than parallel constructions**. This is not accidental; it comes from the design perspective of someone who has used dbt in production for years and knows where the pain points are when integrations are not native. Concrete examples:

### Warehouse snapshots — `on-run-start` / `on-run-end` / `post-hook`

A macro `{{ create_or_update_fabric_warehouse_snapshot(name, description) }}` callable from any Jinja context. Free side benefits: dynamic snapshot names via Jinja expressions (`'snapshot_' ~ modules.datetime.datetime.now().strftime('%Y%m%d')`), per-model snapshot timing via `post-hook`, environment-variable-driven names via `env_var()`. This is exactly how Snowflake, BigQuery, and Postgres users have been orchestrating side effects in dbt for years. No new mental model to learn.

### External tables — dbt's dispatch system + `{{ source() }}` lineage

Instead of a standalone `openrowset_source()` macro outside dbt's source system (the upstream approach), this contribution goes through dbt's [dispatch system](https://docs.getdbt.com/reference/dbt-jinja-functions/dispatch) to override the Fabric plugin of the `dbt-external-tables` package. Result: external files are modeled as regular `{{ source('my_external', 'sales') }}` references — automatically visible in dbt's lineage graph, with freshness checking working out of the box, and `dbt run-operation stage_external_sources` is the standard interface that users of other warehouses already recognize.

### `cluster_by` — standard model config

```sql
{{ config(materialized='table', cluster_by=['customer_id', 'order_date']) }}
```

Syntactically identical to how Snowflake and BigQuery expose clustering. Works on tables, incremental models, and models with contract enforcement. Generated DDL is a clean `WITH (CLUSTER BY ([...]))` clause — no custom DDL injection, no post-hook gymnastics.

### Manual statistics — declarative model config

```sql
{{ config(statistics=['col1', 'col2'], statistics_sample_percent=50) }}
```

Idempotent: `CREATE STATISTICS` on first run, `UPDATE STATISTICS` on subsequent runs. Naming convention `dbt_stats__<md5_hash>` avoids collisions with Fabric's auto-generated `_WA_Sys_*` statistics — a detail only someone with production experience would think of.

### Catalog statistics — zero-config enrichment

Row counts appear automatically in `dbt docs generate` output without any configuration. Implemented via a clean override of the catalog query using `OBJECTPROPERTYEX(object_id, 'Cardinality')`. No extra macros, no extra commands.

### Microsoft Purview integration — `persist_docs`-aware

The macro `{{ purview_sync() }}` is callable from `on-run-end` or as a `dbt run-operation`. It respects dbt's standard [`persist_docs`](https://docs.getdbt.com/reference/resource-configs/persist_docs) configuration — models with `persist_docs: false` are skipped entirely; models with granular `relation: true, columns: false` get only the corresponding parts synced. Lineage uses dbt's `ref()` and `source()` dependency graph. End-users do not need to learn a separate mental model — it is just dbt.

### Authentication — extends dbt's standard credential pattern

A unified `FabricTokenProvider` across both adapter types. Configuration through the standard `authentication` profile key. Workload identity (federated OIDC) configured through the same top-level credential fields as other methods — no separate profile section. Custom `TokenCredential` classes via `credential_class` and `credential_kwargs`, which aligns with how `azure-identity` users are already accustomed to extending the SDK.

### Python models — standard `model(dbt, spark)` API

```python
def model(dbt, spark):
    source_df = dbt.ref("my_upstream_model")
    return source_df.withColumn("full_name", ...)
```

Identical signature, identical `dbt.ref()` / `dbt.source()` semantics, identical `dbt.config.get()` access pattern. Developer experience matches dbt-spark exactly.

### High-concurrency Livy session reuse — deep Fabric optimization

The FabricSpark adapter derives a **deterministic session tag** from `(workspace_id, lakehouse_id)`, so successive `dbt run` invocations against the same workspace and lakehouse reattach to the still-warm underlying Livy session. This eliminates Spark cold-start (typically over 2 minutes) on subsequent runs, bringing first-statement latency under 1 second. This is a deep Fabric optimization that only someone who has personally waited many times for a Spark cold-start during a dbt run would think to build. Production impact: direct cost savings, because Spark capacity is not unnecessarily reprovisioned.

### PEP 249 cursor — Lakehouse feels like every other database

The FabricSpark cursor parses Spark JSON results into standard Python types via a [PEP 249](https://peps.python.org/pep-0249/) compatible cursor, so dbt interacts with the Lakehouse "exactly the way it interacts with any other database." No Spark-specific deviations in connection management.

### Transparent limitations documentation

The [limitations page](https://microsoft.github.io/fabric-toolbox/dbt-fabric/limitations/) documents, per platform (Data Warehouse and Lakehouse), exactly which dbt features do not work and why — organized into "Unsupported dbt features", "SQL dialect limitations", "DDL limitations", and "Incremental model limitations". For every limitation there is either a workaround or a reference to the underlying Fabric platform constraint. This is not a feature; it is a diagnostic signal — the maintainer knows the underlying engines deeply enough to map the gaps honestly.

### Community package compatibility with depth

Seven community packages are tested with per-package compatibility documentation:

- dbt-utils (1.3.3)
- dbt-date (0.17.2)
- dbt-codegen (0.14.1)
- dbt-expectations (0.10.10)
- dbt-audit-helper (0.13.0)
- dbt-external-tables (0.11.0)
- dbt-profiler (1.0.0)

For each package, `docs/packages/<package>.md` lists which macros do and do not work, which tests run, and the tested version. This goes beyond "it works" toward "here is the exact compatibility matrix" — which is what data teams need to make production plans.

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

Flat structure without inheritance: `FabricCredentials`, `FabricConnectionManager`, `FabricAdapter`, `WarehouseSnapshotManager` — all standalone, no shared abstractions.

### `microsoft/dbt-fabricspark`

Standalone `FabricSparkAdapter(SQLAdapter)` without a `dbt-spark` dependency. Must reimplement everything that dbt-spark provides — and automatically misses anything that dbt-spark adds.

### Arguments for this architecture

- **Shared abstractions between DW and Lakehouse eliminate duplication.** One auth stack, one Fabric API client, one Python model submission path.
- **Inheritance from `dbt-spark` means improvements, bug fixes, and new materializations in dbt-spark land automatically in this FabricSpark adapter.** Significantly less maintenance burden per dbt-core release.
- **Instance encapsulation makes the adapter thread-safe by default.** No separate synchronization logic needed.
- **Capability declarations let dbt-core decide which optimized paths to use.** No monkey-patching of dbt internals required.

---

## End-user benefits

With the dbt-native harmony theme as throughline:

- **One `pip install dbt-fabric` for both engines**, instead of two separate packages with overlapping dependencies and version-conflict risk.
- **No external ODBC driver installation needed.** `mssql-python` bundles ODBC Driver 18 and unixODBC; eliminates a common installation barrier on macOS and in containers.
- **Functions** (dbt 1.11 scalar functions) supported on both adapter types where the platform allows.
- **Python models on both engines** via PySpark, with dbt's standard `model(dbt, spark)` API.
- **Microsoft Purview integration via API** with `persist_docs`-aware sync — no Purview scan configuration, no scan-capacity costs.
- **11 authentication methods** including workload identity (federated OIDC for CI/CD) and custom `TokenCredential` classes, all configured through standard dbt profile keys.
- **Auto host-resolution from workspace name** — no hardcoded SQL endpoint per environment.
- **Manual statistics declaratively manageable via model config** — no post-hook gymnastics.
- **Catalog statistics in `dbt docs generate`** without configuration.
- **`cluster_by` as a standard model config option**, syntactically identical to Snowflake and BigQuery.
- **High-concurrency Livy session reuse** — measurable cost savings on Spark capacity.
- **Compatible with seven community packages** with per-package compatibility matrix.
- **Transparent limitations documentation** — customers can assess in advance what will and will not work for their use case.

---

## Proposed maintenance model post-acceptance

Not "we contribute and disappear":

- **Sam Debruyn remains primary maintainer** with commit rights on `tools/dbt-fabric/`.
- **Microsoft Fabric product team and CAT team as co-maintainers** with review authority on all PRs.
- **Community contributions** via the standard PR flow with CLA.
- **Release cadence tied to dbt-core releases.** Within four weeks of each dbt-core minor, including being fully tested against that minor — not version-bump-only.
- **Versioning convention strict:** `dbt-fabric==1.X.Y` means tested and guaranteed compatible with `dbt-core==1.X.*`.
- **Monthly issue triage.**
- **Clear escalation path** for production-blocking issues (24h response target).
- **Co-maintenance of the docs site** (GitHub Pages under fabric-toolbox).

---

## Migration path for existing users

### `microsoft/dbt-fabric` (Data Warehouse) users

Drop-in replacement. `pip uninstall dbt-fabric && pip install dbt-fabric` with this version. Profile configuration is 100% compatible. Migration guide to be added at `docs/migration.md`.

### `microsoft/dbt-fabricspark` (Lakehouse) users

Profile type remains `fabricspark`. A config-mapping table will accompany the migration guide, documenting the small number of options that differ.
