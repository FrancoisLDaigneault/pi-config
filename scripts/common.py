"""Fonctions partagees par sync.py, restore.py et backup.py (stdlib uniquement)."""

import fnmatch
import shutil
from pathlib import Path

HOME = Path.home()
PI_AGENT = HOME / ".pi" / "agent"
AGENTS_SKILLS = HOME / ".agents" / "skills"
MEMPALACE = HOME / ".mempalace"
REPO = Path(__file__).resolve().parent.parent
CONFIG = REPO / "config"

# Chemin relatif (identique cote vif et cote repo) du fichier patche dans node_modules
PATCHED_REL = Path("context-mode/build/adapters/pi/extension.js")
CONTEXT_MODE_PKG = PI_AGENT / "npm" / "node_modules" / "context-mode" / "package.json"

# Exclusions par nom, appliquees a toute profondeur
EXCLUDE_DIRS = {"node_modules", "sessions", "__pycache__", ".venv", ".git"}
EXCLUDE_FILE_PATTERNS = [
    "auth.json",
    "*.bak*",
    "settings.backup*",
    "mcp-cache.json",
    "run-history.jsonl",
    "*.pyc",
]


def is_excluded_file(name: str) -> bool:
    return any(fnmatch.fnmatch(name, pat) for pat in EXCLUDE_FILE_PATTERNS)


def copy_tree(src: Path, dst: Path) -> int:
    """Copie recursive src -> dst en appliquant les exclusions. Retourne le nombre de fichiers copies."""
    count = 0
    for item in src.iterdir():
        if item.is_dir():
            if item.name in EXCLUDE_DIRS:
                continue
            count += copy_tree(item, dst / item.name)
        elif item.is_file():
            if is_excluded_file(item.name):
                continue
            dst.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dst / item.name)
            count += 1
    return count


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def context_mode_version() -> str:
    import json

    if CONTEXT_MODE_PKG.exists():
        return json.loads(CONTEXT_MODE_PKG.read_text(encoding="utf-8")).get("version", "inconnue")
    return "inconnue (package.json absent)"
