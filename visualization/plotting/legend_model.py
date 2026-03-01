"""Legend model helpers shared by in-plot and panel legends."""
from __future__ import annotations

from core import app_state
from visualization.line_styles import resolve_line_style
from .geo import (
    get_plumbotectonics_group_entries,
    get_plumbotectonics_group_palette,
    get_overlay_default_color,
)


# Maps overlay style_key → app_state toggle attribute name
OVERLAY_TOGGLE_MAP: dict[str, str] = {
    'model_curve': 'show_model_curves',
    'plumbotectonics_curve': 'show_plumbotectonics_curves',
    'paleoisochron': 'show_paleoisochrons',
    'model_age_line': 'show_model_age_lines',
    'isochron': 'show_isochrons',
    'growth_curve': 'show_growth_curves',
}


def normalize_render_mode(mode: str | None) -> str:
    value = str(mode or '').strip()
    if value in ('PB_MODELS_76', 'PB_MODELS_86'):
        return 'PB_EVOL_76' if value.endswith('_76') else 'PB_EVOL_86'
    if value in ('ISOCHRON1', 'ISOCHRON2'):
        return 'PB_EVOL_76' if value.endswith('1') else 'PB_EVOL_86'
    return value


def group_legend_items(
    palette: dict[str, str] | None = None,
    marker_map: dict[str, str] | None = None,
    visible_groups: set | list | None = None,
    all_groups: list[str] | None = None,
) -> list[dict]:
    """Return group legend entries.

    Each entry: ``{'type': 'group', 'label', 'color', 'marker', 'visible'}``
    """
    _palette = palette if palette is not None else getattr(app_state, 'current_palette', {})
    _marker_map = marker_map if marker_map is not None else getattr(app_state, 'group_marker_map', {})
    _visible = set(visible_groups) if visible_groups is not None else None
    groups = all_groups if all_groups is not None else list(getattr(app_state, 'available_groups', []))
    default_marker = getattr(app_state, 'plot_marker_shape', 'o')

    entries: list[dict] = []
    for group in groups:
        entries.append({
            'type': 'group',
            'label': str(group),
            'color': _palette.get(group, '#94a3b8'),
            'marker': _marker_map.get(group, default_marker),
            'visible': _visible is None or group in _visible,
        })
    return entries


def overlay_legend_items(
    render_mode: str | None = None,
    actual_algorithm: str | None = None,
    include_disabled: bool = False
) -> list[dict]:
    """Return overlay legend entries for the current render mode.

    Each entry: ``{'type': 'overlay', 'label_key', 'style_key', 'fallback', 'default_color'}``
    """
    mode = actual_algorithm or normalize_render_mode(render_mode or getattr(app_state, 'render_mode', ''))
    is_pb_evol = mode in ('PB_EVOL_76', 'PB_EVOL_86')
    is_plumb = mode in ('PLUMBOTECTONICS_76', 'PLUMBOTECTONICS_86')
    is_mu_kappa = mode in ('PB_MU_AGE', 'PB_KAPPA_AGE')

    entries: list[dict] = []
    if is_pb_evol and (include_disabled or getattr(app_state, 'show_model_curves', True)):
        entries.append({
            'type': 'overlay',
            'label_key': 'Model Curves',
            'style_key': 'model_curve',
            'fallback': {
                'color': None,
                'linewidth': getattr(app_state, 'model_curve_width', 1.2),
                'linestyle': '-',
                'alpha': 0.8
            },
            'default_color': get_overlay_default_color('model_curve')
        })

    if is_plumb and (include_disabled or getattr(app_state, 'show_plumbotectonics_curves', True)):
        group_entries = get_plumbotectonics_group_entries()
        if group_entries:
            base_fallback = {
                'color': None,
                'linewidth': getattr(app_state, 'plumbotectonics_curve_width', 1.2),
                'linestyle': '-',
                'alpha': 0.85
            }
            base_style = resolve_line_style(app_state, 'plumbotectonics_curve', base_fallback)
            group_palette = get_plumbotectonics_group_palette()
            group_visibility = getattr(app_state, 'plumbotectonics_group_visibility', {}) or {}
            for entry in group_entries:
                if not include_disabled and not group_visibility.get(entry['style_key'], True):
                    continue
                group_name = entry['name']
                entries.append({
                    'type': 'overlay',
                    'label_key': group_name,
                    'style_key': entry['style_key'],
                    'fallback': dict(base_style),
                    'default_color': group_palette.get(entry['style_key'])
                })
        else:
            entries.append({
                'type': 'overlay',
                'label_key': 'Plumbotectonics Curves',
                'style_key': 'plumbotectonics_curve',
                'fallback': {
                    'color': None,
                    'linewidth': getattr(app_state, 'plumbotectonics_curve_width', 1.2),
                    'linestyle': '-',
                    'alpha': 0.85
                },
                'default_color': '#64748b'
            })

    if (is_pb_evol or is_plumb or is_mu_kappa) and (
        include_disabled or getattr(app_state, 'show_paleoisochrons', True)
    ):
        entries.append({
            'type': 'overlay',
            'label_key': 'Paleoisochrons',
            'style_key': 'paleoisochron',
            'fallback': {
                'color': None,
                'linewidth': getattr(app_state, 'paleoisochron_width', 0.9),
                'linestyle': '--',
                'alpha': 0.85
            },
            'default_color': get_overlay_default_color('paleoisochron')
        })

    if is_pb_evol and (include_disabled or getattr(app_state, 'show_model_age_lines', True)):
        entries.append({
            'type': 'overlay',
            'label_key': 'Model Age Lines',
            'style_key': 'model_age_line',
            'fallback': {
                'color': None,
                'linewidth': getattr(app_state, 'model_age_line_width', 0.7),
                'linestyle': '-',
                'alpha': 0.7
            },
            'default_color': get_overlay_default_color('model_age_line')
        })

    if is_pb_evol and (
        include_disabled
        or getattr(app_state, 'show_isochrons', False)
        or getattr(app_state, 'selected_isochron_data', None) is not None
    ):
        entries.append({
            'type': 'overlay',
            'label_key': 'Isochron Fits',
            'style_key': 'isochron',
            'fallback': {
                'color': None,
                'linewidth': getattr(app_state, 'isochron_line_width', 1.5),
                'linestyle': '-',
                'alpha': 0.8
            },
            'default_color': '#64748b'
        })

    return entries


__all__ = [
    "normalize_render_mode",
    "overlay_legend_items",
    "group_legend_items",
    "OVERLAY_TOGGLE_MAP",
]
