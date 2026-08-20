"""Tests for locally patched node_modules metadata."""

from pathlib import Path

import pytest

from pi_config_tools.patched import context_mode_version


def _touch(path: Path, content: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_context_mode_version_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PI_CONFIG_HOME", str(tmp_path))
    assert context_mode_version() == "unknown (package.json missing)"


def test_context_mode_version_unreadable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PI_CONFIG_HOME", str(tmp_path))
    pkg = tmp_path / ".pi" / "agent" / "npm" / "node_modules" / "context-mode" / "package.json"
    _touch(pkg, "{not json}")
    assert context_mode_version() == "unknown (package.json unreadable)"


def test_context_mode_version_rejects_non_object(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PI_CONFIG_HOME", str(tmp_path))
    pkg = tmp_path / ".pi" / "agent" / "npm" / "node_modules" / "context-mode" / "package.json"
    _touch(pkg, "[]")
    assert context_mode_version() == "unknown (package.json unreadable)"


def test_context_mode_version_rejects_non_string(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PI_CONFIG_HOME", str(tmp_path))
    pkg = tmp_path / ".pi" / "agent" / "npm" / "node_modules" / "context-mode" / "package.json"
    _touch(pkg, '{"version": 1}')
    assert context_mode_version() == "unknown (package.json unreadable)"
