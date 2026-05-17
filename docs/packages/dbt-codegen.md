# dbt-codegen

**Tested version:** 0.14.1 | **Integration tested:** Yes

[dbt-codegen](https://github.com/dbt-labs/dbt-codegen) generates dbt model YAML, source YAML, base models, and unit test templates from your existing database schema.

## Dispatch configuration

```yaml
dispatch:
  - macro_namespace: codegen
    search_order: ['your_project_name', 'dbt', 'codegen']
```

## Macro compatibility

All dbt-codegen macros work on Fabric without adapter-specific overrides. The package queries `INFORMATION_SCHEMA` views which Fabric supports natively.

| Macro | Status | Notes |
|---|---|---|
| `generate_source` | :white_check_mark: | |
| `generate_model_yaml` | :white_check_mark: | |
| `generate_base_model` | :white_check_mark: | |
| `generate_model_import_ctes` | :white_check_mark: | |
| `generate_unit_test_template` | :white_check_mark: | |

## Notes

dbt-codegen depends on [dbt-utils](dbt-utils.md). Make sure you include the dbt-utils dispatch configuration as well:

```yaml
dispatch:
  - macro_namespace: dbt_utils
    search_order: ['your_project_name', 'dbt', 'dbt_utils']
  - macro_namespace: codegen
    search_order: ['your_project_name', 'dbt', 'codegen']
```
