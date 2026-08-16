"""Integration : backup contre un sandbox (sections, inclusions, erreur simulee)."""

from pathlib import Path

import pytest

import pi_config_tools.backup as backup_mod
from pi_config_tools.backup import main


def test_backup_sections_and_inclusions(
    sandbox: tuple[Path, Path], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dest = tmp_path / "backup"
    assert main(["--destination", str(dest)]) == 0

    # Backup local complet : auth.json et settings.backup* INCLUS
    assert (dest / "pi-agent" / "auth.json").is_file()
    assert (dest / "pi-agent" / "settings.backup-old.json").is_file()
    # Exclusions propres au backup
    assert not (dest / "pi-agent" / "npm" / "node_modules").exists()
    assert not (dest / "pi-agent" / "sessions").exists()
    assert not (dest / "pi-agent" / "mcp-cache.json").exists()
    # Patch + version
    assert (
        dest
        / "patched-node_modules"
        / "context-mode"
        / "build"
        / "adapters"
        / "pi"
        / "extension.js"
    ).is_file()
    version = dest / "patched-node_modules" / "context-mode-version.txt"
    assert "9.9.9" in version.read_text(encoding="utf-8")
    # MemPalace complet + avertissement wal/shm
    assert (dest / "mempalace" / "knowledge_graph.sqlite3").is_file()
    assert (dest / "mempalace" / "knowledge_graph.sqlite3-wal").is_file()
    out = capsys.readouterr().out
    assert "ATTENTION MemPalace" in out
    # Skills sans caches Python
    assert (dest / "agents-skills" / "scaffold" / "SKILL.md").is_file()
    assert not (dest / "agents-skills" / "scaffold" / "__pycache__").exists()


def test_backup_exit_1_on_section_error(
    sandbox: tuple[Path, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def boom(*_args: object, **_kwargs: object) -> int:
        raise OSError("disque plein (simule)")

    monkeypatch.setattr(backup_mod, "copy_tree", boom)
    dest = tmp_path / "backup"
    assert main(["--destination", str(dest)]) == 1
    out = capsys.readouterr().out
    assert "ERREUR pi-agent" in out
    assert "ERREURS dans section(s)" in out
