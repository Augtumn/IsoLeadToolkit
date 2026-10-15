"""
Session Management - Save and Load Algorithm Parameters
Handles persistence of last used parameters across program sessions
"""
from __future__ import annotations

import json
import logging
from typing import Any

from ..config import CONFIG
from ..persistence.atomic import atomic_write_json

logger = logging.getLogger(__name__)


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
    parent_groups: dict[str, list[str]] | None = None,
    parent_shape_map: dict[str, str] | None = None,
    group_decomposition: dict[str, str] | None = None,
    plot_panels: list[str] | None = None,
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
            'ui_theme': ui_theme,
            'parent_groups': {
                str(k): list(v or []) for k, v in (parent_groups or {}).items()
            },
            'parent_shape_map': {
                str(k): str(v) for k, v in (parent_shape_map or {}).items()
            },
            'group_decomposition': {
                str(k): str(v) for k, v in (group_decomposition or {}).items()
            },
            'plot_panels': [str(panel) for panel in list(plot_panels or [])],
        }

        logger.debug("Saving session params. Tooltip columns: %s", tooltip_columns)

        atomic_write_json(CONFIG['params_temp_file'], session_data)
        logger.info("Session parameters saved to %s", CONFIG['params_temp_file'])
        return True
    except Exception as exc:
        logger.exception("Failed to save session parameters: %s", exc)
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
        if not params_file.exists():
            logger.info("No previous session found")
            return None

        with open(params_file, 'r', encoding='utf-8') as f:
            session_data = json.load(f)

        current_version = int(CONFIG.get('session_version', 1))
        version = int(session_data.get('session_version', 1))
        if version > current_version:
            # A file from a FUTURE app version may carry incompatible
            # structure; refuse to load it instead of guessing.
            logger.warning(
                "Session version %s is newer than supported %s; ignoring session",
                version,
                current_version,
            )
            return None
        logger.info("Session parameters loaded from %s", params_file)
        logger.info("Previous algorithm: %s", session_data.get('algorithm', 'UMAP'))
        logger.info("Previous group: %s", session_data.get('group_col', 'Province'))
        return session_data
    except Exception as exc:
        logger.exception("Failed to load session parameters: %s", exc)
        return None


def clear_session_params() -> bool:
    """Clear saved session parameters"""
    try:
        params_file = CONFIG['params_temp_file']
        if params_file.exists():
            params_file.unlink()
            logger.info("Session parameters cleared")
            return True
    except Exception as exc:
        logger.exception("Failed to clear session parameters: %s", exc)
    return False


def get_temp_dir_size() -> float:
    """Get size of temp directory in MB"""
    try:
        total_size = 0
        for item in CONFIG['temp_dir'].iterdir():
            if item.is_file():
                total_size += item.stat().st_size
        return total_size / (1024 * 1024)  # Convert to MB
    except Exception as exc:
        logger.warning("Cannot size temp directory, reporting 0 MB: %s", exc)
        return 0
