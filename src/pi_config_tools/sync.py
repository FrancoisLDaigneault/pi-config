"""Syncs the live Pi configuration to the repo's config/ folder.

Usage: uv run scripts/sync.py
"""

import json
import shutil
import sys

from pi_config_tools import paths
from pi_config_tools.fsops import context_mode_version, copy_file, copy_tree
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


def sync_json_with_audit(rel: str) -> list[str] | None:
    """Copy a JSON file from .pi/agent to config/pi-agent, redacting any secrets.

    Returns None if the file is unreadable or not valid JSON.
    """
    src = paths.pi_agent() / rel
    dst = paths.config_dir() / "pi-agent" / rel
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


def _sync_agent_dirs() -> int:
    total = 0
    for rel in AGENT_DIRS:
        src = paths.pi_agent() / rel
        if not src.is_dir() or not any(src.iterdir()):
            print(f"  info: {rel}/ missing or empty, skipped")
            continue
        n = copy_tree(src, paths.config_dir() / "pi-agent" / rel)
        total += n
        print(f"  pi-agent/{rel}/ : {n} file(s)")
    return total


def _sync_agent_files() -> tuple[int, list[str]] | None:
    """Returns None if a config JSON is invalid (error propagated to main)."""
    total = 0
    redacted: list[str] = []
    for rel in AGENT_FILES:
        src = paths.pi_agent() / rel
        if not src.is_file():
            print(f"  warning: {rel} missing, skipped")
            continue
        if rel.endswith(".json"):
            found = sync_json_with_audit(rel)
            if found is None:
                return None
            redacted += found
        else:
            copy_file(src, paths.config_dir() / "pi-agent" / rel)
        total += 1
        print(f"  pi-agent/{rel} : ok")
    return total, redacted


def _sync_patch() -> int:
    """Patched file in node_modules (overwritten by any npm update)."""
    patched_src = paths.patched_live()
    if not patched_src.is_file():
        print("  warning: context-mode patch missing, skipped")
        return 0
    dest_root = paths.config_dir() / "patched-node_modules"
    copy_file(patched_src, dest_root / paths.PATCHED_REL)
    version = context_mode_version()
    (dest_root / "README.md").write_text(
        "# Patched files in node_modules\n\n"
        f"- `{paths.PATCHED_REL.as_posix()}` - local patch applied to context-mode "
        f"(version at sync time: {version}).\n\n"
        "Any `npm update` of context-mode overwrites this file: copy it back from "
        "here after each update (or via `uv run scripts/restore.py --apply`).\n",
        encoding="utf-8",
    )
    print(f"  patched-node_modules : extension.js + README (context-mode {version})")
    return 2


def _sync_skills() -> int:
    if not paths.agents_skills().is_dir():
        print("  warning: .agents/skills missing, skipped")
        return 0
    n = copy_tree(paths.agents_skills(), paths.config_dir() / "agents-skills")
    print(f"  agents-skills/ : {n} file(s)")
    return n


def main(argv: list[str] | None = None) -> int:  # argv kept for restore/backup symmetry
    del argv
    config = paths.config_dir()
    if config.exists():
        try:
            shutil.rmtree(config)
        except OSError as exc:
            print(f"  error: cannot clean {config} ({exc})")
            return 1

    total = _sync_agent_dirs()
    files_result = _sync_agent_files()
    if files_result is None:
        return 1
    n, redacted = files_result
    total += n
    total += _sync_patch()
    total += _sync_skills()
    redacted += scan_copied_json(config)

    print(f"\nSync done: {total} file(s) in {config}")
    if redacted:
        print(f"WARNING: {len(redacted)} secret(s) redacted - see README for restore instructions.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
