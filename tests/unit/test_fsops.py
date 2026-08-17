"""Unit tests for copy_tree and the exclusions (everything in tmp_path)."""

from pathlib import Path

from pi_config_tools.fsops import copy_tree, is_excluded_file


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


def test_is_excluded_file() -> None:
    assert is_excluded_file("auth.json")
    assert is_excluded_file("settings.json.bak-2026")
    assert is_excluded_file("settings.backup-20260809.json")
    assert is_excluded_file("module.pyc")
    assert not is_excluded_file("settings.json")
    assert not is_excluded_file("APPEND_SYSTEM.md")
