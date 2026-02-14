from __future__ import annotations

from pathlib import Path

from .app_constants import (
    DEFAULT_TEMPLATE_FORMAT,
    FORMAT_TO_TEMPLATE_EXT,
    TEMPLATE_EXT_TO_FORMAT,
)
from .app_paths import templates_dir


def validate_template_name_input(name: str) -> None:
    if not name.strip():
        raise SystemExit("Template name cannot be empty")
    if Path(name).name != name:
        raise SystemExit("Template name cannot contain path separators")


def split_template_name(name: str) -> tuple[str, str | None]:
    validate_template_name_input(name)
    suffix = Path(name).suffix.lower()
    if suffix in TEMPLATE_EXT_TO_FORMAT:
        stem = Path(name).stem
        if not stem:
            raise SystemExit("Template name cannot be empty")
        return stem, suffix
    return name, None


def list_template_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for ext in TEMPLATE_EXT_TO_FORMAT:
        files.extend(templates_dir(root).glob(f"*{ext}"))
    return sorted(files, key=lambda p: (p.stem, p.suffix))


def find_template_files_by_stem(root: Path, stem: str) -> list[Path]:
    out: list[Path] = []
    for ext in TEMPLATE_EXT_TO_FORMAT:
        candidate = templates_dir(root) / f"{stem}{ext}"
        if candidate.exists():
            out.append(candidate)
    return sorted(out, key=lambda p: p.suffix)


def resolve_existing_template_file(root: Path, name: str) -> Path:
    stem, explicit_ext = split_template_name(name)
    if explicit_ext:
        path = templates_dir(root) / f"{stem}{explicit_ext}"
        if not path.exists():
            raise SystemExit(f"Template `{name}` not found at {path}")
        return path
    matches = find_template_files_by_stem(root, stem)
    if not matches:
        raise SystemExit(f"Template `{name}` not found")
    if len(matches) > 1:
        choices = ", ".join(path.name for path in matches)
        raise SystemExit(f"Template name `{name}` is ambiguous. Use one of: {choices}")
    return matches[0]


def resolve_new_template_file(
    root: Path,
    name: str,
    template_format: str | None,
    preserve_extension: str | None = None,
) -> Path:
    stem, explicit_ext = split_template_name(name)
    if explicit_ext:
        explicit_format = TEMPLATE_EXT_TO_FORMAT[explicit_ext]
        if template_format and template_format != explicit_format:
            raise SystemExit(
                f"Conflicting format for `{name}`. Extension implies {explicit_format}."
            )
        return templates_dir(root) / f"{stem}{explicit_ext}"
    if template_format:
        ext = FORMAT_TO_TEMPLATE_EXT[template_format]
    elif preserve_extension:
        ext = preserve_extension
    else:
        ext = FORMAT_TO_TEMPLATE_EXT[DEFAULT_TEMPLATE_FORMAT]
    return templates_dir(root) / f"{stem}{ext}"
