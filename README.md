# pi-config

[![CI](https://img.shields.io/github/actions/workflow/status/fld-forge/pi-config/ci.yml?branch=main&logo=githubactions&logoColor=white&label=CI)](https://github.com/fld-forge/pi-config/actions/workflows/ci.yml)
[![CodeQL](https://github.com/fld-forge/pi-config/actions/workflows/github-code-scanning/codeql/badge.svg)](https://github.com/fld-forge/pi-config/security/code-scanning)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/fld-forge/pi-config/badge)](https://scorecard.dev/viewer/?uri=github.com/fld-forge/pi-config)
[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/14164/badge)](https://www.bestpractices.dev/projects/14164)
[![Release](https://img.shields.io/github/v/release/fld-forge/pi-config?logo=github)](https://github.com/fld-forge/pi-config/releases)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue?logo=python&logoColor=white)](pyproject.toml)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Coverage](https://img.shields.io/badge/coverage-%E2%89%A590%25%20(branch)-brightgreen)](pyproject.toml)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](.pre-commit-config.yaml)
[![License](https://img.shields.io/github/license/fld-forge/pi-config)](LICENSE)

Official repository for the Pi configuration (Maestro persona, extensions, prompts, skills, settings). Goal: never lose the configuration, even after a Pi update or a machine reinstall.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) installed
- Python 3.12+ (uv downloads it automatically if missing, via `.python-version`)

## Setup

```bash
cd pi-config
uv sync --locked                           # creates .venv/, installs the pi_config_tools package (editable) and the dev tools
uv run pre-commit install --install-hooks  # installs the framework hooks (redo after every clone)
```

### Task runner (optional)

With [just](https://just.systems) installed (`winget install Casey.Just`), the
`justfile` wraps the common commands -- every one of them works standalone too:
`just setup` (onboarding), `just check` (the quality gates), `just sync`,
`just restore [--apply]`, `just backup`. Run `just --list` for the summary.

## Code structure

```
src/pi_config_tools/   # business logic (package installed in editable mode)
  paths.py             # paths, redirectable via PI_CONFIG_HOME / PI_CONFIG_REPO (tests)
  fsops.py             # copy_tree/copy_file with exclusions
  patched.py           # copy and metadata operations for local node_modules patches
  secrets.py           # detection and redaction of secrets in JSON files
  sync.py, restore.py, backup.py   # one testable main(argv) per command
scripts/               # thin entry points (import + sys.exit(main()))
tests/unit/            # pure functions and tmp_path, incl. the size gate (test_standards.py)
tests/integration/     # each module against a fake tree in a sandbox
tests/e2e/             # full sync -> restore cycle and backup via subprocess on scripts/
```

The `scripts/` wrappers are kept (rather than `[project.scripts]`) so that the
commands documented here stay unchanged.

## Quality standards (enforced by tooling)

- `ruff` (rule families selected in `pyproject.toml`, line length 100): cyclomatic
  complexity **max 8**, **max 30 statements** and **max 5 arguments** per
  function - `uv run ruff check .` must pass with zero violations.
- `tests/unit/test_standards.py` fails the suite if a module in `src/` exceeds
  **200 lines** or a script in `scripts/` exceeds **20 lines**: the size limit
  is a test, not a promise.
- `tests/unit/test_language.py` fails the suite if a scanned file contains
  accented (non-English) characters. The scan covers a defined file set (the
  Python trees, root docs, workflows, templates, justfile); generated or
  third-party files (`CHANGELOG.md`, `config/`, `LICENSE`, `CODE_OF_CONDUCT.md`)
  are excluded. The English-only rule itself applies to everything written here.

These standards are **enforced automatically** at two levels:

- **Pre-commit hooks** ([pre-commit framework](https://pre-commit.com),
  `.pre-commit-config.yaml`): on the changed files, hygiene checks plus ruff
  lint and format through its mirror hooks (with autofix) and lockfile
  consistency; whole-project local hooks then run
  `uv run ty check --error-on-warning src scripts tests`, `uv run mypy`,
  `uv run deptry src` (keeps the stdlib-only invariant honest),
  `uv run lint-imports` (enforces package seams) and `uv run pytest -q`
  (the whole suite, with its 90% branch-coverage floor)
  before every commit. Replay everything with
  `uv run pre-commit run --all-files`, except the secrets gate: gitleaks reads
  the staged diff, so it has nothing to scan when nothing is staged; run
  `gitleaks git --redact -v .` for the full-history scan CI performs.
- **GitHub Actions CI** (`.github/workflows/ci.yml`): on every push/PR to `main`
  and every Monday 06:00 UTC (catches bit-rot without pushes), a quality job on
  `windows-latest` runs `uv sync --locked` then the seven full-project gate
  commands (`uv run ruff check .`, `uv run ruff format --check .`,
  `uv run ty check --error-on-warning src scripts tests`, `uv run mypy`,
  `uv run deptry src`, `uv run lint-imports`, `uv run pytest -q`); separate
  Linux jobs run a
  full-history secret scan (gitleaks), complementary locked dependency audits
  (`uv audit --locked` and pip-audit), a Semgrep CE scan of first-party Python,
  and a workflow audit (zizmor). Pull requests also run GitHub's Dependency
  Review Action. Semgrep uses the remote `p/python` pack, whose rules can evolve
  independently of the pinned CLI version. Import Linter keeps `backup`,
  `restore` and `sync` independent and keeps `secrets` from depending on path,
  file-operation, patch or command modules. Ruff TID251 separately prevents
  production modules from importing `tests` or `scripts`.

The project KPIs (with current values and targets) live in [`NORTHSTAR.md`](NORTHSTAR.md).

## Tests

```bash
uv run pytest                              # the whole suite
uv run pytest tests/unit --no-cov          # unit (pure, tmp_path)
uv run pytest tests/integration --no-cov   # modules against a sandbox (never the real config)
uv run pytest tests/e2e --no-cov           # full cycle through the real scripts (subprocess)
```

Subset runs need `--no-cov`: the 90% coverage floor is enforced on the full suite only.

The tests never touch the real config: paths are redirected to temporary
folders via `PI_CONFIG_HOME` / `PI_CONFIG_REPO`.

## The three commands

Logic in pure Python stdlib (`dependencies = []`; quality tooling in the dev group only):

| Script | Role |
| --- | --- |
| `uv run scripts/sync.py` | Copies the **live** config (`~/.pi/agent`, `~/.agents/skills`, context-mode patch) to `config/` in the repo. Sections missing or empty on the live side are named and skipped. Run before every commit. |
| `uv run scripts/restore.py` | The reverse path: `config/` -> live locations. **Simulation by default**; add `--apply` to execute. Never touches `auth.json`. Existing, differing files under `.pi/agent` require `--force`; vendor patches remain freely restorable with `--patch`. Additive: never deletes obsolete live files. |
| `uv run scripts/backup.py` | Full **local** backup (config + patch + MemPalace + skills) into a timestamped folder under `~/pi-backups/`. Option `--destination`. Exit code 1 if a section fails. |

## Recommended workflow before every Pi update

`main` only accepts pull requests - direct pushes are rejected - so config
syncs go through a branch:

```bash
uv run scripts/backup.py     # full local safety net (close Pi first for MemPalace)
uv run scripts/sync.py       # updates config/ in the repo
git switch -c chore/sync-config
git add -A
git commit -m "chore: sync Pi config before update"   # the pre-commit hooks run the quality gates
git push -u origin chore/sync-config
gh pr create --fill          # squash-merge once the checks are green
```

This machine also runs a daily scheduled backup task (`pi-config-daily-backup`,
19:00) as a machine-side safeguard; it is not installed by this repository.

After any `npm install` or package update: every locally patched file under `node_modules/` is overwritten on the live side - restore them with `uv run scripts/restore.py --apply --patch`. The versioned copies live in `config/patched-node_modules/`; the authoritative list of covered entries is `PATCHED_RELS` in `src/pi_config_tools/paths.py`, mirrored by that folder's generated `README.md`.

If `sync.py` fails midway (unreadable JSON, permission denied), `config/` may be left partial: recover it with `git restore config/`.

## Restoring on a fresh machine

Order matters: the context-mode patch must be copied back **after** the npm install, otherwise the install overwrites it (that is why `restore.py` only restores it with the explicit `--patch` flag).

1. **Install Pi** (and `uv`) on the new machine.
2. **Clone this repo**: `git clone <url> pi-config && cd pi-config && uv sync --locked`, then `uv run pre-commit install --install-hooks` (re-enables the pre-commit hooks).
3. **Restore the Pi config** (without the patch): `uv run scripts/restore.py` to check in simulation, then `uv run scripts/restore.py --apply`. This puts back `~/.pi/agent` (persona, extensions, prompts, skills, settings, `npm/package.json` + `package-lock.json`), plus `~/.agents/skills` when the snapshot holds it. `config/agents-skills/` is currently absent from the repo - its last skill was deliberately removed in #34 and git never versions the now-empty folder - so restore prints `info: agents-skills/ missing from the repo, skipped` (the doc gate `test_agents_skills_snapshot_status_documented` keeps this paragraph honest).
4. **Reinstall Pi's npm packages**: `cd ~/.pi/agent/npm && npm ci` (the lockfile restored in step 3 guarantees exact versions).
5. **Reapply the context-mode patch** - now that `node_modules` exists: `uv run scripts/restore.py --apply --patch` (from the repo).
6. **Restore `auth.json`** from a local `backup.py` backup (never in the repo): copy it by hand to `~/.pi/agent/auth.json`.
7. **Restore `~/.mempalace`** from the same local backup, if desired (the agent's memory).
8. Launch Pi and check that the persona, extensions and skills are loaded.

## What is NOT in the repo

- **`auth.json`** - credentials and secrets. Never versioned (excluded by `sync.py` **and** by `.gitignore`).
- **MemPalace data** (`~/.mempalace`) - the agent's personal memory, large and private.

Both are covered by `backup.py` **locally only**. Never upload a `pi-backups/` folder unencrypted.

## Redacted secrets

`sync.py` audits every config JSON before inclusion (keys `apiKey`, `token`, `secret`, etc. and values `sk-...`, `ghp_...`, `Bearer ...`). Any suspicious value is replaced with `<REDACTED>` and reported in the output. To restore a redacted file: get the real value from the source machine (or the local backup) and put it back by hand after `restore.py --apply`.

## Release integrity

Each [release](https://github.com/fld-forge/pi-config/releases) ships
the wheel, the sdist, a CycloneDX SBOM exported from `uv.lock`, an SPDX
SBOM from the dependency graph, SHA-256 checksums and GitHub
build-provenance attestations. See [SECURITY.md](SECURITY.md) for the
verification commands.
