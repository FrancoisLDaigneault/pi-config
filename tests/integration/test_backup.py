"""Integration: backup against a sandbox (sections, inclusions, simulated error)."""

import sqlite3
from pathlib import Path

import pytest

import pi_config_tools.backup as backup_mod
from pi_config_tools.backup import main


def test_backup_sections_and_inclusions(
    sandbox: tuple[Path, Path], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dest = tmp_path / "backup"
    assert main(["--destination", str(dest)]) == 0

    # Full local backup: auth.json and settings.backup* INCLUDED
    assert (dest / "pi-agent" / "auth.json").is_file()
    assert (dest / "pi-agent" / "settings.backup-old.json").is_file()
    # Backup-specific exclusions
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
    # MemPalace: databases snapshotted, plain neighbours copied, sidecars skipped
    backed_up = dest / "mempalace" / "knowledge_graph.sqlite3"
    assert backed_up.is_file()
    assert (dest / "mempalace" / "notes.md").is_file()
    assert not (dest / "mempalace" / "knowledge_graph.sqlite3-wal").exists(), (
        "copying the sidecar back would restore the torn state the snapshot avoids"
    )
    out = capsys.readouterr().out
    assert "1 SQLite database(s) snapshotted" in out
    assert "WARNING MemPalace" not in out, "a live -wal is normal, not a warning"
    # Skills without Python caches
    assert (dest / "agents-skills" / "scaffold" / "SKILL.md").is_file()
    assert not (dest / "agents-skills" / "scaffold" / "__pycache__").exists()


def test_backup_exit_1_on_section_error(
    sandbox: tuple[Path, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def boom(*_args: object, **_kwargs: object) -> int:
        raise OSError("disk full (simulated)")

    monkeypatch.setattr(backup_mod, "copy_tree", boom)
    dest = tmp_path / "backup"
    assert main(["--destination", str(dest)]) == 1
    out = capsys.readouterr().out
    assert "ERROR pi-agent" in out
    assert "ERRORS in section(s)" in out


def test_backup_refuses_a_destination_that_is_a_backed_up_root(
    sandbox: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    home, _repo = sandbox
    mem = home / ".mempalace"
    before = sorted(p.name for p in mem.iterdir())

    assert main(["--destination", str(mem)]) == 1
    out = capsys.readouterr().out
    assert "is the backed-up folder" in out
    assert "would copy itself" in out
    assert sorted(p.name for p in mem.iterdir()) == before, "nothing may be written"


def test_backup_refuses_a_destination_under_a_backed_up_root(
    sandbox: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    home, _repo = sandbox
    nested = home / ".pi" / "agent" / "nested" / "backup"

    assert main(["--destination", str(nested)]) == 1
    assert "is inside the backed-up folder" in capsys.readouterr().out
    assert not nested.exists(), "the destination must not be created before the refusal"


def test_backup_resolves_the_destination_before_judging_it(
    sandbox: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    """A `..` detour must not smuggle the destination back under a source."""
    home, _repo = sandbox
    detour = home / ".mempalace" / ".." / ".mempalace" / "sneaky"

    assert main(["--destination", str(detour)]) == 1
    assert "is inside the backed-up folder" in capsys.readouterr().out
    assert not (home / ".mempalace" / "sneaky").exists()


def test_backup_accepts_a_destination_outside_every_source(
    sandbox: tuple[Path, Path], tmp_path: Path
) -> None:
    """The guard must not reject the ordinary case it exists to protect."""
    dest = tmp_path / "elsewhere" / "backup"
    assert main(["--destination", str(dest)]) == 0
    assert (dest / "mempalace" / "knowledge_graph.sqlite3").is_file()


def test_backup_while_the_database_is_open_restores_its_committed_rows(
    sandbox: tuple[Path, Path], tmp_path: Path
) -> None:
    """Back up while Pi is running - the case the old warning told you to avoid.

    A live connection keeps the -wal on disk and the newest commits inside it.
    The measure that matters is not that files were copied, but that the backup
    opens and still holds every committed row.
    """
    home, _repo = sandbox
    live = home / ".mempalace" / "knowledge_graph.sqlite3"
    dest = tmp_path / "backup"

    holder = sqlite3.connect(live)
    try:
        holder.executemany("INSERT INTO memories VALUES (?)", [(f"live-{i}",) for i in range(25)])
        holder.commit()
        assert (home / ".mempalace" / "knowledge_graph.sqlite3-wal").exists(), (
            "an open connection must leave a live WAL for this test to mean anything"
        )
        assert main(["--destination", str(dest)]) == 0
    finally:
        holder.close()

    assert not (dest / "mempalace" / "knowledge_graph.sqlite3-wal").exists()
    restored = sqlite3.connect(dest / "mempalace" / "knowledge_graph.sqlite3")
    try:
        assert restored.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        rows = int(restored.execute("SELECT count(*) FROM memories").fetchone()[0])
    finally:
        restored.close()
    # 1 row from the fixture plus the 25 committed into the live WAL: a copy
    # that dropped the WAL would answer 1.
    assert rows == 26
