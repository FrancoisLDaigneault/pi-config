"""Detection and redaction of secrets in configuration JSON files."""

import json
import re
from pathlib import Path

SECRET_KEYS = {
    "apikey",
    "api_key",
    "token",
    "secret",
    "password",
    "authtoken",
    "accesstoken",
    "refreshtoken",
    "bearer",
}
# Keep _PATTERN_PREFIXES in tests/unit/test_secrets_properties.py in sync with this regex.
SECRET_VALUE_RE = re.compile(r"^(sk-|ghp_|gho_|github_pat_|xox[a-z]-|Bearer )")
REDACTED = "<REDACTED>"


def _is_secret_value(value: object) -> bool:
    return isinstance(value, str) and bool(SECRET_VALUE_RE.match(value))


def _is_secret_entry(key: str, value: object) -> bool:
    # Replacing an already-redacted value would be a no-op; skipping it buys report idempotence.
    if not isinstance(value, str) or value == REDACTED:
        return False
    return key.lower() in SECRET_KEYS or bool(SECRET_VALUE_RE.match(value))


def _redact_dict(node: dict[str, object], path: str) -> list[str]:
    found: list[str] = []
    for key, value in node.items():
        where = f"{path}.{key}" if path else key
        if _is_secret_entry(key, value):
            node[key] = REDACTED
            found.append(where)
        else:
            found += redact(value, where)
    return found


def _redact_list(node: list[object], path: str) -> list[str]:
    found: list[str] = []
    for i, value in enumerate(node):
        where = f"{path}[{i}]"
        if _is_secret_value(value):
            node[i] = REDACTED
            found.append(where)
        else:
            found += redact(value, where)
    return found


def redact(node: object, path: str = "") -> list[str]:
    """Recursively redact suspicious values. Returns the list of redacted paths.

    A bare secret string at the root is reported but cannot be replaced in
    place (strings are immutable); the caller performs that replacement.
    """
    if isinstance(node, dict):
        return _redact_dict(node, path)
    if isinstance(node, list):
        return _redact_list(node, path)
    if _is_secret_value(node):
        return [path or "<root>"]
    return []


def scan_copied_json(config: Path) -> list[str]:
    """Post-copy audit: redact secrets in every *.json copied into config/."""
    found: list[str] = []
    for path in sorted(config.rglob("*.json")):
        rel = path.relative_to(config).as_posix()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            print(f"  info: {rel} not parseable as JSON, left as is")
            continue
        hits = redact(data)
        if hits:
            if isinstance(data, str):
                data = REDACTED
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            print(f"  WARNING {rel}: {len(hits)} value(s) redacted: {', '.join(hits)}")
            found += [f"{rel}:{h}" for h in hits]
    return found
