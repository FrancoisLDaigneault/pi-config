"""Restaure la configuration versionnee (config/) vers les emplacements vifs.

Usage : uv run scripts/restore.py                    (simulation, rien n'est ecrit)
        uv run scripts/restore.py --apply            (execution reelle)
        uv run scripts/restore.py --apply --patch    (inclut le patch context-mode)

Ne touche JAMAIS auth.json.
Le patch context-mode (patched-node_modules/) n'est restaure qu'avec --patch,
APRES l'installation npm de Pi - sinon il creerait un node_modules partiel
orphelin que l'installation ecraserait (voir README, restauration machine neuve).
"""

import argparse
import sys
from pathlib import Path

from pi_config_tools import paths
from pi_config_tools.fsops import copy_file


def _mappings() -> list[tuple[Path, Path]]:
    """(source dans config/, destination vive)"""
    config = paths.config_dir()
    return [
        (config / "pi-agent", paths.pi_agent()),
        (config / "patched-node_modules", paths.pi_agent() / "npm" / "node_modules"),
        (config / "agents-skills", paths.agents_skills()),
    ]


def list_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*") if p.is_file())


def _skip_repo_doc(src_root: Path, src: Path, rel: Path) -> bool:
    """Le README de patched-node_modules documente le repo, il n'est pas restaure."""
    is_patch_root = src_root.name == "patched-node_modules"
    return is_patch_root and src.name == "README.md" and len(rel.parts) == 1


def _restore_tree(src_root: Path, dst_root: Path, apply: bool) -> int:
    count = 0
    for src in list_files(src_root):
        rel = src.relative_to(src_root)
        if src.name == "auth.json":
            print(f"  IGNORE (securite) : {rel}")
            continue
        if _skip_repo_doc(src_root, src, rel):
            continue
        dst = dst_root / rel
        print(f"  {'copie' if apply else 'copierait'} : {rel}  ->  {dst}")
        if apply:
            copy_file(src, dst)
        count += 1
    return count


def _parse_args(argv) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Restaure config/ vers les emplacements vifs.")
    parser.add_argument(
        "--apply", action="store_true", help="executer reellement (defaut : simulation)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="simulation (comportement par defaut)"
    )
    parser.add_argument(
        "--patch",
        action="store_true",
        help="inclure le patch context-mode (a lancer APRES l'installation npm)",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv)
    apply = args.apply and not args.dry_run

    if not paths.config_dir().is_dir():
        print(f"erreur : {paths.config_dir()} absent - lancer d'abord uv run scripts/sync.py")
        return 1

    mode = "APPLICATION" if apply else "SIMULATION (--apply pour executer)"
    print(f"Restauration - mode {mode}\n")

    count = 0
    for src_root, dst_root in _mappings():
        if src_root.name == "patched-node_modules" and not args.patch:
            print(
                "  info : patched-node_modules/ ignore (utiliser --patch APRES "
                "l'installation npm, voir README)"
            )
            continue
        if not src_root.is_dir():
            print(f"  info : {src_root.name}/ absent du repo, ignore")
            continue
        count += _restore_tree(src_root, dst_root, apply)

    verb = "copie(s)" if apply else "fichier(s) seraient copies"
    print(f"\nTermine : {count} {verb}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
