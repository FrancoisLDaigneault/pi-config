# Contributing

## Setup

```bash
uv sync                           # creates .venv/ and installs the package + dev tools
git config core.hooksPath hooks   # enables the versioned pre-commit hook
```

With [just](https://just.systems) installed, `just setup` runs both commands in
one step (optional -- the commands above remain the baseline).

## Contribution flow

`main` is protected: direct pushes are rejected and every change lands through
a pull request. Work on a branch, let the pre-commit hook run the gates at each
commit, push the branch, open a PR, and merge (squash) once the checks are
green.

## Quality gates

Before any PR, these commands must pass without errors (the pre-commit hook
and the CI quality job run them too):

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest -q
```

The full pytest run enforces a 90% branch-coverage floor; subset runs
(e.g. `uv run pytest tests/unit`) need `--no-cov`. CI additionally installs
with `uv sync --locked` to prove the lockfile is reproducible.

## Standards enforced by tooling

- Cyclomatic complexity (McCabe) <= 8
- <= 30 statements per function, <= 5 arguments
- Lines <= 100 characters
- Strict static typing (`mypy --strict` via `[tool.mypy]` in pyproject.toml)
- <= 200 lines per module, <= 20 per script - checked by `tests/unit/test_standards.py`
- English only in code, comments and docs. `tests/unit/test_language.py`
  enforces this with an accent heuristic over a defined file set (generated
  files such as `CHANGELOG.md` are excluded); the rule itself applies to
  everything you write.

## Commit messages

[Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/)
are mandatory. The type drives the release: `feat:` bumps the minor version,
`fix:` bumps the patch, and a breaking change bumps the major; `docs:`, `ci:`,
`chore:`, `refactor:` and `test:` do not trigger a release by themselves.
release-please opens and updates the release PR from these commits; merging
that PR creates the tag and the GitHub release and uploads the release assets
(wheel, sdist, SBOM, checksums, attestations).
