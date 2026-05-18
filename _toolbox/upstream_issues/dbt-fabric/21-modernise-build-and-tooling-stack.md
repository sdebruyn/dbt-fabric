# Proposal: modernise the build and tooling stack (PEP 621 `pyproject.toml`, `uv`, `ruff`, drop EOL Python)

**Repo:** `microsoft/dbt-fabric`
**Labels (suggested):** `proposal`, `tooling`, `priority/medium`

> [x] **Validated by maintainer** — code refs, line numbers, and claims confirmed against upstream HEAD

## Summary

The build, packaging, and developer tooling in this repo is the Python stack of ~mid-2023: `setup.py` plus a near-empty `pyproject.toml`, pinned-old `black` / `isort` / `flake8` / `mypy` via `pre-commit`, no lockfile, and Python 3.8/3.9 still in the classifier list despite both being end-of-life. The cumulative effect is a slower contribution loop, weaker static checks, and metadata that misrepresents what's supported. The fix is a one-time migration to the standard 2025 Python stack — PEP 621 `pyproject.toml` as the single source of truth, [`hatchling`](https://hatch.pypa.io/latest/) as the build backend, [`uv`](https://docs.astral.sh/uv/) for dependency management and locking, [`ruff`](https://docs.astral.sh/ruff/) replacing `black` + `isort` + `flake8`, [PEP 604](https://peps.python.org/pep-0604/) union syntax, and a `requires-python` range that drops the EOL versions.

## Evidence (HEAD [`0de2190`](https://github.com/microsoft/dbt-fabric/tree/0de2190))

- [`setup.py`](https://github.com/microsoft/dbt-fabric/blob/0de2190/setup.py) — all packaging metadata lives in `setup.py`, including a custom `VerifyVersionCommand` `install` subclass to check the git tag.
- [`pyproject.toml`](https://github.com/microsoft/dbt-fabric/blob/0de2190/pyproject.toml) — only declares `[build-system]` with `setuptools>=61.0`; no PEP 621 `[project]` table, no tool config.
- [`.pre-commit-config.yaml`](https://github.com/microsoft/dbt-fabric/blob/0de2190/.pre-commit-config.yaml) — `black 23.3.0`, `isort 5.12.0`, `flake8 6.1.0`, `mypy v1.3.0`, `pre-commit-hooks v4.4.0`, `yamllint v1.32.0`, `absolufy-imports v0.3.1`. All pinned to mid-2023 releases.
- `.pre-commit-config.yaml` — `flake8` runs with `--max-line-length=1000 --extend-ignore=E203`, which effectively disables line-length and most style checks.
- `.pre-commit-config.yaml` — `mypy` is invoked with `--ignore-missing-imports` and is scoped only to `^dbt/adapters`, so most untyped third-party APIs disappear from the check.
- `.pre-commit-config.yaml` — `default_language_version: python: python3.12.0` pins a specific patch release; `pre-commit` normally expects a `pythonX.Y` series, not a patch version.
- [`setup.py#L80-L86`](https://github.com/microsoft/dbt-fabric/blob/0de2190/setup.py) — classifiers list Python 3.8, 3.9, 3.10, 3.11, 3.12. Python 3.8 reached EOL in October 2024 and 3.9 in October 2025; both should no longer be advertised as supported.
- No `requires-python` is declared anywhere, so `pip` does not refuse the install on EOL interpreters and PyPI displays no compatibility range.
- No lockfile (`uv.lock`, `requirements.lock`, `pdm.lock`) is checked in, so neither contributors nor CI install from a reproducible snapshot.
- Source-code scan (`rg -n 'typing\.(Union|Optional|List|Dict|Tuple)' dbt/`) shows `typing.Union`/`Optional` are still in use across the adapter; the codebase has not been migrated to [PEP 604](https://peps.python.org/pep-0604/) (`X | Y`) or PEP 585 builtin generics (`list[str]` instead of `List[str]`), both available since Python 3.10.

## User impact

- **Contributors** wait minutes per run for `black` + `isort` + `flake8` + `mypy` over `pre-commit`, where `ruff format` + `ruff check` would do the same work in well under a second. Slow checks reduce the frequency contributors run them locally and push more failures into CI.
- **`flake8 --max-line-length=1000`** is "lint is on" theatre — no realistic violation will ever trigger.
- **`mypy --ignore-missing-imports`** hides genuine import-time bugs (typos, removed APIs) as silent "ignored" warnings. Several of the issues filed alongside this proposal would be caught by a stricter `mypy` profile.
- **No lockfile** means CI greenness is not reproducible; a transitive dependency release can fail builds with no code change in this repo.
- **`setup.py` install hook (`VerifyVersionCommand`)** runs as part of `python setup.py install`, which is itself a deprecated install path and is increasingly rejected by modern build frontends. Tag verification belongs in CI, not in the install hook.
- **EOL Python in classifiers** misrepresents what the adapter actually supports. Users on 3.8/3.9 think they're supported and file bugs that the maintainers cannot reasonably reproduce on supported runtimes.

## Suggested fix (single-PR migration)

1. **Move to PEP 621 `pyproject.toml`.** Delete `setup.py`. Put all metadata under `[project]` in `pyproject.toml`: `name`, `description`, `readme`, `license`, `authors`, `requires-python`, `classifiers`, `dependencies`, `optional-dependencies`, `urls`. Use `dynamic = ["version"]` and point at the existing `__version__.py` through `[tool.hatch.version]`.
2. **Use `hatchling` as the build backend.** `requires = ["hatchling"]`, `build-backend = "hatchling.build"`. No more custom `setup.py` install commands; the modern build front-ends (`pip`, `uv`, `build`) call the backend directly.
3. **Adopt `uv` for dependency management.** `uv sync` for environment setup, `uv lock` for the lockfile, check `uv.lock` into the repo so CI installs from a known snapshot. (See `astral-sh/uv` for the rationale; in practice it is one to two orders of magnitude faster than `pip`-based equivalents.)
4. **Replace `black` + `isort` + `flake8` with `ruff`.** One tool, one config block under `[tool.ruff]` in `pyproject.toml`. Keep `mypy` separately for type checking. Drop the `flake8` `--max-line-length=1000` placeholder and pick a real line length (99 matches the existing `black` config).
5. **Tighten `mypy` config.** Remove `--ignore-missing-imports` from the default profile and add per-package overrides only for the imports that genuinely have no stubs. Extend the file pattern beyond `^dbt/adapters` so utility modules are also checked.
6. **Set `requires-python = ">=3.11"` (or `>=3.10`).** Drop the EOL 3.8/3.9 classifiers. Add 3.13. `pip` and PyPI will then reject installs on unsupported interpreters automatically.
7. **Migrate `typing.Union` / `Optional` / `List` / `Dict` to PEP 604 `X | Y` and PEP 585 builtin generics.** A single `ruff` rule (`UP007`, `UP006`) does this as an autofix; the diff is mechanical.
8. **Move tag-version verification out of the install hook into the release workflow.** A `gh` step or a small CI script does the same check without piggybacking on the install path.

## Reference

The toolbox contribution at [`sdebruyn/dbt-fabric`](https://github.com/sdebruyn/dbt-fabric) is already running this stack end-to-end (`hatchling` + `uv` + `ruff` + PEP 604 unions + Python 3.11–3.13). The `pyproject.toml` there can be used as a concrete template; nothing in the proposal is speculative.
