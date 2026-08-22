"""Syncs the live Pi configuration to the repo's config/ folder.

Usage: uv run scripts/sync.py
"""

import json
import shutil
import sys
from pathlib import Path

from pi_config_tools import paths
from pi_config_tools.fsops import (
    SwapError,
    copy_file,
    copy_tree,
    recover_interrupted_swap,
    report_stale_stagings,
    staging_for,
    swap_dir,
)
from pi_config_tools.patched import context_mode_version, copy_patched
from pi_config_tools.secrets import REDACTED, redact, scan_copied_json

# Items of .pi/agent to version (folders and files, relative paths)
AGENT_DIRS = ["extensions", "prompts", "skills", "packages", "agents"]
AGENT_FILES = [
    "APPEND_SYSTEM.md",
    "settings.json",
    "mcp.json",
    "claude-bridge.json",
    "models-store.json",
    "npm/package.json",
    "npm/package-lock.json",
]


def sync_json_with_audit(rel: str, dest: Path) -> list[str] | None:
    """Copy a JSON file from .pi/agent to `dest`/pi-agent, redacting any secrets.

    Returns None if the file is unreadable or not valid JSON.
    """
    src = paths.pi_agent() / rel
    dst = dest / "pi-agent" / rel
    try:
        data = json.loads(src.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"  error: {rel} unreadable or invalid JSON ({exc}) - sync aborted")
        return None
    found = redact(data)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if found:
        if isinstance(data, str):
            data = REDACTED
        dst.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(f"  WARNING {rel}: {len(found)} value(s) redacted: {', '.join(found)}")
    else:
        shutil.copy2(src, dst)
    return found


def _sync_agent_dirs(dest: Path) -> int:
    total = 0
    for rel in AGENT_DIRS:
        src = paths.pi_agent() / rel
        if not src.is_dir() or not any(src.iterdir()):
            print(f"  info: {rel}/ missing or empty, skipped")
            continue
        n = copy_tree(src, dest / "pi-agent" / rel)
        total += n
        print(f"  pi-agent/{rel}/ : {n} file(s)")
    return total


def _sync_agent_files(dest: Path) -> tuple[int, list[str]] | None:
    """Returns None if a config JSON is invalid (error propagated to main)."""
    total = 0
    redacted: list[str] = []
    for rel in AGENT_FILES:
        src = paths.pi_agent() / rel
        if not src.is_file():
            print(f"  warning: {rel} missing, skipped")
            continue
        if rel.endswith(".json"):
            found = sync_json_with_audit(rel, dest)
            if found is None:
                return None
            redacted += found
        else:
            copy_file(src, dest / "pi-agent" / rel)
        total += 1
        print(f"  pi-agent/{rel} : ok")
    return total, redacted


def _write_patch_readme(dest_root: Path) -> None:
    entries = "\n".join(f"- `{rel.as_posix()}`" for rel in paths.PATCHED_RELS)
    (dest_root / "README.md").write_text(
        "# Patched files in node_modules\n\n"
        "Local modifications to installed packages, versioned here because any "
        "`npm install` or package update overwrites them. Directory entries are "
        "snapshotted whole, so every local edit inside them is preserved:\n\n"
        f"{entries}\n\n"
        f"context-mode version at sync time: {context_mode_version()}.\n\n"
        "Copy them back after each update with "
        "`uv run scripts/restore.py --apply --patch`.\n",
        encoding="utf-8",
    )


def _sync_patch(dest: Path) -> int:
    """Patched entries in node_modules (overwritten by any npm update)."""
    dest_root = dest / paths.PATCHED_SNAPSHOT_DIR
    total = copy_patched(dest_root)
    if not total:
        return 0
    _write_patch_readme(dest_root)
    return total + 1


def _sync_skills(dest: Path) -> int:
    if not paths.agents_skills().is_dir():
        print("  warning: .agents/skills missing, skipped")
        return 0
    n = copy_tree(paths.agents_skills(), dest / "agents-skills")
    print(f"  agents-skills/ : {n} file(s)")
    return n


def _build(dest: Path) -> tuple[int, list[str]] | None:
    """Build a complete snapshot under `dest`; None if a live JSON is invalid."""
    total = _sync_agent_dirs(dest)
    files_result = _sync_agent_files(dest)
    if files_result is None:
        return None
    n, redacted = files_result
    total += n
    total += _sync_patch(dest)
    total += _sync_skills(dest)
    return total, redacted + scan_copied_json(dest)


def _report_swap_failure(exc: SwapError, config: Path) -> None:
    """Say what the filesystem actually looks like, never what it should."""
    print(f"  error: {exc}")
    if exc.target_intact:
        print(f"  {config} is unchanged.")
        return
    print(f"  {config} IS MISSING - do not run git restore, it would not bring it back.")
    if exc.aside is not None:
        print(f"  the previous snapshot is at {exc.aside}")
        print(f"  recover it with:  mv {exc.aside} {config}")
    if exc.staging is not None:
        print(f"  the new snapshot is complete at {exc.staging} and was left in place")


def main(argv: list[str] | None = None) -> int:  # argv kept for restore/backup symmetry
    del argv
    config = paths.config_dir()
    interrupted = recover_interrupted_swap(config)
    if interrupted is not None:
        print(f"  error: {interrupted}")
        return 1
    report_stale_stagings(config)
    staging = staging_for(config)
    shutil.rmtree(staging, ignore_errors=True)
    if staging.exists():
        # Ignoring the cleanup error would fold a crashed run's leftovers into
        # the snapshot that is about to be installed.
        print(f"  error: {staging} survived cleanup - remove it by hand and run sync again")
        return 1
    try:
        built = _build(staging)
        if built is None:
            # Nothing has touched config/ yet: the previous snapshot is intact.
            return 1
        total, redacted = built
        leftover = swap_dir(staging, config)
    except SwapError as exc:
        _report_swap_failure(exc, config)
        return 1
    finally:
        # Kept when the target is missing: the staging tree is then the only
        # complete copy of the new snapshot, and the message above points at it.
        if config.exists():
            shutil.rmtree(staging, ignore_errors=True)

    if leftover is not None:
        print(f"  warning: previous snapshot left behind at {leftover}, remove it by hand")
    print(f"\nSync done: {total} file(s) in {config}")
    if redacted:
        print(f"WARNING: {len(redacted)} secret(s) redacted - see README for restore instructions.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
