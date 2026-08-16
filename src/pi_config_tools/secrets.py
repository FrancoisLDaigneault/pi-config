"""Detection et caviardage de secrets dans les JSON de configuration."""

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
SECRET_VALUE_RE = re.compile(r"^(sk-|ghp_|gho_|github_pat_|xox[a-z]-|Bearer )")


def _is_secret_value(value) -> bool:
    return isinstance(value, str) and bool(SECRET_VALUE_RE.match(value))


def _is_secret_entry(key: str, value) -> bool:
    if not isinstance(value, str):
        return False
    return key.lower() in SECRET_KEYS or bool(SECRET_VALUE_RE.match(value))


def _redact_dict(node: dict, path: str) -> list[str]:
    found = []
    for key, value in node.items():
        where = f"{path}.{key}" if path else key
        if _is_secret_entry(key, value):
            node[key] = "<REDACTED>"
            found.append(where)
        else:
            found += redact(value, where)
    return found


def _redact_list(node: list, path: str) -> list[str]:
    found = []
    for i, value in enumerate(node):
        where = f"{path}[{i}]"
        if _is_secret_value(value):
            node[i] = "<REDACTED>"
            found.append(where)
        else:
            found += redact(value, where)
    return found


def redact(node, path="") -> list[str]:
    """Caviarde recursivement les valeurs suspectes. Retourne la liste des chemins caviardes."""
    if isinstance(node, dict):
        return _redact_dict(node, path)
    if isinstance(node, list):
        return _redact_list(node, path)
    return []


def scan_copied_json(config: Path) -> list[str]:
    """Audit post-copie : caviarde les secrets dans tous les *.json copies dans config/."""
    found = []
    for path in sorted(config.rglob("*.json")):
        rel = path.relative_to(config).as_posix()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            print(f"  info : {rel} non analysable en JSON, laisse tel quel")
            continue
        hits = redact(data)
        if hits:
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            print(f"  ATTENTION {rel} : {len(hits)} valeur(s) caviardee(s) : {', '.join(hits)}")
            found += [f"{rel}:{h}" for h in hits]
    return found
