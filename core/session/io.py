"""
Session Management - Save and Load Algorithm Parameters
Handles persistence of last used parameters across program sessions
"""
from __future__ import annotations

import json
import logging
from typing import Any

from ..config import CONFIG
from .migration import migrate_session_data

logger = logging.getLogger(__name__)


def _atomic_write_json(path: Any, data: dict[str, Any]) -> None:
    """Write JSON atomically (temp file + rename) to avoid corrupting the
    session file when the process dies mid-write."""
    import os

    tmp_path = Path(str(path) + ".tmp")
    with open(tmp_path, 'w', encoding='utf-8') as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp_path, path)


def save_session_params(
    algorithm: str,
    umap_params: dict[str, Any],
    tsne_params: dict[str, Any],
    point_size: float | int,
    group_col: str,
    group_cols: list[str] | None = None,
    data_cols: list[str] | None = None,
    file_path: str | None = None,
    sheet_name: str | None = None,
    render_mode: str = 'UMAP',
    selected_2d_cols: list[str] | None = None,
    selected_3d_cols: list[str] | None = None,
    language: str | None = None,
    tooltip_columns: list[str] | None = None,
    ui_theme: str | None = None,
) -> bool:
    """
    Save current session parameters to temporary file
    """
    try:
        session_data = {
            'session_version': CONFIG.get('session_version', 1),
            'algorithm': algorithm,
            'umap_params': umap_params,
            'tsne_params': tsne_params,
            'point_size': point_size,
            'group_col': group_col,
            'group_cols': group_cols,
            'data_cols': data_cols,
            'file_path': file_path,
            'sheet_name': sheet_name,
            'render_mode': render_mode,
            'selected_2d_cols': selected_2d_cols or [],
            'selected_3d_cols': selected_3d_cols or [],
            'language': language,
            'tooltip_columns': tooltip_columns,
            'ui_theme': ui_theme
        }
        
        logger.debug("Saving session params. Tooltip columns: %s", tooltip_columns)

        _atomic_write_json(CONFIG['params_temp_file'], session_data)
        logger.info("Session parameters saved to %s", CONFIG['params_temp_file'])
        return True
    except Exception as e:
        logger.exception("Failed to save session parameters: %s", e)
        return False


def load_session_params() -> dict[str, Any] | None:
    """
    Load last session parameters from temporary file
    
    Returns:
        dict with keys: algorithm, umap_params, tsne_params, point_size, group_col
        or None if file doesn't exist or load fails
    """
    try:
        params_file = CONFIG['params_temp_file']
        legacy_params_file = CONFIG.get('legacy_params_temp_file')

        if not params_file.exists():
            if legacy_params_file is not None and legacy_params_file.exists():
                params_file = legacy_params_file
            else:
                logger.info("No previous session found")
                return None

        with open(params_file, 'r', encoding='utf-8') as f:
            session_data = json.load(f)

        current_version = int(CONFIG.get('session_version', 1))
        version = int(session_data.get('session_version', 1))
        if version < current_version:
            logger.info("Session data version %s -> %s", version, current_version)

        session_data, migrated = migrate_session_data(session_data, current_version)

        if legacy_params_file and params_file == legacy_params_file:
            # Migrate to preferred location for faster future loads.
            try:
                _atomic_write_json(CONFIG['params_temp_file'], session_data)
                logger.info("Migrated session parameters to %s", CONFIG['params_temp_file'])
            except Exception as exc:
                logger.warning("Failed to persist migrated session parameters: %s", exc)
        elif migrated:
            try:
                _atomic_write_json(CONFIG['params_temp_file'], session_data)
                logger.info("Updated session parameters to version %s", current_version)
            except Exception:
                logger.exception("Failed to persist migrated session parameters")
        
        logger.info("Session parameters loaded from %s", params_file)
        logger.info("Previous algorithm: %s", session_data.get('algorithm', 'UMAP'))
        logger.info("Previous group: %s", session_data.get('group_col', 'Province'))
        return session_data
    except Exception as e:
        logger.exception("Failed to load session parameters: %s", e)
        return None


def clear_session_params() -> bool:
    """Clear saved session parameters"""
    try:
        params_file = CONFIG['params_temp_file']
        if params_file.exists():
            params_file.unlink()
            logger.info("Session parameters cleared")
            return True
    except Exception as e:
        logger.exception("Failed to clear session parameters: %s", e)
    return False


def get_temp_dir_size() -> float:
    """Get size of temp directory in MB"""
    try:
        total_size = 0
        for item in CONFIG['temp_dir'].iterdir():
            if item.is_file():
                total_size += item.stat().st_size
        return total_size / (1024 * 1024)  # Convert to MB
    except Exception:
        return 0
