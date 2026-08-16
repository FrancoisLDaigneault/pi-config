"""Sauvegarde complete locale de Pi (config + patch + MemPalace + skills).

Usage : uv run scripts/backup.py [--destination DOSSIER]

Remplace l'ancien backup-pi.ps1. Chemins absents = avertissement, pas d'echec.
Code de sortie 1 si au moins une section a echoue.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from common import (
    AGENTS_SKILLS,
    HOME,
    MEMPALACE,
    PATCHED_REL,
    PI_AGENT,
    context_mode_version,
    copy_file,
    copy_tree,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sauvegarde complete locale de Pi.")
    parser.add_argument(
        "--destination",
        type=Path,
        default=HOME / "pi-backups" / datetime.now().strftime("%Y-%m-%d_%H%M%S"),
        help="dossier de destination (defaut : ~/pi-backups/horodate)",
    )
    args = parser.parse_args()
    dest = args.destination
    dest.mkdir(parents=True, exist_ok=True)
    print(f"Sauvegarde vers : {dest}\n")

    totals: dict[str, int] = {}
    failed: list[str] = []

    def section(name: str, fn) -> None:
        try:
            totals[name] = fn()
        except Exception as exc:  # une section en echec ne doit pas stopper les autres
            print(f"  ERREUR {name} : {exc}")
            totals[name] = 0
            failed.append(name)

    # 1. Config Pi — memes exclusions que l'ancien backup-pi.ps1 (auth.json et
    # settings.backup* INCLUS : c'est un backup local complet, pas un repo)
    def do_pi_agent() -> int:
        if not PI_AGENT.is_dir():
            print(f"  attention : {PI_AGENT} absent, section ignoree")
            return 0
        return copy_tree(
            PI_AGENT,
            dest / "pi-agent",
            exclude_dirs={"node_modules", "sessions"},
            exclude_files=["mcp-cache.json", "run-history.jsonl"],
        )

    # 2. Fichier patche context-mode
    def do_patch() -> int:
        patched = PI_AGENT / "npm" / "node_modules" / PATCHED_REL
        if not patched.is_file():
            print(
                f"  attention : patch context-mode absent ({patched}), section ignoree"
            )
            return 0
        copy_file(patched, dest / "patched-node_modules" / PATCHED_REL)
        version_file = dest / "patched-node_modules" / "context-mode-version.txt"
        version_file.write_text(
            f"context-mode version au moment du backup : {context_mode_version()}\n",
            encoding="utf-8",
        )
        return 2

    # 3. Donnees MemPalace
    def do_mempalace() -> int:
        if not MEMPALACE.is_dir():
            print(f"  attention : {MEMPALACE} absent, section ignoree")
            return 0
        wal_shm = [
            p.name for p in MEMPALACE.rglob("*") if p.name.endswith(("-wal", "-shm"))
        ]
        if wal_shm:
            print(
                f"  ATTENTION MemPalace : fichiers SQLite -wal/-shm detectes ({', '.join(wal_shm)}). "
                "Fermez Pi/mempalace avant le backup pour une copie coherente."
            )
        return copy_tree(
            MEMPALACE, dest / "mempalace", exclude_dirs=set(), exclude_files=[]
        )

    # 4. Skills utilisateur
    def do_skills() -> int:
        if not AGENTS_SKILLS.is_dir():
            print(f"  attention : {AGENTS_SKILLS} absent, section ignoree")
            return 0
        return copy_tree(
            AGENTS_SKILLS,
            dest / "agents-skills",
            exclude_dirs={"__pycache__"},
            exclude_files=["*.pyc"],
        )

    section("pi-agent", do_pi_agent)
    section("patch context-mode", do_patch)
    section("mempalace", do_mempalace)
    section("agents-skills", do_skills)

    print("\n=== Resume du backup ===")
    for name, n in totals.items():
        print(f"  {name:<20} {n} fichier(s)")
    print(f"  {'TOTAL':<20} {sum(totals.values())} fichier(s)")
    print("\nATTENTION : pi-agent/auth.json contient des identifiants sensibles.")
    print("Ne pas uploader ce backup en clair (cloud, repo git, etc.).")

    if failed:
        print(f"\nERREURS dans section(s) : {', '.join(failed)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
