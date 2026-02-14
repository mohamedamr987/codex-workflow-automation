from __future__ import annotations

import argparse
import json

from ..core import (
    DEFAULT_CONFIG,
    DEFAULT_PROFILE_NAME,
    DEFAULT_TEMPLATE_FORMAT,
    STARTER_TEMPLATES,
    TEMPLATE_EXT_TO_FORMAT,
    cadence_text,
    config_dir,
    config_file,
    ensure_initialized,
    list_template_files,
    load_config,
    load_mapping_file,
    load_template,
    normalize_template_data,
    resolve_new_template_file,
    resolve_root,
    save_json,
    save_template,
    scope_text,
    templates_dir,
)


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
            f"{path.name:20} [{template_format} | {profile} | {scope_text(data)} | {cadence_text(data)}] {data['description']}"
        )
    return 0


def command_show(args: argparse.Namespace) -> int:
    root = resolve_root(args.root)
    ensure_initialized(root)
    path, data = load_template(root, args.name)
    out = {**data, "file": path.name, "format": TEMPLATE_EXT_TO_FORMAT[path.suffix.lower()]}
    print(json.dumps(out, indent=2))
    return 0
