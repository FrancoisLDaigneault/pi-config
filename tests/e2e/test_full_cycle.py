"""E2E: full cycle through the real scripts/ entry points (subprocess)."""

import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"


def run_script(
    name: str, args: list[str], home: Path, repo: Path
) -> subprocess.CompletedProcess[str]:
    env = os.environ | {"PI_CONFIG_HOME": str(home), "PI_CONFIG_REPO": str(repo)}
    # S603: list form without a shell, running sys.executable on a script
    # from this repo with test-controlled args - no untrusted input involved.
    return subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPTS / name), *args],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def files_under(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): p.read_text(encoding="utf-8")
        for p in root.rglob("*")
        if p.is_file()
    }


def test_sync_then_restore_on_fresh_machine(
    tmp_path: Path, make_fake_home: Callable[[Path], Path]
) -> None:
    """Fake live config -> repo -> fresh empty machine -> identical files."""
    source_home = make_fake_home(tmp_path / "source-machine")
    repo = tmp_path / "repo"
    repo.mkdir()

    result = run_script("sync.py", [], source_home, repo)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Sync done" in result.stdout

    fresh_home = tmp_path / "fresh-machine"
    result = run_script("restore.py", ["--apply", "--patch"], fresh_home, repo)
    assert result.returncode == 0, result.stdout + result.stderr

    # Each restored file must be identical to the source machine,
    # except settings.json whose secret is legitimately redacted by sync
    restored = files_under(fresh_home)
    source = files_under(source_home)
    assert restored, "no file restored"
    for rel, content in restored.items():
        assert rel in source, f"unexpected restored file: {rel}"
        if rel == ".pi/agent/settings.json":
            assert "<REDACTED>" in content
            assert "sk-secret" not in content
        else:
            assert content == source[rel], f"different content: {rel}"

    # Security exclusions never cross the cycle
    assert ".pi/agent/auth.json" not in restored
    assert not any("sessions" in rel for rel in restored)
    assert not any(rel.endswith(".pyc") for rel in restored)
    # The patch crosses with --patch
    assert ".pi/agent/npm/node_modules/context-mode/build/adapters/pi/extension.js" in restored


def test_backup_full_sandbox(tmp_path: Path, make_fake_home: Callable[[Path], Path]) -> None:
    home = make_fake_home(tmp_path / "machine")
    repo = tmp_path / "repo"
    repo.mkdir()
    dest = tmp_path / "backup-dest"

    result = run_script("backup.py", ["--destination", str(dest)], home, repo)
    assert result.returncode == 0, result.stdout + result.stderr

    for line in ["pi-agent", "context-mode patch", "mempalace", "agents-skills", "TOTAL"]:
        assert line in result.stdout
    assert "WARNING MemPalace" in result.stdout
    # The full local backup includes auth.json (unlike the repo)
    assert (dest / "pi-agent" / "auth.json").is_file()
    assert (dest / "mempalace" / "knowledge_graph.sqlite3").is_file()
    assert (dest / "patched-node_modules" / "context-mode-version.txt").is_file()
