# Microsoft Purview integration

This adapter can sync dbt metadata to [Microsoft Purview Data Catalog](https://learn.microsoft.com/en-us/purview/), enriching your existing scanned assets with descriptions, business metadata, and lineage from your dbt project.

## Why this integration

Microsoft Purview has a [built-in integration with Microsoft Fabric](https://learn.microsoft.com/en-us/fabric/governance/microsoft-purview-fabric) that scans your Fabric workspace and discovers items like Warehouses, Lakehouses, Notebooks, and Pipelines. However, this built-in scanner has significant limitations when it comes to the metadata that dbt users care about:

| Capability | Built-in Purview scanner | dbt Purview sync |
|---|---|---|
| **Table discovery** | Lakehouse tables only (preview). Data Warehouse tables are [not scanned as sub-items](https://learn.microsoft.com/en-us/purview/data-map-lineage-fabric). | Works with any table entity already in Purview, regardless of how it was discovered. |
| **Column discovery** | Lakehouse column names and data types (preview). | N/A — works with columns already discovered by the scanner. |
| **Table descriptions** | Not populated. Must be [manually entered](https://learn.microsoft.com/en-us/purview/data-gov-classic-metadata-curation) in the Purview portal per table. | Automatically pushed from dbt model YAML files after every run. |
| **Column descriptions** | Not populated. Must be manually entered per column. | Automatically pushed from dbt column YAML files after every run. |
| **Table-level lineage** | Not supported. The scanner only captures [item-level lineage](https://learn.microsoft.com/en-us/purview/data-map-lineage-fabric) (e.g., Lakehouse → Notebook → Lakehouse), not which specific table was derived from which other tables. | Full table-level lineage graph based on dbt's `ref()` and `source()` dependencies. |
| **Business metadata** | Not populated. No built-in mechanism to attach tags, test results, or custom metadata to table entities. | Automatically creates a `dbt_metadata` business metadata type with model ID, tags, materialization, test names, test results, custom meta, and sync timestamp. |
| **Automation** | Runs on a scan schedule configured in Purview. | Runs automatically after every `dbt run` via `on-run-end` hook, or on-demand via `dbt run-operation`. |

In short: the built-in scanner discovers _what exists_ in Fabric (table names, column schemas). This dbt integration adds the context that the scanner cannot provide: _what each table means_ (descriptions), _how tables relate to each other_ (lineage), and _what guarantees are in place_ (tests, tags, metadata).

The two are complementary — the scanner creates the entities in Purview, and the dbt sync enriches them.

## How it works

When Purview scans your Fabric workspace, it discovers tables and views but doesn't know about the rich metadata in your dbt project: model descriptions, column documentation, tests, tags, and lineage. The Purview sync bridges this gap by:

1. **Matching** each dbt model to its corresponding Purview entity (table/view) via the Purview Discovery API
2. **Enriching** the entity with dbt descriptions (on both tables and columns)
3. **Adding business metadata** like dbt tags, materialization type, test results, and custom meta
4. **Creating lineage** between tables using dbt's dependency graph

The sync writes to `userDescription` (not `description`), so it never overwrites metadata set by Purview scanners.

## Configuration

Add the `purview_endpoint` to your target in `profiles.yml`:

```yaml
my_project:
  target: dev
  outputs:
    dev:
      type: fabric  # or fabricspark
      # ... existing configuration ...
      purview_endpoint: "https://your-account.purview.azure.com"
```

You can find the endpoint URL in the Azure portal under your Purview account's Properties page (labeled "Atlas endpoint") or in the Purview governance portal settings.

!!! tip "Alias"
    You can also use `purview` as an alias for `purview_endpoint`.

### Authentication

The Purview integration reuses the same authentication method configured for your Fabric connection. No additional authentication setup is needed. The identity must have **Data Curator** and **Data Reader** roles in the Purview account's root collection.

All [authentication methods](authentication.md) supported by the adapter work with Purview.

## Usage

### Automatic sync after every run

Add the macro to your `dbt_project.yml` as an `on-run-end` hook:

```yaml
on-run-end:
  - "{{ purview_sync() }}"
```

This syncs metadata for all models that were part of the run.

### Manual sync

Run the sync manually as a dbt operation:

```shell
dbt run-operation purview_sync
```

This syncs metadata for all models in the project, regardless of whether they were recently run.

### Options

The `purview_sync` macro accepts these parameters:

| Parameter | Default | Description |
|---|---|---|
| `sync_descriptions` | `true` | Push model and column descriptions to Purview |
| `sync_lineage` | `true` | Create lineage relationships in Purview |
| `sync_metadata` | `true` | Push business metadata (tags, tests, materialization) |

Example with options:

```yaml
# Only sync descriptions, skip lineage and metadata
on-run-end:
  - "{{ purview_sync(sync_lineage=false, sync_metadata=false) }}"
```

Or via the CLI:

```shell
dbt run-operation purview_sync --args '{sync_lineage: false}'
```

## What gets synced

### Descriptions

| Source | Target |
|---|---|
| Model `description` | `userDescription` on the table/view entity |
| Column `description` | `userDescription` on the column entity |

### Business metadata

A custom business metadata type called `dbt_metadata` is automatically created in Purview. It contains:

| Attribute | Source | Example |
|---|---|---|
| `dbt_model_id` | Model unique ID | `model.my_project.orders` |
| `dbt_tags` | Model tags | `finance,daily` |
| `dbt_materialization` | Materialization type | `incremental` |
| `dbt_meta` | Custom meta (JSON) | `{"owner": "data-team"}` |
| `dbt_tests` | Test names on model | `not_null_id,unique_id` |
| `dbt_test_status` | Test results from last run | `all_passed` or `2/3 passed` |
| `dbt_last_sync` | Sync timestamp | `2026-01-15T10:30:00+00:00` |

### Lineage

For each dbt model with upstream dependencies, the sync creates:

- A `dbt_transformation` entity representing the dbt transformation
- `dataset_process_inputs` relationships from upstream tables to the process
- `process_dataset_outputs` relationships from the process to the output table

This shows up in Purview's lineage view as a graph of how data flows through your dbt models.

## Entity matching

The sync finds existing Purview entities by searching for tables matching the dbt model's name, schema, and database. This works regardless of how Purview discovered the entities or what entity types they have (e.g., `fabric_lakehouse_table`, `azure_sql_table`).

If a dbt model cannot be matched to a Purview entity (e.g., the table hasn't been scanned yet, or it's an ephemeral model), it's skipped with a log message.

## Supported adapters

The Purview integration works with both adapter types:

- **FabricSpark** (Lakehouse) — matches `fabric_lakehouse_table` entities discovered by Purview's Fabric workspace scan. This requires [Lakehouse sub-item metadata scanning](https://learn.microsoft.com/en-us/purview/register-scan-fabric-tenant) to be enabled.
- **Fabric** (Data Warehouse) — Purview currently scans Fabric Data Warehouses at the item level only (`fabric_data_warehouse`), without indexing individual tables. To get table-level entities, register the Data Warehouse's SQL analytics endpoint as an Azure SQL data source in Purview. The resulting `azure_sql_table` entities are matched by the sync.
