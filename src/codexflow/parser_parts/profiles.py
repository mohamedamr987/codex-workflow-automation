from __future__ import annotations

from argparse import _SubParsersAction

from ..commands import (
    command_profile_add,
    command_profile_default,
    command_profile_format,
    command_profile_list,
    command_profile_remove,
    command_profile_show,
)
from ..core import FORMAT_TO_TEMPLATE_EXT


def register_profile_commands(subparsers: _SubParsersAction) -> None:
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
    p_profile_add.add_argument("--arg", action="append", default=[], help="Runner argument, repeat to add multiple args.")
    p_profile_add.add_argument("--prompt-mode", choices=["stdin", "arg"], default="stdin", help="How to pass prompt to runner.")
    p_profile_add.add_argument("--prompt-flag", default="--prompt", help="Flag used when prompt-mode=arg.")
    p_profile_add.add_argument("--force", action="store_true", help="Overwrite existing profile.")
    p_profile_add.set_defaults(func=command_profile_add)

    p_profile_remove = profile_sub.add_parser("remove", help="Remove a profile.")
    p_profile_remove.add_argument("name", help="Profile name.")
    p_profile_remove.set_defaults(func=command_profile_remove)

    p_profile_default = profile_sub.add_parser("default", help="Set the default profile.")
    p_profile_default.add_argument("name", help="Profile name.")
    p_profile_default.set_defaults(func=command_profile_default)

    p_profile_format = profile_sub.add_parser("default-format", help="Set default template file format for new templates.")
    p_profile_format.add_argument("template_format", choices=sorted(FORMAT_TO_TEMPLATE_EXT.keys()), help="json or yaml")
    p_profile_format.set_defaults(func=command_profile_format)
