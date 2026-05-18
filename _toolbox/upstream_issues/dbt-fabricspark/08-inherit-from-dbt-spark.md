# Proposal: inherit from `dbt-spark` instead of being a standalone `SQLAdapter`

**Repo:** `microsoft/dbt-fabricspark`
**Labels (suggested):** `proposal`, `architecture`, `priority/high`

> [x] **Validated by maintainer** — code refs, line numbers, and claims confirmed against upstream HEAD

## Summary

[`FabricSparkAdapter`](https://github.com/microsoft/dbt-fabricspark/blob/d315a56/src/dbt/adapters/fabricspark/impl.py) is currently a standalone `SQLAdapter`. It reimplements — or omits — the Spark-flavoured materializations, incremental strategies, column type handling, constraint handling, and Python-model API that `dbt-spark` already ships and that any Spark-backed dbt adapter is expected to inherit.

The Spark engine the Fabric Lakehouse runs is, for dbt's purposes, the same engine `dbt-spark` already targets. The work of mapping dbt operations onto Spark SQL has been done once, in `dbt-spark`. There is no engineering case for redoing it independently here.

This proposal: have `FabricSparkAdapter` inherit from `dbt-spark`'s `SparkAdapter`, the same way Databricks does. Ship only the Fabric-specific bits — connection layer (Livy), authentication, Fabric workspace/lakehouse naming, the engine quirks that genuinely differ from generic Spark — and inherit the rest.

## What `dbt-spark` already gives you

The package (`https://github.com/dbt-labs/dbt-adapters/tree/main/dbt-spark`) ships:

- The full Spark materializations: table, view, incremental, snapshot, materialized view.
- All Spark-flavoured incremental strategies: `merge`, `append`, `insert_overwrite`, `microbatch`.
- Spark-aware column type handling.
- Constraint handling.
- The Spark Python-model API.
- An opinionated `SparkAdapter` base class that codifies how a Spark engine plugs into dbt.

The entire point of the package is to be inherited from. Every dbt-core minor that ships new `Base*` test classes for Spark is satisfied by `dbt-spark` first; downstream adapters that inherit from it pick up the work automatically.

## Precedent: this is what Databricks does

This is not a theoretical pattern. `dbt-databricks` — Databricks' own production adapter, maintained by Databricks themselves — depends on `dbt-spark>=1.10.0,<1.11.0` in [its `pyproject.toml`](https://github.com/databricks/dbt-databricks/blob/main/pyproject.toml) and declares `class DatabricksAdapter(SparkAdapter):` in [`dbt/adapters/databricks/impl.py:230`](https://github.com/databricks/dbt-databricks/blob/main/dbt/adapters/databricks/impl.py).

Databricks does not reimplement Spark adapter behaviour because that is not where their value lies — their value is in the Databricks-specific extensions on top. Whatever Microsoft's competitive position on Databricks is, the engineering pattern Databricks uses for *their* dbt adapter is the one worth copying: build on the shared foundation, ship only the platform-specific bits.

## What the current standalone-`SQLAdapter` design costs

`microsoft/dbt-fabricspark` has no `dbt-spark` dependency (see [`pyproject.toml`](https://github.com/microsoft/dbt-fabricspark/blob/d315a56/pyproject.toml)). It is a standalone `SQLAdapter`. Every macro, materialization, type rule, incremental strategy, and Python-model path therefore has to be implemented and maintained by hand.

The compounding cost is structural:

- Every `dbt-spark` release that ships a fix or a new feature silently widens the gap. The same fix has to be re-implemented here or skipped.
- Every dbt-core minor that adds a `Base*` test class for Spark requires a manual port of whatever `dbt-spark` did to satisfy it. Right now those ports either don't happen or happen late.
- Bugs already fixed upstream in `dbt-spark` re-occur here because the code paths are independent.
- Feature parity with what dbt users on Spark expect (e.g. `insert_overwrite`, microbatch, materialized views, full snapshot semantics) is on the maintainer's plate forever, instead of being picked up by a version bump.

This is the maintenance treadmill the inheritance pattern exists to eliminate. A year of `dbt-spark` improvements that an inherited adapter gets for free is a year of work a standalone adapter has to do manually — and largely doesn't, which is exactly why a comparable feature set isn't there.

## What the change looks like

Two things change in the package:

1. Add `dbt-spark` as a dependency in [`pyproject.toml`](https://github.com/microsoft/dbt-fabricspark/blob/d315a56/pyproject.toml).
2. Change `class FabricSparkAdapter(SQLAdapter):` in [`src/dbt/adapters/fabricspark/impl.py`](https://github.com/microsoft/dbt-fabricspark/blob/d315a56/src/dbt/adapters/fabricspark/impl.py) to `class FabricSparkAdapter(SparkAdapter):` (importing from `dbt.adapters.spark`).

The macros under `src/dbt/include/fabricspark/macros/` then act as overrides on top of `dbt-spark`'s macros. Most of them can be deleted because the inherited versions are correct for the Fabric Lakehouse engine. The ones that need to stay are the genuinely Fabric-specific cases — the cross-workspace `workspace.database.schema` naming, the Fabric-only Materialized Lake View handling, etc.

Python's multiple inheritance also makes this composable with a shared `BaseFabricAdapter` (if such a base exists, or is extracted) so the FabricSpark adapter can extend `SparkAdapter` *and* the cross-adapter Fabric base at the same time:

```python
class FabricSparkAdapter(BaseFabricAdapter, SparkAdapter):
    ...
```

That gives you the dbt-spark machinery and the cross-adapter Fabric code (auth, REST client, Livy session reuse, workspace resolution) in one class.

## What this proposal is not

- It is not "rewrite everything." Most of the engine-facing macro and adapter code can be deleted, not rewritten.
- It is not Databricks-specific. The `dbt-spark` package is the open-source reference Spark adapter; Databricks builds on it, but `dbt-spark` predates the Databricks adapter and is independent of it.
- It is not a one-line change. Inheriting from `SparkAdapter` will surface a number of behavioral differences between the current standalone implementation and the inherited Spark defaults. Each one is a discrete decision: accept the upstream behaviour (usually the right call) or override with a documented Fabric-specific reason.

## Suggested path

1. Add `dbt-spark` to `pyproject.toml` as a dependency.
2. Switch the adapter class to inherit from `SparkAdapter`.
3. Delete every macro under `dbt/include/fabricspark/macros/` whose behaviour matches the `dbt-spark` equivalent. Keep only Fabric-specific overrides.
4. Run `dbt-tests-adapter` against the inherited adapter to surface the behavioral differences and triage them one by one.
5. For each difference: either accept the inherited behaviour, or add a `fabricspark__*` override with an inline comment stating what differs from the upstream Spark macro and why (a Fabric Lakehouse engine quirk, a Lakehouse-specific Delta limitation, etc.).

[The fork](https://github.com/sdebruyn/dbt-fabric) has done this work. The references in `microsoft/dbt-fabricspark` for what to keep vs. what to inherit are visible at `https://github.com/sdebruyn/dbt-fabric/tree/main/src/dbt/include/fabricspark/macros` — most of the file count is gone, and what remains is annotated with what it overrides and why.

