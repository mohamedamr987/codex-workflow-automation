from __future__ import annotations

from pathlib import Path

from .app_constants import CONFIG_DIR_NAME, CONFIG_FILE_NAME, TEMPLATES_DIR_NAME


def resolve_root(path: str | None) -> Path:
    return Path(path).expanduser().resolve() if path else Path.cwd().resolve()


def config_dir(root: Path) -> Path:
    return root / CONFIG_DIR_NAME


def templates_dir(root: Path) -> Path:
    return config_dir(root) / TEMPLATES_DIR_NAME


def config_file(root: Path) -> Path:
    return config_dir(root) / CONFIG_FILE_NAME


def ensure_initialized(root: Path) -> None:
    missing = []
    if not config_dir(root).exists():
        missing.append(str(config_dir(root)))
    if not templates_dir(root).exists():
        missing.append(str(templates_dir(root)))
    if not config_file(root).exists():
        missing.append(str(config_file(root)))
    if missing:
        joined = "\n - ".join([""] + missing)
        raise SystemExit(
            "Project is not initialized. Run `codexflow init` first. Missing:" + joined
        )
