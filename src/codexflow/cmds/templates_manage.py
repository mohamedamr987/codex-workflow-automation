from __future__ import annotations

import argparse
from typing import Any

from ..core import (
    FORMAT_TO_TEMPLATE_EXT,
    ensure_initialized,
    ensure_profile_exists,
    ensure_stem_not_ambiguous,
    load_config,
    load_template,
    parse_duration_seconds,
    read_text_arg_or_file,
    resolve_new_template_file,
    resolve_root,
    save_template,
    split_template_name,
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
        raise SystemExit(f"Template `{args.name}` already exists at {output_path}. Use --force to overwrite.")

    scope = args.scope
    specific_to = args.specific_to.strip() if args.specific_to else None
    if scope == "specific" and not specific_to:
        raise SystemExit("--specific-to is required when --scope specific")
    if scope == "general" and specific_to:
        raise SystemExit("--specific-to can only be used with --scope specific")

    repeat_for = args.repeat_for.strip() if args.repeat_for else None
    repeat_every = args.repeat_every.strip() if args.repeat_every else None
    if repeat_for:
        parse_duration_seconds(repeat_for, "repeat_for")
    if repeat_every:
        parse_duration_seconds(repeat_every, "repeat_every")
    if repeat_every and not repeat_for:
        raise SystemExit("--repeat-every requires --repeat-for")

    data: dict[str, Any] = {
        "name": stem,
        "description": args.description.strip(),
        "role_prompt": read_text_arg_or_file(args.role).strip(),
        "instructions": read_text_arg_or_file(args.instructions).strip(),
        "scope": scope,
    }
    if selected_profile:
        data["profile"] = selected_profile
    if scope == "specific" and specific_to:
        data["specific_to"] = specific_to
    if repeat_for:
        data["repeat_for"] = repeat_for
    if repeat_every:
        data["repeat_every"] = repeat_every

    save_template(output_path, data)
    print(f"Saved template `{stem}` to {output_path}")
    return 0


def command_edit(args: argparse.Namespace) -> int:
    root = resolve_root(args.root)
    ensure_initialized(root)
    cfg = load_config(root)
    path, data = load_template(root, args.name)
    changed = False
    if args.clear_repeat and (args.repeat_for is not None or args.repeat_every is not None):
        raise SystemExit("Cannot use --clear-repeat with --repeat-for/--repeat-every")

    if args.description is not None:
        data["description"] = args.description.strip(); changed = True
    if args.role is not None:
        data["role_prompt"] = read_text_arg_or_file(args.role).strip(); changed = True
    if args.instructions is not None:
        data["instructions"] = read_text_arg_or_file(args.instructions).strip(); changed = True

    if args.profile and args.clear_profile:
        raise SystemExit("Cannot use --profile and --clear-profile together")
    if args.profile:
        profile = args.profile.strip(); ensure_profile_exists(cfg, profile)
        data["profile"] = profile; changed = True
    if args.clear_profile and "profile" in data:
        data.pop("profile", None); changed = True

    if args.scope is not None:
        data["scope"] = args.scope; changed = True
        if args.scope == "general":
            data.pop("specific_to", None)
    if args.clear_specific_to:
        data.pop("specific_to", None); changed = True
    if args.specific_to is not None:
        data["specific_to"] = args.specific_to.strip(); changed = True

    if args.repeat_for is not None:
        value = args.repeat_for.strip()
        if not value:
            raise SystemExit("--repeat-for cannot be empty")
        parse_duration_seconds(value, "repeat_for")
        data["repeat_for"] = value; changed = True
    if args.repeat_every is not None:
        value = args.repeat_every.strip()
        if not value:
            raise SystemExit("--repeat-every cannot be empty")
        parse_duration_seconds(value, "repeat_every")
        data["repeat_every"] = value; changed = True
    if args.clear_repeat:
        data.pop("repeat_for", None); data.pop("repeat_every", None); changed = True
    if args.clear_repeat_every:
        data.pop("repeat_every", None); changed = True

    if not changed:
        raise SystemExit("No updates provided. Use edit flags to change template fields.")
    if data.get("scope") == "specific" and not str(data.get("specific_to", "")).strip():
        raise SystemExit("Template scope is `specific`; provide --specific-to")
    if data.get("repeat_every") and not data.get("repeat_for"):
        raise SystemExit("Template has repeat_every but repeat_for is missing")

    save_template(path, data)
    print(f"Updated template `{data['name']}` ({path.name})")
    return 0
