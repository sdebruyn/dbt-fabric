# Upstream issue drafts

Issue drafts for `microsoft/dbt-fabric` and `microsoft/dbt-fabricspark`, derived from `_toolbox/PR_DESCRIPTION.md` and `_toolbox/FORK_ANALYSIS.md`.

**Status: drafts only.** None of these have been filed yet. The intent is to file the highest-priority items as upstream issues before opening the toolbox PR, so the PR can reference real issue numbers instead of hand-waving at "known bugs".

## How to use

- Each file is a standalone issue body. Title at the top, evidence in the body, suggested fix at the bottom.
- File:line references point at upstream HEAD as of 2026-05-18 (`microsoft/dbt-fabric` [`0de2190`](https://github.com/microsoft/dbt-fabric/tree/0de2190), `microsoft/dbt-fabricspark` [`d315a56`](https://github.com/microsoft/dbt-fabricspark/tree/d315a56)) and are linked as GitHub permalinks. Re-verify before filing if more time has passed.
- Reference fork commits are provided for the maintainer to compare against — useful when the maintainer wants to cherry-pick the fix.
- All issue bodies are in English (upstream convention).

## Validation tracker

Each issue body carries a `> [ ] Validated by maintainer` checkbox at the top. Sam confirms an issue after reading the file, opening the linked code, and confirming the claim. Update the tracker below as issues are validated.

### dbt-fabric

- [x] 01 — `varchar(8000)` silent string-truncation
- [x] 02 — Case-sensitive Fabric DWHs broken
- [x] 03 — `apply_grants` misses Entra-principal grants
- [x] 04 — Pre/post hooks fail (`commit;` emitted)
- [ ] 05 — CTAS via `EXEC('...')` breaks on apostrophes
- [ ] 06 — `get_response` drops warnings + statement ID
- [ ] 07 — `quote()` does not escape `]` (injection vector)
- [ ] 08 — pyodbc pooling silently disabled
- [ ] 09 — `USE [None];` emitted when `database=None`
- [ ] 10 — Incremental `--full-refresh` data-loss risk
- [ ] 11 — `microbatch` ignores `unique_key`
- [ ] 12 — `snapshot_merge_sql` UPDATE+INSERT instead of MERGE
- [ ] 13 — `delete_warehouse_snapshot` is a stub
- [ ] 14 — `apply_label` emits `log()` on every call
- [ ] 15 — `check_for_nested_cte` false positives
- [ ] 16 — PR #315 `login_timeout` is a no-op
- [ ] 17 — Warehouse snapshots via `atexit` + connection lifecycle
- [ ] 18 — Adapter-private `delete_condition` on `incremental`
- [ ] 19 — `list_relations` retry at wrong layer
- [ ] 20 — Module-level `_TOKEN` global

### dbt-fabricspark

- [ ] 01 — Six `__exit__` methods return `True`
- [ ] 02 — Hardcoded 2028 token expiry
- [ ] 03 — `tokenPrint=True` can leak bearer tokens
- [ ] 04 — `_getLivySQL` regex bug
- [ ] 05 — Global mutable state in Livy modules
- [ ] 06 — `atexit` handlers leak Livy sessions
- [ ] 07 — Dead code from Databricks ancestry
- [ ] 08 — Proposal: inherit from `dbt-spark`

## Priority guidance

Filing all 27 at once would be noise. Suggested staging:

**File first — data-loss / security / unusable-for-some-users (8):**
- dbt-fabric:
  - `01-varchar-8000-silent-truncation.md` — silent data truncation on hashes/keys
  - `02-case-sensitive-dwh-broken.md` — adapter unusable on CS collations
  - `04-pre-post-hooks-fail-with-commit.md` — entire feature broken
  - `07-identifier-quoting-not-escaped.md` — T-SQL injection vector
  - `10-incremental-full-refresh-data-loss-risk.md` — production data loss on transient failure
  - `13-delete-warehouse-snapshot-is-noop-stub.md` — silent failure
- dbt-fabricspark:
  - `01-exit-methods-return-true-swallow-exceptions.md` — silent failure throughout
  - `03-tokenprint-can-leak-bearer-token.md` — security risk

**File second — concrete bugs (10):**
- dbt-fabric: `03`, `05`, `06`, `08`, `09`, `11`, `14`, `15`, `16`
- dbt-fabricspark: `02`, `04`

**File third — design / refactor proposals (10):**
These are debatable and may invite long discussion. File only if the second batch is engaged with; otherwise hold them for the toolbox PR's "what we replaced" narrative.

- dbt-fabric: `12`, `17`, `18`, `19`, `20`
- dbt-fabricspark: `05`, `06`, `07`, `08`

`dbt-fabricspark/08` (inherit from `dbt-spark`) is the structural one — file it last because it's the meta-fix that the other FabricSpark bugs flow from, and engagement with the individual bugs first gives the proposal a concrete factual basis to argue from.

## Full index

### microsoft/dbt-fabric

| # | Title | Severity | Type |
|---|---|---|---|
| 01 | `varchar(8000)` silent string-truncation in `FabricColumn` | high | bug, data-loss |
| 02 | Case-sensitive Fabric DWHs broken — missing `_make_match_kwargs` | high | bug |
| 03 | `apply_grants` misses Entra-principal grants, re-issues on every run | medium | bug |
| 04 | Pre/post hooks fail (`commit;` emitted by dbt-adapters default) | high | bug |
| 05 | CTAS via `EXEC('...')` silently breaks on embedded apostrophes | high | bug |
| 06 | `get_response` drops Fabric warnings and statement ID | medium | bug, observability |
| 07 | `FabricAdapter.quote()` does not escape `]` (T-SQL injection vector) | high | bug, security |
| 08 | pyodbc pooling silently disabled (missing `odbcversion = "3.8"`) | medium | bug, performance |
| 09 | `fabric__get_use_database_sql` emits invalid `USE [None];` | medium | bug |
| 10 | Incremental `--full-refresh` drop-then-recreate risks data loss | high | bug, data-loss |
| 11 | `fabric__get_incremental_microbatch_sql` ignores `unique_key` | medium | bug |
| 12 | `fabric__snapshot_merge_sql` is custom UPDATE+INSERT instead of MERGE | low | enhancement |
| 13 | `delete_warehouse_snapshot` is a `return True` stub | high | bug |
| 14 | `apply_label` macro emits a debug `log()` on every invocation | low | bug, observability |
| 15 | `check_for_nested_cte` macro has false positives | medium | bug |
| 16 | PR #315 `login_timeout` parameter is a no-op | low | bug |
| 17 | Warehouse snapshots via `atexit` + `open()` should be a Jinja macro | medium | design |
| 18 | `delete_condition` / `delete_not_matched_by_source`: adapter-private knobs on `incremental` | medium | design |
| 19 | v1.9.10 `list_relations` retry at wrong layer (use `add_query`'s `retryable_exceptions`) | medium | enhancement |
| 20 | Module-level `_TOKEN` global — thread-safety and scope issues | medium | bug, concurrency |

### microsoft/dbt-fabricspark

| # | Title | Severity | Type |
|---|---|---|---|
| 01 | Six `__exit__` methods return `True` — silent exception swallowing | high | bug |
| 02 | Hardcoded 2028 token expiry bypasses refresh logic | high | bug, security |
| 03 | `tokenPrint=True` can leak bearer tokens into logs | high | security |
| 04 | `_getLivySQL` regex bug: `re.DOTALL` passed as positional `count` | medium | bug |
| 05 | Global mutable state in `singleton_livy` / `concurrent_livy` causes race conditions | high | bug, concurrency |
| 06 | `atexit` handlers leak Livy sessions on hard kill / OOM | medium | bug |
| 07 | Dead code from Databricks ancestry (Thrift, AWS logging, dup `_parse_retry_after`) | low | tech-debt |
| 08 | Proposal: inherit from `dbt-spark` instead of standalone `SQLAdapter` | high | proposal, architecture |

## What is deliberately NOT filed as an issue

These concerns from `PR_DESCRIPTION.md` are not actionable as upstream bug reports. They belong in the toolbox PR description as evidence for the broader case, not in a one-bug-per-ticket issue tracker.

- "Narrow CI test coverage" / "no Python matrix" — meta-concern about engineering practice.
- "PyPI ownership on a personal account" — organizational concern, not a code bug.
- "AI-assisted code merged without dbt-domain review" — pattern observation; the underlying specific examples (PR #315, v1.9.10 retry, `check_for_nested_cte`) are filed individually above.
- General doc gaps — too broad; file as specific doc requests only when they map to a discrete page or behavior.

## Note on filing strategy

If filing as drafts: open each issue, paste the body verbatim, set the suggested labels, and leave a one-line "filed in preparation for [toolbox PR link]" comment so the maintainer sees the context. Don't cross-reference between issues until at least one is acknowledged — over-cross-referenced issues read as coordinated pressure rather than independent bug reports.
