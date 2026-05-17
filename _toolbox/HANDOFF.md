# Handoff to Microsoft Fabric Toolbox maintainers

This document describes how the contents of this branch (`to-toolbox`) map to a contribution under `tools/dbt-fabric/` in [`microsoft/fabric-toolbox`](https://github.com/microsoft/fabric-toolbox), and what work is required on the toolbox side that this branch cannot do.

The `_toolbox/` directory (this file plus the PR draft and workflow concepts) is **handoff-only** content. It must **not** be copied into the toolbox subfolder.

---

## What to copy into `tools/dbt-fabric/`

These top-level paths from the branch root become the contents of `tools/dbt-fabric/`:

| Path | Purpose |
|---|---|
| `src/` | Both adapters (`dbt/adapters/fabric/`, `dbt/adapters/fabricspark/`) and macros (`dbt/include/fabric/`, `dbt/include/fabricspark/`) |
| `tests/` | Integration test suite (`tests/fabric/`, `tests/fabricspark/`, `tests/unit/`, `tests/packages/`) |
| `docs/` | Documentation source files |
| `assets/` | Logos and image assets used by README and docs |
| `overrides/` | Zensical theme overrides (now containing only structural overrides, no analytics) |
| `pyproject.toml` | Package metadata (already pointing at toolbox URLs) |
| `uv.lock` | Dependency lock file |
| `README.md` | Tool README (toolbox template format, Sam in acknowledgements) |
| `CONTRIBUTING.md` | Development workflow guide |
| `CLAUDE.md` | Internal AI-assisted development guide (optional — toolbox may rename or remove) |
| `zensical.toml` | Docs site config (pointing at `microsoft.github.io/fabric-toolbox/dbt-fabric/`) |
| `test.env.sample` | Template for integration-test credentials |

## What to leave behind (do NOT copy)

These paths exist in this branch for our local development but do **not** belong in the toolbox subfolder:

| Path | Reason |
|---|---|
| `.github/` | Toolbox has its own workflows on repo root. Workflows in this branch are sample material that must be adapted, not copied verbatim (see CI/CD migration below). |
| `.devcontainer/` | Toolbox has its own devcontainer configuration on repo root. |
| `LICENSE` | Toolbox has one shared MIT license at repo root. No per-tool LICENSE needed. |
| `_toolbox/` | This handoff folder. Strictly for transition planning. |
| `logs/`, `docs_build/`, `__pycache__/`, `.venv/`, `.ruff_cache/` | Build artifacts and caches. |

A safe copy command (run from this branch's worktree root, with the toolbox checked out alongside):

```shell
mkdir -p ../fabric-toolbox/tools/dbt-fabric
rsync -av --exclude='.git' --exclude='.github' --exclude='.devcontainer' \
  --exclude='LICENSE' --exclude='_toolbox' --exclude='logs' \
  --exclude='docs_build' --exclude='__pycache__' --exclude='.venv' \
  --exclude='.ruff_cache' --exclude='test.env' \
  ./ ../fabric-toolbox/tools/dbt-fabric/
```

---

## What the toolbox maintainers still need to do

### 1. CI/CD migration

The five workflows in `.github/workflows/` of this branch (`integration-tests-dw.yml`, `integration-tests-de.yml`, `lint-format.yml`, `unit-tests.yml`, `release-version.yml`) must be **adapted** to monorepo context, not copied as-is:

- Add `paths` filters so they only run when files under `tools/dbt-fabric/` change:
  ```yaml
  on:
    pull_request:
      paths:
        - 'tools/dbt-fabric/**'
        - '.github/workflows/dbt-fabric-*.yml'
  ```
- Rename the workflow files with a `dbt-fabric-` prefix to avoid collisions with other toolbox-tool workflows.
- Update working directory in every step: add `working-directory: tools/dbt-fabric` or prefix paths.
- The release workflow needs PyPI publishing credentials from the toolbox organization, not the current fork.

### 2. Azure OIDC federated credentials

The current Azure OIDC federation is configured against `sdebruyn/dbt-fabric`. New federated credentials must be created on `microsoft/fabric-toolbox` with:

- Subject: `repo:microsoft/fabric-toolbox:pull_request`
- Subject: `repo:microsoft/fabric-toolbox:ref:refs/heads/main`
- Audience: `api://AzureADTokenExchange`

The same app registration that the existing fork uses can serve as a starting point if its trust relationships are extended; alternatively, register a new dedicated app for the toolbox CI.

### 3. Fabric test infrastructure

The CI integration tests need access to a Fabric workspace with a Data Warehouse and a Lakehouse. Configure these as GitHub Actions Variables (non-secret) and Secrets (where applicable) on the toolbox repo:

- `FABRIC_TEST_WORKSPACE_NAME`
- `FABRIC_TEST_WORKSPACE_ID`
- `FABRIC_TEST_DWH_NAME`
- `FABRIC_TEST_HOST`
- `FABRIC_TEST_LAKEHOUSE_NAME`
- `FABRIC_TEST_LIVY_SESSION_NAME`
- `FABRIC_TEST_THREADS`
- Azure OIDC: `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`

A dedicated Fabric workspace for toolbox CI (separate from any product or customer workspace) is recommended to isolate test impact.

### 4. PyPI publishing

Coordinate PyPI account access for the `dbt-fabric` package name. Microsoft already controls this name. The contribution should be published as the next major or minor version after the current `microsoft/dbt-fabric` release, with a deprecation notice on the existing repo pointing to the toolbox.

### 5. Docs site (GitHub Pages)

`zensical.toml` and `overrides/` are included so the existing docs site can be rebuilt under the toolbox.

- Activate GitHub Pages on `microsoft/fabric-toolbox` (Settings → Pages → Source: `gh-pages` branch).
- Add a docs publish workflow (a starting concept is provided in `_toolbox/workflows/docs-publish.yml`) to `.github/workflows/` of the toolbox.
- The site is configured to serve under `https://microsoft.github.io/fabric-toolbox/dbt-fabric/`. If you choose a different URL prefix, update `site_url` in `tools/dbt-fabric/zensical.toml`.
- Future toolbox tools can use the same workflow pattern for their own docs subdirectories.

### 6. Test runner agent

`.github/agents/test-runner.agent.md` contains a catalog of FabricSpark test classes and instructions for triggering on-demand DE tests via `/test-de` PR comments. The toolbox can:

- Move it to `.github/agents/` of the toolbox if Copilot-driven test triggering is desired.
- Or copy the catalog content into `tools/dbt-fabric/CONTRIBUTING.md` as plain documentation.

### 7. CHANGELOG.md

The fabric-toolbox PR template requires a `CHANGELOG.md` entry under "Unreleased". Add an entry describing the new `tools/dbt-fabric/` tool.

### 8. CLA

The PR author must sign the Microsoft CLA via the CLA bot on first PR submission. This is automatic — the bot comments on the PR with a signing link.

### 9. Issue migration

Triage and migrate open issues from `microsoft/dbt-fabric` and `microsoft/dbt-fabricspark` to the toolbox. Several of those issues are already fixed in this contribution (see the bug-fix track record in `PR_DESCRIPTION.md`); those can be closed with a reference to the toolbox release.

### 10. Deprecation notices

Coordinate deprecation notices on:
- The `microsoft/dbt-fabric` README and PyPI page
- The `microsoft/dbt-fabricspark` README and PyPI page
- Any Microsoft Learn documentation that references the existing packages

---

## What stays unchanged about this branch

- All Python source code in `src/`
- All integration tests in `tests/`
- All documentation pages in `docs/` (now without personal branding or comparative criticism)
- The macro override structure under `src/dbt/include/`
- The package layout and `pyproject.toml` declarations (now with toolbox URLs)

The branch represents the canonical state of what `tools/dbt-fabric/` should look like at the moment of contribution. After acceptance, all further changes happen on the toolbox monorepo via standard PR flow.
