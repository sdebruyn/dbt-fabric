# Compatibility

The first release of this fork was version 1.10.0. The adapter follows [dbt-adapters](https://github.com/dbt-labs/dbt-adapters) versioning rather than dbt-core versioning, so the adapter version number does not correspond to the dbt-core version.

## dbt-core

| dbt-core version | Supported |
|---|---|
| 1.9 | Yes |
| 1.10 | Yes |
| 1.11 | Yes |

## Python

| Python version | Supported |
|---|---|
| 3.11 | Yes |
| 3.12 | Yes |
| 3.13 | Yes |

## Fabric compute types

| Compute type | Adapter type | SQL dialect |
|---|---|---|
| Fabric Data Warehouse | `fabric` | T-SQL |
| Fabric Lakehouse | `fabricspark` | Spark SQL |

The `fabricspark` adapter type requires the optional `spark` dependency: `pip install dbt-fabric-samdebruyn[spark]`.
