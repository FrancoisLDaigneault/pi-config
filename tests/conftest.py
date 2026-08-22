"""Shared fixtures: fake live Pi config + path redirection via environment variables."""

import json
import os
import sqlite3
from collections.abc import Callable
from pathlib import Path

import pytest
from hypothesis import settings

# Hypothesis runs deterministically by default so the pre-commit hook, CI and
# `just check` all see the exact same examples on every run; set
# HYPOTHESIS_PROFILE=explore for a randomized, larger local search. deadline is
# disabled to absorb Windows CI timing variance; the budget is bounded by
# max_examples and the strategies' size caps instead.
settings.register_profile("deterministic", derandomize=True, max_examples=50, deadline=None)
settings.register_profile("explore", max_examples=300, deadline=None)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "deterministic"))


def touch(path: Path, content: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def make_wal_database(path: Path, rows: int = 1) -> None:
    """A real WAL-mode SQLite database, cleanly closed (Pi not running).

    A text file named `.sqlite3` proved nothing about the backup path: it never
    reached SQLite. This one does, so the backup section is exercised for what
    it actually has to do. Closing the last connection checkpoints and removes
    the -wal, so a test that needs a live one opens its own connection.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    try:
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("CREATE TABLE IF NOT EXISTS memories (body TEXT)")
        con.executemany("INSERT INTO memories VALUES (?)", [(f"memory-{i}",) for i in range(rows)])
        con.commit()
    finally:
        con.close()


def build_fake_home(home: Path) -> Path:
    """Builds a minimal but representative fake live Pi config."""
    agent = home / ".pi" / "agent"
    touch(agent / "APPEND_SYSTEM.md", "# Persona")
    touch(agent / "settings.json", json.dumps({"packages": ["pi-lens"], "apiKey": "sk-secret"}))
    touch(agent / "mcp.json", json.dumps({"servers": {}}))
    touch(agent / "auth.json", json.dumps({"token": "private"}))
    touch(agent / "mcp-cache.json", "{}")
    touch(agent / "run-history.jsonl", "{}")
    touch(agent / "settings.backup-old.json", "{}")
    touch(agent / "extensions" / "guard.ts", "export {}")
    touch(agent / "prompts" / "contract.md", "# Contract")
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
        agent
        / "npm"
        / "node_modules"
        / "context-mode"
        / "build"
        / "adapters"
        / "pi"
        / "extension.js",
        "// patched",
    )
    # Directory entry of PATCHED_RELS: snapshotted whole (the bigpowers skills entries
    # stay absent on purpose, so the missing-entry branch is exercised too).
    touch(
        agent / "npm" / "node_modules" / "context-mode" / "skills" / "ctx-stats" / "SKILL.md",
        "# Stats",
    )
    # Vendor helper scripts carry local fixes too: the whole tree is an entry.
    touch(
        agent / "npm" / "node_modules" / "bigpowers" / "scripts" / "lib" / "doc-fetch-cache.sh",
        "#!/usr/bin/env bash\n",
    )
    touch(
        agent
        / "npm"
        / "node_modules"
        / "pi-subagents"
        / "src"
        / "runs"
        / "shared"
        / "mcp-direct-tool-allowlist.ts",
        "// patched direct tool allowlist\n",
    )
    skills = home / ".agents" / "skills"
    touch(skills / "scaffold" / "SKILL.md", "# Scaffold")
    touch(skills / "scaffold" / "__pycache__" / "m.pyc", "bin")
    mem = home / ".mempalace"
    make_wal_database(mem / "knowledge_graph.sqlite3")
    touch(mem / "notes.md", "# plain file next to a database")
    return home


@pytest.fixture(autouse=True)
def _isolate_real_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Defense in depth: without a sandbox, paths point to a nonexistent tmp dir."""
    monkeypatch.setenv("PI_CONFIG_HOME", str(tmp_path / "void" / "home"))
    monkeypatch.setenv("PI_CONFIG_REPO", str(tmp_path / "void" / "repo"))


@pytest.fixture
def sandbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    """(home, repo) redirected via PI_CONFIG_HOME / PI_CONFIG_REPO."""
    home = build_fake_home(tmp_path / "home")
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv("PI_CONFIG_HOME", str(home))
    monkeypatch.setenv("PI_CONFIG_REPO", str(repo))
    return home, repo


@pytest.fixture
def make_fake_home() -> Callable[[Path], Path]:
    """Exposes the builder to e2e tests without cross-imports between test modules."""
    return build_fake_home


@pytest.fixture
def wal_database() -> Callable[..., None]:
    """Exposes the real-database builder to the backup tests."""
    return make_wal_database
