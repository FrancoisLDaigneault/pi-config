# Contributing

## Setup

```bash
uv sync                           # creates .venv/ and installs the package + dev tools
git config core.hooksPath hooks   # enables the versioned pre-commit hook
```

## Quality gates

Before any PR, the three commands must pass without errors (the pre-commit
hook and the CI run them too):

```bash
uv run ruff check .
uv run mypy
uv run pytest -q
```

## Standards enforced by tooling

- Cyclomatic complexity (McCabe) <= 8
- <= 30 statements per function, <= 5 arguments
- Lines <= 100 characters
- Strict static typing (`mypy --strict` via `[tool.mypy]` in pyproject.toml)
- <= 200 lines per module, <= 20 per script - checked by `tests/unit/test_standards.py`
- English only in code, comments and docs - checked by `tests/unit/test_language.py`

## Commit messages

[Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/)
are mandatory (`feat:`, `fix:`, `ci:`, `docs:`, `chore:`...):
release-please uses them to generate versions and the CHANGELOG.
