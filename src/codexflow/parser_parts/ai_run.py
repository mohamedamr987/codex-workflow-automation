from __future__ import annotations

from argparse import _SubParsersAction

from ..commands import command_ai, command_run
from ..core import ALLOWED_SCOPES, FORMAT_TO_TEMPLATE_EXT


def register_ai_and_run_commands(subparsers: _SubParsersAction) -> None:
    p_ai = subparsers.add_parser(
        "ai",
        help="Use the runner (e.g. codex) to create or update a template from a natural-language request.",
    )
    p_ai.add_argument("request", nargs="+", help="Natural-language description of the role to generate.")
    p_ai.add_argument("--name", help="Optional template name. If omitted, a name is auto-generated from the request.")
    p_ai.add_argument("--runner-profile", help="Runner profile used for AI generation (defaults to config default profile).")
    p_ai.add_argument("--bind-profile", help="Bind generated template to this profile.")
    p_ai.add_argument("--scope", choices=sorted(ALLOWED_SCOPES), help="Force generated scope (general or specific).")
    p_ai.add_argument("--specific-to", help="Force specific target (used with or implies specific scope).")
    p_ai.add_argument("--repeat-for", help="Force default runtime window for repeated execution in generated template.")
    p_ai.add_argument("--repeat-every", help="Force default repeat interval in generated template.")
    p_ai.add_argument("--format", choices=sorted(FORMAT_TO_TEMPLATE_EXT.keys()), help="Target template format (json or yaml). For update, can convert format.")
    p_ai.add_argument("--dry-run", action="store_true", help="Show generated template JSON without saving.")
    p_ai.add_argument("--print-command", action="store_true", help="Print runner command before execution.")
    p_ai.set_defaults(func=command_ai)

    p_run = subparsers.add_parser("run", help="Run a template against a task.")
    p_run.add_argument("name", help="Template name.")
    p_run.add_argument("task", help="Task text.")
    p_run.add_argument("--extra", help="Additional context text.")
    p_run.add_argument("--profile", help="Override runner profile for this run.")
    p_run.add_argument("--var", action="append", default=[], metavar="KEY=VALUE", help="Template variable. Can be repeated. Example: --var repo=payments")
    p_run.add_argument("--strict-vars", action="store_true", help="Fail if any {{variable}} placeholder is unresolved.")
    p_run.add_argument("--repeat-for", help="Override runtime window for repeated execution (e.g. 2h).")
    p_run.add_argument("--repeat-every", help="Override repeat interval (e.g. 10m). Defaults to template setting or 10m.")
    p_run.add_argument("--max-runs", type=int, help="Cap number of repeated runs (requires repeat-for).")
    p_run.add_argument("--continue-on-error", action="store_true", help="Continue repeated runs even if one run exits with a non-zero code.")
    p_run.add_argument("--dry-run", action="store_true", help="Print composed prompt only. Does not execute runner command.")
    p_run.add_argument("--print-command", action="store_true", help="Print external command before execution.")
    p_run.set_defaults(func=command_run)
