---
name: multi-agent
description: Use when coordinating parallel agents to fix multiple test failures at once, or when asked to do multi-agent development work.
user-invocable: true
---

When implementing multiple test classes or fixing many failures at once, use parallel agents to speed up the work. The main conversation acts as coordinator.

### How it works

**Phase 1 — Discover failures**

Run the full test suite for each adapter. Tests run against real Fabric infrastructure and are slow (minutes per test class). Don't wait for the full suite to finish — monitor the output for failures as they arrive and start working on fixes immediately:

```shell
# Run tests in the background
uv run pytest --dw -v &
uv run pytest --de -v &

# Monitor for failures as they come in (use Monitor tool or tail the output)
```

As soon as enough failures have come in to form a work package, start phase 2. The test suite keeps running while workers fix earlier failures.

**Phase 2 — Group by root cause**

Analyze the failures before spawning any agents. Multiple test failures often share a single root cause:
- 5 tests fail on `fabric__dateadd not found` → one missing macro
- 3 tests fail on `VARCHAR` without length → one type mapping issue
- 2 tests fail on `LIMIT` syntax → one SQL dialect difference

Group these into **work packages**. Each work package:
- Has a clear root cause
- Lists all test classes affected
- Targets specific files that need to change (macros, adapter code, test fixtures)

Ensure work packages have **non-overlapping target files** where possible. If two packages need to edit the same file, either merge them into one package or assign them sequentially.

**Phase 3 — Spawn worker agents**

Spawn one agent per work package using `isolation: "worktree"`. Each worker gets a self-contained prompt with:
- The root cause and the failing test classes
- Which files to look at and modify
- The full TDD loop instructions (fix, run affected tests, regression check)
- Instructions to add any recurring patterns to the "Lessons learned" section of CLAUDE.md

Worker prompt template:

```
You are working on dbt-fabric, a dbt adapter for Microsoft Fabric. Read CLAUDE.md first.

Root cause: [description of the root cause]
Failing tests: [list of test classes]
Target files: [which macros/adapter files/test files to modify]

Instructions:
1. Read CLAUDE.md to understand the project and workflow.
2. Read the failing test classes and their base classes to understand what they expect.
3. Implement the fix in the target files.
4. Run ONLY the specific failing test: uv run pytest -k "TestClassName" --dw -v (or --de -v)
5. If you discover a recurring pattern, add it to the "Lessons learned" section of CLAUDE.md.
6. Report back: what you changed, which tests pass/fail, any lessons learned.
```

Spawn agents for independent work packages in parallel (single message, multiple Agent tool calls). Keep dependent work packages sequential.

**Phase 4 — Merge and validate**

After workers complete:
1. Review each worker's changes (the worktree diff).
2. Merge non-conflicting worktrees. If CLAUDE.md was updated by multiple workers, consolidate the lessons learned entries.
3. Run the full test suite on the merged result:
   ```shell
   uv run pytest --dw -v
   uv run pytest --de -v
   ```
4. If new failures appear, go back to phase 2 with the remaining failures.

### Guidelines for the coordinator

- **Don't do the fixing yourself** — your job is to analyze, distribute, and validate. Workers do the implementation.
- **Be specific in prompts** — include file paths, error messages, and the exact test class names. Workers start without context.
- **Start broad, narrow down** — in the first round, tackle the root causes that affect the most tests. Later rounds handle stragglers.
- **Cap workers at 3-4 per round** — more creates merge complexity and potential test infrastructure contention due to Fabric API rate limiting.
- **Track progress** — after each round, note which tests went from failing to passing. If a worker's fix introduces new failures, revert and reassign.
- **Regression checks are the coordinator's job** — after merging worker changes, the coordinator runs the full suite. Workers only run their own specific tests.

### Guidelines for workers

- **Read CLAUDE.md first** — it contains everything you need about the project, architecture, and patterns.
- **Read the base test class** — understand what the test expects before fixing. The fix often becomes obvious from reading the base class SQL.
- **Minimal fixes only** — fix the root cause, don't refactor. If a macro works, don't also clean up unrelated macros.
- **Only run your own specific tests** — never run the full test suite. Fabric infrastructure is slow (Livy sessions, rate-limited APIs). Run only the test class you are fixing: `uv run pytest -k "TestClassName" --dw -v` (or `--de -v`). The coordinator handles regression checks after merging.
- **Validate and commit before finishing** — after your fix works, run `uv run ruff format .` and `uv run ruff check --fix .`, then commit only your own changes (not unrelated changes in the repo). Use a descriptive commit message.
- **Report clearly** — list: files changed, tests that now pass, tests that still fail (if any), and any lessons learned.
- **Update CLAUDE.md** — if you find a pattern that will help future work, add it to "Lessons learned". This is part of your job, not optional.
