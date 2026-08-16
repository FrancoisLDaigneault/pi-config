"""Synchronise la configuration Pi vive vers le dossier config/ du repo.

Usage : uv run scripts/sync.py
"""

import json
import shutil
import sys

from pi_config_tools import paths
from pi_config_tools.fsops import context_mode_version, copy_file, copy_tree
from pi_config_tools.secrets import redact, scan_copied_json

# Elements de .pi/agent a versionner (dossiers et fichiers, chemins relatifs)
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


def sync_json_with_audit(rel: str) -> list[str]:
    """Copie un JSON de .pi/agent vers config/pi-agent en caviardant les secrets eventuels."""
    src = paths.pi_agent() / rel
    dst = paths.config_dir() / "pi-agent" / rel
    try:
        data = json.loads(src.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"  erreur : {rel} illisible ou JSON invalide ({exc}) - sync interrompu")
        raise SystemExit(1) from exc
    found = redact(data)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if found:
        dst.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(f"  ATTENTION {rel} : {len(found)} valeur(s) caviardee(s) : {', '.join(found)}")
    else:
        shutil.copy2(src, dst)
    return found


def _sync_agent_dirs() -> int:
    total = 0
    for rel in AGENT_DIRS:
        src = paths.pi_agent() / rel
        if not src.is_dir() or not any(src.iterdir()):
            print(f"  info : {rel}/ absent ou vide, ignore")
            continue
        n = copy_tree(src, paths.config_dir() / "pi-agent" / rel)
        total += n
        print(f"  pi-agent/{rel}/ : {n} fichier(s)")
    return total


def _sync_agent_files() -> tuple[int, list[str]]:
    total = 0
    redacted: list[str] = []
    for rel in AGENT_FILES:
        src = paths.pi_agent() / rel
        if not src.is_file():
            print(f"  attention : {rel} absent, ignore")
            continue
        if rel.endswith(".json"):
            redacted += sync_json_with_audit(rel)
        else:
            copy_file(src, paths.config_dir() / "pi-agent" / rel)
        total += 1
        print(f"  pi-agent/{rel} : ok")
    return total, redacted


def _sync_patch() -> int:
    """Fichier patche dans node_modules (ecrase par tout npm update)."""
    patched_src = paths.patched_live()
    if not patched_src.is_file():
        print("  attention : patch context-mode absent, ignore")
        return 0
    dest_root = paths.config_dir() / "patched-node_modules"
    copy_file(patched_src, dest_root / paths.PATCHED_REL)
    version = context_mode_version()
    (dest_root / "README.md").write_text(
        "# Fichiers patches dans node_modules\n\n"
        f"- `{paths.PATCHED_REL.as_posix()}` — patch local applique a context-mode "
        f"(version au moment du sync : {version}).\n\n"
        "Tout `npm update` de context-mode ecrase ce fichier : le recopier depuis ici "
        "apres chaque update (ou via `uv run scripts/restore.py --apply`).\n",
        encoding="utf-8",
    )
    print(f"  patched-node_modules : extension.js + README (context-mode {version})")
    return 2


def _sync_skills() -> int:
    if not paths.agents_skills().is_dir():
        print("  attention : .agents/skills absent, ignore")
        return 0
    n = copy_tree(paths.agents_skills(), paths.config_dir() / "agents-skills")
    print(f"  agents-skills/ : {n} fichier(s)")
    return n


def main(argv=None) -> int:  # argv accepte pour symetrie avec restore/backup (aucune option)
    del argv
    config = paths.config_dir()
    if config.exists():
        try:
            shutil.rmtree(config)
        except OSError as exc:
            print(f"  erreur : impossible de nettoyer {config} ({exc})")
            return 1

    total = _sync_agent_dirs()
    n, redacted = _sync_agent_files()
    total += n
    total += _sync_patch()
    total += _sync_skills()
    redacted += scan_copied_json(config)

    print(f"\nSync termine : {total} fichier(s) dans {config}")
    if redacted:
        print(
            f"ATTENTION : {len(redacted)} secret(s) caviarde(s) - voir README pour la restauration."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
