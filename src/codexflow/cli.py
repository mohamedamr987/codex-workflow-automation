#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    yaml = None

CONFIG_DIR_NAME = ".codexflow"
TEMPLATES_DIR_NAME = "templates"
CONFIG_FILE_NAME = "config.json"

TEMPLATE_EXT_TO_FORMAT = {
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
}
FORMAT_TO_TEMPLATE_EXT = {
    "json": ".json",
    "yaml": ".yaml",
}
DEFAULT_TEMPLATE_FORMAT = "json"

VAR_PATTERN = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_.-]*)\s*\}\}")


@dataclass
class RunnerConfig:
    command: str
    args: list[str]
    prompt_mode: str
    prompt_flag: str


STARTER_TEMPLATES: dict[str, dict[str, str]] = {
    "planning": {
        "description": "Plan implementation work in clear, testable steps.",
        "role_prompt": (
            "You are a planning specialist. Break problems into concrete steps, "
            "highlight tradeoffs, and define verification criteria before coding."
        ),
        "instructions": (
            "Output a short execution plan with risks, assumptions, and checkpoints."
        ),
    },
    "testing": {
        "description": "Design and implement targeted tests for reliability.",
        "role_prompt": (
            "You are a testing specialist. Focus on regressions, edge cases, and "
            "reproducible checks."
        ),
        "instructions": (
            "Prioritize high-signal tests first. Include setup, assertions, and "
            "commands to run tests."
        ),
    },
    "review": {
        "description": "Perform code review with findings-first output.",
        "role_prompt": (
            "You are a code reviewer. Identify behavioral bugs, risks, and missing "
            "tests before style suggestions."
        ),
        "instructions": "List findings ordered by severity with file/line references.",
    },
}

DEFAULT_PROFILE_NAME = "default"
DEFAULT_CONFIG: dict[str, Any] = {
    "default_profile": DEFAULT_PROFILE_NAME,
    "default_template_format": DEFAULT_TEMPLATE_FORMAT,
    "profiles": {
        DEFAULT_PROFILE_NAME: {
            "command": "codex",
            "args": [],
            "prompt_mode": "stdin",
            "prompt_flag": "--prompt",
        }
    },
}

REQUIRED_TEMPLATE_FIELDS = ["name", "description", "role_prompt", "instructions"]
ALLOWED_SCOPES = {"general", "specific"}


def resolve_root(path: str | None) -> Path:
    return Path(path).expanduser().resolve() if path else Path.cwd().resolve()


def config_dir(root: Path) -> Path:
    return root / CONFIG_DIR_NAME


def templates_dir(root: Path) -> Path:
    return config_dir(root) / TEMPLATES_DIR_NAME


def config_file(root: Path) -> Path:
    return config_dir(root) / CONFIG_FILE_NAME


def ensure_initialized(root: Path) -> None:
    missing = []
    if not config_dir(root).exists():
        missing.append(str(config_dir(root)))
    if not templates_dir(root).exists():
        missing.append(str(templates_dir(root)))
    if not config_file(root).exists():
        missing.append(str(config_file(root)))
    if missing:
        joined = "\n - ".join([""] + missing)
        raise SystemExit(
            "Project is not initialized. Run `codexflow init` first. Missing:" + joined
        )


def parse_runner(name: str, raw: dict[str, Any]) -> RunnerConfig:
    if not isinstance(raw, dict):
        raise SystemExit(f"Profile `{name}` must be an object")

    command = str(raw.get("command", "")).strip()
    if not command:
        raise SystemExit(f"Profile `{name}` has empty command")

    args = raw.get("args", [])
    if not isinstance(args, list):
        raise SystemExit(f"Profile `{name}` args must be a list")
    args = [str(item) for item in args]

    prompt_mode = str(raw.get("prompt_mode", "stdin")).strip()
    if prompt_mode not in {"stdin", "arg"}:
        raise SystemExit(f"Profile `{name}` prompt_mode must be `stdin` or `arg`")

    prompt_flag = str(raw.get("prompt_flag", "--prompt")).strip() or "--prompt"

    return RunnerConfig(
        command=command,
        args=args,
        prompt_mode=prompt_mode,
        prompt_flag=prompt_flag,
    )


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
            value = "\n".join(block).rstrip("\n")
            data[key] = value
            continue

        data[key] = parse_simple_yaml_scalar(raw)

    return data


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
        if yaml is not None:
            out = yaml.safe_load(text)
        else:
            out = parse_simple_yaml(text)
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
        if yaml is not None:
            text = yaml.safe_dump(data, sort_keys=False, allow_unicode=False)
        else:
            text = dump_simple_yaml(data)
        path.write_text(text, encoding="utf-8")
        return

    raise SystemExit(f"Unsupported template extension: {ext}")


