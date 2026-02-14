from __future__ import annotations

import json
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from .app_constants import RunnerConfig
from .app_paths import templates_dir
from .template_paths import find_template_files_by_stem, split_template_name


def build_subprocess_command(
    runner: RunnerConfig, prompt: str
) -> tuple[list[str], dict[str, Any]]:
    cmd = [runner.command, *runner.args]
    kwargs: dict[str, Any] = {"text": True}
    if runner.prompt_mode == "stdin":
        kwargs["input"] = prompt
    else:
        cmd.extend([runner.prompt_flag, prompt])
    return cmd, kwargs


def run_runner_process(
    runner: RunnerConfig,
    prompt: str,
    capture_output: bool = False,
    print_command: bool = False,
) -> subprocess.CompletedProcess[str]:
    if shutil.which(runner.command) is None:
        raise SystemExit(
            f"Runner command `{runner.command}` was not found in PATH. "
            "Update config with a valid command or use --dry-run."
        )
    cmd, kwargs = build_subprocess_command(runner, prompt)
    if capture_output:
        kwargs["capture_output"] = True
    if print_command:
        print("Executing:", shlex.join(cmd), file=sys.stderr)
    try:
        return subprocess.run(cmd, check=False, **kwargs)
    except OSError as exc:
        raise SystemExit(f"Failed to execute runner command: {exc}") from exc


def extract_json_object(text: str) -> dict[str, Any]:
    payload = text.strip()
    if not payload:
        raise SystemExit("Runner returned empty output; expected JSON object.")
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", payload, re.DOTALL)
    if match:
        payload = match.group(1).strip()
    try:
        parsed = json.loads(payload)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    decoder = json.JSONDecoder()
    for idx, ch in enumerate(payload):
        if ch != "{":
            continue
        try:
            candidate, _ = decoder.raw_decode(payload[idx:])
        except json.JSONDecodeError:
            continue
        if isinstance(candidate, dict):
            return candidate
    raise SystemExit("Could not parse a JSON object from runner output.")


def maybe_resolve_existing_template_file(root: Path, name: str) -> Path | None:
    stem, explicit_ext = split_template_name(name)
    if explicit_ext:
        path = templates_dir(root) / f"{stem}{explicit_ext}"
        return path if path.exists() else None
    matches = find_template_files_by_stem(root, stem)
    if not matches:
        return None
    if len(matches) > 1:
        choices = ", ".join(path.name for path in matches)
        raise SystemExit(f"Template name `{name}` is ambiguous. Use one of: {choices}")
    return matches[0]
