# Detailed comparison with microsoft/dbt-fabricspark

This report provides a detailed technical comparison between the **FabricSpark adapter in this package** and **Microsoft's dedicated [dbt-fabricspark](https://github.com/microsoft/dbt-fabricspark) repository**. Both target the same compute engine -- Microsoft Fabric Lakehouse with Spark SQL via Livy sessions -- but take fundamentally different architectural approaches.

| | dbt-fabric-samdebruyn | microsoft/dbt-fabricspark |
|---|---|---|
| **PyPI package** | `dbt-fabric-samdebruyn[spark]` | `dbt-fabricspark` |

---

## Architecture

This is the most significant difference and influences nearly every other comparison point.

### This adapter: multiple inheritance from dbt-spark

This adapter's FabricSpark adapter uses **multiple inheritance**: `FabricSparkAdapter(BaseFabricAdapter, SparkAdapter)`. It inherits from dbt-spark's `SparkAdapter` and a shared `BaseFabricAdapter` also used by the T-SQL adapter.

- **Plugin registration** declares `dependencies=["spark"]`, so dbt-spark's macros are available at runtime.
- **Adapter code** is thin because it delegates heavily to dbt-spark and the shared base.
- **Macros** are primarily overrides of dbt-spark macros for Fabric-specific behavior.

### Upstream: standalone SQLAdapter

The upstream is **fully standalone**: `FabricSparkAdapter(SQLAdapter)`. No dbt-spark dependency.

- **Plugin registration** has no `dependencies` -- all Spark SQL behavior is self-contained.
- **Adapter code** is significantly larger because it reimplements everything dbt-spark would provide.
- **Macros** include utility functions normally inherited from dbt-spark.

| Aspect | dbt-fabric-samdebruyn | microsoft/dbt-fabricspark |
|---|---|---|
| Code reuse | High (inherits dbt-spark + shared base) | None (self-contained) |
| Maintenance burden | Lower per-adapter, coupled to dbt-spark | Higher, no external coupling |
| dbt-spark compatibility | Automatic (inherits macros/behaviors) | Manual (must reimplement) |

---

## Features

### Materializations

| Materialization | dbt-fabric-samdebruyn | microsoft/dbt-fabricspark |
|---|---|---|
| **Table** | ✅ | ✅ |
| **View** | ✅ | ✅ |
| **Incremental** | append, merge, insert_overwrite, microbatch | append, merge, insert_overwrite, microbatch |
| **Snapshot** | ✅ | ✅ |
| **Ephemeral** | ✅ | ✅ |
| **Materialized View / Lake View** | ✅ (standard dbt MV pattern) | ✅ (Fabric-specific MLV with REST API refresh) |
| **Clone** | ✅ | ✅ |
| **Seed** | ✅ | ✅ |

Notable differences:

- **Materialized Lake View**: The upstream uses Fabric REST API for on-demand and scheduled refresh. This adapter uses standard `CREATE OR REPLACE` without REST API calls.

### Authentication methods

| Method | dbt-fabric-samdebruyn | microsoft/dbt-fabricspark |
|---|---|---|
| **Azure CLI** | ✅ | ✅ |
| **Service Principal** | ✅ | ✅ |
| **Token Credential** | ✅ | ✅ |
| **Workload Identity** | ✅ (federated OIDC) | ❌ |
| **Static Access Token** | ✅ | ✅ |
| **Fabric Notebook** | ✅ | ✅ |

### Livy session management

