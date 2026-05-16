# Detailed comparison with microsoft/dbt-fabricspark

This report provides a detailed technical comparison between the **FabricSpark adapter in this package** and **Microsoft's dedicated [dbt-fabricspark](https://github.com/microsoft/dbt-fabricspark) repository**. Both target the same compute engine -- Microsoft Fabric Lakehouse with Spark SQL via Livy sessions -- but take fundamentally different architectural approaches.

| | dbt-fabric-samdebruyn | microsoft/dbt-fabricspark |
|---|---|---|
| **PyPI package** | `dbt-fabric-samdebruyn[spark]` | `dbt-fabricspark` |
| **Latest version** | v1.11.3b0 | v1.11.0 |

**Last updated:** 2026-05-16

---

## Architecture

This is the most significant difference and influences nearly every other comparison point.

### This adapter: multiple inheritance from dbt-spark

This adapter's FabricSpark adapter uses **multiple inheritance**: `FabricSparkAdapter(BaseFabricAdapter, SparkAdapter)`. It inherits from dbt-spark's `SparkAdapter` and a shared `BaseFabricAdapter` also used by the T-SQL adapter.

- **Plugin registration** declares `dependencies=["spark"]`, so dbt-spark's macros are available at runtime.
- **Adapter code** is thin (~749 LOC) because it delegates heavily to dbt-spark and the shared base.
- **Macros** (24 files) are primarily overrides of dbt-spark macros for Fabric-specific behavior.

### Upstream: standalone SQLAdapter

The upstream is **fully standalone**: `FabricSparkAdapter(SQLAdapter)`. No dbt-spark dependency.

- **Plugin registration** has no `dependencies` -- all Spark SQL behavior is self-contained.
- **Adapter code** is significantly larger (~4,387 LOC) because it reimplements everything dbt-spark would provide.
- **Macros** (34 files) include utility functions normally inherited from dbt-spark.

| Aspect | dbt-fabric-samdebruyn | microsoft/dbt-fabricspark |
|---|---|---|
| Code reuse | High (inherits dbt-spark + shared base) | None (self-contained) |
| Maintenance burden | Lower per-adapter, coupled to dbt-spark | Higher total LOC, no external coupling |
| dbt-spark compatibility | Automatic (inherits macros/behaviors) | Manual (must reimplement) |
| Customization surface | Limited by what dbt-spark exposes | Full control |

---

## Features

### Materializations

| Materialization | dbt-fabric-samdebruyn | microsoft/dbt-fabricspark |
|---|---|---|
| **Table** | Yes (via dbt-spark) | Yes (custom implementation) |
| **View** | Not yet (Spark SQL views are not yet supported in schema-enabled Lakehouses) | Yes |
| **Incremental** | append, merge, insert_overwrite, microbatch | append, merge, insert_overwrite, microbatch |
| **Snapshot** | Yes | Yes |
| **Ephemeral** | Yes | Yes |
| **Materialized View / Lake View** | Yes (standard dbt MV pattern) | Yes (Fabric-specific MLV with REST API refresh) |
| **Clone** | Yes | Yes |
| **Seed** | Yes (via dbt-spark) | Yes (custom implementation) |

Notable differences:

