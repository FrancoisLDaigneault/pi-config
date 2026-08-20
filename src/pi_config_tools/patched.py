"""Copies and metadata for locally patched node_modules entries."""

import json
from pathlib import Path

from pi_config_tools import paths
from pi_config_tools.fsops import copy_file, copy_tree


def copy_patched(dest_root: Path) -> int:
    """Copy every locally patched node_modules entry (file or whole directory).

    Shared by sync and backup so the file/directory dispatch is written once.
    Returns the number of files copied; missing entries are reported and skipped.
    """
    total = 0
    for rel in paths.PATCHED_RELS:
        src = paths.patched_live(rel)
        if src.is_dir():
            count = copy_tree(src, dest_root / rel)
        elif src.is_file():
            copy_file(src, dest_root / rel)
            count = 1
        else:
            print(f"  warning: {rel.as_posix()} missing from node_modules, skipped")
            continue
        total += count
        print(f"  patched-node_modules/{rel.as_posix()} : {count} file(s)")
    return total


def context_mode_version() -> str:
    pkg = paths.context_mode_pkg()
    if not pkg.exists():
        return "unknown (package.json missing)"
    try:
        data = json.loads(pkg.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "unknown (package.json unreadable)"
    if not isinstance(data, dict):
        return "unknown (package.json unreadable)"
    version = data.get("version", "unknown")
    return version if isinstance(version, str) else "unknown (package.json unreadable)"
