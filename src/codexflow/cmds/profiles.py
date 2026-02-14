from __future__ import annotations

import argparse
import json

from ..core import (
    FORMAT_TO_TEMPLATE_EXT,
    ensure_initialized,
    list_template_files,
    load_config,
    load_mapping_file,
    normalize_template_data,
    parse_runner,
    resolve_root,
    save_config,
)


def command_profile_list(args: argparse.Namespace) -> int:
    root = resolve_root(args.root)
    ensure_initialized(root)
    cfg = load_config(root)
    default_profile = cfg["default_profile"]
    for name in sorted(cfg["profiles"].keys()):
        marker = "*" if name == default_profile else " "
        profile = parse_runner(name, cfg["profiles"][name])
        print(f"{marker} {name:14} cmd={profile.command} mode={profile.prompt_mode} args={len(profile.args)}")
    return 0


def command_profile_show(args: argparse.Namespace) -> int:
    root = resolve_root(args.root)
    ensure_initialized(root)
    cfg = load_config(root)
    if args.name not in cfg["profiles"]:
        raise SystemExit(f"Profile `{args.name}` not found")
    out = {"name": args.name, "default": args.name == cfg["default_profile"], **cfg["profiles"][args.name]}
    print(json.dumps(out, indent=2))
    return 0


def command_profile_add(args: argparse.Namespace) -> int:
    root = resolve_root(args.root)
    ensure_initialized(root)
    cfg = load_config(root)
    name = args.name.strip()
    if not name:
        raise SystemExit("Profile name cannot be empty")
    if name in cfg["profiles"] and not args.force:
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
        raise SystemExit(f"Profile `{name}` is the default profile. Set another default first.")

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
    if args.name not in cfg["profiles"]:
        raise SystemExit(f"Profile `{args.name}` not found")
    cfg["default_profile"] = args.name
    save_config(root, cfg)
    print(f"Default profile set to `{args.name}`")
    return 0


def command_profile_format(args: argparse.Namespace) -> int:
    root = resolve_root(args.root)
    ensure_initialized(root)
    cfg = load_config(root)
    if args.template_format not in FORMAT_TO_TEMPLATE_EXT:
        raise SystemExit("Template format must be `json` or `yaml`")
    cfg["default_template_format"] = args.template_format
    save_config(root, cfg)
    print(f"Default template format set to `{args.template_format}`")
    return 0
