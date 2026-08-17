"""Unit tests for the backup default destination (second-resolution timestamp)."""

from datetime import datetime
from pathlib import Path

import pytest

from pi_config_tools.backup import default_destination


def test_default_destination_format(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PI_CONFIG_HOME", str(tmp_path))
    fixed = datetime(2026, 8, 16, 14, 30, 59)
    dest = default_destination(fixed)
    assert dest == tmp_path / "pi-backups" / "2026-08-16_143059"


def test_default_destination_second_resolution(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Two backups within the same minute must not share the same folder."""
    monkeypatch.setenv("PI_CONFIG_HOME", str(tmp_path))
    a = default_destination(datetime(2026, 8, 16, 14, 30, 1))
    b = default_destination(datetime(2026, 8, 16, 14, 30, 2))
    assert a != b
