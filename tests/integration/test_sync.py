"""Integration: sync against a fake tree (never the real config)."""

import json
import os
import shutil
from pathlib import Path

import pytest

from pi_config_tools.sync import main


def _snapshot(root: Path) -> dict[str, bytes]:
    """Every file under `root`, by content - directories excluded on purpose.

    Reading a directory raises PermissionError on Windows, which would make the
    survival assertion below fail for a reason that has nothing to do with the
    snapshot surviving.
    """
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_sync_copies_and_excludes(sandbox: tuple[Path, Path]) -> None:
    home, repo = sandbox
    live_mcp = home / ".pi" / "agent" / "mcp.json"
    mcp_payload = b'{"servers":{"sandbox":{"command":"distinctive-sync-marker"}}}\n'
    live_mcp.write_bytes(mcp_payload)

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
    assert (config / "pi-agent" / "mcp.json").read_bytes() == mcp_payload
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


def test_sync_copies_a_patched_directory_whole(sandbox: tuple[Path, Path]) -> None:
    """A directory entry of PATCHED_RELS is snapshotted with its whole content."""
    _home, repo = sandbox
    assert main() == 0
    skill = repo / "config" / "patched-node_modules" / "context-mode" / "skills"
    assert (skill / "ctx-stats" / "SKILL.md").read_text(encoding="utf-8") == "# Stats"
    # The generated README lists every configured entry, not just the single file
    readme = (repo / "config" / "patched-node_modules" / "README.md").read_text(encoding="utf-8")
    assert "context-mode/skills" in readme
    assert "bigpowers/skills" in readme


def test_sync_copies_patched_vendor_scripts(sandbox: tuple[Path, Path]) -> None:
    """Vendor helper scripts are snapshotted: a local fix there survives a reinstall."""
    _home, repo = sandbox
    assert main() == 0
    patched = repo / "config" / "patched-node_modules"
    helper = patched / "bigpowers" / "scripts" / "lib" / "doc-fetch-cache.sh"
    assert helper.read_text(encoding="utf-8") == "#!/usr/bin/env bash\n"
    allowlist = (
        patched / "pi-subagents" / "src" / "runs" / "shared" / "mcp-direct-tool-allowlist.ts"
    )
    assert allowlist.read_text(encoding="utf-8") == "// patched direct tool allowlist\n"


