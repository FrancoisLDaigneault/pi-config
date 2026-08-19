"""Pi configuration paths.

Roots are resolved at call time (not at import) and can be redirected for
tests via the PI_CONFIG_HOME (user root) and PI_CONFIG_REPO (root of the
repository containing config/) environment variables.
"""

import os
from pathlib import Path

# Relative paths (identical on the live side and the repo side) of the locally patched
# entries under node_modules. An entry is either a single file or a whole directory:
# directories are snapshotted entirely, so every local edit inside them is preserved
# without maintaining a per-file list that would silently rot.
PATCHED_RELS: tuple[Path, ...] = (
    Path("context-mode/build/adapters/pi/extension.js"),
    Path("context-mode/skills"),
    Path("bigpowers/.pi/skills"),
    Path("bigpowers/skills"),
    Path("bigpowers/scripts"),
    Path("pi-mcp-adapter/ui-server.ts"),
    Path("pi-subagents/src/runs/shared/mcp-direct-tool-allowlist.ts"),
)


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


def node_modules() -> Path:
    return pi_agent() / "npm" / "node_modules"


def patched_live(rel: Path) -> Path:
    return node_modules() / rel
