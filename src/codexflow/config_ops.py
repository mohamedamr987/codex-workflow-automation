from __future__ import annotations

from pathlib import Path
from typing import Any

from .app_constants import (
    DEFAULT_PROFILE_NAME,
    DEFAULT_TEMPLATE_FORMAT,
    FORMAT_TO_TEMPLATE_EXT,
    RunnerConfig,
)
from .app_paths import config_file
from .mapping_io import load_json, save_json


def parse_runner(name: str, raw: dict[str, Any]) -> RunnerConfig:
    if not isinstance(raw, dict):
        raise SystemExit(f"Profile `{name}` must be an object")
    command = str(raw.get("command", "")).strip()
    if not command:
        raise SystemExit(f"Profile `{name}` has empty command")
    args = raw.get("args", [])
    if not isinstance(args, list):
        raise SystemExit(f"Profile `{name}` args must be a list")
    prompt_mode = str(raw.get("prompt_mode", "stdin")).strip()
    if prompt_mode not in {"stdin", "arg"}:
        raise SystemExit(f"Profile `{name}` prompt_mode must be `stdin` or `arg`")
    prompt_flag = str(raw.get("prompt_flag", "--prompt")).strip() or "--prompt"
    return RunnerConfig(
        command=command,
        args=[str(item) for item in args],
        prompt_mode=prompt_mode,
        prompt_flag=prompt_flag,
    )


def normalized_config(raw: dict[str, Any]) -> dict[str, Any]:
    if "profiles" in raw:
        default_profile = str(raw.get("default_profile", "")).strip()
        if not default_profile:
            raise SystemExit("Config default_profile cannot be empty")
        profiles = raw.get("profiles")
        if not isinstance(profiles, dict) or not profiles:
            raise SystemExit("Config profiles must be a non-empty object")
        if default_profile not in profiles:
            raise SystemExit(
                f"Config default_profile `{default_profile}` was not found in profiles"
            )
        default_template_format = str(
            raw.get("default_template_format", DEFAULT_TEMPLATE_FORMAT)
        ).strip()
        if default_template_format not in FORMAT_TO_TEMPLATE_EXT:
            raise SystemExit("Config default_template_format must be `json` or `yaml`")
        return {
            "default_profile": default_profile,
            "default_template_format": default_template_format,
            "profiles": profiles,
        }
    if "runner" in raw:
        return {
            "default_profile": DEFAULT_PROFILE_NAME,
            "default_template_format": DEFAULT_TEMPLATE_FORMAT,
            "profiles": {DEFAULT_PROFILE_NAME: raw["runner"]},
        }
    raise SystemExit(
        "Config must include either `profiles` (new format) or `runner` (legacy format)"
    )


def load_config(root: Path) -> dict[str, Any]:
    cfg = normalized_config(load_json(config_file(root)))
    for name, profile in cfg["profiles"].items():
        parse_runner(name, profile)
    return cfg


def save_config(root: Path, cfg: dict[str, Any]) -> None:
    save_json(config_file(root), cfg)


def load_runner_profile(root: Path, profile_name: str | None) -> tuple[str, RunnerConfig]:
    cfg = load_config(root)
    selected_name = profile_name or cfg["default_profile"]
    profiles = cfg["profiles"]
    if selected_name not in profiles:
        raise SystemExit(f"Profile `{selected_name}` not found in {config_file(root)}")
    return selected_name, parse_runner(selected_name, profiles[selected_name])
