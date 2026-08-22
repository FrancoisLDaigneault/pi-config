"""Integration: restore against a sandbox (dry-run, --apply, auth.json, --patch)."""

import shutil
from pathlib import Path

import pytest

from pi_config_tools import sync
from pi_config_tools.restore import main


def snapshot(root: Path) -> dict[str, bytes]:
    """Bytes: the sandbox holds a real SQLite database, which is not text."""
    if not root.exists():
        return {}
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_restore_requires_config(sandbox: tuple[Path, Path]) -> None:
    assert main([]) == 1


def test_dry_run_changes_nothing(sandbox: tuple[Path, Path]) -> None:
    home, _repo = sandbox
    assert sync.main() == 0
    before = snapshot(home)
    assert main([]) == 0
    assert snapshot(home) == before


def test_apply_restores_to_fresh_home(
    sandbox: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _home, _repo = sandbox
    assert sync.main() == 0
    fresh = tmp_path / "fresh-home"
    monkeypatch.setenv("PI_CONFIG_HOME", str(fresh))

    assert main(["--apply"]) == 0

    agent = fresh / ".pi" / "agent"
    assert (agent / "APPEND_SYSTEM.md").read_text(encoding="utf-8") == "# Persona"
    assert (agent / "extensions" / "guard.ts").is_file()
    assert (fresh / ".agents" / "skills" / "scaffold" / "SKILL.md").is_file()
    # Without --patch: nothing in node_modules
    assert not (agent / "npm" / "node_modules").exists()


def test_apply_never_touches_auth_json(
    sandbox: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Defense in depth: even an auth.json planted in config/ is not restored."""
    _home, repo = sandbox
    assert sync.main() == 0
    (repo / "config" / "pi-agent" / "auth.json").write_text("{malicious}", encoding="utf-8")
    fresh = tmp_path / "fresh-home"
    monkeypatch.setenv("PI_CONFIG_HOME", str(fresh))

    assert main(["--apply"]) == 0
    assert not (fresh / ".pi" / "agent" / "auth.json").exists()


def test_restore_names_a_section_absent_from_the_snapshot(
    sandbox: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    """A section missing from config/ is named and skipped, never silent.

    Mirrors the real repo since #34: config/agents-skills vanished when its
    last skill was removed, because git never versions empty folders.
    """
    _home, repo = sandbox
    assert sync.main() == 0
    shutil.rmtree(repo / "config" / "agents-skills")

    assert main([]) == 0
    assert "info: agents-skills/ missing from the repo, skipped" in capsys.readouterr().out


def test_restore_flags_a_differing_live_file(
    sandbox: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    """A live file whose content differs is named, never silently clobbered."""
    home, _repo = sandbox
    assert sync.main() == 0
    (home / ".pi" / "agent" / "APPEND_SYSTEM.md").write_text("# Changed", encoding="utf-8")

    assert main([]) == 0
    out = capsys.readouterr().out
    assert "APPEND_SYSTEM.md" in out
    assert "DIFFERS from the live file" in out


def test_apply_protects_differing_live_config_until_forced(
    sandbox: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    """Every divergent live configuration file requires destructive opt-in."""
    home, repo = sandbox
    agent = home / ".pi" / "agent"
    live_files = {
        "mcp.json": agent / "mcp.json",
        "settings.json": agent / "settings.json",
        "agents/browser.md": agent / "agents" / "browser.md",
    }
    live_files["agents/browser.md"].parent.mkdir()
    live_files["agents/browser.md"].write_bytes(b"snapshot browser\n")
    assert sync.main() == 0
    snapshot_files = {rel: (repo / "config" / "pi-agent" / rel).read_bytes() for rel in live_files}
    divergent_files = {
        "mcp.json": b'{"servers":{"live-only":{}}}\n',
        "settings.json": b'{"packages":["live-only"]}\n',
        "agents/browser.md": b"live browser\n",
    }
    for rel, content in divergent_files.items():
        live_files[rel].write_bytes(content)

    assert main(["--apply"]) == 1
    assert {rel: path.read_bytes() for rel, path in live_files.items()} == divergent_files
    out = capsys.readouterr().out
    for rel in divergent_files:
        assert f"REFUSED: {rel} differs from live; use --force" in out

    assert main(["--apply", "--force"]) == 0
    assert {rel: path.read_bytes() for rel, path in live_files.items()} == snapshot_files


def test_restore_is_idempotent_and_reports_identical(
    sandbox: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    """Re-applying over an already-restored tree rewrites the same bytes."""
    home, _repo = sandbox
    assert sync.main() == 0
    assert main(["--apply", "--patch", "--force"]) == 0
    before = snapshot(home)

    assert main(["--apply", "--patch"]) == 0
    assert snapshot(home) == before
    assert "(identical)" in capsys.readouterr().out


def test_patch_flag_overwrites_differing_vendor_without_force(
    sandbox: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Vendor patches remain freely restorable after an upstream install."""
    _home, _repo = sandbox
    assert sync.main() == 0
    fresh = tmp_path / "fresh-home"
    monkeypatch.setenv("PI_CONFIG_HOME", str(fresh))
    assert main(["--apply"]) == 0
    patched = (
        fresh
        / ".pi"
        / "agent"
        / "npm"
        / "node_modules"
        / "context-mode"
        / "build"
        / "adapters"
        / "pi"
        / "extension.js"
    )
    patched.parent.mkdir(parents=True)
    patched.write_text("// upstream replacement", encoding="utf-8")

    assert main(["--apply", "--patch"]) == 0
    assert patched.read_text(encoding="utf-8") == "// patched"
    # The patched-node_modules README is repo documentation: never restored
    assert not (fresh / ".pi" / "agent" / "npm" / "node_modules" / "README.md").exists()
