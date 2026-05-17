# dbt-project-evaluator

**Tested version:** 1.2.4 | **Integration tested:** Yes

[dbt-project-evaluator](https://github.com/dbt-labs/dbt-project-evaluator) analyzes your dbt project structure and flags potential issues: missing documentation, unused sources, DAG problems, and modeling best-practice violations.

## Dispatch configuration

```yaml
dispatch:
  - macro_namespace: dbt_project_evaluator
    search_order: ['your_project_name', 'dbt', 'dbt_project_evaluator']
```

## Macro compatibility

Legend: ✅ = supported on Fabric, ❌ = not supported on Fabric

Macros marked with **(override)** have a T-SQL-compatible override in this adapter. All other supported macros work without any adapter-specific override.

### Graph introspection

| Macro | Status | Notes |
|---|---|---|
| `get_node_values` | ✅ **(override)** | Casts booleans to BIT (1/0) instead of TRUE/FALSE literals |
| `get_relationship_values` | ✅ **(override)** | Casts booleans to BIT instead of TRUE/FALSE literals |
| `get_source_values` | ✅ **(override)** | Casts booleans to BIT (1/0) instead of TRUE/FALSE literals |

### DAG analysis

| Macro | Status | Notes |
|---|---|---|
| `recursive_dag` | ✅ **(override)** | BIT booleans in recursive CTE; explicit column typing for T-SQL |

### Utilities

| Macro | Status | Notes |
|---|---|---|
| `loop_vars` | ✅ **(override)** | Uses `WHERE 1=0` instead of `LIMIT 0` for empty result sets |

## Notes

This package does not have an `integration_tests` subdirectory — it evaluates the project it is installed in. The integration test runs `dbt build` on a minimal project with this package installed and verifies all models compile and execute against Fabric.
