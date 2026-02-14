from __future__ import annotations

from .ai_utils import (
    build_ai_template_prompt,
    derive_template_name_from_request,
    next_available_template_name,
)
from .app_constants import (
    ALLOWED_SCOPES,
    CONFIG_DIR_NAME,
    CONFIG_FILE_NAME,
    DEFAULT_CONFIG,
    DEFAULT_PROFILE_NAME,
    DEFAULT_REPEAT_EVERY,
    DEFAULT_TEMPLATE_FORMAT,
    DURATION_CHUNKS_PATTERN,
    FORMAT_TO_TEMPLATE_EXT,
    REQUIRED_TEMPLATE_FIELDS,
    RunnerConfig,
    STARTER_TEMPLATES,
    TEMPLATE_EXT_TO_FORMAT,
    TEMPLATES_DIR_NAME,
    VAR_PATTERN,
)
from .app_paths import config_dir, config_file, ensure_initialized, resolve_root, templates_dir
from .config_ops import load_config, load_runner_profile, normalized_config, parse_runner, save_config
from .mapping_io import load_json, parse_simple_yaml, parse_simple_yaml_scalar, save_json
from .mapping_yaml_dump import dump_simple_yaml, load_mapping_file, save_mapping_file
from .prompting import (
    build_prompt,
    ensure_profile_exists,
    ensure_stem_not_ambiguous,
    parse_vars,
    read_text_arg_or_file,
    render_text_with_vars,
)
from .runner_utils import (
    build_subprocess_command,
    extract_json_object,
    maybe_resolve_existing_template_file,
    run_runner_process,
)
from .template_logic import (
    cadence_text,
    load_template,
    normalize_template_data,
    parse_duration_seconds,
    save_template,
    scope_text,
)
from .template_paths import (
    find_template_files_by_stem,
    list_template_files,
    resolve_existing_template_file,
    resolve_new_template_file,
    split_template_name,
    validate_template_name_input,
)
