from __future__ import annotations

import argparse
import sys
import time

from ..core import (
    DEFAULT_REPEAT_EVERY,
    build_prompt,
    ensure_initialized,
    load_config,
    load_runner_profile,
    load_template,
    parse_duration_seconds,
    parse_vars,
    resolve_root,
    run_runner_process,
)


def command_run(args: argparse.Namespace) -> int:
    root = resolve_root(args.root)
    ensure_initialized(root)
    cfg = load_config(root)
    _, template = load_template(root, args.name)

    template_profile = str(template.get("profile", "")).strip() or None
    selected_profile_name, runner = load_runner_profile(
        root, args.profile or template_profile or cfg["default_profile"]
    )

    prompt, missing = build_prompt(
        template,
        args.task,
        args.extra,
        root,
        selected_profile_name,
        parse_vars(args.var),
    )
    if missing:
        if args.strict_vars:
            raise SystemExit(f"Missing variable values for: {', '.join(sorted(missing))}")
        print(
            f"Warning: unresolved placeholders kept as-is: {', '.join(sorted(missing))}",
            file=sys.stderr,
        )

    template_repeat_for = str(template.get("repeat_for", "")).strip() or None
    template_repeat_every = str(template.get("repeat_every", "")).strip() or None
    repeat_for_value = args.repeat_for.strip() if args.repeat_for else template_repeat_for
    repeat_every_value = args.repeat_every.strip() if args.repeat_every else template_repeat_every

    if args.max_runs is not None and args.max_runs <= 0:
        raise SystemExit("--max-runs must be greater than zero")
    if repeat_every_value and not repeat_for_value:
        raise SystemExit("--repeat-every requires repeat-for (CLI or template default)")
    if args.max_runs is not None and not repeat_for_value:
        raise SystemExit("--max-runs requires repeat-for (CLI or template default)")
    if args.continue_on_error and not repeat_for_value:
        raise SystemExit("--continue-on-error requires repeat-for (CLI or template default)")

    repeat_for_seconds = parse_duration_seconds(repeat_for_value, "repeat_for") if repeat_for_value else None
    if repeat_for_seconds and not repeat_every_value:
        repeat_every_value = DEFAULT_REPEAT_EVERY
    repeat_every_seconds = parse_duration_seconds(repeat_every_value, "repeat_every") if repeat_every_value else None

    if args.dry_run:
        print(f"# profile: {selected_profile_name}\n")
        if repeat_for_seconds:
            print(
                f"# cadence: repeat-for={repeat_for_value} repeat-every={repeat_every_value}"
                + (f" max-runs={args.max_runs}" if args.max_runs is not None else "")
                + "\n"
            )
        print(prompt)
        return 0

    if not repeat_for_seconds:
        return int(run_runner_process(runner, prompt, print_command=args.print_command).returncode)
    end_time = time.monotonic() + repeat_for_seconds
    run_index = 0
    last_nonzero = 0
    while True:
        run_index += 1
        print(f"[codexflow] run {run_index} starting", file=sys.stderr)
        code = int(
            run_runner_process(
                runner,
                prompt,
                capture_output=False,
                print_command=args.print_command,
            ).returncode
        )
        if code != 0:
            last_nonzero = code
            if not args.continue_on_error:
                return code

        if args.max_runs is not None and run_index >= args.max_runs:
            break
        assert repeat_every_seconds is not None
        remaining = end_time - time.monotonic()
        if remaining <= 0 or repeat_every_seconds > remaining:
            break

        print(f"[codexflow] sleeping {repeat_every_value} before next run", file=sys.stderr)
        time.sleep(repeat_every_seconds)

    return last_nonzero
