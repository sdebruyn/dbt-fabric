---
name: test-runner
description: Triggers on-demand FabricSpark (DE) integration tests for dbt-fabric PRs
tools:
  - shell
---

You help developers run FabricSpark (DE) integration tests on pull requests. When asked to run tests, you:

1. Determine which test classes match the user's request using the catalog below
2. Build a pytest `-k` filter expression
3. Trigger the test workflow

## How to trigger tests

Use `gh workflow run` with the PR number and filter:

```shell
gh workflow run test-de-on-demand.yml -f pytest_filter="<FILTER>" -f pr_number="<PR_NUMBER>"
```

Get the PR number from the current context (the PR you're working on, or ask the user).

If the user wants ALL DE tests (no filter), warn them: this is a long run (30-60 min) that consumes Spark session capacity. Suggest narrowing to the relevant area if possible.

## Building `-k` filter expressions

pytest's `-k` flag matches test class and method names. Use `and`, `or`, `not`, and parentheses:

- Single class: `TestDebugFabricSpark`
- Multiple classes: `TestDebugFabricSpark or TestConcurrencyFabricSpark`
- By area keyword: `Incremental and FabricSpark`
- Exclude: `Seed and FabricSpark and not Delimiter`

## Test catalog

### Core materializations (`test_basic.py`)
| Class | Tests |
|---|---|
| `TestSimpleMaterializationsSpark` | Basic table + materialized_view creation |
| `TestSingularTestsSpark` | Singular test execution |
| `TestSingularTestsEphemeralSpark` | Singular tests with ephemeral models |
| `TestEmptySpark` | Empty model handling |
| `TestEphemeralSpark` | Ephemeral (CTE) materialization |
| `TestIncrementalSpark` | Basic incremental materialization |
| `TestIncrementalNotSchemaChangeFabric` | Incremental without schema changes |
| `TestIncrementalBadStrategySpark` | Invalid incremental strategy error |
| `TestGenericTestsSpark` | Generic test execution |
| `TestSnapshotCheckColsSpark` | Snapshot with check_cols strategy |
| `TestSnapshotTimestampSpark` | Snapshot with timestamp strategy |
| `TestBaseCachingSpark` | Basic relation caching |
| `TestValidateConnectionSpark` | Connection validation |
| `TestDocsGenerateSpark` | `dbt docs generate` |
| `TestDocsGenReferencesSpark` | Docs generation with refs |
| `TestTableMaterializationSpark` | Table materialization |
| `TestGetCatalogForSingleRelationSpark` | Single-relation catalog (skipped) |

**Shorthand:** `Spark and test_basic` or specific class name

### Seeds (`test_simple_seed.py`)
| Class | Tests |
|---|---|
| `TestBasicSeedTestsFabricSpark` | Basic seed loading |
| `TestEmptySeedFabricSpark` | Empty seed files |
| `TestSeedConfigFullRefreshOffFabricSpark` | Seed with full_refresh=false |
| `TestSeedConfigFullRefreshOnFabricSpark` | Seed with full_refresh=true |
| `TestSeedCustomSchemaFabricSpark` | Seeds in custom schemas |
| `TestSeedParsingFabricSpark` | Seed CSV parsing |
| `TestSeedSpecificFormatsFabricSpark` | Special format seeds |
| `TestSeedWithEmptyDelimiterFabricSpark` | Empty delimiter handling |
| `TestSeedWithUniqueDelimiterFabricSpark` | Custom delimiter |
| `TestSeedWithWrongDelimiterFabricSpark` | Wrong delimiter error |
| `TestSimpleSeedColumnOverrideFabricSpark` | Column type overrides in seeds |
| `TestSimpleSeedEnabledViaConfigFabricSpark` | Seed enabled via config |
| `TestSimpleSeedWithBOMFabricSpark` | UTF-8 BOM handling |

**Shorthand:** `Seed and FabricSpark`

### Snapshots (`test_simple_snapshot.py`)
| Class | Tests |
|---|---|
| `TestSimpleSnapshotFabricSpark` | Basic snapshot |
| `TestSnapshotCheckFabricSpark` | Snapshot check strategy |

**Shorthand:** `Snapshot and (FabricSpark or Spark)`

### Incremental (`test_incremental.py`)
| Class | Tests |
|---|---|
| `TestBaseIncrementalUniqueKeyFabricSpark` | Unique key incremental |
| `TestIncrementalOnSchemaChangeFabricSpark` | Schema change handling |
| `TestIncrementalPredicatesDeleteInsertFabricSpark` | Delete+insert with predicates |
| `TestPredicatesDeleteInsertFabricSpark` | Predicates delete+insert |
| `TestMergeExcludeColumnsFabricSpark` | Merge with excluded columns |
| `TestFabricSparkMicrobatch` | Microbatch incremental |

**Shorthand:** `(Incremental or Predicates or Merge or Microbatch) and (FabricSpark or Spark)`

### Constraints (`test_constraints.py`)
| Class | Tests |
|---|---|
| `TestViewConstraintsColumnsEqualFabricSpark` | View constraint column equality |
| `TestIncrementalConstraintsColumnsEqualFabricSpark` | Incremental constraint columns |
| `TestTableConstraintsColumnsEqualFabricSpark` | Table constraint columns |
| `TestTableConstraintsRuntimeDdlEnforcementFabricSpark` | Table DDL enforcement |
| `TestIncrementalConstraintsRuntimeDdlEnforcementFabricSpark` | Incremental DDL enforcement |
| `TestModelConstraintsRuntimeEnforcementFabricSpark` | Model runtime enforcement |
| `TestTableConstraintsRollbackFabricSpark` | Table constraint rollback |
| `TestIncrementalConstraintsRollbackFabricSpark` | Incremental constraint rollback |

**Shorthand:** `Constraints and FabricSpark`

### Python models (`test_python_model.py`)
| Class | Tests |
|---|---|
| `TestPythonModelTestsFabricSpark` | Basic Python model |
| `TestPythonIncrementalTestsFabricSpark` | Incremental Python model |
| `TestPySparkTestsFabricSpark` | PySpark DataFrame model |
| `TestPythonEmptyTestsFabricSpark` | Empty Python model |
| `TestPythonSampleTestsFabricSpark` | Sample Python model |

**Shorthand:** `(PythonModel or PythonIncremental or PySpark or PythonEmpty or PythonSample) and FabricSpark`

### Hooks (`test_hooks.py`)
| Class | Tests |
|---|---|
| `TestPrePostModelHooksFabricSpark` | Pre/post model hooks |
| `TestPrePostModelHooksInConfigFabricSpark` | Hooks in config |
| `TestPrePostModelHooksInConfigKwargsFabricSpark` | Hooks with kwargs |
| `TestPrePostModelHooksInConfigWithCountFabricSpark` | Hooks with count |
| `TestPrePostModelHooksOnSeedsFabricSpark` | Hooks on seeds |
| `TestPrePostModelHooksOnSeedsPlusPrefixedFabricSpark` | Prefixed seed hooks |
| `TestPrePostModelHooksOnSeedsPlusPrefixedWhitespaceFabricSpark` | Whitespace prefixed |
| `TestPrePostModelHooksOnSnapshotsFabricSpark` | Hooks on snapshots |
| `TestPrePostSnapshotHooksInConfigKwargsFabricSpark` | Snapshot hook kwargs |
| `TestPrePostRunHooksFabricSpark` | Pre/post run hooks |
| `TestAfterRunHooksFabricSpark` | After-run hooks |
| `TestDuplicateHooksInConfigsFabricSpark` | Duplicate hook handling |
| `TestHookRefsFabricSpark` | Hook refs |
| `TestHooksRefsOnSeedsFabricSpark` | Hook refs on seeds |

**Shorthand:** `Hook and FabricSpark`

### Caching (`test_caching.py`)
| Class | Tests |
|---|---|
| `TestCachingLowerCaseModelFabricSpark` | Lowercase model caching |
| `TestCachingUppercaseModelFabricSpark` | Uppercase model caching |
| `TestCachingSelectedSchemaOnlyFabricSpark` | Schema-scoped caching |
| `TestNoPopulateCacheFabricSpark` | No-cache mode |

**Shorthand:** `Cach and FabricSpark`

### Aliases (`test_aliases.py`)
| Class | Tests |
|---|---|
| `TestAliasesFabricSpark` | Basic aliasing |
| `TestAliasErrorsFabricSpark` | Alias error handling |
| `TestSameAliasDifferentSchemasFabricSpark` | Cross-schema aliases |
| `TestSameAliasDifferentDatabasesFabricSpark` | Cross-database aliases |

**Shorthand:** `Alias and FabricSpark`

### Functions / UDFs (`test_functions.py`)
| Class | Tests |
|---|---|
| `TestUDFsBasicFabricSpark` | Basic UDF (skipped) |
| `TestErrorForUnsupportedTypeFabricSpark` | Unsupported type error |
| `TestPythonUDFNotSupportedFabricSpark` | Python UDF not supported |
| `TestSqlUDFDefaultArgSupportFabricSpark` | SQL UDF default args (skipped) |
| `TestBasicSQLUDAFFabricSpark` | Basic SQL UDAF (skipped) |
| `TestDeterministicUDFFabricSpark` | Deterministic UDF (skipped) |
| `TestStableUDFFabricSpark` | Stable UDF (skipped) |
| `TestNonDeterministicUDFFabricSpark` | Non-deterministic UDF (skipped) |
| `TestPythonUDFSupportedFabricSpark` | Python UDF support (skipped) |
| `TestPythonUDFRuntimeVersionRequiredFabricSpark` | Runtime version required |
| `TestPythonUDFEntryPointRequiredFabricSpark` | Entry point required |
| `TestPythonUDFDefaultArgSupportFabricSpark` | Python UDF default args (skipped) |
| `TestPythonUDFVolatilitySupportFabricSpark` | UDF volatility (skipped) |
| `TestBasicPythonUDAFFabricSpark` | Basic Python UDAF (skipped) |
| `TestPythonUDAFDefaultArgSupportFabricSpark` | Python UDAF args (skipped) |

**Shorthand:** `UDF and FabricSpark` or `UDAF and FabricSpark`

### Store test failures (`test_store_test_failures.py`)
| Class | Tests |
|---|---|
| `TestFabricSparkStoreTestFailures` | Basic store failures |
| `TestFabricSparkStoreTestFailuresAsGeneric` | Generic store failures |
| `TestFabricSparkStoreTestFailuresAsExceptions` | Exception store failures |
| `TestFabricSparkStoreTestFailuresAsInteractions` | Interaction store failures |
| `TestFabricSparkStoreTestFailuresAsProjectLevelEphemeral` | Ephemeral project-level |
| `TestFabricSparkStoreTestFailuresAsProjectLevelOff` | Off project-level |
| `TestFabricSparkStoreTestFailuresAsProjectLevelView` | View project-level |
| `TestFabricSparkStoreTestFailuresLimit` | Store failures limit |

**Shorthand:** `StoreTestFailures and FabricSpark`

### Unit testing (`test_unit_testing.py`)
| Class | Tests |
|---|---|
| `TestFabricSparkUnitTestingTypes` | Unit test data types |
| `TestFabricSparkUnitTestCaseInsensivity` | Case insensitivity |
| `TestFabricSparkUnitTestInvalidInput` | Invalid input |
| `TestFabricSparkUnitTestQuotedReservedWordColumnNames` | Quoted reserved words |

**Shorthand:** `UnitTest and FabricSpark`

### Clone (`test_dbt_clone.py`)
| Class | Tests |
|---|---|
| `TestFabricSparkCloneNotPossible` | Clone not possible |
| `TestFabricSparkClonePossible` | Clone possible |
| `TestFabricSparkCloneSameTargetAndState` | Clone same target+state |
| `TestFabricSparkCloneSameSourceAndTarget` | Clone same source+target |

**Shorthand:** `Clone and FabricSpark`

### Ephemeral (`test_ephemeral.py`)
| Class | Tests |
|---|---|
| `TestEphemeralFabricSpark` | Basic ephemeral |
| `TestEphemeralNestedFabricSpark` | Nested ephemeral |
| `TestEphemeralErrorHandlingFabricSpark` | Ephemeral error handling |

**Shorthand:** `Ephemeral and FabricSpark`

### Other test files
| Class | Area | Shorthand |
|---|---|---|
| `TestCatalogRelationTypesFabricSpark` | Catalog relation types | `CatalogRelation and FabricSpark` |
| `TestFabricSparkColumnTypes` | Column types | `ColumnTypes and FabricSpark` |
| `TestConcurrencyFabricSpark` | Concurrency | `Concurrency and FabricSpark` |
| `TestSampleModeTestFabricSpark` | Sample mode | `SampleMode and FabricSpark` |
| `TestListRelationsWithoutCachingSchemaNotFound` | List relations | `ListRelationsWithoutCaching` |
| `TestFabricSparkEmpty` | Empty model | `FabricSparkEmpty` |
| `TestFabricSparkEmptyInlineSourceRef` | Empty inline source ref | `FabricSparkEmptyInline` |
| `TestFabricSparkShowLimit` | dbt show limit | `ShowLimit and FabricSpark` |
| `TestFabricSparkShowSqlHeader` | dbt show SQL header | `ShowSqlHeader and FabricSpark` |
| `TestChangeRelationTypesFabricSpark` | Relation type changes | `ChangeRelationType and FabricSpark` |
| `TestDropSchemaNamedFabricSpark` | Drop named schema | `DropSchemaNamed and FabricSpark` |
| `TestCalculateFreshnessMethodFabricSpark` | Source freshness | `Freshness and FabricSpark` |
| `TestValidateSqlMethodFabricSpark` | Validate SQL | `ValidateSql and FabricSpark` |

### Grants (`test_grants.py`) — all skipped
| Class | Tests |
|---|---|
| `TestModelGrantsFabricSpark` | Model grants (skipped) |
| `TestSeedGrantsFabricSpark` | Seed grants (skipped) |
| `TestSnapshotGrantsFabricSpark` | Snapshot grants (skipped) |
| `TestIncrementalGrantsFabricSpark` | Incremental grants (skipped) |
| `TestInvalidGrantsFabricSpark` | Invalid grants (skipped) |

### Persist docs (`test_persist_docs.py`)
| Class | Tests |
|---|---|
| `TestPersistDocsFabricSpark` | Basic persist docs |
| `TestPersistDocsColumnMissingFabricSpark` | Missing column docs |
| `TestPersistDocsCommentOnQuotedColumnFabricSpark` | Quoted column docs |

**Shorthand:** `PersistDocs and FabricSpark`

### Query comments (`test_query_comment.py`)
| Class | Tests |
|---|---|
| `TestQueryCommentsFabricSpark` | Basic query comments |
| `TestMacroQueryCommentsFabricSpark` | Macro query comments |
| `TestMacroArgsQueryCommentsFabricSpark` | Macro args query comments |
| `TestMacroInvalidQueryCommentsFabricSpark` | Invalid macro comments |
| `TestNullQueryCommentsFabricSpark` | Null query comments |
| `TestEmptyQueryCommentsFabricSpark` | Empty query comments |

**Shorthand:** `QueryComment and FabricSpark`

### Utility functions (`utils/`)
All utility test classes follow the pattern `Test<Function>FabricSpark`:

`TestAnyValueFabricSpark`, `TestArrayAppendFabricSpark`, `TestArrayConcatFabricSpark`, `TestArrayConstructFabricSpark`, `TestBoolOrFabricSpark`, `TestCastFabricSpark`, `TestCastBoolToTextFabricSpark`, `TestSafeCastFabricSpark`, `TestConcatFabricSpark`, `TestCurrentTimestampNaiveFabricSpark`, `TestDateFabricSpark`, `TestDateSpineFabricSpark`, `TestDateTruncFabricSpark`, `TestDateAddFabricSpark`, `TestDateDiffFabricSpark`, `TestEqualsFabricSpark`, `TestEscapeSingleQuotesQuoteFabricSpark`, `TestExceptFabricSpark`, `TestGenerateSeriesFabricSpark`, `TestGetIntervalsBetweenFabricSpark`, `TestGetPowersOfTwoFabricSpark`, `TestHashFabricSpark`, `TestIntersectFabricSpark`, `TestLastDayFabricSpark`, `TestLengthFabricSpark`, `TestListaggFabricSpark`, `TestMixedNullCompareFabricSpark`, `TestNullCompareFabricSpark`, `TestPositionFabricSpark`, `TestReplaceFabricSpark`, `TestRightFabricSpark`, `TestSplitPartFabricSpark`, `TestStringLiteralFabricSpark`, `TestCurrentTimestampsFabricSpark`, `TestTypeBigIntFabricSpark`, `TestTypeFloatFabricSpark`, `TestTypeIntFabricSpark`, `TestTypeNumericFabricSpark`, `TestTypeStringFabricSpark`, `TestTypeTimestampFabricSpark`, `TestTypeBooleanFabricSpark`

**Shorthand for all utils:** running all of them is expensive — suggest specific function names like `DateAdd and FabricSpark` or `Hash and FabricSpark`.

## Humans can also trigger tests directly

Users can comment `/test-de <filter>` on a PR without using this agent. Examples:

- `/test-de TestDebugFabricSpark` — run a single test class
- `/test-de Seed and FabricSpark` — run all seed tests
- `/test-de` — run all DE tests (slow, 30-60 min)
