from __future__ import annotations

from pathlib import Path
from typing import Any

from .app_constants import (
    ALLOWED_SCOPES,
    DEFAULT_REPEAT_EVERY,
    DURATION_CHUNKS_PATTERN,
    REQUIRED_TEMPLATE_FIELDS,
)
from .mapping_yaml_dump import load_mapping_file, save_mapping_file
from .template_paths import resolve_existing_template_file


def scope_text(template: dict[str, Any]) -> str:
    scope = str(template.get("scope", "general"))
    if scope == "specific":
        return f"specific:{template.get('specific_to', '')}"
    return "general"


def parse_duration_seconds(raw: str, field_name: str) -> float:
    value = raw.strip().lower()
    if not value:
        raise SystemExit(f"Template field `{field_name}` cannot be empty")
    matches = list(DURATION_CHUNKS_PATTERN.finditer(value))
    if not matches or "".join(match.group(0) for match in matches) != value:
        raise SystemExit(
            f"Invalid duration `{raw}` for `{field_name}`. Use values like 30s, 10m, 2h, 1h30m."
        )
    unit_seconds = {"s": 1.0, "m": 60.0, "h": 3600.0, "d": 86400.0}
    total = 0.0
    for match in matches:
        total += float(match.group(1)) * unit_seconds[match.group(2)]
    if total <= 0:
        raise SystemExit(f"Duration for `{field_name}` must be greater than zero")
    return total


def cadence_text(template: dict[str, Any]) -> str:
    repeat_for = str(template.get("repeat_for", "")).strip()
    if not repeat_for:
        return "once"
    repeat_every = str(template.get("repeat_every", "")).strip() or DEFAULT_REPEAT_EVERY
    return f"repeat:{repeat_for}/{repeat_every}"


def normalize_template_data(data: dict[str, Any], fallback_name: str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for field in REQUIRED_TEMPLATE_FIELDS:
        if field not in data:
            if field == "name" and fallback_name:
                out["name"] = fallback_name
                continue
            raise SystemExit(f"Template is missing required field: {field}")
        value = str(data[field]).strip()
        if not value:
            raise SystemExit(f"Template field `{field}` cannot be empty")
        out[field] = value
    profile = data.get("profile")
    if profile is not None and str(profile).strip():
        out["profile"] = str(profile).strip()
    scope = str(data.get("scope", "general")).strip().lower() or "general"
    if scope not in ALLOWED_SCOPES:
        raise SystemExit("Template scope must be `general` or `specific`")
    out["scope"] = scope
    specific_to = str(data.get("specific_to", "")).strip() or None
    if scope == "specific" and not specific_to:
        raise SystemExit("Template scope is `specific` but `specific_to` is missing")
    if scope == "specific" and specific_to:
        out["specific_to"] = specific_to
    repeat_for = str(data.get("repeat_for", "")).strip() or None
    if repeat_for:
        parse_duration_seconds(repeat_for, "repeat_for")
        out["repeat_for"] = repeat_for
    repeat_every = str(data.get("repeat_every", "")).strip() or None
    if repeat_every:
        parse_duration_seconds(repeat_every, "repeat_every")
        out["repeat_every"] = repeat_every
    if repeat_every and not repeat_for:
        raise SystemExit("Template has `repeat_every` but `repeat_for` is missing")
    return out


def load_template(root: Path, name: str) -> tuple[Path, dict[str, Any]]:
    path = resolve_existing_template_file(root, name)
    normalized = normalize_template_data(load_mapping_file(path), fallback_name=path.stem)
    return path, normalized


def save_template(path: Path, data: dict[str, Any]) -> None:
    save_mapping_file(path, normalize_template_data(data))
