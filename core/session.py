"""
Session Management - Save and Load Algorithm Parameters
Handles persistence of last used parameters across program sessions
"""
import json
import logging

from .config import CONFIG

logger = logging.getLogger(__name__)


def _normalize_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, (tuple, set)):
        return list(value)
    if isinstance(value, str):
        return [value]
    return []


def _normalize_algorithm(value):
    if not value:
        return 'UMAP'
    value_str = str(value).strip()
    lowered = value_str.lower()
    if lowered in ('tsne', 't-sne', 't_sne', 'tsne '):
        return 'tSNE'
    if lowered in ('pca',):
        return 'PCA'
    if lowered in ('robustpca', 'robust_pca', 'robust-pca', 'robust pca'):
        return 'RobustPCA'
    if lowered in ('v1v2', 'v1_v2'):
        return 'V1V2'
    return value_str if value_str else 'UMAP'


def _normalize_render_mode(value, algorithm, plot_mode):
    if value:
        value_str = str(value).strip()
        if value_str in ('UMAP', 'tSNE', 'PCA', 'RobustPCA', '2D', '3D'):
            return value_str
    if plot_mode:
        plot_mode_str = str(plot_mode).strip()
        if plot_mode_str in ('2D', '3D'):
            return plot_mode_str
    return algorithm or 'UMAP'


def _merge_params(defaults, override):
    if not isinstance(override, dict):
        override = {}
    merged = defaults.copy()
    merged.update(override)
    return merged


def _migrate_session_data(session_data, current_version):
    if not isinstance(session_data, dict):
        session_data = {}
    migrated = dict(session_data)
    changed = False

    algorithm = _normalize_algorithm(migrated.get('algorithm'))
    if migrated.get('algorithm') != algorithm:
        migrated['algorithm'] = algorithm
        changed = True

    migrated_umap = _merge_params(CONFIG.get('umap_params', {}), migrated.get('umap_params'))
    if migrated.get('umap_params') != migrated_umap:
        migrated['umap_params'] = migrated_umap
        changed = True

    migrated_tsne = _merge_params(CONFIG.get('tsne_params', {}), migrated.get('tsne_params'))
    if migrated.get('tsne_params') != migrated_tsne:
        migrated['tsne_params'] = migrated_tsne
        changed = True

    point_size = migrated.get('point_size', CONFIG.get('point_size'))
    try:
        point_size = float(point_size)
        if point_size.is_integer():
            point_size = int(point_size)
    except Exception:
        point_size = CONFIG.get('point_size')
    if migrated.get('point_size') != point_size:
        migrated['point_size'] = point_size
        changed = True

    normalized_group_cols = _normalize_list(migrated.get('group_cols'))
    if migrated.get('group_cols') != normalized_group_cols:
        migrated['group_cols'] = normalized_group_cols
        changed = True

    normalized_data_cols = _normalize_list(migrated.get('data_cols'))
    if migrated.get('data_cols') != normalized_data_cols:
        migrated['data_cols'] = normalized_data_cols
        changed = True

    normalized_2d_cols = _normalize_list(migrated.get('selected_2d_cols'))
    if migrated.get('selected_2d_cols') != normalized_2d_cols:
        migrated['selected_2d_cols'] = normalized_2d_cols
        changed = True

    normalized_3d_cols = _normalize_list(migrated.get('selected_3d_cols'))
    if migrated.get('selected_3d_cols') != normalized_3d_cols:
        migrated['selected_3d_cols'] = normalized_3d_cols
        changed = True

    tooltip_value = migrated.get('tooltip_columns')
    normalized_tooltip = _normalize_list(tooltip_value) if tooltip_value is not None else None
    if tooltip_value != normalized_tooltip:
        migrated['tooltip_columns'] = normalized_tooltip
        changed = True

    render_mode = _normalize_render_mode(migrated.get('render_mode'), algorithm, migrated.get('plot_mode'))
    if migrated.get('render_mode') != render_mode:
        migrated['render_mode'] = render_mode
        changed = True

    if 'plot_mode' in migrated:
        migrated.pop('plot_mode', None)
        changed = True

    if 'session_version' not in migrated or int(migrated.get('session_version', 1)) != current_version:
        migrated['session_version'] = current_version
        changed = True

    if 'ui_theme' not in migrated:
        migrated['ui_theme'] = None
        changed = True
    if 'language' not in migrated:
        migrated['language'] = None
        changed = True

    return migrated, changed


def save_session_params(algorithm, umap_params, tsne_params, point_size, group_col,
                        group_cols=None, data_cols=None, file_path=None, sheet_name=None,
                        render_mode='UMAP', selected_2d_cols=None, selected_3d_cols=None,
                        language=None, tooltip_columns=None, ui_theme=None):
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

        with open(CONFIG['params_temp_file'], 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
        
        logger.info("Session parameters saved to %s", CONFIG['params_temp_file'])
        return True
    except Exception as e:
        logger.exception("Failed to save session parameters: %s", e)
        return False


def load_session_params():
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

        session_data, migrated = _migrate_session_data(session_data, current_version)

        if legacy_params_file and params_file == legacy_params_file:
            # Migrate to preferred location for faster future loads.
            try:
                with open(CONFIG['params_temp_file'], 'w', encoding='utf-8') as out:
                    json.dump(session_data, out, indent=2, ensure_ascii=False)
                logger.info("Migrated session parameters to %s", CONFIG['params_temp_file'])
            except Exception:
                pass
        elif migrated:
            try:
                with open(CONFIG['params_temp_file'], 'w', encoding='utf-8') as out:
                    json.dump(session_data, out, indent=2, ensure_ascii=False)
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


def clear_session_params():
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


def get_temp_dir_size():
    """Get size of temp directory in MB"""
    try:
        total_size = 0
        for item in CONFIG['temp_dir'].iterdir():
            if item.is_file():
                total_size += item.stat().st_size
        return total_size / (1024 * 1024)  # Convert to MB
    except Exception:
        return 0
