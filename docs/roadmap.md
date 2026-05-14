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

### Proposed approach

The most practical approach for this adapter combines **two targets** with **shared storage** and optional **dbt-loom** for cross-project references:

#### Option A: Single project, two targets (simplest)

```yaml title="profiles.yml"
my_project:
  outputs:
    fabric:
      type: fabric
      workspace_name: my_workspace
      database: my_warehouse
      schema: dbt
    fabricspark:
      type: fabricspark
      workspace_name: my_workspace
      lakehouse: my_lakehouse
      schema: dbt
```

```yaml title="dbt_project.yml"
models:
  my_project:
    staging:
      +materialized: table
      +tags: [spark]      # These models run on Spark
    marts:
      +materialized: table
      +tags: [tsql]       # These models run on T-SQL
```

Orchestration runs dbt twice:

```shell
dbt run --target fabricspark --select tag:spark
dbt run --target fabric --select tag:tsql
```

T-SQL models can reference Spark-materialized tables via cross-database queries. The adapter would need to generate the correct three-part names when a T-SQL model references a table that lives in a Lakehouse.

**What the adapter needs:**

- A cross-database `ref()` resolver that generates three-part names (e.g., `my_lakehouse.dbo.staging_orders`) when a Fabric DW model references a Lakehouse table
- Documentation and examples for the two-target workflow
- A helper macro or configuration option to declare which models live on which engine

#### Option B: Two projects with dbt-loom (most robust)

