"""Chemins de la configuration Pi.

Les racines sont resolues a l'appel (pas a l'import) et redirigeables pour les
tests via les variables d'environnement PI_CONFIG_HOME (racine utilisateur) et
PI_CONFIG_REPO (racine du depot contenant config/).
"""

import os
from pathlib import Path

# Chemin relatif (identique cote vif et cote repo) du fichier patche dans node_modules
PATCHED_REL = Path("context-mode/build/adapters/pi/extension.js")


def home() -> Path:
    return Path(os.environ.get("PI_CONFIG_HOME") or Path.home())


def pi_agent() -> Path:
    return home() / ".pi" / "agent"


def agents_skills() -> Path:
    return home() / ".agents" / "skills"


def mempalace() -> Path:
    return home() / ".mempalace"


def repo_root() -> Path:
    return Path(os.environ.get("PI_CONFIG_REPO") or Path(__file__).resolve().parents[2])


def config_dir() -> Path:
    return repo_root() / "config"


def context_mode_pkg() -> Path:
    return pi_agent() / "npm" / "node_modules" / "context-mode" / "package.json"


def patched_live() -> Path:
    return pi_agent() / "npm" / "node_modules" / PATCHED_REL
