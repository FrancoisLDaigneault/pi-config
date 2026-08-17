# Optional convenience task runner (https://just.systems).
# Every command below works standalone -- just is never required.

# One-command onboarding: install deps and enable the versioned pre-commit hook
setup:
    uv sync
    git config core.hooksPath hooks

# Run the three quality gates (same as the pre-commit hook and CI)
check:
    uv run ruff check .
    uv run mypy
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
