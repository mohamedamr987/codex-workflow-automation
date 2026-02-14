from __future__ import annotations

from .cmds.ai import command_ai
from .cmds.profiles import (
    command_profile_add,
    command_profile_default,
    command_profile_format,
    command_profile_list,
    command_profile_remove,
    command_profile_show,
)
from .cmds.run import command_run
from .cmds.templates_fileops import command_copy, command_delete, command_rename
from .cmds.templates_manage import command_create, command_edit
from .cmds.templates_meta import command_init, command_list, command_show

__all__ = [
    "command_ai",
    "command_copy",
    "command_create",
    "command_delete",
    "command_edit",
    "command_init",
    "command_list",
    "command_profile_add",
    "command_profile_default",
    "command_profile_format",
    "command_profile_list",
    "command_profile_remove",
    "command_profile_show",
    "command_rename",
    "command_run",
    "command_show",
]
