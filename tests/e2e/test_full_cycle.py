"""E2E : cycle complet via les vrais points d'entree scripts/ (subprocess)."""

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"


def run_script(name, args, home, repo):
    env = os.environ | {"PI_CONFIG_HOME": str(home), "PI_CONFIG_REPO": str(repo)}
    return subprocess.run(
        [sys.executable, str(SCRIPTS / name), *args],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def files_under(root):
    return {
        p.relative_to(root).as_posix(): p.read_text(encoding="utf-8")
        for p in root.rglob("*")
        if p.is_file()
    }


def test_sync_then_restore_on_fresh_machine(tmp_path, make_fake_home):
    """Fausse config vive -> repo -> nouvelle machine vide -> fichiers identiques."""
    source_home = make_fake_home(tmp_path / "machine-source")
    repo = tmp_path / "repo"
    repo.mkdir()

    result = run_script("sync.py", [], source_home, repo)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Sync termine" in result.stdout

    fresh_home = tmp_path / "machine-neuve"
    result = run_script("restore.py", ["--apply", "--patch"], fresh_home, repo)
    assert result.returncode == 0, result.stdout + result.stderr

    # Chaque fichier restaure doit etre identique a la machine source,
    # sauf settings.json dont le secret est legitimement caviarde par sync
    restored = files_under(fresh_home)
    source = files_under(source_home)
    assert restored, "aucun fichier restaure"
    for rel, content in restored.items():
        assert rel in source, f"fichier inattendu restaure : {rel}"
        if rel == ".pi/agent/settings.json":
            assert "<REDACTED>" in content
            assert "sk-secret" not in content
        else:
            assert content == source[rel], f"contenu different : {rel}"

    # Les exclusions de securite ne traversent jamais le cycle
    assert ".pi/agent/auth.json" not in restored
    assert not any("sessions" in rel for rel in restored)
    assert not any(rel.endswith(".pyc") for rel in restored)
    # Le patch traverse avec --patch
    assert ".pi/agent/npm/node_modules/context-mode/build/adapters/pi/extension.js" in restored


def test_backup_full_sandbox(tmp_path, make_fake_home):
    home = make_fake_home(tmp_path / "machine")
    repo = tmp_path / "repo"
    repo.mkdir()
    dest = tmp_path / "backup-dest"

    result = run_script("backup.py", ["--destination", str(dest)], home, repo)
    assert result.returncode == 0, result.stdout + result.stderr

    for line in ["pi-agent", "patch context-mode", "mempalace", "agents-skills", "TOTAL"]:
        assert line in result.stdout
    assert "ATTENTION MemPalace" in result.stdout
    # Le backup local complet inclut auth.json (contrairement au repo)
    assert (dest / "pi-agent" / "auth.json").is_file()
    assert (dest / "mempalace" / "knowledge_graph.sqlite3").is_file()
    assert (dest / "patched-node_modules" / "context-mode-version.txt").is_file()
