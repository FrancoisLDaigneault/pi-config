"""Sauvegarde complete locale de Pi (config + patch + MemPalace + skills).

Usage : uv run scripts/backup.py [--destination DOSSIER]

Remplace l'ancien backup-pi.ps1. Chemins absents = avertissement, pas d'echec.
Code de sortie 1 si au moins une section a echoue.
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
    """Config Pi - memes exclusions que l'ancien backup-pi.ps1 (auth.json et
    settings.backup* INCLUS : c'est un backup local complet, pas un repo)."""
    if not paths.pi_agent().is_dir():
        print(f"  attention : {paths.pi_agent()} absent, section ignoree")
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
        print(f"  attention : patch context-mode absent ({patched}), section ignoree")
        return 0
    copy_file(patched, dest / "patched-node_modules" / paths.PATCHED_REL)
    version_file = dest / "patched-node_modules" / "context-mode-version.txt"
    version_file.write_text(
        f"context-mode version au moment du backup : {context_mode_version()}\n",
        encoding="utf-8",
    )
    return 2


def _backup_mempalace(dest: Path) -> int:
    root = paths.mempalace()
    if not root.is_dir():
        print(f"  attention : {root} absent, section ignoree")
        return 0
    wal_shm = [p.name for p in root.rglob("*") if p.name.endswith(("-wal", "-shm"))]
    if wal_shm:
        print(
            f"  ATTENTION MemPalace : fichiers SQLite -wal/-shm detectes ({', '.join(wal_shm)}). "
            "Fermez Pi/mempalace avant le backup pour une copie coherente."
        )
    return copy_tree(root, dest / "mempalace", exclude_dirs=set(), exclude_files=[])


def _backup_skills(dest: Path) -> int:
    if not paths.agents_skills().is_dir():
        print(f"  attention : {paths.agents_skills()} absent, section ignoree")
        return 0
    return copy_tree(
        paths.agents_skills(),
        dest / "agents-skills",
        exclude_dirs={"__pycache__"},
        exclude_files=["*.pyc"],
    )


SECTIONS = [
    ("pi-agent", _backup_pi_agent),
    ("patch context-mode", _backup_patch),
    ("mempalace", _backup_mempalace),
    ("agents-skills", _backup_skills),
]


def _print_summary(totals: dict[str, int]) -> None:
    print("\n=== Resume du backup ===")
    for name, n in totals.items():
        print(f"  {name:<20} {n} fichier(s)")
    print(f"  {'TOTAL':<20} {sum(totals.values())} fichier(s)")
    print("\nATTENTION : pi-agent/auth.json contient des identifiants sensibles.")
    print("Ne pas uploader ce backup en clair (cloud, repo git, etc.).")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sauvegarde complete locale de Pi.")
    parser.add_argument(
        "--destination",
        type=Path,
        default=None,
        help="dossier de destination (defaut : ~/pi-backups/horodate)",
    )
    args = parser.parse_args(argv)
    dest = args.destination if args.destination is not None else default_destination()
    dest.mkdir(parents=True, exist_ok=True)
    print(f"Sauvegarde vers : {dest}\n")

    totals: dict[str, int] = {}
    failed: list[str] = []
    for name, fn in SECTIONS:
        try:
            totals[name] = fn(dest)
        except Exception as exc:  # une section en echec ne doit pas stopper les autres
            print(f"  ERREUR {name} : {exc}")
            totals[name] = 0
            failed.append(name)

    _print_summary(totals)
    if failed:
        print(f"\nERREURS dans section(s) : {', '.join(failed)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
