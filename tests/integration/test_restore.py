"""Integration: restore against a sandbox (dry-run, --apply, auth.json, --patch)."""

from pathlib import Path

import pytest

from pi_config_tools import sync
from pi_config_tools.restore import main


def snapshot(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}
    return {
        p.relative_to(root).as_posix(): p.read_text(encoding="utf-8")
        for p in root.rglob("*")
        if p.is_file()
    }


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


def test_patch_flag_includes_patched_node_modules(
    sandbox: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _home, _repo = sandbox
    assert sync.main() == 0
    fresh = tmp_path / "fresh-home"
    monkeypatch.setenv("PI_CONFIG_HOME", str(fresh))

    assert main(["--apply", "--patch"]) == 0
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
    assert patched.read_text(encoding="utf-8") == "// patched"
    # The patched-node_modules README is repo documentation: never restored
    assert not (fresh / ".pi" / "agent" / "npm" / "node_modules" / "README.md").exists()
