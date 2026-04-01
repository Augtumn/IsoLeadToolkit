"""Session payload normalization and migration helpers."""
from __future__ import annotations

from typing import Any

from .config import CONFIG


def _normalize_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, (tuple, set)):
        return list(value)
    if isinstance(value, str):
        return [value]
    return []


def _normalize_algorithm(value: Any) -> str:
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


def _normalize_render_mode(value: Any, algorithm: str, plot_mode: Any) -> str:
    if value:
        value_str = str(value).strip()
        if value_str in ('UMAP', 'tSNE', 'PCA', 'RobustPCA', '2D', '3D'):
            return value_str
    if plot_mode:
        plot_mode_str = str(plot_mode).strip()
        if plot_mode_str in ('2D', '3D'):
            return plot_mode_str
    return algorithm or 'UMAP'


def _merge_params(defaults: dict[str, Any], override: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(override, dict):
        override = {}
    merged = defaults.copy()
    merged.update(override)
    return merged


def migrate_session_data(session_data: Any, current_version: int) -> tuple[dict[str, Any], bool]:
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