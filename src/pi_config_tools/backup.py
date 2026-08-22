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
from pi_config_tools.fsops import copy_tree
from pi_config_tools.patched import context_mode_version, copy_patched
from pi_config_tools.sqlite_backup import snapshot_tree


def default_destination(now: datetime | None = None) -> Path:
    stamp = (now or datetime.now()).strftime("%Y-%m-%d_%H%M%S")
    return paths.home() / "pi-backups" / stamp


def rejected_destination(dest: Path) -> str | None:
    """Why `dest` cannot receive a backup, or None when it can.

    A destination inside a backed-up root makes the copy walk into its own
    output: the sections duplicate data already written, the snapshot inflates,
    and a restore cannot tell the backup from what it was backing up. Both
    sides are resolved, so `..` segments and symlinks cannot smuggle a
    destination back under a source.

    Known limit: resolution is textual, so two names for the same volume (a
    mapped drive or a UNC share pointing at the same folder) are not seen as
    equal. Comparing physical identity would mean carrying a Windows-specific
    file-id probe for a case a single maintainer reaches by choosing to, and
    the containment check is defence in depth rather than the last line: pick
    a destination outside the backed-up roots.

    A non-empty destination is refused as well. Writing into one leaves files
    from an earlier run beside the new ones -- deleted upstream, or companions
    of a database that no longer exists -- and nothing in the result says which
    run a file came from, while the summary still reports a success.
    """
    resolved = dest.resolve()
    for root in (paths.pi_agent(), paths.agents_skills(), paths.mempalace()):
        source = root.resolve()
        if resolved == source:
            return f"the destination is the backed-up folder {source} itself"
        if source in resolved.parents:
            return f"the destination is inside the backed-up folder {source}"
    if dest.is_file():
        return f"{dest} is a file, not a folder"
    if dest.is_dir() and any(dest.iterdir()):
        return f"{dest} is not empty, and a backup must not be mixed with an earlier one"
    return None


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
    dest_root = dest / paths.PATCHED_SNAPSHOT_DIR
    total = copy_patched(dest_root)
    if not total:
        print("  warning: no patched node_modules entry found, section skipped")
        return 0
    version_file = dest_root / "context-mode-version.txt"
    version_file.write_text(
        f"context-mode version at backup time: {context_mode_version()}\n",
        encoding="utf-8",
    )
    return total + 1


def _backup_mempalace(dest: Path) -> int:
    """MemPalace, with its databases snapshotted rather than copied.

    A live `-wal` used to earn a warning telling the operator to close Pi, and
    the copy was made anyway: a torn backup was reported as a success. The
    snapshot removes both the false success and the reason to close Pi.
    """
    root = paths.mempalace()
    if not root.is_dir():
        print(f"  warning: {root} missing, section skipped")
        return 0
    files, databases = snapshot_tree(root, dest / "mempalace")
    if databases:
        print(f"  mempalace: {databases} SQLite database(s) snapshotted under their own locks")
    return files


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
    # Checked before the folder is created: refusing after mkdir would already
    # have written into the tree being backed up.
    rejection = rejected_destination(dest)
    if rejection is not None:
        print(f"error: {rejection} - pick an empty folder outside the backed-up roots.")
        return 1
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
