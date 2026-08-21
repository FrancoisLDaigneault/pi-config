# AGENTS.md - operating manual for coding agents

pi-config is the sync/restore/backup tool for the Pi configuration: it copies
the live config (`~/.pi/agent`, skills, context-mode patch) into `config/`,
restores it on a fresh machine, and makes full local backups.

Layout: `src/pi_config_tools/` (logic, one testable `main(argv)` per command),
`scripts/` (thin wrappers), `tests/` (unit / integration / e2e), `config/`
(the synced snapshot); local gates run through the pre-commit framework
(`.pre-commit-config.yaml`).

## Hard rules

- `config/` is a snapshot of the live machine, produced by `sync.py`.
  Never edit it by hand; it is excluded from the style gates (Ruff, deptry,
  the language scan - ADR-0003); gitleaks and the test suite still cover it.
- `auth.json` is never committed (excluded by `sync.py` and `.gitignore`).
- English only, everywhere you write. An accent-heuristic gate
  (`tests/unit/test_language.py`) fails the suite on accented characters.
- `main` accepts no direct pushes: every change lands through a branch and a
  pull request.

## Gates and commands

Setup: `uv sync --locked` then `uv run pre-commit install --install-hooks`
(both via `just setup`). Python 3.12+.

The seven quality commands (also available as `just check`; the CI quality
job runs exactly these; pre-commit runs ty/mypy/deptry/Import Linter/pytest as
whole-project local hooks and ruff through its changed-files mirror hooks with autofix):

```bash
uv run ruff check .
uv run ruff format --check .
uv run ty check --error-on-warning src scripts tests
uv run mypy
uv run deptry src
uv run lint-imports
uv run pytest -q
```

The full pytest run enforces a 90% branch-coverage floor; subset runs
(e.g. `uv run pytest tests/unit`) need `--no-cov`. Size and complexity caps:
McCabe <= 8, <= 30 statements and <= 5 arguments per function, lines <= 100
(ruff); modules <= 200 lines, scripts <= 20 lines (`test_standards.py`).
A documentation drift gate (`tests/unit/test_docs.py`) fails the suite when
doc claims (test counts, gate commands, caps, floors) diverge from reality.

## Release semantics (empirically verified)

Conventional Commits drive release-please (config under
`.github/release-please/`): `feat:` bumps the minor version, `fix:` and
`docs:` bump the patch (`docs:` produces a visible Documentation changelog
section - proven on PR #14), a breaking change bumps the major; `ci:`,
`chore:`, `refactor:` and `test:` do not release by themselves. The release
PR carries `pyproject.toml`, `uv.lock`, `CHANGELOG.md` and the manifest;
merging it creates the tag and fires the release-assets job (wheel, sdist,
CycloneDX + SPDX SBOMs, SHA-256 checksums, provenance attestation).

## Known quirks

- `uv run` may rewrite `uv.lock` when `pyproject.toml` is ahead of it
  (post-release window). Restore with `git checkout -- uv.lock` unless the
  change is intended.
- release-please PRs run CI only when the `RELEASE_PLEASE_TOKEN` secret exists
  (a fine-grained PAT; with the `github.token` fallback GitHub's anti-recursion
  suppresses the checks - see `.github/workflows/release-please.yml`). Check
  the PR's checks tab rather than assuming either state; post-merge CI on
  `main` always runs.
- CRLF warnings on Windows are checkout-side only; committed blobs are LF
  (`.gitattributes` enforces `eol=lf`).
- Repo-local SSH commit signing is configured (`commit.gpgsign true`);
  commits sign automatically - do not disable or bypass it. Squash-merge only:
  a rebase merge would land author commits that GitHub does not re-sign.