def test_sync_reports_missing_patched_entry(
    sandbox: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    """The bigpowers skills entries are absent from the sandbox: reported, never silent."""
    _home, repo = sandbox
    assert main() == 0
    out = capsys.readouterr().out
    assert "bigpowers/.pi/skills missing from node_modules, skipped" in out
    assert "bigpowers/skills missing from node_modules, skipped" in out
    assert not (repo / "config" / "patched-node_modules" / "bigpowers" / "skills").exists()


def test_sync_redacts_secrets(sandbox: tuple[Path, Path]) -> None:
    _home, repo = sandbox
    assert main() == 0
    settings = json.loads(
        (repo / "config" / "pi-agent" / "settings.json").read_text(encoding="utf-8")
    )
    assert settings["apiKey"] == "<REDACTED>"
    assert settings["packages"] == ["pi-lens"]


def test_sync_redacts_root_string_file(
    sandbox: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    home, repo = sandbox
    (home / ".pi" / "agent" / "claude-bridge.json").write_text(
        json.dumps("sk-live-abc123"), encoding="utf-8"
    )
    assert main() == 0
    copied = repo / "config" / "pi-agent" / "claude-bridge.json"
    assert copied.read_text(encoding="utf-8") == '"<REDACTED>"\n'
    # Reported once by sync_json_with_audit; the post-copy scan must not re-report it.
    assert capsys.readouterr().out.count("<root>") == 1


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
    """An invalid live JSON aborts the sync AND leaves the last snapshot intact.

    Asserting the exit code alone passed against the version that deleted
    config/ before reading anything: the run failed loudly while the previous
    snapshot was already gone. What has to hold is that it survives.
    """
    home, repo = sandbox
    config = repo / "config"
    config.mkdir()
    (config / "PRECIOUS.md").write_text("irreplaceable", encoding="utf-8")
    before = _snapshot(config)

    (home / ".pi" / "agent" / "settings.json").write_text("{not json", encoding="utf-8")
    assert main() == 1
    assert "sync aborted" in capsys.readouterr().out

    after = _snapshot(config)
    assert after == before, "a failed sync must leave the previous snapshot byte-identical"
    assert not list(repo.glob(".config-staging-*")), "the staging tree must be cleaned up"


def test_sync_swap_failure_exits_1_and_keeps_the_previous_snapshot(
    sandbox: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The build succeeds but installing it fails: report, and keep the old snapshot."""
    _home, repo = sandbox
    config = repo / "config"
    config.mkdir()
    (config / "PRECIOUS.md").write_text("irreplaceable", encoding="utf-8")

    def deny(*_args: object, **_kwargs: object) -> None:
        raise PermissionError("access denied (simulated)")

    monkeypatch.setattr(os, "replace", deny)
    assert main() == 1
    out = capsys.readouterr().out
    assert "could not move the previous" in out
    assert "is unchanged" in out
    assert (config / "PRECIOUS.md").read_text(encoding="utf-8") == "irreplaceable"
    assert not list(repo.glob(".config-staging-*")), "the staging tree must be cleaned up"


def test_sync_says_the_snapshot_is_missing_when_the_rollback_also_failed(
    sandbox: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Install and rollback both fail: name the aside copy, never say 'unchanged'."""
    _home, repo = sandbox
    config = repo / "config"
    config.mkdir()
    (config / "PRECIOUS.md").write_text("irreplaceable", encoding="utf-8")
    real_replace = os.replace
    calls: list[int] = []

    def fail_after_first(src: Path, dst: Path) -> None:
        calls.append(1)
        if len(calls) == 1:
            real_replace(src, dst)
            return
        raise PermissionError("access denied (simulated)")

    monkeypatch.setattr(os, "replace", fail_after_first)
    assert main() == 1
    out = capsys.readouterr().out

    assert "IS MISSING" in out, "the operator must be told the snapshot is gone"
    assert "is unchanged" not in out, "claiming it is unchanged is the bug under test"
    asides = list(repo.glob("config.old-*"))
    assert len(asides) == 1
    assert (asides[0] / "PRECIOUS.md").read_text(encoding="utf-8") == "irreplaceable"
    assert str(asides[0]) in out, "the recovery path must be printed, not merely implied"
    assert list(repo.glob(".config-staging-*")), (
        "the new snapshot is the only complete copy left and must not be deleted"
    )


def test_sync_recovers_a_snapshot_left_aside_by_an_interrupted_run(
    sandbox: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    """config/ missing plus exactly one aside copy is the deterministic crash state.

    Recovery restores the git reference, not the content: the sync that follows
    rebuilds config/ from the live tree, so PRECIOUS.md is gone by the end and
    that is correct. What the recovery actually moved is asserted where it can
    still be seen -- in test_fsops.py, and in the test below, where the rebuild
    never gets far enough to replace it.
    """
    _home, repo = sandbox
    aside = repo / "config.old-deadbeef"
    aside.mkdir()
    (aside / "PRECIOUS.md").write_text("irreplaceable", encoding="utf-8")

    assert main() == 0
    out = capsys.readouterr().out
    assert "a previous sync was interrupted" in out
    assert not aside.exists(), "the aside copy is moved back, not copied"
    assert (repo / "config" / "pi-agent").is_dir(), "the rebuild replaces what was recovered"


def test_sync_keeps_the_recovered_snapshot_when_the_rebuild_fails(
    sandbox: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    """Recovery has to put the files back, not merely announce that it did.

    A recovery that deleted the aside and printed the same line passed the test
    above -- replayed, it did, because nothing there reads the recovered files.
    Invalid live JSON stops the rebuild before the swap, so the snapshot is
    still on disk at the end and its content can be read back.
    """
    home, repo = sandbox
    aside = repo / "config.old-deadbeef"
    aside.mkdir()
    (aside / "PRECIOUS.md").write_text("irreplaceable", encoding="utf-8")
    (home / ".pi" / "agent" / "mcp.json").write_text("{ not json", encoding="utf-8")

    assert main() == 1
    out = capsys.readouterr().out

    assert "a previous sync was interrupted" in out
    assert (repo / "config" / "PRECIOUS.md").read_text(encoding="utf-8") == "irreplaceable", (
        "the recovered snapshot must be the files themselves, not a line about them"
    )
    assert not aside.exists()


def test_sync_refuses_to_choose_between_several_aside_copies(
    sandbox: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    """Ambiguous recovery is the operator's call; sync must not guess."""
    _home, repo = sandbox
    for token in ("aaaa1111", "bbbb2222"):
        aside = repo / f"config.old-{token}"
        aside.mkdir()
        (aside / "PRECIOUS.md").write_text(token, encoding="utf-8")

    assert main() == 1
    out = capsys.readouterr().out
    assert "several previous snapshots" in out
    assert "config.old-aaaa1111" in out and "config.old-bbbb2222" in out
    assert not (repo / "config").exists(), "nothing may be installed while it is ambiguous"


def test_sync_leaves_no_staging_directory_behind(sandbox: tuple[Path, Path]) -> None:
    """A successful sync must not leave the transient build tree in the repo."""
    _home, repo = sandbox
    assert main() == 0
    assert not list(repo.glob(".config-staging-*"))
    assert not list(repo.glob("config.old-*"))


def test_sync_names_a_build_tree_left_by_an_earlier_run(
    sandbox: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    """A dead run's build tree is gitignored, so only sync can mention it.

    It is named rather than removed: the pid in the name may belong to a sync
    running right now, or to a process whose pid has since been reused, and
    deleting a live run's build tree would be worse than leaving this one.

    The warning has to carry that same doubt. Sync cannot tell a dead run's
    tree from a live one's, so an instruction to delete it without qualifying
    it is advice to destroy a concurrent run's work.
    """
    _home, repo = sandbox
    stale = repo / ".config-staging-dead"
    stale.mkdir()
    (stale / "GHOST.md").write_text("from a killed run", encoding="utf-8")

    assert main() == 0
    out = capsys.readouterr().out

    assert str(stale) in out, "the path must be named, not merely counted"
    assert "remove it by hand" in out
    assert "another or a previous run" in out, "it may be a live run's tree, not a leftover"
    assert "make sure no other" in out, "deleting it blind is the dangerous part"
    assert (stale / "GHOST.md").is_file(), "an unknown build tree is not sync's to delete"
    assert f".config-staging-{os.getpid()}" not in out, (
        "a run must not warn about the build tree it just made itself"
    )


def test_sync_stops_when_a_stale_staging_tree_survives_cleanup(
    sandbox: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A crashed run's leftovers must not be folded into the new snapshot."""
    _home, repo = sandbox
    (repo / "config").mkdir()
    staging = repo / f".config-staging-{os.getpid()}"
    (staging / "pi-agent").mkdir(parents=True)
    (staging / "pi-agent" / "GHOST.md").write_text("from a crashed run", encoding="utf-8")
    monkeypatch.setattr(shutil, "rmtree", lambda *_a, **_kw: None)

    assert main() == 1
    out = capsys.readouterr().out
    assert "survived cleanup" in out
    assert not (repo / "config" / "pi-agent" / "GHOST.md").exists(), (
        "the stale file must never reach the installed snapshot"
    )