- **View**: The upstream supports Spark SQL views, but these are [not yet supported in schema-enabled Lakehouses](https://learn.microsoft.com/en-us/fabric/data-engineering/lakehouse-schemas?WT.mc_id=MVP_310840). Schema-enabled Lakehouses are [the default when creating new Lakehouses](https://blog.fabric.microsoft.com/en-US/blog/lakehouse-schemas-generally-available/). Microsoft has [announced](https://community.fabric.microsoft.com/t5/Fabric-Updates-Blog/Lakehouse-Schemas-Generally-Available/ba-p/5172416) that Spark SQL view support is coming. This adapter will add view support once it becomes available ([#163](https://github.com/sdebruyn/dbt-fabric/issues/163)).
- **Materialized Lake View**: The upstream uses Fabric REST API for on-demand and scheduled refresh. This adapter uses standard `CREATE OR REPLACE` without REST API calls.

### Authentication methods

| Method | dbt-fabric-samdebruyn | microsoft/dbt-fabricspark |
|---|---|---|
| **Azure CLI** | Yes | Yes |
| **Service Principal** | Yes | Yes |
| **Token Credential** | Yes | Yes |
| **Workload Identity** | Yes (federated OIDC) | No |
| **Static Access Token** | Yes | Yes |
| **Fabric Notebook** | No | Yes |

### Livy session management

| Feature | dbt-fabric-samdebruyn | microsoft/dbt-fabricspark |
|---|---|---|
| **Session creation** | `FabricApiClient` singleton | `LivySessionManager` with static globals |
| **Session reuse** | By session name | Via `session_id_file` + `reuse_session` flag |
| **Polling interval** | Fixed 3 seconds | Adaptive (configurable) |
| **Session idle timeout** | 15 min default | 30 min default, configurable |
| **Local Livy mode** | No | Yes (`livy_mode: local`) |
| **Statement timeout** | 24 hours | 12 hours (configurable) |
| **Thread-safe token refresh** | No | Yes (`_token_lock`) |

### Unique to this adapter

| Feature | Description |
|---|---|
| **[Purview integration](purview-integration.md)** | Sync dbt metadata to Microsoft Purview |
| **[Python model](python-models.md) support** | Submit Python models to Livy |
| **Workload identity auth** | Federated OIDC for CI/CD |
| **Shared T-SQL + Spark** | One package, two adapters |
| **Capability declarations** | `SchemaMetadataByRelations`, `TableLastModifiedMetadata` |
| **PEP 249 cursor** | Proper type conversion for all Spark SQL types |

### Unique to upstream

| Feature | Description |
|---|---|
| **MLV REST API** | On-demand refresh, scheduled refresh via Fabric API |
| **OneLake shortcuts** | `ShortcutClient` for shortcut CRUD |
| **Fabric Notebook auth** | Ambient auth inside notebooks |
| **Local Livy mode** | Connect to local Livy for development |
| **Spark SQL views** | `CREATE OR REPLACE VIEW` support (not yet available in schema-enabled Lakehouses) |
| **Cross-workspace 4-part naming** | Full read+write for `workspace.lakehouse.schema.table` |
| **Credential validation** | UUID format, HTTPS domain whitelist |

### Lakehouse schema support

| Aspect | dbt-fabric-samdebruyn | microsoft/dbt-fabricspark |
|---|---|---|
| **Schema detection** | Via dbt-spark | Auto-detected via API, process-level cache |
| **Schema-enabled naming** | Always 3-part | Dynamic: 3-part or 2-part based on detection |
| **Non-schema mode** | Not explicitly handled | Full support with identifier prefixing |

---

## Test suite

| Metric | dbt-fabric-samdebruyn | microsoft/dbt-fabricspark |
|---|---|---|
| **Test files** | 60 | 50 |
| **Test classes** | ~183 | ~141 |
| **Unit/functional split** | All integration | Unit (mock) + functional (real infra) |
| **Schema mode toggle** | No | Yes (`--schema-mode` CLI flag) |
| **Session sharding** | No | Yes (`--session-id-files` for xdist workers) |
| **Fail-fast sentinel** | No | Yes (cross-worker abort on first failure) |
| **Session reuse assertion** | No | Yes (verifies no extra sessions created) |

**This adapter covers that upstream does not:** Purview tests, broader dbt-tests-adapter base class coverage (183 vs 141 classes).

**Upstream covers that this adapter does not:** Unit tests (mock-based), cross-workspace tests, MLV lifecycle tests, OneLake shortcut tests, dual schema-mode testing, fail-fast sentinel, session reuse verification.

---

## dbt Core compatibility

| Aspect | dbt-fabric-samdebruyn | microsoft/dbt-fabricspark |
|---|---|---|
| **dbt-adapters** | >=1.22.6, <2.0 | >=1.7, <2.0 |
| **dbt-common** | >=1.37.3, <2.0 | >=1.10, <2.0 |
| **dbt-core** (dev) | >=1.9.6, <1.13.0 | >=1.8.0 |
| **dbt-spark** | >=1.10.1 (optional) | Not used |
| **Python** | >=3.11, <3.14 | >=3.10, <3.14 |
| **azure-identity** | >=1.12.0 | >=1.21.0 |

---

## dbt best practices

| Practice | dbt-fabric-samdebruyn | microsoft/dbt-fabricspark |
|---|---|---|
| **Inherits official base** | Yes (SparkAdapter + BaseFabricAdapter) | Partially (SQLAdapter only) |
| **Capability declarations** | Yes | No |
| **`@available` methods** | Yes (inherited) | Yes (MLV, schema detection) |
| **Plugin dependencies** | `dependencies=["spark"]` | None |
| **Dispatch fallback** | dbt-spark macros available | Must reimplement everything |

---

## Maturity

| | dbt-fabric-samdebruyn | microsoft/dbt-fabricspark |
|---|---|---|
| **Total commits** | 500+ since Jan 2025 | 329 total, ~278 since Jan 2025 |
| **Release tags** | 67+ (v1.4.0rc1 to v1.11.3b0) | 8 (v1.7.0rc1 to v1.11.0) |
| **Python** | 3.11-3.14 | 3.10-3.13 |
| **Documentation** | [Docs website](https://dbt-fabric.debruyn.dev) + development guide | README + CONTRIBUTING.md |
| **Code style** | ruff, PEP 604, line-length 99 | ruff, older typing style |

Both repositories use the MIT License and the hatchling build system.

---

## Code quality

A detailed review of the upstream's Python source code reveals several significant issues that affect reliability and maintainability.

### Global mutable state

The upstream stores critical runtime state in module-level and class-level global variables:

- **Authentication token** (`livysession.py` line 35): A single `accessToken: AccessToken = None` global shared by all threads. While a `_token_lock` protects the refresh path, other code reads `accessToken.token` after releasing the lock, creating a data race in multi-threaded dbt runs.
- **Livy session** (`livysession.py` line 1327): `LivySessionManager.livy_global_session` is a class variable mutated from multiple threads. The lock only protects `connect()`/`disconnect()`, but `is_new_session_required` is set outside the lock at multiple call sites.
- **Connection managers** (`connections.py` line 93): A class-level `connection_managers = {}` dict mutated at runtime, with no cleanup between test runs.
- **Relation state** (`relation.py` lines 44-45): `_schemas_enabled` and `_identifier_prefix` are `ClassVar` attributes mutated at connection time, meaning all relation instances across all threads share the same value.

This adapter uses proper instance-based encapsulation: `FabricTokenProvider` (per-scope token caching), `FabricApiClient` (singleton with thread-safe session lock), and no module-level mutable state.

### atexit handler for session cleanup

The upstream registers an `atexit` handler at module import time (`livysession.py` lines 1314-1322) to delete Livy sessions on process exit. This is fragile: `atexit` handlers run in undefined order, logging/network may already be torn down, and merely importing the module registers the handler even if no session was created.

This adapter manages session lifecycle through dbt's normal connection manager `close()` path.

### Exception swallowing

Both `LivySession.__exit__` and `LivyCursor.__exit__` return `True` (`livysession.py` lines 489-495, 855-859), which suppresses all exceptions — including database errors, timeouts, and `KeyboardInterrupt` — inside any `with` block using these objects.

### Misleading security comment with actual regex bug

`_getLivySQL()` (`livysession.py` lines 980-988) contains alarming security comments ("repurcursions of code injection... arbritary Python code") about code that now just strips SQL block comments. The comment was left behind from a previous implementation. Additionally, `re.sub(r"\s*/\*(.|\n)*?\*/\s*", "\n", sql, re.DOTALL)` passes `re.DOTALL` (integer value 16) as the `count` parameter instead of as `flags=re.DOTALL`, meaning it limits replacements to 16 instead of enabling dotall mode.

### Dead code and copy-paste artifacts

- **Thrift exception handling** (`connections.py` lines 97-113): References `thrift_resp.status.errorMessage`, a pattern from Apache Thrift used by dbt-spark. This adapter uses Livy over HTTP, not Thrift — this code path is dead.
- **AWS logging** (`connections.py` lines 39-46): Sets `botocore` and `boto3` (AWS libraries) to DEBUG level at import time. These are leftovers from a Spark/Databricks ancestor.
- **Hardcoded 2028 timestamp** (`livysession.py` lines 194-198): The `int_tests` auth path creates a token with `expires_on = 1845972874` (a date in 2028), bypassing all token refresh logic.
- **Duplicated functions**: `_parse_retry_after` is copied identically in both `livysession.py` and `mlv_api.py`, using the deprecated `datetime.utcnow()`.
- **Dead parameter**: `get_headers()` has a `tokenPrint` parameter that logs the full bearer token when `True`, but is never called with `True`.

### Inconsistent style

The upstream mixes camelCase (`tokenPrint`, `accessToken`, `_submitLivyCode`, `_getLivySQL`) with snake_case throughout. Pre-3.9 typing aliases (`Dict`, `List`, `Optional`, `Union`) are used despite targeting Python 3.10+.

---

## Summary

This adapter deliberately targets **schema-enabled Lakehouses**, which is [the default when creating new Lakehouses](https://blog.fabric.microsoft.com/en-US/blog/lakehouse-schemas-generally-available/) in the Fabric portal ([schemas are enabled by default](https://learn.microsoft.com/en-us/fabric/data-engineering/lakehouse-schemas?WT.mc_id=MVP_310840)). This means some upstream features that only work without schemas (e.g., Spark SQL views) are not yet supported. Microsoft has [announced](https://community.fabric.microsoft.com/t5/Fabric-Updates-Blog/Lakehouse-Schemas-Generally-Available/ba-p/5172416) that Spark SQL views are coming to schema-enabled Lakehouses, and this adapter will add support when they become available ([#163](https://github.com/sdebruyn/dbt-fabric/issues/163)).

This adapter takes a **code-reuse approach** (thin adapter on dbt-spark), while the upstream takes a **self-contained approach** (everything reimplemented). The fork's approach results in dramatically less code (749 LOC vs 4,387 LOC) with proper instance-based lifecycle management and no global mutable state.

The upstream has more Fabric-specific features (MLV REST API refresh, OneLake shortcuts, cross-workspace 4-part naming, local Livy mode), while this adapter offers broader dbt ecosystem integration (dbt-spark inheritance, Purview, capability declarations, shared T-SQL + Spark in one package) and significantly higher code quality.
