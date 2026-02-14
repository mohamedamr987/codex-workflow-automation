from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .mapping_io import parse_simple_yaml

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


def dump_simple_yaml(data: dict[str, Any]) -> str:
    lines: list[str] = []
    for key, value in data.items():
        if value is None:
            lines.append(f"{key}: null")
            continue
        if isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
            continue
        if isinstance(value, str):
            if "\n" in value:
                lines.append(f"{key}: |-")
                for line in value.split("\n"):
                    lines.append(f"  {line}")
            else:
                lines.append(f"{key}: {json.dumps(value)}")
            continue
        lines.append(f"{key}: {json.dumps(value)}")
    return "\n".join(lines) + "\n"


def load_mapping_file(path: Path) -> dict[str, Any]:
    ext = path.suffix.lower()
    text = path.read_text(encoding="utf-8")
    if ext == ".json":
        try:
            out = json.loads(text)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc
    elif ext in {".yaml", ".yml"}:
        out = yaml.safe_load(text) if yaml is not None else parse_simple_yaml(text)
    else:
        raise SystemExit(f"Unsupported template extension: {ext}")
    if not isinstance(out, dict):
        raise SystemExit(f"Template file {path} must contain an object/map")
    return out


def save_mapping_file(path: Path, data: dict[str, Any]) -> None:
    ext = path.suffix.lower()
    if ext == ".json":
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return
    if ext in {".yaml", ".yml"}:
        text = (
            yaml.safe_dump(data, sort_keys=False, allow_unicode=False)
            if yaml is not None
            else dump_simple_yaml(data)
        )
        path.write_text(text, encoding="utf-8")
        return
    raise SystemExit(f"Unsupported template extension: {ext}")
