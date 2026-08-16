"""Tests unitaires de la destination par defaut du backup (horodatage a la seconde)."""

from datetime import datetime

from pi_config_tools.backup import default_destination


def test_default_destination_format(monkeypatch, tmp_path):
    monkeypatch.setenv("PI_CONFIG_HOME", str(tmp_path))
    fixed = datetime(2026, 8, 16, 14, 30, 59)
    dest = default_destination(fixed)
    assert dest == tmp_path / "pi-backups" / "2026-08-16_143059"


def test_default_destination_second_resolution(monkeypatch, tmp_path):
    """Deux backups dans la meme minute ne doivent pas partager le meme dossier."""
    monkeypatch.setenv("PI_CONFIG_HOME", str(tmp_path))
    a = default_destination(datetime(2026, 8, 16, 14, 30, 1))
    b = default_destination(datetime(2026, 8, 16, 14, 30, 2))
    assert a != b
