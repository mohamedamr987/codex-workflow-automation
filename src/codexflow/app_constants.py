from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

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
DEFAULT_REPEAT_EVERY = "10m"
DEFAULT_PROFILE_NAME = "default"

VAR_PATTERN = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_.-]*)\s*\}\}")
DURATION_CHUNKS_PATTERN = re.compile(r"(\d+(?:\.\d+)?)([smhd])")


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
