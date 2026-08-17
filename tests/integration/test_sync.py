"""Integration: sync against a fake tree (never the real config)."""

import json
import shutil
from pathlib import Path

import pytest

from pi_config_tools.sync import main


def test_sync_copies_and_excludes(sandbox: tuple[Path, Path]) -> None:
    _home, repo = sandbox
    assert main() == 0
    config = repo / "config"

    # Expected copies
    assert (config / "pi-agent" / "APPEND_SYSTEM.md").is_file()
    assert (config / "pi-agent" / "extensions" / "guard.ts").is_file()
    assert (config / "pi-agent" / "prompts" / "contract.md").is_file()
    assert (config / "pi-agent" / "skills" / "loop" / "SKILL.md").is_file()
    assert (config / "pi-agent" / "packages" / "parity" / "index.js").is_file()
    assert (config / "pi-agent" / "npm" / "package.json").is_file()
    assert (config / "pi-agent" / "npm" / "package-lock.json").is_file()
    assert (config / "agents-skills" / "scaffold" / "SKILL.md").is_file()

    # context-mode patch + generated README with the version
    patched = config / "patched-node_modules"
    assert (patched / "context-mode" / "build" / "adapters" / "pi" / "extension.js").is_file()
    assert "9.9.9" in (patched / "README.md").read_text(encoding="utf-8")

    # Exclusions
    copied = {p.name for p in config.rglob("*") if p.is_file()}
    assert "auth.json" not in copied
    assert "mcp-cache.json" not in copied
    assert "run-history.jsonl" not in copied
    assert "settings.backup-old.json" not in copied
    assert "m.pyc" not in copied
    assert not (config / "pi-agent" / "sessions").exists()
    assert not (config / "pi-agent" / "npm" / "node_modules").exists()


def test_sync_redacts_secrets(sandbox: tuple[Path, Path]) -> None:
    _home, repo = sandbox
    assert main() == 0
    settings = json.loads(
        (repo / "config" / "pi-agent" / "settings.json").read_text(encoding="utf-8")
    )
    assert settings["apiKey"] == "<REDACTED>"
    assert settings["packages"] == ["pi-lens"]


def test_sync_rebuilds_config_from_scratch(sandbox: tuple[Path, Path]) -> None:
    _home, repo = sandbox
    stale = repo / "config" / "obsolete.txt"
    stale.parent.mkdir(parents=True)
    stale.write_text("old", encoding="utf-8")
    assert main() == 0
    assert not stale.exists()


def test_sync_invalid_live_json_exits_1(
    sandbox: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    home, _repo = sandbox
    (home / ".pi" / "agent" / "settings.json").write_text("{not json", encoding="utf-8")
    assert main() == 1
    assert "sync aborted" in capsys.readouterr().out


def test_sync_rmtree_failure_exits_1(
    sandbox: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _home, repo = sandbox
    (repo / "config").mkdir()

    def boom(path: Path) -> None:
        raise OSError("access denied")

    # sync.shutil is the global shutil module: patching it directly is equivalent
    # (mypy strict forbids access to the implicit re-export sync.shutil)
    monkeypatch.setattr(shutil, "rmtree", boom)
    assert main() == 1
    assert "cannot clean" in capsys.readouterr().out
