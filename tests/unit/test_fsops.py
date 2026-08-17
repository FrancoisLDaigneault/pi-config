"""Unit tests for copy_tree and the exclusions (everything in tmp_path)."""

from pathlib import Path

import pytest

from pi_config_tools.fsops import context_mode_version, copy_tree


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


def test_context_mode_version_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PI_CONFIG_HOME", str(tmp_path))
    assert context_mode_version() == "unknown (package.json missing)"


def test_context_mode_version_unreadable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PI_CONFIG_HOME", str(tmp_path))
    pkg = tmp_path / ".pi" / "agent" / "npm" / "node_modules" / "context-mode" / "package.json"
    _touch(pkg, "{not json}")
    assert context_mode_version() == "unknown (package.json unreadable)"
