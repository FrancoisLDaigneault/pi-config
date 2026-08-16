"""Integration : restore contre un sandbox (dry-run, --apply, auth.json, --patch)."""

from pi_config_tools import sync
from pi_config_tools.restore import main


def snapshot(root):
    if not root.exists():
        return {}
    return {
        p.relative_to(root).as_posix(): p.read_text(encoding="utf-8")
        for p in root.rglob("*")
        if p.is_file()
    }


def test_restore_requires_config(sandbox):
    assert main([]) == 1


def test_dry_run_changes_nothing(sandbox):
    home, _repo = sandbox
    assert sync.main() == 0
    before = snapshot(home)
    assert main([]) == 0
    assert snapshot(home) == before


def test_apply_restores_to_fresh_home(sandbox, monkeypatch, tmp_path):
    _home, _repo = sandbox
    assert sync.main() == 0
    fresh = tmp_path / "fresh-home"
    monkeypatch.setenv("PI_CONFIG_HOME", str(fresh))

    assert main(["--apply"]) == 0

    agent = fresh / ".pi" / "agent"
    assert (agent / "APPEND_SYSTEM.md").read_text(encoding="utf-8") == "# Persona"
    assert (agent / "extensions" / "guard.ts").is_file()
    assert (fresh / ".agents" / "skills" / "scaffold" / "SKILL.md").is_file()
    # Sans --patch : rien dans node_modules
    assert not (agent / "npm" / "node_modules").exists()


def test_apply_never_touches_auth_json(sandbox, monkeypatch, tmp_path):
    """Defense en profondeur : meme un auth.json plante dans config/ n'est pas restaure."""
    _home, repo = sandbox
    assert sync.main() == 0
    (repo / "config" / "pi-agent" / "auth.json").write_text("{malveillant}", encoding="utf-8")
    fresh = tmp_path / "fresh-home"
    monkeypatch.setenv("PI_CONFIG_HOME", str(fresh))

    assert main(["--apply"]) == 0
    assert not (fresh / ".pi" / "agent" / "auth.json").exists()


def test_patch_flag_includes_patched_node_modules(sandbox, monkeypatch, tmp_path):
    _home, _repo = sandbox
    assert sync.main() == 0
    fresh = tmp_path / "fresh-home"
    monkeypatch.setenv("PI_CONFIG_HOME", str(fresh))

    assert main(["--apply", "--patch"]) == 0
    patched = (
        fresh / ".pi" / "agent" / "npm" / "node_modules" / "context-mode" / "build"
        / "adapters" / "pi" / "extension.js"
    )
    assert patched.read_text(encoding="utf-8") == "// patched"
    # Le README de patched-node_modules est une doc du repo : jamais restaure
    assert not (fresh / ".pi" / "agent" / "npm" / "node_modules" / "README.md").exists()
