"""File and tree copies with exclusions (stdlib only)."""

import fnmatch
import json
import shutil
from pathlib import Path

from pi_config_tools import paths

# Name-based exclusions, applied at any depth (repo-side rules)
EXCLUDE_DIRS = {"node_modules", "sessions", "__pycache__", ".venv", ".git"}
EXCLUDE_FILE_PATTERNS = [
    "auth.json",
    "*.bak*",
    "settings.backup*",
    "mcp-cache.json",
    "run-history.jsonl",
    "*.pyc",
]


def copy_tree(
    src: Path,
    dst: Path,
    exclude_dirs: set[str] | None = None,
    exclude_files: list[str] | None = None,
) -> int:
    """Recursively copy src -> dst applying the exclusions (default: repo rules).
    Returns the number of files copied."""
    if exclude_dirs is None:
        exclude_dirs = EXCLUDE_DIRS
    if exclude_files is None:
        exclude_files = EXCLUDE_FILE_PATTERNS
    count = 0
    for item in src.iterdir():
        if item.is_dir():
            if item.name in exclude_dirs:
                continue
            count += copy_tree(item, dst / item.name, exclude_dirs, exclude_files)
        elif item.is_file():
            if any(fnmatch.fnmatch(item.name, pat) for pat in exclude_files):
                continue
            dst.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dst / item.name)
            count += 1
    return count


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def context_mode_version() -> str:
    pkg = paths.context_mode_pkg()
    if not pkg.exists():
        return "unknown (package.json missing)"
    try:
        version: str = json.loads(pkg.read_text(encoding="utf-8")).get("version", "unknown")
        return version
    except (OSError, json.JSONDecodeError):
        return "unknown (package.json unreadable)"