def normalized_config(raw: dict[str, Any]) -> dict[str, Any]:
    if "profiles" in raw:
        default_profile = str(raw.get("default_profile", "")).strip()
        if not default_profile:
            raise SystemExit("Config default_profile cannot be empty")
        profiles = raw.get("profiles")
        if not isinstance(profiles, dict) or not profiles:
            raise SystemExit("Config profiles must be a non-empty object")
        if default_profile not in profiles:
            raise SystemExit(
                f"Config default_profile `{default_profile}` was not found in profiles"
            )

        default_template_format = str(
            raw.get("default_template_format", DEFAULT_TEMPLATE_FORMAT)
        ).strip()
        if default_template_format not in FORMAT_TO_TEMPLATE_EXT:
            raise SystemExit(
                "Config default_template_format must be `json` or `yaml`"
            )

        return {
            "default_profile": default_profile,
            "default_template_format": default_template_format,
            "profiles": profiles,
        }

    if "runner" in raw:
        return {
            "default_profile": DEFAULT_PROFILE_NAME,
            "default_template_format": DEFAULT_TEMPLATE_FORMAT,
            "profiles": {DEFAULT_PROFILE_NAME: raw["runner"]},
        }

    raise SystemExit(
        "Config must include either `profiles` (new format) or `runner` (legacy format)"
    )


def load_config(root: Path) -> dict[str, Any]:
    raw = load_json(config_file(root))
    cfg = normalized_config(raw)

    profiles = cfg["profiles"]
    for name, profile in profiles.items():
        parse_runner(name, profile)

    return cfg


def save_config(root: Path, cfg: dict[str, Any]) -> None:
    save_json(config_file(root), cfg)


def load_runner_profile(root: Path, profile_name: str | None) -> tuple[str, RunnerConfig]:
    cfg = load_config(root)
    selected_name = profile_name or cfg["default_profile"]
    profiles = cfg["profiles"]
    if selected_name not in profiles:
        raise SystemExit(f"Profile `{selected_name}` not found in {config_file(root)}")
    return selected_name, parse_runner(selected_name, profiles[selected_name])


def validate_template_name_input(name: str) -> None:
    if not name.strip():
        raise SystemExit("Template name cannot be empty")
    if Path(name).name != name:
        raise SystemExit("Template name cannot contain path separators")


def split_template_name(name: str) -> tuple[str, str | None]:
    validate_template_name_input(name)
    suffix = Path(name).suffix.lower()
    if suffix in TEMPLATE_EXT_TO_FORMAT:
        stem = Path(name).stem
        if not stem:
            raise SystemExit("Template name cannot be empty")
        return stem, suffix
    return name, None


def list_template_files(root: Path) -> list[Path]:
    tdir = templates_dir(root)
    files: list[Path] = []
    for ext in TEMPLATE_EXT_TO_FORMAT:
        files.extend(tdir.glob(f"*{ext}"))
    return sorted(files, key=lambda p: (p.stem, p.suffix))


def find_template_files_by_stem(root: Path, stem: str) -> list[Path]:
    out: list[Path] = []
    for ext in TEMPLATE_EXT_TO_FORMAT:
        candidate = templates_dir(root) / f"{stem}{ext}"
        if candidate.exists():
            out.append(candidate)
    return sorted(out, key=lambda p: p.suffix)


def resolve_existing_template_file(root: Path, name: str) -> Path:
    stem, explicit_ext = split_template_name(name)

    if explicit_ext:
        path = templates_dir(root) / f"{stem}{explicit_ext}"
        if not path.exists():
            raise SystemExit(f"Template `{name}` not found at {path}")
        return path

    matches = find_template_files_by_stem(root, stem)
    if not matches:
        raise SystemExit(f"Template `{name}` not found")
    if len(matches) > 1:
        choices = ", ".join(path.name for path in matches)
        raise SystemExit(
            f"Template name `{name}` is ambiguous. Use one of: {choices}"
        )
    return matches[0]


def resolve_new_template_file(
    root: Path,
    name: str,
    template_format: str | None,
    preserve_extension: str | None = None,
) -> Path:
    stem, explicit_ext = split_template_name(name)

    if explicit_ext:
        explicit_format = TEMPLATE_EXT_TO_FORMAT[explicit_ext]
        if template_format and template_format != explicit_format:
            raise SystemExit(
                f"Conflicting format for `{name}`. Extension implies {explicit_format}."
            )
        return templates_dir(root) / f"{stem}{explicit_ext}"

    if template_format:
        ext = FORMAT_TO_TEMPLATE_EXT[template_format]
    elif preserve_extension:
        ext = preserve_extension
    else:
        ext = FORMAT_TO_TEMPLATE_EXT[DEFAULT_TEMPLATE_FORMAT]

    return templates_dir(root) / f"{stem}{ext}"


