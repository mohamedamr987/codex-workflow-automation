from __future__ import annotations

import argparse

from ..core import (
    ensure_initialized,
    ensure_stem_not_ambiguous,
    load_template,
    resolve_new_template_file,
    resolve_root,
    save_template,
    split_template_name,
)


def command_rename(args: argparse.Namespace) -> int:
    root = resolve_root(args.root)
    ensure_initialized(root)
    source_path, data = load_template(root, args.source)
    target_path = resolve_new_template_file(
        root,
        args.target,
        args.format,
        preserve_extension=source_path.suffix.lower(),
    )
    target_stem, _ = split_template_name(args.target)
    ensure_stem_not_ambiguous(root, target_stem, target_path)
    if target_path.exists() and target_path != source_path and not args.force:
        raise SystemExit(f"Target template already exists at {target_path}. Use --force to overwrite.")
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
    target_path = resolve_new_template_file(
        root,
        args.target,
        args.format,
        preserve_extension=source_path.suffix.lower(),
    )
    target_stem, _ = split_template_name(args.target)
    ensure_stem_not_ambiguous(root, target_stem, target_path)
    if target_path.exists() and not args.force:
        raise SystemExit(f"Template `{args.target}` already exists at {target_path}. Use --force to overwrite.")
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
