from __future__ import annotations

import argparse

from .parser_parts.ai_run import register_ai_and_run_commands
from .parser_parts.profiles import register_profile_commands
from .parser_parts.templates import register_template_commands


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
    register_template_commands(subparsers)
    register_ai_and_run_commands(subparsers)
    register_profile_commands(subparsers)
    return parser
