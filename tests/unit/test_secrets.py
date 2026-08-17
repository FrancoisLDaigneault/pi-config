"""Unit tests for secret redaction (pure functions + tmp_path)."""

import json
from pathlib import Path

from pi_config_tools.secrets import redact, scan_copied_json


def test_redact_dict_secret_key() -> None:
    data = {"apiKey": "abc123", "name": "ok"}
    found = redact(data)
    assert data == {"apiKey": "<REDACTED>", "name": "ok"}
    assert found == ["apiKey"]


def test_redact_dict_secret_value_prefix() -> None:
    data = {"header": "Bearer xyz", "url": "https://example.com"}
    found = redact(data)
    assert data["header"] == "<REDACTED>"
    assert data["url"] == "https://example.com"
    assert found == ["header"]


def test_redact_list_values() -> None:
    data = {"headers": ["Bearer xyz", "ok"], "plain": ["sk-abc"]}
    found = redact(data)
    assert data == {"headers": ["<REDACTED>", "ok"], "plain": ["<REDACTED>"]}
    assert sorted(found) == ["headers[0]", "plain[0]"]


def test_redact_nested() -> None:
    data = {"outer": [{"token": "ghp_abcdef"}]}
    found = redact(data)
    assert data == {"outer": [{"token": "<REDACTED>"}]}
    assert found == ["outer[0].token"]


def test_redact_clean_data_untouched() -> None:
    data = {"maxTokens": 4096, "models": ["claude-fable-5"], "ask-user": {"enabled": True}}
    before = json.dumps(data)
    assert redact(data) == []
    assert json.dumps(data) == before


def test_scan_copied_json_skips_already_redacted_files(tmp_path: Path) -> None:
    config = tmp_path / "config"
    config.mkdir()
    raw = '{"token": "<REDACTED>", "list": ["<REDACTED>"]}'
    (config / "done.json").write_text(raw, encoding="utf-8")

    found = scan_copied_json(config)

    assert found == []
    assert (config / "done.json").read_text(encoding="utf-8") == raw


def test_scan_copied_json_replaces_root_string_file(tmp_path: Path) -> None:
    config = tmp_path / "config"
    config.mkdir()
    (config / "token.json").write_text(json.dumps("sk-live-abc123"), encoding="utf-8")

    found = scan_copied_json(config)

    assert found == ["token.json:<root>"]
    assert json.loads((config / "token.json").read_text(encoding="utf-8")) == "<REDACTED>"


def test_scan_copied_json_redacts_and_reports(tmp_path: Path) -> None:
    config = tmp_path / "config"
    nested = config / "pi-agent" / "extensions"
    nested.mkdir(parents=True)
    (nested / "probe.json").write_text(
        json.dumps({"apiKey": "sk-proj-test", "safe": "ok"}), encoding="utf-8"
    )
    (config / "clean.json").write_text(json.dumps({"a": 1}), encoding="utf-8")
    (config / "invalid.json").write_text("{not json", encoding="utf-8")

    found = scan_copied_json(config)

    assert found == ["pi-agent/extensions/probe.json:apiKey"]
    rewritten = json.loads((nested / "probe.json").read_text(encoding="utf-8"))
    assert rewritten == {"apiKey": "<REDACTED>", "safe": "ok"}
    assert json.loads((config / "clean.json").read_text(encoding="utf-8")) == {"a": 1}
    assert (config / "invalid.json").read_text(encoding="utf-8") == "{not json"
