from __future__ import annotations

import argparse
import json
from typing import Any

from ..core import (
    ALLOWED_SCOPES,
    build_ai_template_prompt,
    derive_template_name_from_request,
    ensure_initialized,
    ensure_profile_exists,
    ensure_stem_not_ambiguous,
    extract_json_object,
    load_config,
    load_mapping_file,
    load_runner_profile,
    maybe_resolve_existing_template_file,
    next_available_template_name,
    normalize_template_data,
    parse_duration_seconds,
    resolve_new_template_file,
    resolve_root,
    run_runner_process,
    save_template,
    split_template_name,
)


def command_ai(args: argparse.Namespace) -> int:
    root = resolve_root(args.root)
    ensure_initialized(root)
    cfg = load_config(root)
    request = " ".join(args.request).strip()
    if not request:
        raise SystemExit("AI request cannot be empty.")

    template_name = args.name.strip() if args.name else next_available_template_name(
        root, derive_template_name_from_request(request)
    )
    _, runner = load_runner_profile(root, args.runner_profile or cfg["default_profile"])

    existing_path = maybe_resolve_existing_template_file(root, template_name)
    if existing_path is None:
        mode = "create"
        source_template = None
        target_path = resolve_new_template_file(root, template_name, args.format or cfg["default_template_format"])
        target_stem, _ = split_template_name(template_name)
        ensure_stem_not_ambiguous(root, target_stem, target_path)
    else:
        mode = "update"
        source_template = normalize_template_data(load_mapping_file(existing_path), fallback_name=existing_path.stem)
        target_path = resolve_new_template_file(
            root, template_name, args.format, preserve_extension=existing_path.suffix.lower()
        )
        target_stem, _ = split_template_name(template_name)
        if target_path.exists() and target_path != existing_path:
            raise SystemExit(f"Target file `{target_path.name}` already exists. Rename/delete it first.")

    if args.scope == "general" and args.specific_to:
        raise SystemExit("--specific-to cannot be used with --scope general")
    if args.repeat_every and not args.repeat_for:
        raise SystemExit("--repeat-every requires --repeat-for")
    if args.repeat_for:
        parse_duration_seconds(args.repeat_for, "repeat_for")
    if args.repeat_every:
        parse_duration_seconds(args.repeat_every, "repeat_every")

    ai_prompt = build_ai_template_prompt(
        mode=mode,
        template_name=target_stem,
        request=request,
        existing_template=source_template,
        scope_override=args.scope,
        specific_to_override=args.specific_to,
        bind_profile_override=args.bind_profile,
        repeat_for_override=args.repeat_for,
        repeat_every_override=args.repeat_every,
    )
    proc = run_runner_process(runner, ai_prompt, capture_output=True, print_command=args.print_command)
    if proc.returncode != 0:
        details = (proc.stderr or "").strip() or (proc.stdout or "").strip() or "(no output)"
        raise SystemExit(f"AI generation failed with exit code {proc.returncode}:\n{details}")

    generated = extract_json_object((proc.stdout or "").strip() or (proc.stderr or "").strip())
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

    specific_to = args.specific_to.strip() if args.specific_to else str(generated.get("specific_to", "")).strip() or None
    if scope == "specific" and not specific_to:
        raise SystemExit("Generated template scope is specific but specific_to is empty. Retry with --specific-to.")
    if scope == "specific" and specific_to:
        data["specific_to"] = specific_to

    bind_profile = args.bind_profile or (str(generated.get("profile", "")).strip() or None)
    if bind_profile:
        ensure_profile_exists(cfg, bind_profile)
        data["profile"] = bind_profile

    repeat_for = args.repeat_for.strip() if args.repeat_for else str(generated.get("repeat_for", "")).strip() or None
    if repeat_for:
        parse_duration_seconds(repeat_for, "repeat_for")
        data["repeat_for"] = repeat_for
    repeat_every = args.repeat_every.strip() if args.repeat_every else str(generated.get("repeat_every", "")).strip() or None
    if repeat_every:
        parse_duration_seconds(repeat_every, "repeat_every")
        data["repeat_every"] = repeat_every
    if data.get("repeat_every") and not data.get("repeat_for"):
        raise SystemExit("Generated template has repeat_every but repeat_for is missing. Retry with --repeat-for.")

    if args.dry_run:
        print(json.dumps({"target_file": str(target_path), "template": data}, indent=2))
        return 0

    save_template(target_path, data)
    if mode == "update" and existing_path is not None and target_path != existing_path:
        existing_path.unlink()
    print(f"{mode.title()}d template `{target_stem}` at {target_path}")
    return 0
