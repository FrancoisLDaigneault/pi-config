# Optional convenience task runner (https://just.systems).
# Every command below works standalone -- just is never required.

# One-command onboarding: install deps and the pre-commit framework hooks
setup:
    uv sync --locked
    git config --unset-all core.hooksPath || true
    uv run pre-commit install --install-hooks

# Run the quality gates (same quality commands as the CI quality job)
check:
    uv run ruff check .
    uv run ruff format --check .
    uv run ty check --error-on-warning src scripts tests
    uv run mypy
    uv run deptry src
    uv run pytest -q

# Copy the live Pi config into the repo
sync:
    uv run python scripts/sync.py

# Restore config/ to the live locations (simulation by default; pass --apply)
restore *ARGS:
    uv run python scripts/restore.py {{ARGS}}

# Full local timestamped backup
backup:
    uv run python scripts/backup.py
