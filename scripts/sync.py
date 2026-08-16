"""Synchronise la configuration Pi vive vers le dossier config/ du repo.

Usage : uv run scripts/sync.py
"""

import json
import re
import shutil
import sys

from common import (
    AGENTS_SKILLS,
    CONFIG,
    PATCHED_REL,
    PI_AGENT,
    context_mode_version,
    copy_file,
    copy_tree,
)

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

# Detection de secrets dans les JSON de config avant inclusion
SECRET_KEYS = {
    "apikey",
    "api_key",
    "token",
    "secret",
    "password",
    "authtoken",
    "accesstoken",
    "refreshtoken",
    "bearer",
}
SECRET_VALUE_RE = re.compile(r"^(sk-|ghp_|gho_|github_pat_|xox[a-z]-|Bearer )")


def redact(node, path=""):
    """Caviarde recursivement les valeurs suspectes. Retourne la liste des chemins caviardes."""
    found = []
    if isinstance(node, dict):
        for key, value in node.items():
            where = f"{path}.{key}" if path else key
            if isinstance(value, str) and (
                key.lower() in SECRET_KEYS or SECRET_VALUE_RE.match(value)
            ):
                node[key] = "<REDACTED>"
                found.append(where)
            else:
                found += redact(value, where)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            where = f"{path}[{i}]"
            if isinstance(value, str) and SECRET_VALUE_RE.match(value):
                node[i] = "<REDACTED>"
                found.append(where)
            else:
                found += redact(value, where)
    return found


def sync_json_with_audit(rel: str) -> list[str]:
    """Copie un JSON de .pi/agent vers config/pi-agent en caviardant les secrets eventuels."""
    src = PI_AGENT / rel
    dst = CONFIG / "pi-agent" / rel
    try:
        data = json.loads(src.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"  erreur : {rel} illisible ou JSON invalide ({exc}) - sync interrompu")
        sys.exit(1)
    found = redact(data)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if found:
        dst.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(
            f"  ATTENTION {rel} : {len(found)} valeur(s) caviardee(s) : {', '.join(found)}"
        )
    else:
        shutil.copy2(src, dst)
    return found


def scan_copied_json() -> list[str]:
    """Audit post-copie : caviarde les secrets dans tous les *.json copies dans config/."""
    found = []
    for path in sorted(CONFIG.rglob("*.json")):
        rel = path.relative_to(CONFIG).as_posix()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            print(f"  info : {rel} non analysable en JSON, laisse tel quel")
            continue
        hits = redact(data)
        if hits:
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            print(
                f"  ATTENTION {rel} : {len(hits)} valeur(s) caviardee(s) : {', '.join(hits)}"
            )
            found += [f"{rel}:{h}" for h in hits]
    return found


def main() -> int:
    if CONFIG.exists():
        try:
            shutil.rmtree(CONFIG)
        except OSError as exc:
            print(f"  erreur : impossible de nettoyer {CONFIG} ({exc})")
            return 1

    total = 0
    redacted = []

    # 1. Dossiers et fichiers de .pi/agent
    for rel in AGENT_DIRS:
        src = PI_AGENT / rel
        if not src.is_dir() or not any(src.iterdir()):
            print(f"  info : {rel}/ absent ou vide, ignore")
            continue
        n = copy_tree(src, CONFIG / "pi-agent" / rel)
        total += n
        print(f"  pi-agent/{rel}/ : {n} fichier(s)")
    for rel in AGENT_FILES:
        src = PI_AGENT / rel
        if not src.is_file():
            print(f"  attention : {rel} absent, ignore")
            continue
        if rel.endswith(".json"):
            redacted += sync_json_with_audit(rel)
        else:
            copy_file(src, CONFIG / "pi-agent" / rel)
        total += 1
        print(f"  pi-agent/{rel} : ok")

    # 2. Fichier patche dans node_modules (ecrase par tout npm update)
    patched_src = PI_AGENT / "npm" / "node_modules" / PATCHED_REL
    if patched_src.is_file():
        copy_file(patched_src, CONFIG / "patched-node_modules" / PATCHED_REL)
        version = context_mode_version()
        readme = CONFIG / "patched-node_modules" / "README.md"
        readme.write_text(
            "# Fichiers patches dans node_modules\n\n"
            f"- `{PATCHED_REL.as_posix()}` — patch local applique a context-mode "
            f"(version au moment du sync : {version}).\n\n"
            "Tout `npm update` de context-mode ecrase ce fichier : le recopier depuis ici "
            "apres chaque update (ou via `uv run scripts/restore.py --apply`).\n",
            encoding="utf-8",
        )
        total += 2
        print(
            f"  patched-node_modules : extension.js + README (context-mode {version})"
        )
    else:
        print("  attention : patch context-mode absent, ignore")

    # 3. Skills utilisateur
    if AGENTS_SKILLS.is_dir():
        n = copy_tree(AGENTS_SKILLS, CONFIG / "agents-skills")
        total += n
        print(f"  agents-skills/ : {n} fichier(s)")
    else:
        print("  attention : .agents/skills absent, ignore")

    # 4. Audit secrets sur tous les JSON copies (y compris via copy_tree)
    redacted += scan_copied_json()

    print(f"\nSync termine : {total} fichier(s) dans {CONFIG}")
    if redacted:
        print(
            f"ATTENTION : {len(redacted)} secret(s) caviarde(s) - voir README pour la restauration."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
