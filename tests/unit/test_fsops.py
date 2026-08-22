"""Unit tests for copy_tree and the exclusions (everything in tmp_path)."""

import os
import shutil
from pathlib import Path

import pytest

from pi_config_tools.fsops import SwapError, copy_tree, swap_dir


def _touch(path: Path, content: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_copy_tree_default_exclusions(tmp_path: Path) -> None:
    src = tmp_path / "src"
    _touch(src / "keep.md")
    _touch(src / "sub" / "keep.json")
    _touch(src / "auth.json", "secret")
    _touch(src / "settings.backup-old.json")
    _touch(src / "mcp-cache.json")
    _touch(src / "run-history.jsonl")
    _touch(src / "module.pyc")
    _touch(src / "node_modules" / "pkg" / "index.js")
    _touch(src / "sessions" / "log.jsonl")
    _touch(src / "__pycache__" / "m.pyc")

    dst = tmp_path / "dst"
    count = copy_tree(src, dst)

    assert count == 2
    copied = sorted(p.relative_to(dst).as_posix() for p in dst.rglob("*") if p.is_file())
    assert copied == ["keep.md", "sub/keep.json"]


def test_copy_tree_custom_exclusions(tmp_path: Path) -> None:
    src = tmp_path / "src"
    _touch(src / "auth.json", "secret")
    _touch(src / "data.txt")
    _touch(src / "node_modules" / "x.js")

    dst = tmp_path / "dst"
    count = copy_tree(src, dst, exclude_dirs=set(), exclude_files=[])

    # empty exclusions = everything is copied (full backup mode)
    assert count == 3
    assert (dst / "auth.json").read_text(encoding="utf-8") == "secret"


def test_copy_tree_preserves_content(tmp_path: Path) -> None:
    src = tmp_path / "src"
    _touch(src / "a" / "b" / "deep.txt", "deep content")
    dst = tmp_path / "dst"
    assert copy_tree(src, dst) == 1
    assert (dst / "a" / "b" / "deep.txt").read_text(encoding="utf-8") == "deep content"


# --- swap_dir: one test per phase, including both rename failures -------------


def _staged_pair(tmp_path: Path) -> tuple[Path, Path]:
    """(staging, target): a fresh snapshot beside an older, populated one."""
    staging, target = tmp_path / ".t-staging", tmp_path / "t"
    _touch(staging / "new.txt", "new snapshot")
    _touch(target / "old.txt", "old snapshot")
    return staging, target


def test_swap_dir_installs_staging_and_drops_the_old_tree(tmp_path: Path) -> None:
    staging, target = _staged_pair(tmp_path)

    assert swap_dir(staging, target) is None

    assert (target / "new.txt").read_text(encoding="utf-8") == "new snapshot"
    assert not (target / "old.txt").exists()
    assert not staging.exists()
    assert list(tmp_path.glob("t.old-*")) == [], "the aside copy must not survive a clean swap"


def test_swap_dir_without_a_pre_existing_target(tmp_path: Path) -> None:
    staging, target = tmp_path / ".t-staging", tmp_path / "t"
    _touch(staging / "new.txt", "new snapshot")

    assert swap_dir(staging, target) is None
    assert (target / "new.txt").read_text(encoding="utf-8") == "new snapshot"


def test_swap_dir_first_rename_failure_leaves_the_target_untouched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Phase 1 raises (a live handle on Windows): abandon without losing anything."""
    staging, target = _staged_pair(tmp_path)

    def deny(*_args: object, **_kwargs: object) -> None:
        raise PermissionError("WinError 5 (simulated)")

    monkeypatch.setattr(os, "replace", deny)
    with pytest.raises(SwapError) as raised:
        swap_dir(staging, target)

    assert raised.value.target_intact, "the target is still there and must be reported as such"
    assert (target / "old.txt").read_text(encoding="utf-8") == "old snapshot", (
        "the previous snapshot must survive a failed first rename"
    )
    assert not (target / "new.txt").exists()


def test_swap_dir_second_rename_failure_rolls_the_old_tree_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Phase 2 raises: the aside copy is put back before the error propagates."""
    staging, target = _staged_pair(tmp_path)
    real_replace = os.replace
    calls: list[int] = []

    def fail_on_second(src: Path, dst: Path) -> None:
        calls.append(1)
        if len(calls) == 2:  # move the staging in
            raise PermissionError("WinError 5 (simulated)")
        real_replace(src, dst)

    monkeypatch.setattr(os, "replace", fail_on_second)
    with pytest.raises(SwapError) as raised:
        swap_dir(staging, target)

    assert len(calls) == 3, "the rollback rename must run after the failed install"
    assert raised.value.target_intact, "the rollback put it back, so it is intact"
    assert (target / "old.txt").read_text(encoding="utf-8") == "old snapshot", (
        "the previous snapshot must be rolled back into place"
    )
    assert not (target / "new.txt").exists()
    assert list(tmp_path.glob("t.old-*")) == [], "the aside copy must not be left behind"


def test_swap_dir_reports_a_failed_rollback_instead_of_claiming_nothing_moved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Install AND rollback raise: the target is gone and must be said to be gone.

    This is the case that used to lie. The rollback error replaced the install
    error, the caller printed "left unchanged", and the previous snapshot was
    sitting under an aside name nothing pointed at.
    """
    staging, target = _staged_pair(tmp_path)
    real_replace = os.replace
    calls: list[int] = []

    def fail_after_first(src: Path, dst: Path) -> None:
        calls.append(1)
        if len(calls) == 1:  # move the old tree aside: let it through
            real_replace(src, dst)
            return
        raise PermissionError(f"WinError 5 (simulated, call {len(calls)})")

    monkeypatch.setattr(os, "replace", fail_after_first)
    with pytest.raises(SwapError) as raised:
        swap_dir(staging, target)

    failure = raised.value
    assert len(calls) == 3, "the rollback must be attempted before giving up"
    assert not failure.target_intact, "the target is missing and must not be called intact"
    assert not target.exists()
    assert failure.aside is not None and (failure.aside / "old.txt").is_file(), (
        "the previous snapshot must be named so the operator can put it back"
    )
    assert failure.staging == staging and (staging / "new.txt").is_file()
    assert "call 2" in str(failure) and "call 3" in str(failure), (
        "both failures must survive in the message, not just the last one"
    )
    assert isinstance(failure.__cause__, PermissionError), "the chain must be preserved"
    assert isinstance(failure.__cause__.__context__, PermissionError)


def test_swap_dir_reports_an_aside_copy_it_could_not_remove(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The swap succeeded; only the cleanup failed, so it is reported, not raised.

    Patching the `shutil` module object itself is what swap_dir resolves at call
    time, so this covers the real code path rather than a re-export.
    """
    staging, target = _staged_pair(tmp_path)
    monkeypatch.setattr(shutil, "rmtree", lambda *_a, **_kw: None)

    leftover = swap_dir(staging, target)

    assert leftover is not None
    assert leftover.name.startswith("t.old-")
    assert (leftover / "old.txt").is_file()
    assert (target / "new.txt").read_text(encoding="utf-8") == "new snapshot"
