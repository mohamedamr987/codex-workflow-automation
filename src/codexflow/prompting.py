from __future__ import annotations

from pathlib import Path
from typing import Any

from .app_constants import VAR_PATTERN
from .template_logic import scope_text
from .template_paths import find_template_files_by_stem


def parse_vars(items: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise SystemExit(f"Invalid --var `{item}`. Expected KEY=VALUE")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise SystemExit(f"Invalid --var `{item}`. Empty key")
        out[key] = value
    return out


def render_text_with_vars(text: str, variables: dict[str, str]) -> tuple[str, set[str]]:
    missing: set[str] = set()

    def repl(match: Any) -> str:
        key = match.group(1)
        if key in variables:
            return variables[key]
        missing.add(key)
        return match.group(0)

    return VAR_PATTERN.sub(repl, text), missing


def build_prompt(
    template: dict[str, Any],
    task: str,
    extra: str | None,
    root: Path,
    selected_profile: str,
    user_vars: dict[str, str],
) -> tuple[str, set[str]]:
    base_vars = {
        "task": task.strip(),
        "extra": (extra or "").strip(),
        "template": template["name"],
        "description": template["description"],
        "profile": selected_profile,
        "scope": template.get("scope", "general"),
        "specific_to": str(template.get("specific_to", "")),
        "root": str(root),
    }
    variables = {**base_vars, **user_vars}
    role_prompt, miss_role = render_text_with_vars(template["role_prompt"], variables)
    instructions, miss_inst = render_text_with_vars(template["instructions"], variables)
    task_text, miss_task = render_text_with_vars(task.strip(), variables)
    extra_text = ""
    miss_extra: set[str] = set()
    if extra and extra.strip():
        extra_text, miss_extra = render_text_with_vars(extra.strip(), variables)
    parts = [
        f"Role: {template['name']}",
        f"Description: {template['description']}",
        f"Scope: {scope_text(template)}",
        f"Profile: {selected_profile}",
        "",
        "Role instructions:",
        role_prompt,
        "",
        "Execution rules:",
        instructions,
        "",
        "Task:",
        task_text,
    ]
    if extra_text:
        parts.extend(["", "Extra context:", extra_text])
    missing = miss_role | miss_inst | miss_task | miss_extra
    return "\n".join(parts).strip() + "\n", missing


def read_text_arg_or_file(value: str) -> str:
    if value.startswith("@"):
        path = Path(value[1:]).expanduser()
        if not path.exists():
            raise SystemExit(f"File not found: {path}")
        return path.read_text(encoding="utf-8")
    return value


def ensure_profile_exists(cfg: dict[str, Any], profile_name: str) -> None:
    if profile_name not in cfg["profiles"]:
        raise SystemExit(
            f"Profile `{profile_name}` not found. Use `codexflow profile list` first."
        )


def ensure_stem_not_ambiguous(root: Path, stem: str, target: Path) -> None:
    for path in find_template_files_by_stem(root, stem):
        if path != target:
            raise SystemExit(
                f"Template stem `{stem}` already exists as `{path.name}`. "
                "Use a different name, or rename/delete the old template first."
            )
