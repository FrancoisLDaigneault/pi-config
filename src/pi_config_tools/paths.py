"""Pi configuration paths.

Roots are resolved at call time (not at import) and can be redirected for
tests via the PI_CONFIG_HOME (user root) and PI_CONFIG_REPO (root of the
repository containing config/) environment variables.
"""

import os
from pathlib import Path

# Relative path (identical on the live side and the repo side) of the patched file in node_modules
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