| Feature | dbt-fabric-samdebruyn | microsoft/dbt-fabricspark |
|---|---|---|
| **[High-concurrency Livy](lakehouse.md#high-concurrency-livy)** | ✅ | ✅ |
| **Session reuse** | Deterministic session tag (HC) | Via `session_id_file` + `reuse_session` flag (singleton) / deterministic session tag (HC) |
| **HC session cleanup** | Connection manager `close()` path | `atexit` handler (fragile — see [Code quality](#code-quality)) |
| **Polling interval** | Fixed 3 seconds | Adaptive (configurable) |
| **Session idle timeout** | 15 min default | 30 min default, configurable |
| **Local Livy mode** | ❌ | ✅ (`livy_mode: local`) |
| **Statement timeout** | 24 hours | 12 hours (configurable) |
| **Thread-safe token refresh** | ❌ | ✅ (`_token_lock`) |

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
| **Local Livy mode** | Connect to local Livy for development |
| **Credential validation** | UUID format, HTTPS domain whitelist |

### Lakehouse schema support

| Aspect | dbt-fabric-samdebruyn | microsoft/dbt-fabricspark |
|---|---|---|
| **Schema detection** | Via dbt-spark | Auto-detected via API, process-level cache |
| **Schema-enabled naming** | Always 3-part | Dynamic: 3-part or 2-part based on detection |
| **Non-schema mode** | Not explicitly handled | Full support with identifier prefixing |

---

## Test suite

| Aspect | dbt-fabric-samdebruyn | microsoft/dbt-fabricspark |
|---|---|---|
| **Testing approach** | Integration tests against real Fabric | Unit tests (mock) + functional tests (real infra) |
| **dbt-tests-adapter coverage** | Broad (standard adapter base classes) | Narrower (custom test suite) |
| **Community package tests** | [✅](packages/index.md) | ❌ |

---

## dbt Core compatibility

For supported dbt-core and Python versions, see the [compatibility page](compatibility.md).

---

## dbt best practices

| Practice | dbt-fabric-samdebruyn | microsoft/dbt-fabricspark |
|---|---|---|
| **Inherits official base** | ✅ (SparkAdapter + BaseFabricAdapter) | Partially (SQLAdapter only) |
| **Capability declarations** | ✅ | ❌ |
| **`@available` methods** | ✅ (inherited) | ✅ (MLV, schema detection) |
| **Plugin dependencies** | `dependencies=["spark"]` | None |
| **Dispatch fallback** | dbt-spark macros available | Must reimplement everything |

---

## Maturity

| | dbt-fabric-samdebruyn | microsoft/dbt-fabricspark |
|---|---|---|
| **Python** | 3.11-3.13 | 3.10-3.13 |
| **Documentation** | [Dedicated docs site](https://dbt-fabric.debruyn.dev) | README + CONTRIBUTING.md |
| **Code style** | ruff, PEP 604 | ruff, older typing style |
| **License** | MIT | MIT |

---

## Code quality

A detailed review of the upstream's Python source code reveals several significant issues that affect reliability and maintainability.

### Global mutable state

The upstream stores critical runtime state in module-level and class-level global variables — authentication tokens, Livy session handles, connection managers, and relation configuration are all shared across threads via globals or `ClassVar` attributes. This leads to data races in multi-threaded dbt runs (e.g., reading a token after releasing its lock, mutating session state outside locks). This adapter uses instance-based encapsulation with no module-level mutable state.

### atexit handler for session cleanup

The upstream registers `atexit` handlers at module import time (in both `singleton_livy.py` and `concurrent_livy.py`) to delete Livy sessions and HC sessions on process exit. This is fragile: `atexit` handlers run in undefined order, logging/network may already be torn down, and merely importing the module registers the handler even if no session was created. The HC implementation adds a second `atexit` handler with a global `_active_sessions` set, compounding the global mutable state problem.

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

The upstream mixes camelCase (`tokenPrint`, `accessToken`, `_submitLivyCode`, `_getLivySQL`) with snake_case throughout. Pre-3.9 typing aliases (`Dict`, `List`, `Optional`, `Union`) are used despite targeting Python 3.13.

---

## Summary

This adapter takes a **code-reuse approach** (thin adapter on dbt-spark), while the upstream takes a **self-contained approach** (everything reimplemented). The fork's approach results in significantly less code with proper instance-based lifecycle management and no global mutable state.

The upstream has more Fabric-specific features (MLV REST API refresh, OneLake shortcuts, local Livy mode), while this adapter offers broader dbt ecosystem integration (dbt-spark inheritance, Purview, capability declarations, shared T-SQL + Spark in one package) and significantly higher code quality.
