"""Restores the versioned configuration (config/) to the live locations.

Usage: uv run scripts/restore.py                    (simulation, nothing is written)
       uv run scripts/restore.py --apply            (real execution)
       uv run scripts/restore.py --apply --patch    (includes the context-mode patch)
       uv run scripts/restore.py --apply --force    (overwrites differing live configuration)

NEVER touches auth.json.
The context-mode patch (patched-node_modules/) is only restored with --patch,
AFTER Pi's npm install - otherwise it would create a partial orphan
node_modules that the install would overwrite (see README, fresh-machine restore).
"""

import argparse
import sys
from pathlib import Path

from pi_config_tools import paths
from pi_config_tools.fsops import copy_file


def _mappings() -> list[tuple[Path, Path]]:
    """(source in config/, live destination)"""
    config = paths.config_dir()
    return [
        (config / "pi-agent", paths.pi_agent()),
        (config / paths.PATCHED_SNAPSHOT_DIR, paths.pi_agent() / "npm" / "node_modules"),
        (config / "agents-skills", paths.agents_skills()),
    ]


def list_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*") if p.is_file())


def _skip_repo_doc(src_root: Path, src: Path, rel: Path) -> bool:
    """The patched-node_modules README documents the repo; it is not restored."""
    is_patch_root = src_root.name == paths.PATCHED_SNAPSHOT_DIR.name
    return is_patch_root and src.name == "README.md" and len(rel.parts) == 1


def _overwrite_note(src: Path, dst: Path) -> str:
    """Flags a live file whose content differs from the snapshot.

    A patched vendor file legitimately differs before restore; an upstream file
    updated since the last sync also does. Either way it is named, never silently
    clobbered. Re-running on an already-restored tree reports '(identical)'.
    """
    if not dst.is_file():
        return ""
    if dst.read_bytes() == src.read_bytes():
        return "  (identical)"
    return "  (DIFFERS from the live file - overwriting)"


def _restore_tree(src_root: Path, dst_root: Path, apply: bool, force: bool) -> tuple[int, int]:
    count = 0
    refused = 0
    for src in list_files(src_root):
        rel = src.relative_to(src_root)
        if src.name == "auth.json":
            print(f"  SKIPPED (security): {rel}")
            continue
        if _skip_repo_doc(src_root, src, rel):
            continue
        dst = dst_root / rel
        note = _overwrite_note(src, dst)
        protects_live_config = src_root.name == "pi-agent"
        if apply and protects_live_config and "DIFFERS" in note and not force:
            print(f"  REFUSED: {rel.as_posix()} differs from live; use --force to overwrite")
            refused += 1
            continue
        print(f"  {'copying' if apply else 'would copy'}: {rel}  ->  {dst}{note}")
        if apply:
            copy_file(src, dst)
        count += 1
    return count, refused


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Restores config/ to the live locations.")
    parser.add_argument(
        "--apply", action="store_true", help="actually execute (default: simulation)"
    )
    parser.add_argument("--dry-run", action="store_true", help="simulation (default behavior)")
    parser.add_argument(
        "--patch",
        action="store_true",
        help="include the context-mode patch (run AFTER the npm install)",
    )
    parser.add_argument(
        "--force", action="store_true", help="overwrite differing live configuration"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    apply = args.apply and not args.dry_run

    if not paths.config_dir().is_dir():
        print(f"error: {paths.config_dir()} missing - run uv run scripts/sync.py first")
        return 1

    mode = "APPLY" if apply else "SIMULATION (--apply to execute)"
    print(f"Restore - {mode} mode\n")

    count = 0
    refused = 0
    for src_root, dst_root in _mappings():
        if src_root.name == paths.PATCHED_SNAPSHOT_DIR.name and not args.patch:
            print(
                "  info: patched-node_modules/ skipped (use --patch AFTER "
                "the npm install, see README)"
            )
            continue
        if not src_root.is_dir():
            print(f"  info: {src_root.name}/ missing from the repo, skipped")
            continue
        copied, blocked = _restore_tree(src_root, dst_root, apply, args.force)
        count += copied
        refused += blocked

    verb = "file(s) copied" if apply else "file(s) would be copied"
    print(f"\nDone: {count} {verb}.")
    if refused:
        print(f"error: {refused} protected file(s) differed; rerun with --force to overwrite")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
