"""
Core module - Configuration, state, session, and localization
"""
from .config import CONFIG, load_and_merge_config
from .state import AppStateGateway, StateStore, app_state, state_gateway
from .session import clear_session_params, get_temp_dir_size, load_session_params, save_session_params
from .persistence import (
    atomic_write_json,
    consume_exit_marker,
    export_session,
    extract_legacy_projection_presets,
    import_session,
    install_autosave,
    load_all,
    load_persistent_cache,
    load_ui_state,
    mark_clean_exit,
    save_all,
)
from .localization import translate, set_language, available_languages, validate_language

__all__ = [
    'CONFIG',
    'load_and_merge_config',
    'app_state',
    'AppStateGateway',
    'StateStore',
    'state_gateway',
    'load_session_params',
    'save_session_params',
    'clear_session_params',
    'get_temp_dir_size',
    'save_all',
    'load_all',
    'load_ui_state',
    'load_persistent_cache',
    'extract_legacy_projection_presets',
    'export_session',
    'import_session',
    'install_autosave',
    'mark_clean_exit',
    'consume_exit_marker',
    'translate',
    'set_language',
    'available_languages',
    'validate_language',
]
