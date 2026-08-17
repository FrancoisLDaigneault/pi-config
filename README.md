# pi-config

[![CI](https://github.com/FrancoisLDaigneault/pi-config/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/FrancoisLDaigneault/pi-config/actions/workflows/ci.yml)
[![CodeQL](https://github.com/FrancoisLDaigneault/pi-config/actions/workflows/github-code-scanning/codeql/badge.svg)](https://github.com/FrancoisLDaigneault/pi-config/security/code-scanning)
[![Release](https://img.shields.io/github/v/release/FrancoisLDaigneault/pi-config)](https://github.com/FrancoisLDaigneault/pi-config/releases)
[![License](https://img.shields.io/github/license/FrancoisLDaigneault/pi-config)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](pyproject.toml)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![mypy](https://img.shields.io/badge/mypy-strict-blue)](pyproject.toml)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Coverage](https://img.shields.io/badge/coverage-%E2%89%A590%25%20(branch)-brightgreen)](pyproject.toml)

Official repository for the Pi configuration (Maestro persona, extensions, prompts, skills, settings). Goal: never lose the configuration, even after a Pi update or a machine reinstall.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) installed
- Python 3.12+ (uv downloads it automatically if missing, via `.python-version`)

## Setup

```bash
cd pi-config
uv sync                            # creates .venv/, installs the pi_config_tools package (editable) and the dev tools
git config core.hooksPath hooks   # enables the versioned pre-commit hook (redo after every clone)
```

### Task runner (optional)

With [just](https://just.systems) installed (`winget install Casey.Just`), the
`justfile` wraps the common commands -- every one of them works standalone too:
`just setup` (onboarding), `just check` (the three gates), `just sync`,
`just restore [--apply]`, `just backup`. Run `just --list` for the summary.

## Code structure

```
src/pi_config_tools/   # business logic (package installed in editable mode)
  paths.py             # paths, redirectable via PI_CONFIG_HOME / PI_CONFIG_REPO (tests)
  fsops.py             # copy_tree/copy_file with exclusions
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

- `ruff` (rules E/F/W/I/PL/C90, line 100): cyclomatic complexity **max 8**,
  **max 30 statements** and **max 5 arguments** per function - `uv run ruff check .`
  must pass with zero violations.
- `tests/unit/test_standards.py` fails the suite if a module in `src/` exceeds
  **200 lines** or a script in `scripts/` exceeds **20 lines**: the size limit
  is a test, not a promise.
- `tests/unit/test_language.py` fails the suite if any source or documentation
  file contains accented (non-English) characters: everything is written in English.

These standards are **enforced automatically** at two levels:

- **Pre-commit hook** (`hooks/pre-commit`, versioned): `ruff check` + the whole
  test suite (~1 s) before every commit. Enable with: `git config core.hooksPath hooks`.
- **GitHub Actions CI** (`.github/workflows/ci.yml`): on every push/PR to `main`,
  ruff + the three test suites on `windows-latest`, plus a secret scan
  (gitleaks) over the entire git history.

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

Logic in pure Python stdlib (`dependencies = []`; ruff/pytest in the dev group only):

| Script | Role |
| --- | --- |
| `uv run scripts/sync.py` | Copies the **live** config (`~/.pi/agent`, `~/.agents/skills`, context-mode patch) to `config/` in the repo. Run before every commit. |
| `uv run scripts/restore.py` | The reverse path: `config/` -> live locations. **Simulation by default**; add `--apply` to execute. Never touches `auth.json`. The context-mode patch is only restored with `--patch` (see below). Additive: never deletes obsolete live files. |
| `uv run scripts/backup.py` | Full **local** backup (config + patch + MemPalace + skills) into a timestamped folder under `~/pi-backups/`. Option `--destination`. Exit code 1 if a section fails. |

## Recommended workflow before every Pi update

```bash
uv run scripts/backup.py     # full local safety net (close Pi first for MemPalace)
uv run scripts/sync.py       # updates config/ in the repo
git add -A
git commit -m "chore: sync Pi config before update"
git push
```

After an `npm update` of context-mode: the patched file `config/patched-node_modules/context-mode/build/adapters/pi/extension.js` is overwritten on the live side - restore it with `uv run scripts/restore.py --apply --patch` (see `config/patched-node_modules/README.md`).

If `sync.py` fails midway (unreadable JSON, permission denied), `config/` may be left partial: recover it with `git restore config/`.

## Restoring on a fresh machine

Order matters: the context-mode patch must be copied back **after** the npm install, otherwise the install overwrites it (that is why `restore.py` only restores it with the explicit `--patch` flag).

1. **Install Pi** (and `uv`) on the new machine.
2. **Clone this repo**: `git clone <url> pi-config && cd pi-config && uv sync`, then `git config core.hooksPath hooks` (re-enables the pre-commit hook).
3. **Restore the Pi config** (without the patch): `uv run scripts/restore.py` to check in simulation, then `uv run scripts/restore.py --apply`. This puts back `~/.pi/agent` (persona, extensions, prompts, skills, settings, `npm/package.json` + `package-lock.json`) and `~/.agents/skills`.
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