Split into two dbt projects (`project-spark` and `project-fabric`), each with its own adapter. Use [dbt-loom](https://github.com/nicholasyager/dbt-loom) (open source, requires dbt-core >= 1.6) for cross-project references:

```python title="project-fabric/dbt_loom.config.yml"
manifests:
  - name: project_spark
    type: file
    config:
      path: ../project-spark/target/manifest.json
```

```sql title="project-fabric/models/marts/orders.sql"
select *
from {{ ref('project_spark', 'stg_orders') }}
where status = 'completed'
```

dbt-loom injects the upstream project's public models into the downstream DAG, allowing standard `ref()` syntax.

**What the adapter needs:**

- Cross-database name resolution (same as Option A)
- Testing and documentation of the dbt-loom integration
- Published manifest location configuration (local file, Azure Blob Storage, or OneLake)

### Implementation steps

1. **Cross-database ref resolution** — When a model's `ref()` target lives in a different Fabric item (Lakehouse vs. Warehouse), generate a three-part name. This requires knowing the mapping between dbt databases/schemas and Fabric items.
2. **Two-target documentation** — Write a guide showing both options (single project with tags, two projects with dbt-loom).
3. **Cross-database macro** — A `fabric__resolve_ref()` macro that checks whether the referenced model's database differs from the current target and generates the appropriate three-part name.
4. **Integration testing** — Test that a T-SQL model can successfully query a table materialized by the Spark adapter, and vice versa.

---

## External Iceberg and Delta Lake tables

### The idea

Enable dbt models to reference data stored outside of Fabric — in Azure Data Lake Storage, Amazon S3, Google Cloud Storage, or other cloud storage — as first-class dbt sources. This extends the existing [external tables](external-tables.md) support (which uses `OPENROWSET` for raw files) to also cover **Delta Lake** and **Iceberg** table formats via [OneLake shortcuts](https://learn.microsoft.com/fabric/onelake/onelake-shortcuts?WT.mc_id=MVP_310840).

### How Fabric handles external tables

Fabric has two mechanisms for accessing external data:

| Mechanism | Formats | Engine | Use case |
|---|---|---|---|
| [`OPENROWSET(BULK ...)`](https://learn.microsoft.com/sql/t-sql/functions/openrowset-bulk-transact-sql?view=fabric&WT.mc_id=MVP_310840) | Parquet, CSV, JSONL | T-SQL (Data Warehouse) | Raw file access, schema-on-read |
| [OneLake shortcuts](https://learn.microsoft.com/fabric/onelake/onelake-shortcuts?WT.mc_id=MVP_310840) | Delta Lake, Iceberg | Both engines | Table-format access with full metadata |

`OPENROWSET` is already supported via the [dbt-external-tables](external-tables.md) integration. This roadmap item focuses on the shortcut approach.

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

### Proposed approach

Extend the adapter to automatically create OneLake shortcuts from dbt source definitions, making external Delta/Iceberg tables available as queryable sources.

#### Source configuration

```yaml title="sources.yml"
sources:
  - name: external_data
    schema: dbt
    tables:
      - name: customer_events
        external:
          # Shortcut target (auto-creates a shortcut in the Lakehouse)
          shortcut:
            type: adlsGen2
            location: "https://myaccount.dfs.core.windows.net"
            subpath: "/container/delta/customer_events"
            connection_id: "{{ env_var('FABRIC_ADLS_CONNECTION_ID') }}"
          file_format: delta  # or iceberg

      - name: product_catalog
        external:
          shortcut:
            type: amazonS3
            location: "https://my-bucket.s3.amazonaws.com"
            subpath: "/iceberg/product_catalog"
            connection_id: "{{ env_var('FABRIC_S3_CONNECTION_ID') }}"
          file_format: iceberg  # auto-converted to Delta via metadata virtualization
```

#### What happens at `dbt run-operation stage_external_sources`

1. For each source with a `shortcut` configuration, the adapter calls the Fabric REST API to create a shortcut in the Lakehouse's `Tables` folder
2. For Iceberg sources, metadata virtualization automatically makes the table queryable as Delta
3. The source becomes available as a regular table — no view wrapper needed (unlike `OPENROWSET`)

#### Querying from T-SQL (Data Warehouse)

Once a shortcut exists in a Lakehouse, T-SQL models in the Data Warehouse can query it via cross-database three-part naming:

```sql
select *
from my_lakehouse.dbo.customer_events
```

### Implementation steps

1. **Shortcut creation macro** — A `fabric__create_shortcut` macro that calls the Fabric REST API to create shortcuts. Follows the same pattern as the existing `fabric_api_client.py`.
2. **dbt-external-tables integration** — Override `stage_external_sources` to handle `shortcut` configurations alongside existing `OPENROWSET` configurations.
3. **Idempotent operations** — Use the `shortcutConflictPolicy: CreateOrOverwrite` API parameter to make the operation safe for repeated runs.
4. **Metadata virtualization check** — Warn if Iceberg shortcuts are configured but metadata virtualization is not enabled at the workspace level.
5. **Connection management** — Fabric Cloud Connections (required for external shortcuts) must be pre-created in the Fabric portal. The adapter references them by ID.
6. **Shortcut cleanup** — Optionally delete shortcuts when sources are removed, similar to `ext_full_refresh` behavior.

### Limitations to document

- Shortcut creation requires `OneLake.ReadWrite.All` delegated scope
- External shortcuts (S3, GCS) are read-only — they work for source tables but not for materializations
- Maximum 100,000 shortcuts per Fabric item
- Delta table names in shortcuts cannot contain spaces
- Iceberg partition transforms `bucket[N]`, `truncate[W]`, and `void` are not supported in metadata virtualization

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

### Proposed approach

There are two integration directions, each serving a different use case:

#### Direction 1: Consume mirrored catalogs as dbt sources

When an external catalog (e.g., Unity Catalog) is mirrored into Fabric, its tables are already queryable via the auto-generated SQL analytics endpoint. The adapter can expose these as dbt sources by resolving table names through cross-database queries.

```yaml title="sources.yml"
sources:
  - name: databricks_catalog
    database: mirrored_unity_catalog  # Name of the mirrored catalog item in Fabric
    schema: production
    tables:
      - name: customers
      - name: orders
      - name: products
```

This already works today with manual configuration. The adapter improvement would be:

- **Auto-discovery** — A macro that queries the mirrored catalog's SQL analytics endpoint metadata to generate `sources.yml` entries automatically
- **Freshness checks** — Enable `dbt source freshness` on mirrored tables by querying the SQL analytics endpoint's `sys.tables` metadata
- **Documentation** — Guide for setting up mirrored catalogs as dbt sources

#### Direction 2: Expose Fabric tables via IRC for external consumers

This is relevant when Fabric is the source of truth and external tools (Snowflake, Databricks, DuckDB) need to consume dbt-managed tables. The OneLake IRC endpoint already exposes all Lakehouse tables automatically. The adapter improvement would be:

- **Metadata virtualization configuration** — A post-hook macro that ensures Delta-to-Iceberg virtualization is enabled for the workspace, so that external consumers can read dbt-materialized tables as Iceberg
- **IRC endpoint documentation** — Document how to configure external tools to read from the OneLake IRC endpoint, including authentication setup
- **Catalog registration macro** — A `register_iceberg_catalog` run-operation that outputs the IRC endpoint URL and configuration for common consumers (Snowflake catalog integration, Spark Iceberg catalog, DuckDB)

#### Direction 3: Direct catalog API access from the adapter

For advanced use cases, the adapter could directly call the OneLake table APIs (IRC or Unity Catalog Open API) to discover tables and their schemas, without requiring catalog mirroring:

```yaml title="sources.yml"
sources:
  - name: external_lakehouse
    meta:
      catalog_api: iceberg
      workspace: other_workspace
      lakehouse: analytics_lakehouse
    schema: gold
    tables:
      - name: customers
      - name: orders
```

The adapter would use the IRC endpoint to list available tables and resolve their schemas at compile time.

### Implementation steps

**Phase 1: Mirrored catalog sources (lowest effort, highest value)**

1. **Documentation** — Write a guide for using mirrored catalogs (Unity Catalog, Dremio) as dbt sources via cross-database queries
2. **Source auto-discovery macro** — `generate_mirrored_catalog_sources` run-operation that queries a mirrored catalog's metadata and generates `sources.yml`
3. **Source freshness** — Test and document `dbt source freshness` with mirrored catalog tables

**Phase 2: IRC endpoint documentation and helpers**

1. **Document the OneLake IRC endpoint** — How external tools can read dbt-managed Fabric tables as Iceberg
2. **Catalog registration macro** — Generate configuration snippets for Snowflake, Spark, and DuckDB
3. **Metadata virtualization helper** — Check/enable Delta-to-Iceberg virtualization via a run-operation

**Phase 3: Direct catalog API integration (future)**

1. **IRC client** — Python client for the OneLake Iceberg REST Catalog API (follows the `PurviewClient` pattern)
2. **Source resolution** — Resolve source table metadata (schema, columns) from the IRC endpoint at compile time
3. **Cross-workspace refs** — Enable `ref()` to resolve tables in other Fabric workspaces via the catalog API
