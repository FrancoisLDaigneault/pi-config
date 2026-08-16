"""Fixtures partagees : fausse config Pi vive + redirection des chemins par variables d'env."""

import json

import pytest


def touch(path, content="x"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_fake_home(home):
    """Construit une fausse config Pi vive minimale mais representative."""
    agent = home / ".pi" / "agent"
    touch(agent / "APPEND_SYSTEM.md", "# Persona")
    touch(agent / "settings.json", json.dumps({"packages": ["pi-lens"], "apiKey": "sk-secret"}))
    touch(agent / "mcp.json", json.dumps({"servers": {}}))
    touch(agent / "auth.json", json.dumps({"token": "prive"}))
    touch(agent / "mcp-cache.json", "{}")
    touch(agent / "run-history.jsonl", "{}")
    touch(agent / "settings.backup-old.json", "{}")
    touch(agent / "extensions" / "guard.ts", "export {}")
    touch(agent / "prompts" / "contract.md", "# Contrat")
    touch(agent / "skills" / "loop" / "SKILL.md", "# Skill")
    touch(agent / "packages" / "parity" / "index.js", "module.exports = {}")
    touch(agent / "sessions" / "old.jsonl", "{}")
    touch(agent / "npm" / "package.json", json.dumps({"dependencies": {}}))
    touch(agent / "npm" / "package-lock.json", json.dumps({"lockfileVersion": 3}))
    touch(
        agent / "npm" / "node_modules" / "context-mode" / "package.json",
        json.dumps({"version": "9.9.9"}),
    )
    touch(
        agent / "npm" / "node_modules" / "context-mode" / "build" / "adapters" / "pi"
        / "extension.js",
        "// patched",
    )
    skills = home / ".agents" / "skills"
    touch(skills / "scaffold" / "SKILL.md", "# Scaffold")
    touch(skills / "scaffold" / "__pycache__" / "m.pyc", "bin")
    mem = home / ".mempalace"
    touch(mem / "knowledge_graph.sqlite3", "db")
    touch(mem / "knowledge_graph.sqlite3-wal", "wal")
    return home


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """(home, repo) rediriges via PI_CONFIG_HOME / PI_CONFIG_REPO."""
    home = build_fake_home(tmp_path / "home")
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv("PI_CONFIG_HOME", str(home))
    monkeypatch.setenv("PI_CONFIG_REPO", str(repo))
    return home, repo


@pytest.fixture
def make_fake_home():
    """Expose le builder aux tests e2e sans import inter-modules de tests."""
    return build_fake_home