def scope_text(template: dict[str, Any]) -> str:
    scope = str(template.get("scope", "general"))
    if scope == "specific":
        return f"specific:{template.get('specific_to', '')}"
    return "general"


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
    if profile is not None:
        profile_value = str(profile).strip()
        if profile_value:
            out["profile"] = profile_value

    scope = str(data.get("scope", "general")).strip().lower() or "general"
    if scope not in ALLOWED_SCOPES:
        raise SystemExit("Template scope must be `general` or `specific`")
    out["scope"] = scope

    specific_to_raw = data.get("specific_to")
    specific_to = None
    if specific_to_raw is not None:
        specific_to = str(specific_to_raw).strip() or None

    if scope == "specific" and not specific_to:
        raise SystemExit("Template scope is `specific` but `specific_to` is missing")

    if scope == "specific" and specific_to:
        out["specific_to"] = specific_to

    return out


def load_template(root: Path, name: str) -> tuple[Path, dict[str, Any]]:
    path = resolve_existing_template_file(root, name)
    raw = load_mapping_file(path)
    normalized = normalize_template_data(raw, fallback_name=path.stem)
    return path, normalized


def save_template(path: Path, data: dict[str, Any]) -> None:
    normalized = normalize_template_data(data)
    save_mapping_file(path, normalized)


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

    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        if key in variables:
            return variables[key]
        missing.add(key)
        return match.group(0)

    rendered = VAR_PATTERN.sub(repl, text)
    return rendered, missing


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

    role_prompt, missing_role = render_text_with_vars(template["role_prompt"], variables)
    instructions, missing_instructions = render_text_with_vars(
        template["instructions"], variables
    )
    task_text, missing_task = render_text_with_vars(task.strip(), variables)

    extra_text = ""
    missing_extra: set[str] = set()
    if extra and extra.strip():
        extra_text, missing_extra = render_text_with_vars(extra.strip(), variables)

    scope_value = scope_text(template)

    parts = [
        f"Role: {template['name']}",
        f"Description: {template['description']}",
        f"Scope: {scope_value}",
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

    missing = missing_role | missing_instructions | missing_task | missing_extra
    return "\n".join(parts).strip() + "\n", missing


def command_init(args: argparse.Namespace) -> int:
    root = resolve_root(args.root)
    cdir = config_dir(root)
    tdir = templates_dir(root)

    if cdir.exists() and not args.force:
        raise SystemExit(
            f"{cdir} already exists. Use --force to overwrite starter config/templates."
        )

    cdir.mkdir(parents=True, exist_ok=True)
    tdir.mkdir(parents=True, exist_ok=True)
    save_json(config_file(root), DEFAULT_CONFIG)

    for name, template in STARTER_TEMPLATES.items():
        path = resolve_new_template_file(root, name, DEFAULT_TEMPLATE_FORMAT)
        save_template(
            path,
            {
                "name": name,
                "description": template["description"],
                "role_prompt": template["role_prompt"],
                "instructions": template["instructions"],
                "profile": DEFAULT_PROFILE_NAME,
                "scope": "general",
            },
        )

    print(f"Initialized codexflow in {cdir}")
    return 0


def command_list(args: argparse.Namespace) -> int:
    root = resolve_root(args.root)
    ensure_initialized(root)
    cfg = load_config(root)

    files = list_template_files(root)
    if not files:
        print("No templates found.")
        return 0

    for path in files:
        data = normalize_template_data(load_mapping_file(path), fallback_name=path.stem)
        profile = data.get("profile", cfg["default_profile"])
        template_format = TEMPLATE_EXT_TO_FORMAT[path.suffix.lower()]
        print(
            f"{path.name:20} [{template_format} | {profile} | {scope_text(data)}] {data['description']}"
        )
    return 0


def command_show(args: argparse.Namespace) -> int:
    root = resolve_root(args.root)
    ensure_initialized(root)
    path, data = load_template(root, args.name)
    out = {
        **data,
        "file": path.name,
        "format": TEMPLATE_EXT_TO_FORMAT[path.suffix.lower()],
    }
    print(json.dumps(out, indent=2))
    return 0


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
    existing = find_template_files_by_stem(root, stem)
    for path in existing:
        if path != target:
            raise SystemExit(
                f"Template stem `{stem}` already exists as `{path.name}`. "
                "Use a different name, or rename/delete the old template first."
            )


def command_create(args: argparse.Namespace) -> int:
    root = resolve_root(args.root)
    ensure_initialized(root)

    cfg = load_config(root)

    selected_profile = args.profile.strip() if args.profile else None
    if selected_profile:
        ensure_profile_exists(cfg, selected_profile)

    chosen_format = args.format or cfg["default_template_format"]
    if chosen_format not in FORMAT_TO_TEMPLATE_EXT:
        raise SystemExit("--format must be `json` or `yaml`")

    output_path = resolve_new_template_file(root, args.name, chosen_format)
    stem, _ = split_template_name(args.name)
    ensure_stem_not_ambiguous(root, stem, output_path)

    if output_path.exists() and not args.force:
        raise SystemExit(
            f"Template `{args.name}` already exists at {output_path}. Use --force to overwrite."
        )

    role_prompt = read_text_arg_or_file(args.role).strip()
    instructions = read_text_arg_or_file(args.instructions).strip()

    scope = args.scope
    specific_to = args.specific_to.strip() if args.specific_to else None
    if scope == "specific" and not specific_to:
        raise SystemExit("--specific-to is required when --scope specific")
    if scope == "general" and specific_to:
        raise SystemExit("--specific-to can only be used with --scope specific")

    data: dict[str, Any] = {
        "name": stem,
        "description": args.description.strip(),
        "role_prompt": role_prompt,
        "instructions": instructions,
        "scope": scope,
    }

    if selected_profile:
        data["profile"] = selected_profile
    if scope == "specific" and specific_to:
        data["specific_to"] = specific_to

    save_template(output_path, data)
    print(f"Saved template `{stem}` to {output_path}")
    return 0


def command_edit(args: argparse.Namespace) -> int:
    root = resolve_root(args.root)
    ensure_initialized(root)

    cfg = load_config(root)
    path, data = load_template(root, args.name)
    changed = False

    if args.description is not None:
        data["description"] = args.description.strip()
        changed = True

    if args.role is not None:
        data["role_prompt"] = read_text_arg_or_file(args.role).strip()
        changed = True

    if args.instructions is not None:
        data["instructions"] = read_text_arg_or_file(args.instructions).strip()
        changed = True

    if args.profile and args.clear_profile:
        raise SystemExit("Cannot use --profile and --clear-profile together")

    if args.profile:
        profile = args.profile.strip()
        ensure_profile_exists(cfg, profile)
        data["profile"] = profile
        changed = True

    if args.clear_profile and "profile" in data:
        data.pop("profile", None)
        changed = True

    if args.scope is not None:
        data["scope"] = args.scope
        if args.scope == "general":
            data.pop("specific_to", None)
        changed = True

    if args.clear_specific_to:
        data.pop("specific_to", None)
        changed = True

    if args.specific_to is not None:
        data["specific_to"] = args.specific_to.strip()
        changed = True

    if not changed:
        raise SystemExit("No updates provided. Use edit flags to change template fields.")

    if data.get("scope") == "specific" and not str(data.get("specific_to", "")).strip():
        raise SystemExit("Template scope is `specific`; provide --specific-to")

    save_template(path, data)
    print(f"Updated template `{data['name']}` ({path.name})")
    return 0


def command_rename(args: argparse.Namespace) -> int:
    root = resolve_root(args.root)
    ensure_initialized(root)

    source_path, data = load_template(root, args.source)
    source_ext = source_path.suffix.lower()
    target_path = resolve_new_template_file(
        root,
        args.target,
        args.format,
        preserve_extension=source_ext,
    )

    target_stem, _ = split_template_name(args.target)
    ensure_stem_not_ambiguous(root, target_stem, target_path)

    if target_path.exists() and target_path != source_path and not args.force:
        raise SystemExit(
            f"Target template already exists at {target_path}. Use --force to overwrite."
        )

    data["name"] = target_stem
    save_template(target_path, data)

    if target_path != source_path and source_path.exists():
        source_path.unlink()

    print(f"Renamed template `{args.source}` to `{target_stem}` ({target_path.name})")
    return 0


def command_copy(args: argparse.Namespace) -> int:
    root = resolve_root(args.root)
    ensure_initialized(root)

    source_path, source = load_template(root, args.source)
    source_ext = source_path.suffix.lower()
    target_path = resolve_new_template_file(
        root,
        args.target,
        args.format,
        preserve_extension=source_ext,
    )

    target_stem, _ = split_template_name(args.target)
    ensure_stem_not_ambiguous(root, target_stem, target_path)

    if target_path.exists() and not args.force:
        raise SystemExit(
            f"Template `{args.target}` already exists at {target_path}. Use --force to overwrite."
        )

    source["name"] = target_stem
    save_template(target_path, source)
    print(f"Copied template `{args.source}` to `{target_stem}` ({target_path.name})")
    return 0


def command_delete(args: argparse.Namespace) -> int:
    root = resolve_root(args.root)
    ensure_initialized(root)

    path, data = load_template(root, args.name)
    path.unlink()
    print(f"Deleted template `{data['name']}` ({path.name})")
    return 0


def build_subprocess_command(
    runner: RunnerConfig, prompt: str
) -> tuple[list[str], dict[str, Any]]:
    cmd = [runner.command, *runner.args]
    kwargs: dict[str, Any] = {"text": True}

    if runner.prompt_mode == "stdin":
        kwargs["input"] = prompt
    else:
        cmd.extend([runner.prompt_flag, prompt])

    return cmd, kwargs


def run_runner_process(
    runner: RunnerConfig,
    prompt: str,
    capture_output: bool = False,
    print_command: bool = False,
) -> subprocess.CompletedProcess[str]:
    if shutil.which(runner.command) is None:
        raise SystemExit(
            f"Runner command `{runner.command}` was not found in PATH. "
            "Update config with a valid command or use --dry-run."
        )

    cmd, kwargs = build_subprocess_command(runner, prompt)
    if capture_output:
        kwargs["capture_output"] = True

    if print_command:
        print("Executing:", shlex.join(cmd), file=sys.stderr)

    try:
        return subprocess.run(cmd, check=False, **kwargs)
    except OSError as exc:
        raise SystemExit(f"Failed to execute runner command: {exc}") from exc


def extract_json_object(text: str) -> dict[str, Any]:
    payload = text.strip()
    if not payload:
        raise SystemExit("Runner returned empty output; expected JSON object.")

    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", payload, re.DOTALL)
    if fence_match:
        payload = fence_match.group(1).strip()

    try:
        direct = json.loads(payload)
        if isinstance(direct, dict):
            return direct
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for idx, ch in enumerate(payload):
        if ch != "{":
            continue
        try:
            candidate, _ = decoder.raw_decode(payload[idx:])
        except json.JSONDecodeError:
            continue
        if isinstance(candidate, dict):
            return candidate

    raise SystemExit("Could not parse a JSON object from runner output.")


def maybe_resolve_existing_template_file(root: Path, name: str) -> Path | None:
    stem, explicit_ext = split_template_name(name)
    if explicit_ext:
        path = templates_dir(root) / f"{stem}{explicit_ext}"
        return path if path.exists() else None

    matches = find_template_files_by_stem(root, stem)
    if not matches:
        return None
    if len(matches) > 1:
        choices = ", ".join(path.name for path in matches)
        raise SystemExit(
            f"Template name `{name}` is ambiguous. Use one of: {choices}"
        )
    return matches[0]


def build_ai_template_prompt(
    mode: str,
    template_name: str,
    request: str,
    existing_template: dict[str, Any] | None,
    scope_override: str | None,
    specific_to_override: str | None,
    bind_profile_override: str | None,
) -> str:
    context = {
        "mode": mode,
        "template_name": template_name,
        "request": request,
        "existing_template": existing_template,
        "scope_override": scope_override,
        "specific_to_override": specific_to_override,
        "bind_profile_override": bind_profile_override,
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
        '  "profile": "string|null"\n'
        "}\n"
        "Rules:\n"
        "- No markdown, no code fences, no explanation.\n"
        "- Keep role_prompt and instructions practical and concise.\n"
        "- Use placeholders like {{task}}, {{root}}, {{specific_to}} only where useful.\n"
        "- If scope is general, set specific_to to null.\n"
        "- If scope is specific, set specific_to to a concrete target.\n\n"
        f"Context:\n{context_json}\n"
    )


def derive_template_name_from_request(request: str) -> str:
    words = re.findall(r"[a-z0-9]+", request.lower())
    stopwords = {
        "a",
        "an",
        "and",
        "for",
        "from",
        "i",
        "is",
        "it",
        "of",
        "or",
        "please",
        "role",
        "template",
        "that",
        "the",
        "this",
        "to",
        "want",
        "with",
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


def command_ai(args: argparse.Namespace) -> int:
    root = resolve_root(args.root)
    ensure_initialized(root)
    cfg = load_config(root)

    request = " ".join(args.request).strip()
    if not request:
        raise SystemExit("AI request cannot be empty.")

    requested_name = args.name.strip() if args.name else ""
    if requested_name:
        template_name = requested_name
    else:
        template_name = next_available_template_name(
            root,
            derive_template_name_from_request(request),
        )

    runner_profile = args.runner_profile or cfg["default_profile"]
    _, runner = load_runner_profile(root, runner_profile)

    existing_path = maybe_resolve_existing_template_file(root, template_name)
    if existing_path is None:
        mode = "create"
        source_template = None
        target_path = resolve_new_template_file(
            root,
            template_name,
            args.format or cfg["default_template_format"],
        )
        target_stem, _ = split_template_name(template_name)
        ensure_stem_not_ambiguous(root, target_stem, target_path)
    else:
        mode = "update"
        source_template = normalize_template_data(
            load_mapping_file(existing_path), fallback_name=existing_path.stem
        )
        source_ext = existing_path.suffix.lower()
        target_path = resolve_new_template_file(
            root,
            template_name,
            args.format,
            preserve_extension=source_ext,
        )
        target_stem, _ = split_template_name(template_name)
        if target_path.exists() and target_path != existing_path:
            raise SystemExit(
                f"Target file `{target_path.name}` already exists. "
                "Rename/delete it first, or pick a different template name."
            )

    if args.scope == "general" and args.specific_to:
        raise SystemExit("--specific-to cannot be used with --scope general")

    ai_prompt = build_ai_template_prompt(
        mode=mode,
        template_name=target_stem,
        request=request,
        existing_template=source_template,
        scope_override=args.scope,
        specific_to_override=args.specific_to,
        bind_profile_override=args.bind_profile,
    )

    proc = run_runner_process(
        runner,
        ai_prompt,
        capture_output=True,
        print_command=args.print_command,
    )
    if proc.returncode != 0:
        stderr_text = (proc.stderr or "").strip()
        stdout_text = (proc.stdout or "").strip()
        details = stderr_text or stdout_text or "(no output)"
        raise SystemExit(
            f"AI generation failed with exit code {proc.returncode}:\n{details}"
        )

    raw_output = (proc.stdout or "").strip() or (proc.stderr or "").strip()
    generated = extract_json_object(raw_output)

    data: dict[str, Any] = {
        "name": target_stem,
        "description": str(generated.get("description", "")).strip(),
        "role_prompt": str(generated.get("role_prompt", "")).strip(),
        "instructions": str(generated.get("instructions", "")).strip(),
    }

    scope = (
        args.scope
        or ("specific" if args.specific_to else None)
        or str(generated.get("scope", "general")).strip().lower()
        or "general"
    )
    if scope not in ALLOWED_SCOPES:
        raise SystemExit("Generated template has invalid scope. Expected general or specific.")
    data["scope"] = scope

    specific_to = (
        args.specific_to.strip()
        if args.specific_to
        else str(generated.get("specific_to", "")).strip() or None
    )
    if scope == "specific" and not specific_to:
        raise SystemExit(
            "Generated template scope is specific but specific_to is empty. "
            "Retry with --specific-to."
        )
    if scope == "specific" and specific_to:
        data["specific_to"] = specific_to

    bind_profile = args.bind_profile
    if not bind_profile:
        candidate_profile = str(generated.get("profile", "")).strip()
        bind_profile = candidate_profile or None
    if bind_profile:
        ensure_profile_exists(cfg, bind_profile)
        data["profile"] = bind_profile

    if args.dry_run:
        print(json.dumps({"target_file": str(target_path), "template": data}, indent=2))
        return 0

    save_template(target_path, data)

    if mode == "update" and existing_path is not None and target_path != existing_path:
        existing_path.unlink()

    print(f"{mode.title()}d template `{target_stem}` at {target_path}")
    return 0


def command_run(args: argparse.Namespace) -> int:
    root = resolve_root(args.root)
    ensure_initialized(root)

    cfg = load_config(root)
    _, template = load_template(root, args.name)

    template_profile = str(template.get("profile", "")).strip() or None
    selected_profile_name = args.profile or template_profile or cfg["default_profile"]
    _, runner = load_runner_profile(root, selected_profile_name)

    vars_from_cli = parse_vars(args.var)
    prompt, missing = build_prompt(
        template,
        args.task,
        args.extra,
        root,
        selected_profile_name,
        vars_from_cli,
    )

    if missing:
        if args.strict_vars:
            missing_text = ", ".join(sorted(missing))
            raise SystemExit(f"Missing variable values for: {missing_text}")
        print(
            f"Warning: unresolved placeholders kept as-is: {', '.join(sorted(missing))}",
            file=sys.stderr,
        )

    if args.dry_run:
        print(f"# profile: {selected_profile_name}\n")
        print(prompt)
        return 0

    proc = run_runner_process(
        runner,
        prompt,
        capture_output=False,
        print_command=args.print_command,
    )
    return int(proc.returncode)


def command_profile_list(args: argparse.Namespace) -> int:
    root = resolve_root(args.root)
    ensure_initialized(root)

    cfg = load_config(root)
    default_profile = cfg["default_profile"]

    for name in sorted(cfg["profiles"].keys()):
        marker = "*" if name == default_profile else " "
        profile = parse_runner(name, cfg["profiles"][name])
        print(
            f"{marker} {name:14} cmd={profile.command} mode={profile.prompt_mode} args={len(profile.args)}"
        )
    return 0


def command_profile_show(args: argparse.Namespace) -> int:
    root = resolve_root(args.root)
    ensure_initialized(root)

    cfg = load_config(root)
    if args.name not in cfg["profiles"]:
        raise SystemExit(f"Profile `{args.name}` not found")

    out = {
        "name": args.name,
        "default": args.name == cfg["default_profile"],
        **cfg["profiles"][args.name],
    }
    print(json.dumps(out, indent=2))
    return 0


def command_profile_add(args: argparse.Namespace) -> int:
    root = resolve_root(args.root)
    ensure_initialized(root)

    cfg = load_config(root)
    name = args.name.strip()
    if not name:
        raise SystemExit("Profile name cannot be empty")

    exists = name in cfg["profiles"]
    if exists and not args.force:
        raise SystemExit(f"Profile `{name}` already exists. Use --force to overwrite.")

    profile_raw = {
        "command": args.command.strip(),
        "args": [str(item) for item in args.arg],
        "prompt_mode": args.prompt_mode,
        "prompt_flag": args.prompt_flag,
    }
    parse_runner(name, profile_raw)

    cfg["profiles"][name] = profile_raw
    save_config(root, cfg)
    print(f"Saved profile `{name}`")
    return 0


def command_profile_remove(args: argparse.Namespace) -> int:
    root = resolve_root(args.root)
    ensure_initialized(root)

    cfg = load_config(root)
    name = args.name

    if name not in cfg["profiles"]:
        raise SystemExit(f"Profile `{name}` not found")
    if name == cfg["default_profile"]:
        raise SystemExit(
            f"Profile `{name}` is the default profile. Set another default first."
        )

    for path in list_template_files(root):
        template = normalize_template_data(load_mapping_file(path), fallback_name=path.stem)
        if str(template.get("profile", "")).strip() == name:
            raise SystemExit(
                f"Profile `{name}` is used by template `{template['name']}` ({path.name}). "
                "Reassign or remove that template first."
            )

    del cfg["profiles"][name]
    save_config(root, cfg)
    print(f"Removed profile `{name}`")
    return 0


def command_profile_default(args: argparse.Namespace) -> int:
    root = resolve_root(args.root)
    ensure_initialized(root)

    cfg = load_config(root)
    name = args.name

    if name not in cfg["profiles"]:
        raise SystemExit(f"Profile `{name}` not found")

    cfg["default_profile"] = name
    save_config(root, cfg)
    print(f"Default profile set to `{name}`")
    return 0


def command_profile_format(args: argparse.Namespace) -> int:
    root = resolve_root(args.root)
    ensure_initialized(root)

    cfg = load_config(root)
    fmt = args.template_format
    if fmt not in FORMAT_TO_TEMPLATE_EXT:
        raise SystemExit("Template format must be `json` or `yaml`")

    cfg["default_template_format"] = fmt
    save_config(root, cfg)
    print(f"Default template format set to `{fmt}`")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codexflow",
        description="Template-driven CLI for role-based coding automation.",
    )
    parser.add_argument(
        "--root",
        help="Project root where .codexflow lives (defaults to current directory).",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    p_init = subparsers.add_parser("init", help="Initialize codexflow config and starter templates.")
    p_init.add_argument("--force", action="store_true", help="Overwrite existing config/templates.")
    p_init.set_defaults(func=command_init)

    p_list = subparsers.add_parser("list", help="List available templates.")
    p_list.set_defaults(func=command_list)

    p_show = subparsers.add_parser("show", help="Show template details by name.")
    p_show.add_argument("name", help="Template name (or file name like testing.yaml).")
    p_show.set_defaults(func=command_show)

    p_create = subparsers.add_parser("create", help="Create or overwrite a template.")
    p_create.add_argument("name", help="Template name (optionally with .json/.yaml extension).")
    p_create.add_argument("--description", required=True, help="Short summary of the template purpose.")
    p_create.add_argument(
        "--role",
        required=True,
        help="Role prompt text, or @/path/to/file to load from a file.",
    )
    p_create.add_argument(
        "--instructions",
        required=True,
        help="Execution instructions text, or @/path/to/file to load from a file.",
    )
    p_create.add_argument(
        "--profile",
        help="Runner profile name for this template (falls back to default profile).",
    )
    p_create.add_argument(
        "--scope",
        choices=sorted(ALLOWED_SCOPES),
        default="general",
        help="Role scope classification.",
    )
    p_create.add_argument(
        "--specific-to",
        help="Required only when --scope specific (e.g. checkout-service).",
    )
    p_create.add_argument(
        "--format",
        choices=sorted(FORMAT_TO_TEMPLATE_EXT.keys()),
        help="Template file format (json or yaml).",
    )
    p_create.add_argument("--force", action="store_true", help="Overwrite if template exists.")
    p_create.set_defaults(func=command_create)

    p_edit = subparsers.add_parser("edit", help="Edit an existing template.")
    p_edit.add_argument("name", help="Template name (or file name).")
    p_edit.add_argument("--description", help="New description.")
    p_edit.add_argument("--role", help="New role prompt text or @file path.")
    p_edit.add_argument("--instructions", help="New execution instructions text or @file path.")
    p_edit.add_argument("--profile", help="Set profile binding.")
    p_edit.add_argument("--clear-profile", action="store_true", help="Remove template profile binding.")
    p_edit.add_argument("--scope", choices=sorted(ALLOWED_SCOPES), help="Set role scope.")
    p_edit.add_argument("--specific-to", help="Set specific target for specific scope.")
    p_edit.add_argument("--clear-specific-to", action="store_true", help="Clear specific target.")
    p_edit.set_defaults(func=command_edit)

    p_rename = subparsers.add_parser("rename", help="Rename a template.")
    p_rename.add_argument("source", help="Current template name.")
    p_rename.add_argument("target", help="New template name.")
    p_rename.add_argument(
        "--format",
        choices=sorted(FORMAT_TO_TEMPLATE_EXT.keys()),
        help="Optionally convert template file format during rename.",
    )
    p_rename.add_argument("--force", action="store_true", help="Overwrite target if it exists.")
    p_rename.set_defaults(func=command_rename)

    p_copy = subparsers.add_parser("copy", help="Copy a template to a new template name.")
    p_copy.add_argument("source", help="Source template name.")
    p_copy.add_argument("target", help="Target template name.")
    p_copy.add_argument(
        "--format",
        choices=sorted(FORMAT_TO_TEMPLATE_EXT.keys()),
        help="Optionally convert template format in the copied template.",
    )
    p_copy.add_argument("--force", action="store_true", help="Overwrite target if it exists.")
    p_copy.set_defaults(func=command_copy)

    p_delete = subparsers.add_parser("delete", help="Delete a template.")
    p_delete.add_argument("name", help="Template name.")
    p_delete.set_defaults(func=command_delete)

    p_ai = subparsers.add_parser(
        "ai",
        help="Use the runner (e.g. codex) to create or update a template from a natural-language request.",
    )
    p_ai.add_argument(
        "request",
        nargs="+",
        help="Natural-language description of the role to generate.",
    )
    p_ai.add_argument(
        "--name",
        help="Optional template name. If omitted, a name is auto-generated from the request.",
    )
    p_ai.add_argument(
        "--runner-profile",
        help="Runner profile used for AI generation (defaults to config default profile).",
    )
    p_ai.add_argument(
        "--bind-profile",
        help="Bind generated template to this profile.",
    )
    p_ai.add_argument(
        "--scope",
        choices=sorted(ALLOWED_SCOPES),
        help="Force generated scope (general or specific).",
    )
    p_ai.add_argument(
        "--specific-to",
        help="Force specific target (used with or implies specific scope).",
    )
    p_ai.add_argument(
        "--format",
        choices=sorted(FORMAT_TO_TEMPLATE_EXT.keys()),
        help="Target template format (json or yaml). For update, can convert format.",
    )
    p_ai.add_argument(
        "--dry-run",
        action="store_true",
        help="Show generated template JSON without saving.",
    )
    p_ai.add_argument(
        "--print-command",
        action="store_true",
        help="Print runner command before execution.",
    )
    p_ai.set_defaults(func=command_ai)

    p_run = subparsers.add_parser("run", help="Run a template against a task.")
    p_run.add_argument("name", help="Template name.")
    p_run.add_argument("task", help="Task text.")
    p_run.add_argument("--extra", help="Additional context text.")
    p_run.add_argument("--profile", help="Override runner profile for this run.")
    p_run.add_argument(
        "--var",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Template variable. Can be repeated. Example: --var repo=payments",
    )
    p_run.add_argument(
        "--strict-vars",
        action="store_true",
        help="Fail if any {{variable}} placeholder is unresolved.",
    )
    p_run.add_argument(
        "--dry-run",
        action="store_true",
        help="Print composed prompt only. Does not execute runner command.",
    )
    p_run.add_argument(
        "--print-command",
        action="store_true",
        help="Print external command before execution.",
    )
    p_run.set_defaults(func=command_run)

    p_profile = subparsers.add_parser("profile", help="Manage runner profiles.")
    profile_sub = p_profile.add_subparsers(dest="profile_command", required=True)

    p_profile_list = profile_sub.add_parser("list", help="List configured profiles.")
    p_profile_list.set_defaults(func=command_profile_list)

    p_profile_show = profile_sub.add_parser("show", help="Show profile details.")
    p_profile_show.add_argument("name", help="Profile name.")
    p_profile_show.set_defaults(func=command_profile_show)

    p_profile_add = profile_sub.add_parser("add", help="Create or update a profile.")
    p_profile_add.add_argument("name", help="Profile name.")
    p_profile_add.add_argument("--command", required=True, help="Runner command (e.g. codex).")
    p_profile_add.add_argument(
        "--arg",
        action="append",
        default=[],
        help="Runner argument, repeat to add multiple args.",
    )
    p_profile_add.add_argument(
        "--prompt-mode",
        choices=["stdin", "arg"],
        default="stdin",
        help="How to pass prompt to runner.",
    )
    p_profile_add.add_argument(
        "--prompt-flag",
        default="--prompt",
        help="Flag used when prompt-mode=arg.",
    )
    p_profile_add.add_argument("--force", action="store_true", help="Overwrite existing profile.")
    p_profile_add.set_defaults(func=command_profile_add)

    p_profile_remove = profile_sub.add_parser("remove", help="Remove a profile.")
    p_profile_remove.add_argument("name", help="Profile name.")
    p_profile_remove.set_defaults(func=command_profile_remove)

    p_profile_default = profile_sub.add_parser("default", help="Set the default profile.")
    p_profile_default.add_argument("name", help="Profile name.")
    p_profile_default.set_defaults(func=command_profile_default)

    p_profile_format = profile_sub.add_parser(
        "default-format",
        help="Set default template file format for new templates.",
    )
    p_profile_format.add_argument(
        "template_format",
        choices=sorted(FORMAT_TO_TEMPLATE_EXT.keys()),
        help="json or yaml",
    )
    p_profile_format.set_defaults(func=command_profile_format)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
