from __future__ import annotations

from argparse import _SubParsersAction

from ..commands import (
    command_copy,
    command_create,
    command_delete,
    command_edit,
    command_init,
    command_list,
    command_rename,
    command_show,
)
from ..core import ALLOWED_SCOPES, FORMAT_TO_TEMPLATE_EXT


def register_template_commands(subparsers: _SubParsersAction) -> None:
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
    p_create.add_argument("--role", required=True, help="Role prompt text, or @/path/to/file to load from a file.")
    p_create.add_argument("--instructions", required=True, help="Execution instructions text, or @/path/to/file to load from a file.")
    p_create.add_argument("--profile", help="Runner profile name for this template (falls back to default profile).")
    p_create.add_argument("--scope", choices=sorted(ALLOWED_SCOPES), default="general", help="Role scope classification.")
    p_create.add_argument("--specific-to", help="Required only when --scope specific (e.g. checkout-service).")
    p_create.add_argument("--repeat-for", help="Default runtime window for repeated execution (e.g. 2h, 45m, 1h30m).")
    p_create.add_argument("--repeat-every", help="Default repeat interval when repeat-for is set (e.g. 10m).")
    p_create.add_argument("--format", choices=sorted(FORMAT_TO_TEMPLATE_EXT.keys()), help="Template file format (json or yaml).")
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
    p_edit.add_argument("--repeat-for", help="Set default runtime window for repeated execution.")
    p_edit.add_argument("--repeat-every", help="Set default repeat interval.")
    p_edit.add_argument("--clear-repeat", action="store_true", help="Clear repeat-for and repeat-every settings.")
    p_edit.add_argument("--clear-repeat-every", action="store_true", help="Clear repeat-every only.")
    p_edit.set_defaults(func=command_edit)

    p_rename = subparsers.add_parser("rename", help="Rename a template.")
    p_rename.add_argument("source", help="Current template name.")
    p_rename.add_argument("target", help="New template name.")
    p_rename.add_argument("--format", choices=sorted(FORMAT_TO_TEMPLATE_EXT.keys()), help="Optionally convert template file format during rename.")
    p_rename.add_argument("--force", action="store_true", help="Overwrite target if it exists.")
    p_rename.set_defaults(func=command_rename)

    p_copy = subparsers.add_parser("copy", help="Copy a template to a new template name.")
    p_copy.add_argument("source", help="Source template name.")
    p_copy.add_argument("target", help="Target template name.")
    p_copy.add_argument("--format", choices=sorted(FORMAT_TO_TEMPLATE_EXT.keys()), help="Optionally convert template format in the copied template.")
    p_copy.add_argument("--force", action="store_true", help="Overwrite target if it exists.")
    p_copy.set_defaults(func=command_copy)

    p_delete = subparsers.add_parser("delete", help="Delete a template.")
    p_delete.add_argument("name", help="Template name.")
    p_delete.set_defaults(func=command_delete)
