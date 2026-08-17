"""Full local backup of Pi (config + patch + MemPalace + skills).

Usage: uv run scripts/backup.py [--destination FOLDER]

Replaces the old backup-pi.ps1. Missing paths = warning, not failure.
Exit code 1 if at least one section failed.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from pi_config_tools import paths
from pi_config_tools.fsops import context_mode_version, copy_file, copy_tree


def default_destination(now: datetime | None = None) -> Path:
    stamp = (now or datetime.now()).strftime("%Y-%m-%d_%H%M%S")
    return paths.home() / "pi-backups" / stamp


def _backup_pi_agent(dest: Path) -> int:
    """Pi config - same exclusions as the old backup-pi.ps1 (auth.json and
    settings.backup* INCLUDED: this is a full local backup, not a repo)."""
    if not paths.pi_agent().is_dir():
        print(f"  warning: {paths.pi_agent()} missing, section skipped")
        return 0
    return copy_tree(
        paths.pi_agent(),
        dest / "pi-agent",
        exclude_dirs={"node_modules", "sessions"},
        exclude_files=["mcp-cache.json", "run-history.jsonl"],
    )


def _backup_patch(dest: Path) -> int:
    patched = paths.patched_live()
    if not patched.is_file():
        print(f"  warning: context-mode patch missing ({patched}), section skipped")
        return 0
    copy_file(patched, dest / "patched-node_modules" / paths.PATCHED_REL)
    version_file = dest / "patched-node_modules" / "context-mode-version.txt"
    version_file.write_text(
        f"context-mode version at backup time: {context_mode_version()}\n",
        encoding="utf-8",
    )
    return 2


def _backup_mempalace(dest: Path) -> int:
    root = paths.mempalace()
    if not root.is_dir():
        print(f"  warning: {root} missing, section skipped")
        return 0
    wal_shm = [p.name for p in root.rglob("*") if p.name.endswith(("-wal", "-shm"))]
    if wal_shm:
        print(
            f"  WARNING MemPalace: SQLite -wal/-shm files detected ({', '.join(wal_shm)}). "
            "Close Pi/mempalace before the backup for a consistent copy."
        )
    return copy_tree(root, dest / "mempalace", exclude_dirs=set(), exclude_files=[])


def _backup_skills(dest: Path) -> int:
    if not paths.agents_skills().is_dir():
        print(f"  warning: {paths.agents_skills()} missing, section skipped")
        return 0
    return copy_tree(
        paths.agents_skills(),
        dest / "agents-skills",
        exclude_dirs={"__pycache__"},
        exclude_files=["*.pyc"],
    )


SECTIONS = [
    ("pi-agent", _backup_pi_agent),
    ("context-mode patch", _backup_patch),
    ("mempalace", _backup_mempalace),
    ("agents-skills", _backup_skills),
]


def _print_summary(totals: dict[str, int]) -> None:
    print("\n=== Backup summary ===")
    for name, n in totals.items():
        print(f"  {name:<20} {n} file(s)")
    print(f"  {'TOTAL':<20} {sum(totals.values())} file(s)")
    print("\nWARNING: pi-agent/auth.json contains sensitive credentials.")
    print("Do not upload this backup unencrypted (cloud, git repo, etc.).")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Full local backup of Pi.")
    parser.add_argument(
        "--destination",
        type=Path,
        default=None,
        help="destination folder (default: ~/pi-backups/<timestamp>)",
    )
    args = parser.parse_args(argv)
    dest = args.destination if args.destination is not None else default_destination()
    dest.mkdir(parents=True, exist_ok=True)
    print(f"Backing up to: {dest}\n")

    totals: dict[str, int] = {}
    failed: list[str] = []
    for name, fn in SECTIONS:
        try:
            totals[name] = fn(dest)
        except Exception as exc:  # a failing section must not stop the others
            print(f"  ERROR {name}: {exc}")
            totals[name] = 0
            failed.append(name)

    _print_summary(totals)
    if failed:
        print(f"\nERRORS in section(s): {', '.join(failed)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
