from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def parse_simple_yaml_scalar(token: str) -> Any:
    if token in {"null", "~"}:
        return None
    if token == "true":
        return True
    if token == "false":
        return False
    if token.startswith('"') and token.endswith('"'):
        try:
            return json.loads(token)
        except json.JSONDecodeError:
            return token[1:-1]
    if token.startswith("'") and token.endswith("'"):
        return token[1:-1].replace("''", "'")
    if token.startswith("[") or token.startswith("{"):
        try:
            return json.loads(token)
        except json.JSONDecodeError:
            return token
    return token


def parse_simple_yaml(text: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if line.startswith(" "):
            raise SystemExit("Unsupported YAML indentation in fallback parser")
        if ":" not in line:
            raise SystemExit(f"Invalid YAML line: {line}")
        key, raw = line.split(":", 1)
        key = key.strip()
        raw = raw.strip()
        if not key:
            raise SystemExit("Invalid YAML key")
        if raw in {"|", "|-"}:
            block: list[str] = []
            while i < len(lines):
                next_line = lines[i]
                if next_line.startswith("  "):
                    block.append(next_line[2:])
                    i += 1
                    continue
                if next_line == "":
                    block.append("")
                    i += 1
                    continue
                break
            data[key] = "\n".join(block).rstrip("\n")
            continue
        data[key] = parse_simple_yaml_scalar(raw)
    return data
