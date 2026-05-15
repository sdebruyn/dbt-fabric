# Roadmap

Ideas for future improvements to this adapter. Contributions are welcome — [create an issue](https://github.com/sdebruyn/dbt-fabric/issues) if you'd like to discuss an approach.

## Spark SQL and T-SQL models in the same project

### The idea

Microsoft Fabric has two SQL engines that share the same storage layer (Delta Lake on OneLake):

- **Fabric Data Warehouse** — T-SQL, best for interactive queries, star schemas, and SQL-native teams
- **Fabric Lakehouse** — Spark SQL, best for large-scale transformations, Python models, and unstructured data

Today, you pick one adapter (`fabric` or `fabricspark`) per dbt project. If you want to use both engines, you need two separate projects. The goal is to let users choose per model which engine to use, within a single project.

### Why this matters

Many organizations have workloads that benefit from both engines. A typical pattern:

1. Raw data ingestion and heavy transformations in Spark (Lakehouse)
2. Business logic, star schemas, and reporting models in T-SQL (Data Warehouse)
3. Cross-database queries already work — Fabric DW can query Lakehouse tables via [three-part naming](https://learn.microsoft.com/fabric/data-warehouse/query-warehouse?WT.mc_id=MVP_310840)

Without adapter-level support, teams must maintain two dbt projects, duplicate shared macros, and orchestrate runs externally.

### Current state of the dbt ecosystem

dbt-core has a fundamental limitation: **one adapter per project per invocation**. There is no built-in way to run some models on one adapter and others on a different adapter in a single `dbt run`.

Several approaches exist to work around this:

| Approach | Maturity | Open source |
|---|---|---|
| Two `dbt run` invocations with different `--target` | Production-ready | Yes |
| Two projects + [dbt-loom](https://github.com/nicholasyager/dbt-loom) for cross-project `ref()` | Active (v0.9.4) | Yes |
| Two projects + [dbt Mesh](https://docs.getdbt.com/best-practices/how-we-mesh/mesh-1-intro) | GA (same-platform) | dbt Cloud Enterprise only |
| [Cross-platform Mesh with Iceberg](https://docs.getdbt.com/docs/mesh/iceberg/about-catalogs) | Beta | dbt Cloud only, Fabric not yet supported |
| dbt-core multi-adapter support ([Discussion #5758](https://github.com/dbt-labs/dbt-core/discussions/5758)) | Proposed, not implemented | N/A |

---

## External Iceberg and Delta Lake tables

### The idea

Enable dbt models to reference data stored outside of Fabric — in Azure Data Lake Storage, Amazon S3, Google Cloud Storage, or other cloud storage — as first-class dbt sources. This extends the existing external tables support (which uses `OPENROWSET` for raw files) to also cover **Delta Lake** and **Iceberg** table formats via [OneLake shortcuts](https://learn.microsoft.com/fabric/onelake/onelake-shortcuts?WT.mc_id=MVP_310840).

### How Fabric handles external tables

Fabric has two mechanisms for accessing external data:

| Mechanism | Formats | Engine | Use case |
|---|---|---|---|
| [`OPENROWSET(BULK ...)`](https://learn.microsoft.com/sql/t-sql/functions/openrowset-bulk-transact-sql?view=fabric&WT.mc_id=MVP_310840) | Parquet, CSV, JSONL | T-SQL (Data Warehouse) | Raw file access, schema-on-read |
| [OneLake shortcuts](https://learn.microsoft.com/fabric/onelake/onelake-shortcuts?WT.mc_id=MVP_310840) | Delta Lake, Iceberg | Both engines | Table-format access with full metadata |

`OPENROWSET` is already supported via the dbt-external-tables integration. This roadmap item focuses on the shortcut approach.

### OneLake shortcuts

A shortcut is a pointer to data stored elsewhere. When placed in a Lakehouse's `Tables` folder, shortcuts appear as native tables:

- **Delta Lake shortcuts** are queryable immediately by both Spark SQL and T-SQL (via cross-database queries)
- **Iceberg shortcuts** are automatically converted to Delta Lake via [metadata virtualization](https://learn.microsoft.com/fabric/onelake/onelake-iceberg-tables?WT.mc_id=MVP_310840) — no manual conversion needed

Supported shortcut targets:

| Source | Read | Write |
|---|---|---|
| Azure Data Lake Storage Gen2 | Yes | Yes |
| Amazon S3 | Yes | No |
| Amazon S3-compatible (MinIO, etc.) | Yes | No |
| Google Cloud Storage | Yes | No |
| Azure Blob Storage | Yes | No |
| Other Fabric items (Lakehouse, Warehouse, etc.) | Yes | Depends |
| Dataverse | Yes | No |

Shortcuts can be created programmatically via the [Fabric REST API](https://learn.microsoft.com/rest/api/fabric/core/onelake-shortcuts/create-shortcut?WT.mc_id=MVP_310840):

```http
POST https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/items/{itemId}/shortcuts
```

---

## External catalog integration

### The idea

Enable dbt to discover and reference tables from external data catalogs — such as Databricks Unity Catalog, Dremio, or any Iceberg REST Catalog (IRC) compatible system — and make them available as dbt sources. This complements the [external tables](#external-iceberg-and-delta-lake-tables) feature by operating at the catalog level rather than individual table level.

### How Fabric integrates with external catalogs

Fabric supports external catalogs through two mechanisms:

#### 1. Catalog mirroring (external catalog -> Fabric)

[Catalog mirroring](https://learn.microsoft.com/fabric/mirroring/overview?WT.mc_id=MVP_310840) brings external catalog metadata into Fabric as shortcuts. No data is copied — Fabric creates pointers to the original data.

| Source catalog | Status | What gets created in Fabric |
|---|---|---|
| [Databricks Unity Catalog](https://learn.microsoft.com/fabric/mirroring/azure-databricks?WT.mc_id=MVP_310840) | GA | Mirrored catalog item + SQL analytics endpoint + OneLake shortcuts per table |
| [Dremio](https://learn.microsoft.com/fabric/mirroring/catalog-mirroring/dremio?WT.mc_id=MVP_310840) | Preview | Mirrored catalog item + shortcuts (max 500 tables) |
| Snowflake | GA | Database mirroring (actual data replication to Delta, not catalog mirroring) |

When a Unity Catalog is mirrored into Fabric:

- Each catalog table becomes a OneLake shortcut pointing to the original data in ADLS
- A SQL analytics endpoint is auto-generated, providing T-SQL read access
- Metadata syncs continuously — new tables/schemas are reflected automatically
- Cross-database queries from the Data Warehouse work immediately

#### 2. OneLake table APIs (Fabric -> external tools)

Fabric also **exposes** its own tables to external tools via two catalog API endpoints:

| API | Endpoint | Protocol | Status |
|---|---|---|---|
| [Iceberg REST Catalog](https://learn.microsoft.com/fabric/onelake/table-apis/iceberg-table-apis-overview?WT.mc_id=MVP_310840) | `https://onelake.table.fabric.microsoft.com/iceberg` | Apache Iceberg REST Catalog spec | Preview |
| [Unity Catalog Open API](https://learn.microsoft.com/fabric/onelake/table-apis/delta-table-apis-overview?WT.mc_id=MVP_310840) | `https://onelake.table.fabric.microsoft.com/delta` | Unity Catalog 2.1 API | Preview |

Both are currently **read-only** for metadata operations. Authentication uses the same Entra ID tokens as OneLake (`https://storage.azure.com/.default` scope).

Compatible external consumers: Snowflake, DuckDB, PyIceberg, Spark with Iceberg catalog, Databricks (via [catalog federation](https://learn.microsoft.com/azure/databricks/query-federation/onelake?WT.mc_id=MVP_310840)).

