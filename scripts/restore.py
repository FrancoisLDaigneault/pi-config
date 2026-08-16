"""Restaure la configuration versionnee (config/) vers les emplacements vifs.

Usage : uv run scripts/restore.py            (simulation, rien n'est ecrit)
        uv run scripts/restore.py --apply    (execution reelle)

Ne touche JAMAIS auth.json.
"""

import argparse
import sys
from pathlib import Path

from common import AGENTS_SKILLS, CONFIG, PI_AGENT, copy_file

# (source dans config/, destination vive)
MAPPINGS = [
    (CONFIG / "pi-agent", PI_AGENT),
    (CONFIG / "patched-node_modules", PI_AGENT / "npm" / "node_modules"),
    (CONFIG / "agents-skills", AGENTS_SKILLS),
]


def list_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*") if p.is_file())


def main() -> int:
    parser = argparse.ArgumentParser(description="Restaure config/ vers les emplacements vifs.")
    parser.add_argument("--apply", action="store_true", help="executer reellement (defaut : simulation)")
    parser.add_argument("--dry-run", action="store_true", help="simulation (comportement par defaut)")
    args = parser.parse_args()
    apply = args.apply and not args.dry_run

    if not CONFIG.is_dir():
        print(f"erreur : {CONFIG} absent - lancer d'abord uv run scripts/sync.py")
        return 1

    mode = "APPLICATION" if apply else "SIMULATION (--apply pour executer)"
    print(f"Restauration - mode {mode}\n")

    count = 0
    for src_root, dst_root in MAPPINGS:
        if not src_root.is_dir():
            print(f"  info : {src_root.name}/ absent du repo, ignore")
            continue
        for src in list_files(src_root):
            rel = src.relative_to(src_root)
            if src.name == "auth.json":
                print(f"  IGNORE (securite) : {rel}")
                continue
            if src_root.name == "patched-node_modules" and src.name == "README.md" and len(rel.parts) == 1:
                continue  # documentation du repo, pas un fichier a restaurer
            dst = dst_root / rel
            print(f"  {'copie' if apply else 'copierait'} : {rel}  ->  {dst}")
            if apply:
                copy_file(src, dst)
            count += 1

    verb = "copie(s)" if apply else "fichier(s) seraient copies"
    print(f"\nTermine : {count} {verb}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
