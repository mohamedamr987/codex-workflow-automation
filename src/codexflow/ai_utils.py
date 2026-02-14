from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .template_paths import find_template_files_by_stem


def build_ai_template_prompt(
    mode: str,
    template_name: str,
    request: str,
    existing_template: dict[str, Any] | None,
    scope_override: str | None,
    specific_to_override: str | None,
    bind_profile_override: str | None,
    repeat_for_override: str | None,
    repeat_every_override: str | None,
) -> str:
    context = {
        "mode": mode,
        "template_name": template_name,
        "request": request,
        "existing_template": existing_template,
        "scope_override": scope_override,
        "specific_to_override": specific_to_override,
        "bind_profile_override": bind_profile_override,
        "repeat_for_override": repeat_for_override,
        "repeat_every_override": repeat_every_override,
    }
    context_json = json.dumps(context, indent=2)
    return (
        "You are generating a codexflow template specification.\n"
        "Return ONLY a valid JSON object with exactly these keys:\n"
        "{\n"
        '  "description": "string",\n'
        '  "role_prompt": "string",\n'
        '  "instructions": "string",\n'
        '  "scope": "general|specific",\n'
        '  "specific_to": "string|null",\n'
        '  "profile": "string|null",\n'
        '  "repeat_for": "duration|null",\n'
        '  "repeat_every": "duration|null"\n'
        "}\n"
        "Rules:\n"
        "- No markdown, no code fences, no explanation.\n"
        "- Keep role_prompt and instructions practical and concise.\n"
        "- Use placeholders like {{task}}, {{root}}, {{specific_to}} only where useful.\n"
        "- repeat_for/repeat_every should use duration strings like 2h, 30m, 1h30m.\n"
        "- If scope is general, set specific_to to null.\n"
        "- If scope is specific, set specific_to to a concrete target.\n\n"
        f"Context:\n{context_json}\n"
    )


def derive_template_name_from_request(request: str) -> str:
    words = re.findall(r"[a-z0-9]+", request.lower())
    stopwords = {
        "a", "an", "and", "for", "from", "i", "is", "it", "of", "or",
        "please", "role", "template", "that", "the", "this", "to", "want", "with",
    }
    filtered = [word for word in words if word not in stopwords]
    chosen = filtered or words
    if not chosen:
        return "generated-role"
    base = "-".join(chosen[:5])[:48].strip("-")
    if not base:
        base = "generated-role"
    if base[0].isdigit():
        base = f"role-{base}"
    return base


def next_available_template_name(root: Path, base_name: str) -> str:
    candidate = base_name
    suffix = 2
    while find_template_files_by_stem(root, candidate):
        candidate = f"{base_name}-{suffix}"
        suffix += 1
    return candidate
