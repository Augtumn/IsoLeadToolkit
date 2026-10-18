"""Action dispatch handlers for StateStore.

This module is extracted from store.py to keep the store class under 800 lines.
The single entry point is ``dispatch_action(store, action)`` — it receives the
full StateStore instance so it can access ``store._snapshot`` and ``store._state``.
"""

from __future__ import annotations

from core.render_modes import algorithm_modes

import logging
from typing import Any

from ..config import CONFIG
from ..legend_state import DEFAULT_LEGEND_FRAME_ALPHA
from ._normalizers import (
    _normalize_panel_legends,
    _normalize_active_subset_indices,
    _normalize_adjust_text_iter_lim,
    _normalize_adjust_text_pair,
    _normalize_adjust_text_time_lim,
    _normalize_algorithm_params,
    _normalize_bw_adjust,
    _normalize_color,
    _normalize_clip_bound,
    _normalize_kde_thresh,
    _normalize_cut,
    _normalize_export_options,
    _normalize_font_name,
    _normalize_grid_linestyle,
    _normalize_gridsize,
    _normalize_kde_auto_bandwidth_method,
    _normalize_kde_bandwidth,
    _normalize_kde_kernel,
    _normalize_locked_axis_limits,
    _normalize_marginal_size,
    _normalize_max_points,
    _normalize_pca_component_indices,
    _normalize_plot_dpi,
    _normalize_plot_font_sizes,
    _normalize_plot_marker_alpha,
    _normalize_plot_marker_size,
    _normalize_style_linewidth,
    _normalize_ternary_boundary_percent,
    _normalize_ternary_limit_anchor,
    _normalize_ternary_limit_mode,
    _normalize_ternary_manual_limits,
    _normalize_ternary_render_margin,
    _normalize_text_pad,
    _normalize_text_weight,
    _normalize_tick_direction,
    _normalize_tick_length,
    _normalize_unit_interval,
    _normalize_visible_groups,
    _to_index_set,
)
from .coercers import DEFAULT_CONFIDENCE_LEVEL

logger = logging.getLogger(__name__)


def _recompute_paleoisochron_ages(snapshot: dict) -> None:
    """Derive the paleoisochron ages from the three controls, so the pair cannot disagree.

    The ages are not a fact of their own: they are min/max/step written out. Recomputing here means changing any of
    the three keeps the list true, which the panel used to do for the step alone.
    """
    from ..overlay_state import paleoisochron_age_list

    snapshot["paleoisochron_ages"] = paleoisochron_age_list(
        snapshot.get("paleoisochron_min_age", 0),
        snapshot.get("paleoisochron_max_age", 3000),
        snapshot.get("paleoisochron_step", 1000),
    )



#: The actions whose whole effect is one snapshot field, declared rather than written as a branch each: 141 of the
#: 180 branches used to be `store._snapshot["field"] = <expression>`, and the expression is the setter. The five
#: that read the current snapshot as their default stay in the chain, where they can see the store.
_SIMPLE_SETTERS: dict[str, tuple[str, Callable[[dict[str, Any]], object]]] = {
    'SET_UMAP_PARAMS': ('umap_params', lambda action: _normalize_algorithm_params(action.get('params'))),
    'SET_TSNE_PARAMS': ('tsne_params', lambda action: _normalize_algorithm_params(action.get('params'))),
    'SET_PCA_PARAMS': ('pca_params', lambda action: _normalize_algorithm_params(action.get('params'))),
    'SET_ROBUST_PCA_PARAMS': ('robust_pca_params', lambda action: _normalize_algorithm_params(action.get('params'))),
    'SET_ML_PARAMS': ('ml_params', lambda action: _normalize_algorithm_params(action.get('params'))),
    'SET_SILVERQUEST_PARAMS': ('silverquest_params', lambda action: _normalize_algorithm_params(action.get('params'))),
    'SET_V1V2_PARAMS': ('v1v2_params', lambda action: _normalize_algorithm_params(action.get('params'))),
    'SET_PLOT_STYLE_GRID': ('plot_style_grid', lambda action: bool(action.get('enabled', False))),
    'SET_PLOT_MARKER_SIZE': ('plot_marker_size', lambda action: _normalize_plot_marker_size(action.get('size', 60))),
    'SET_PLOT_MARKER_ALPHA': ('plot_marker_alpha', lambda action: _normalize_plot_marker_alpha(action.get('alpha', 0.8))),
    'SET_SHOW_PLOT_TITLE': ('show_plot_title', lambda action: bool(action.get('show', False))),
    'SET_PLOT_DPI': ('plot_dpi', lambda action: _normalize_plot_dpi(action.get('dpi', 130))),
    'SET_CUSTOM_PRIMARY_FONT': ('custom_primary_font', lambda action: _normalize_font_name(action.get('font_name', ''))),
    'SET_CUSTOM_CJK_FONT': ('custom_cjk_font', lambda action: _normalize_font_name(action.get('font_name', ''))),
    'SET_PLOT_FONT_SIZES': ('plot_font_sizes', lambda action: _normalize_plot_font_sizes(action.get('sizes'))),
    'SET_PLOT_FACECOLOR': ('plot_facecolor', lambda action: _normalize_color(action.get('color', '#ffffff'), '#ffffff')),
    'SET_AXES_FACECOLOR': ('axes_facecolor', lambda action: _normalize_color(action.get('color', '#ffffff'), '#ffffff')),
    'SET_GRID_COLOR': ('grid_color', lambda action: _normalize_color(action.get('color', '#e2e8f0'), '#e2e8f0')),
    'SET_GRID_LINEWIDTH': ('grid_linewidth', lambda action: _normalize_style_linewidth(action.get('width', 0.6), default=0.6)),
    'SET_GRID_ALPHA': ('grid_alpha', lambda action: _normalize_unit_interval(action.get('alpha', 0.7), default=0.7)),
    'SET_GRID_LINESTYLE': ('grid_linestyle', lambda action: _normalize_grid_linestyle(action.get('linestyle', '--'))),
    'SET_TICK_DIRECTION': ('tick_direction', lambda action: _normalize_tick_direction(action.get('direction', 'out'))),
    'SET_TICK_COLOR': ('tick_color', lambda action: _normalize_color(action.get('color', '#1f2937'), '#1f2937')),
    'SET_TICK_LENGTH': ('tick_length', lambda action: _normalize_tick_length(action.get('length', 4.0), default=4.0)),
    'SET_TICK_WIDTH': ('tick_width', lambda action: _normalize_style_linewidth(action.get('width', 0.8), default=0.8)),
    'SET_AXIS_LINEWIDTH': ('axis_linewidth', lambda action: _normalize_style_linewidth(action.get('width', 1.0), default=1.0)),
    'SET_AXIS_LINE_COLOR': ('axis_line_color', lambda action: _normalize_color(action.get('color', '#1f2937'), '#1f2937')),
    'SET_MINOR_TICKS': ('minor_ticks', lambda action: bool(action.get('enabled', False))),
    'SET_MINOR_TICK_LENGTH': ('minor_tick_length', lambda action: _normalize_tick_length(action.get('length', 2.5), default=2.5)),
    'SET_MINOR_TICK_WIDTH': ('minor_tick_width', lambda action: _normalize_style_linewidth(action.get('width', 0.6), default=0.6)),
    'SET_SHOW_TOP_SPINE': ('show_top_spine', lambda action: bool(action.get('show', True))),
    'SET_SHOW_RIGHT_SPINE': ('show_right_spine', lambda action: bool(action.get('show', True))),
    'SET_MINOR_GRID': ('minor_grid', lambda action: bool(action.get('enabled', False))),
    'SET_MINOR_GRID_COLOR': ('minor_grid_color', lambda action: _normalize_color(action.get('color', '#e2e8f0'), '#e2e8f0')),
    'SET_MINOR_GRID_LINEWIDTH': ('minor_grid_linewidth', lambda action: _normalize_style_linewidth(action.get('width', 0.4), default=0.4)),
    'SET_MINOR_GRID_ALPHA': ('minor_grid_alpha', lambda action: _normalize_unit_interval(action.get('alpha', 0.4), default=0.4)),
    'SET_MINOR_GRID_LINESTYLE': ('minor_grid_linestyle', lambda action: _normalize_grid_linestyle(action.get('linestyle', ':'))),
    'SET_SCATTER_SHOW_EDGE': ('scatter_show_edge', lambda action: bool(action.get('show', True))),
    'SET_SCATTER_EDGECOLOR': ('scatter_edgecolor', lambda action: _normalize_color(action.get('color', '#1e293b'), '#1e293b')),
    'SET_SCATTER_EDGEWIDTH': ('scatter_edgewidth', lambda action: _normalize_style_linewidth(action.get('width', 0.4), default=0.4)),
    'SET_LABEL_COLOR': ('label_color', lambda action: _normalize_color(action.get('color', '#1f2937'), '#1f2937')),
    'SET_LABEL_WEIGHT': ('label_weight', lambda action: _normalize_text_weight(action.get('weight', 'normal'), default='normal')),
    'SET_LABEL_PAD': ('label_pad', lambda action: _normalize_text_pad(action.get('pad', 6.0), default=6.0, max_value=60.0)),
    'SET_TITLE_COLOR': ('title_color', lambda action: _normalize_color(action.get('color', '#111827'), '#111827')),
    'SET_TITLE_WEIGHT': ('title_weight', lambda action: _normalize_text_weight(action.get('weight', 'bold'), default='bold')),
    'SET_TITLE_PAD': ('title_pad', lambda action: _normalize_text_pad(action.get('pad', 20.0), default=20.0, max_value=80.0)),
    'SET_LEGEND_FRAME_ON': ('legend_frame_on', lambda action: bool(action.get('enabled', True))),
    'SET_LEGEND_FRAME_ALPHA': ('legend_frame_alpha', lambda action: _normalize_unit_interval(action.get('alpha', DEFAULT_LEGEND_FRAME_ALPHA), default=DEFAULT_LEGEND_FRAME_ALPHA)),
    'SET_LEGEND_FRAME_FACECOLOR': ('legend_frame_facecolor', lambda action: _normalize_color(action.get('color', '#ffffff'), '#ffffff')),
    'SET_LEGEND_FRAME_EDGECOLOR': ('legend_frame_edgecolor', lambda action: _normalize_color(action.get('color', '#cbd5f5'), '#cbd5f5')),
    'SET_ADJUST_TEXT_FORCE_TEXT': ('adjust_text_force_text', lambda action: _normalize_adjust_text_pair(action.get('force', (0.8, 1.0)), default=(0.8, 1.0), min_value=0.0, max_value=3.0)),
    'SET_ADJUST_TEXT_FORCE_STATIC': ('adjust_text_force_static', lambda action: _normalize_adjust_text_pair(action.get('force', (0.4, 0.6)), default=(0.4, 0.6), min_value=0.0, max_value=3.0)),
    'SET_ADJUST_TEXT_EXPAND': ('adjust_text_expand', lambda action: _normalize_adjust_text_pair(action.get('expand', (1.08, 1.2)), default=(1.08, 1.2), min_value=1.0, max_value=2.5)),
    'SET_ADJUST_TEXT_ITER_LIM': ('adjust_text_iter_lim', lambda action: _normalize_adjust_text_iter_lim(action.get('iter_lim', 120))),
    'SET_ADJUST_TEXT_TIME_LIM': ('adjust_text_time_lim', lambda action: _normalize_adjust_text_time_lim(action.get('time_lim', 0.25))),
    'SET_SHOW_KDE': ('show_kde', lambda action: bool(action.get('show', False))),
    'SET_SHOW_MARGINAL_KDE': ('show_marginal_kde', lambda action: bool(action.get('show', False))),
    'SET_SHOW_EQUATION_OVERLAYS': ('show_equation_overlays', lambda action: bool(action.get('show', False))),
    'SET_GEO_MODEL_NAME': ('geo_model_name', lambda action: str(action.get('model_name', 'Stacey & Kramers (2nd Stage)'))),
    'SET_PALEO_LABEL_REFRESHING': ('paleo_label_refreshing', lambda action: bool(action.get('refreshing', False))),
    'SET_OVERLAY_LABEL_REFRESHING': ('overlay_label_refreshing', lambda action: bool(action.get('refreshing', False))),
    'SET_OVERLAY_CURVE_LABEL_DATA': ('overlay_curve_label_data', lambda action: list(action.get('data') or [])),
    'SET_PALEOISOCHRON_LABEL_DATA': ('paleoisochron_label_data', lambda action: list(action.get('data') or [])),
    'SET_PLUMBOTECTONICS_LABEL_DATA': ('plumbotectonics_label_data', lambda action: list(action.get('data') or [])),
    'SET_PLUMBOTECTONICS_ISOAGE_LABEL_DATA': ('plumbotectonics_isoage_label_data', lambda action: list(action.get('data') or [])),
    'SET_OVERLAY_ARTISTS': ('overlay_artists', lambda action: dict(action.get('artists') or {})),
    'SET_SELECTED_ISOCHRON_DATA': ('selected_isochron_data', lambda action: action.get('data')),
    'SET_EMBEDDING_TASK_TOKEN': ('embedding_task_token', lambda action: int(action.get('task_token', 0))),
    'SET_EMBEDDING_TASK_RUNNING': ('embedding_task_running', lambda action: bool(action.get('running', False))),
    'SET_MARGINAL_AXES': ('marginal_axes', lambda action: action.get('marginal_axes')),
    'SET_ADJUST_TEXT_IN_PROGRESS': ('adjust_text_in_progress', lambda action: bool(action.get('in_progress', False))),
    'SET_CONFIDENCE_LEVEL': ('confidence_level', lambda action: float(action.get('level', DEFAULT_CONFIDENCE_LEVEL))),
    'SET_CURRENT_PALETTE': ('current_palette', lambda action: dict(action.get('palette') or {})),
    'SET_GROUP_MARKER_MAP': ('group_marker_map', lambda action: dict(action.get('marker_map') or {})),
    'SET_CURRENT_PLOT_TITLE': ('current_plot_title', lambda action: str(action.get('title', ''))),
    'SET_SHOW_ISOCHRONS': ('show_isochrons', lambda action: bool(action.get('show', False))),
    'SET_ISOCHRON_RESULTS': ('isochron_results', lambda action: dict(action.get('results') or {})),
    'SET_PLUMBOTECTONICS_GROUP_VISIBILITY': ('plumbotectonics_group_visibility', lambda action: dict(action.get('visibility') or {})),
    'SET_USE_REAL_AGE_FOR_MU_KAPPA': ('use_real_age_for_mu_kappa', lambda action: bool(action.get('enabled', False))),
    'SET_MU_KAPPA_AGE_COL': ('mu_kappa_age_col', lambda action: action.get('column')),
    'SET_PLUMBOTECTONICS_VARIANT': ('plumbotectonics_variant', lambda action: str(action.get('variant', '0'))),
    'SET_PALEOISOCHRON_AGES': ('paleoisochron_ages', lambda action: list(action.get('ages') or [])),
    'SET_DRAW_SELECTION_ELLIPSE': ('draw_selection_ellipse', lambda action: bool(action.get('enabled', False))),
    'SET_POINT_SIZE': ('point_size', lambda action: max(1, int(action.get('point_size', 60)))),
    'SET_SHOW_TOOLTIP': ('show_tooltip', lambda action: bool(action.get('show', False))),
    'SET_TOOLTIP_COLUMNS': ('tooltip_columns', lambda action: [str(col) for col in list(action.get('columns') or [])]),
    'SET_UI_THEME': ('ui_theme', lambda action: str(action.get('theme', 'Modern Light') or 'Modern Light')),
    'SET_LANGUAGE_CODE': ('language', lambda action: str(action.get('code'))),
    'SET_COLOR_SCHEME': ('color_scheme', lambda action: str(action.get('color_scheme'))),
    'SET_LEGEND_POSITION': ('legend_position', lambda action: action.get('position')),
    'SET_LEGEND_LOCATION': ('legend_location', lambda action: action.get('location')),
    'SET_LEGEND_DISPLAY_MODE': ('legend_display_mode', lambda action: str(action.get('mode', 'inline'))),
    'SET_LEGEND_COLUMNS': ('legend_columns', lambda action: int(action.get('columns', 0))),
    'SET_LEGEND_NUDGE_STEP': ('legend_nudge_step', lambda action: float(action.get('step', 0.02))),
    'SET_HIDDEN_GROUPS': ('hidden_groups', lambda action: set(action.get('groups') or set())),
    'SET_LINE_STYLES': ('line_styles', lambda action: dict(action.get('line_styles') or {})),
    'SET_SAVED_THEMES': ('saved_themes', lambda action: dict(action.get('themes') or {})),
    'SET_CUSTOM_PALETTES': ('custom_palettes', lambda action: dict(action.get('palettes') or {})),
    'SET_CUSTOM_SHAPE_SETS': ('custom_shape_sets', lambda action: dict(action.get('shape_sets') or {})),
    'SET_LEGEND_ITEM_ORDER': ('legend_item_order', lambda action: list(action.get('order') or [])),
    'SET_MIXING_ENDMEMBERS': ('mixing_endmembers', lambda action: dict(action.get('mapping') or {})),
    'SET_MIXING_MIXTURES': ('mixing_mixtures', lambda action: dict(action.get('mapping') or {})),
    'SET_TERNARY_RANGES': ('ternary_ranges', lambda action: dict(action.get('ranges') or {})),
    'SET_ML_LAST_RESULT': ('ml_last_result', lambda action: action.get('result')),
    'SET_ML_LAST_MODEL_META': ('ml_last_model_meta', lambda action: action.get('meta')),
    'SET_PRESERVE_IMPORT_RENDER_MODE': ('preserve_import_render_mode', lambda action: bool(action.get('enabled', False))),
    'SET_ACTIVE_SUBSET_INDICES': ('active_subset_indices', lambda action: _normalize_active_subset_indices(action.get('indices'))),
    'SET_SELECTION_MODE': ('selection_mode', lambda action: bool(action.get('enabled', False))),
    'SET_FILE_PATH': ('file_path', lambda action: str(action.get('file_path'))),
    'SET_SHEET_NAME': ('sheet_name', lambda action: action.get('sheet_name')),
    'SET_DATA_VERSION': ('data_version', lambda action: int(action.get('version', 0))),
    'SET_STANDARDIZE_DATA': ('standardize_data', lambda action: bool(action.get('enabled', False))),
    'SET_INITIAL_RENDER_DONE': ('initial_render_done', lambda action: bool(action.get('done', False))),
    'SET_PCA_COMPONENT_INDICES': ('pca_component_indices', lambda action: _normalize_pca_component_indices(action.get('indices'))),
    'SET_TERNARY_AUTO_ZOOM': ('ternary_auto_zoom', lambda action: bool(action.get('enabled', False))),
    'SET_AXIS_SCALE_LOCKED': ('axis_scale_locked', lambda action: bool(action.get('enabled', False))),
    'SET_LOCKED_AXIS_LIMITS': ('locked_axis_limits', lambda action: _normalize_locked_axis_limits(action.get('limits'))),
    'SET_TERNARY_LIMIT_MODE': ('ternary_limit_mode', lambda action: _normalize_ternary_limit_mode(action.get('mode'))),
    'SET_TERNARY_LIMIT_ANCHOR': ('ternary_limit_anchor', lambda action: _normalize_ternary_limit_anchor(action.get('anchor'))),
    'SET_TERNARY_BOUNDARY_PERCENT': ('ternary_boundary_percent', lambda action: _normalize_ternary_boundary_percent(action.get('percent'))),
    'SET_TERNARY_MANUAL_LIMITS_ENABLED': ('ternary_manual_limits_enabled', lambda action: bool(action.get('enabled', False))),
    'SET_TERNARY_MANUAL_LIMITS': ('ternary_manual_limits', lambda action: _normalize_ternary_manual_limits(action.get('limits'))),
    'SET_TERNARY_RENDER_MARGIN': ('ternary_render_margin', lambda action: _normalize_ternary_render_margin(action.get('margin'))),
    'SET_TERNARY_STRETCH_MODE': ('ternary_stretch_mode', lambda action: str(action.get('mode', 'power') or 'power')),
    'SET_TERNARY_STRETCH': ('ternary_stretch', lambda action: bool(action.get('stretch', False))),
    'SET_TERNARY_FACTORS': ('ternary_factors', lambda action: list(action.get('factors') or [1.0, 1.0, 1.0])),
    'SET_MODEL_CURVE_WIDTH': ('model_curve_width', lambda action: float(action.get('width', 1.2))),
    'SET_PLUMBOTECTONICS_CURVE_WIDTH': ('plumbotectonics_curve_width', lambda action: float(action.get('width', 1.2))),
    'SET_PALEOISOCHRON_WIDTH': ('paleoisochron_width', lambda action: float(action.get('width', 0.9))),
    'SET_MODEL_AGE_LINE_WIDTH': ('model_age_line_width', lambda action: float(action.get('width', 0.7))),
    'SET_ISOCHRON_LINE_WIDTH': ('isochron_line_width', lambda action: float(action.get('width', 1.5))),
    'SET_SELECTED_ISOCHRON_LINE_WIDTH': ('selected_isochron_line_width', lambda action: float(action.get('width', 2.0))),
    'SET_ISOCHRON_LABEL_OPTIONS': ('isochron_label_options', lambda action: dict(action.get('options') or {})),
    'SET_EQUATION_OVERLAYS': ('equation_overlays', lambda action: list(action.get('overlays') or [])),
    'SET_VISIBLE_GROUPS': ('visible_groups', lambda action: _normalize_visible_groups(action.get('groups'))),
    'SET_PARENT_GROUPS': ('parent_groups', lambda action: {str(k): [str(v) for v in list(vs or [])] for k, vs in (action.get('mapping') or {}).items()}),
    'SET_GROUP_DECOMPOSITION': ('group_decomposition', lambda action: {str(k): str(v) for k, v in (action.get('mapping') or {}).items()}),
    'SET_PLOT_PANELS': ('plot_panels', lambda action: [str(p) for p in list(action.get('panels') or [])]),
    'SET_PLOT_PANEL_LEGENDS': ('plot_panel_legends', lambda action: _normalize_panel_legends(action.get('legends'))),
    'SET_PARENT_SHAPE_MAP': ('parent_shape_map', lambda action: {str(k): str(v) for k, v in (action.get('mapping') or {}).items()}),
    'SET_PARAM_PRESETS': ('param_presets', lambda action: {str(k): dict(v or {}) for k, v in (action.get('presets') or {}).items()}),
}



def dispatch_action(store: Any, action: dict[str, Any]) -> None:
    """Apply *action* mutations to *store._snapshot* in-place.

    This function contains the full if/elif chain that was previously the body
    of ``StateStore.dispatch()``.  It does **not** call ``_sync_state()`` or
    return a snapshot — those responsibilities remain in the store method.
    """
    action_type = str(action.get("type", "")).upper().strip()

    simple = _SIMPLE_SETTERS.get(action_type)
    if simple is not None:
        field, setter = simple
        store._snapshot[field] = setter(action)
        return

    if action_type == "SET_RENDER_MODE":
        render_mode = str(action.get("render_mode", "UMAP") or "UMAP")
        store._snapshot["render_mode"] = render_mode
        if render_mode in algorithm_modes():
            store._snapshot["algorithm"] = render_mode

    elif action_type == "SET_ALGORITHM":
        algorithm = str(action.get("algorithm", "UMAP") or "UMAP")
        store._snapshot["algorithm"] = algorithm
        # For embedding algorithms the render mode IS the algorithm; without
        # this the sync step overwrote algorithm from render_mode and
        # set_algorithm() was silently a no-op.
        if algorithm in algorithm_modes():
            store._snapshot["render_mode"] = algorithm



































































    elif action_type == "SET_LAST_EMBEDDING":
        store._snapshot["last_embedding"] = action.get("embedding")
        store._snapshot["last_embedding_type"] = str(action.get("embedding_type", "") or "")





    elif action_type == "SET_PCA_DIAGNOSTICS":
        if "last_pca_variance" in action:
            store._snapshot["last_pca_variance"] = action.get("last_pca_variance")
        if "last_pca_components" in action:
            store._snapshot["last_pca_components"] = action.get("last_pca_components")
        if "current_feature_names" in action:
            store._snapshot["current_feature_names"] = action.get("current_feature_names")






    elif action_type == "SET_LAST_2D_COLS":
        columns = action.get("columns")
        store._snapshot["last_2d_cols"] = list(columns or []) if columns is not None else None

    elif action_type == "SET_SHOW_MODEL_CURVES":
        store._snapshot["show_model_curves"] = bool(
            action.get("show", store._snapshot.get("show_model_curves", True))
        )

    elif action_type == "SET_SHOW_PLUMBOTECTONICS_CURVES":
        store._snapshot["show_plumbotectonics_curves"] = bool(
            action.get("show", store._snapshot.get("show_plumbotectonics_curves", True))
        )

    elif action_type == "SET_SHOW_PALEOISOCHRONS":
        store._snapshot["show_paleoisochrons"] = bool(
            action.get("show", store._snapshot.get("show_paleoisochrons", True))
        )

    elif action_type == "SET_SHOW_MODEL_AGE_LINES":
        store._snapshot["show_model_age_lines"] = bool(
            action.get("show", store._snapshot.get("show_model_age_lines", True))
        )

    elif action_type == "SET_SHOW_GROWTH_CURVES":
        store._snapshot["show_growth_curves"] = bool(
            action.get("show", store._snapshot.get("show_growth_curves", True))
        )


    elif action_type == "SET_ISOCHRON_ERROR_COLUMNS":
        store._snapshot["isochron_error_mode"] = "columns"
        store._snapshot["isochron_sx_col"] = str(action.get("sx_col", "") or "")
        store._snapshot["isochron_sy_col"] = str(action.get("sy_col", "") or "")
        store._snapshot["isochron_rxy_col"] = str(action.get("rxy_col", "") or "")

    elif action_type == "SET_ISOCHRON_ERROR_FIXED":
        store._snapshot["isochron_error_mode"] = "fixed"
        store._snapshot["isochron_sx_value"] = float(action.get("sx_value", 0.001))
        store._snapshot["isochron_sy_value"] = float(action.get("sy_value", 0.001))
        store._snapshot["isochron_rxy_value"] = float(action.get("rxy_value", 0.0))






    elif action_type == "SET_PALEOISOCHRON_MIN_AGE":
        store._snapshot["paleoisochron_min_age"] = int(action.get("age", 0))
        _recompute_paleoisochron_ages(store._snapshot)

    elif action_type == "SET_PALEOISOCHRON_MAX_AGE":
        store._snapshot["paleoisochron_max_age"] = int(action.get("age", 3000))
        _recompute_paleoisochron_ages(store._snapshot)

    elif action_type == "SET_PALEOISOCHRON_STEP":
        store._snapshot["paleoisochron_step"] = int(action.get("step", 1000))
        _recompute_paleoisochron_ages(store._snapshot)



    elif action_type == "SET_MARGINAL_KDE_LAYOUT":
        top_size = action.get("top_size")
        right_size = action.get("right_size")
        if top_size is not None:
            store._snapshot["marginal_kde_top_size"] = _normalize_marginal_size(top_size)
        if right_size is not None:
            store._snapshot["marginal_kde_right_size"] = _normalize_marginal_size(right_size)

    elif action_type == "SET_KDE_COMPUTE_OPTIONS":
        bw_adjust = action.get("bw_adjust")
        bw_method = action.get("bw_method")
        gridsize = action.get("gridsize")
        thresh = action.get("thresh")
        clip_min = action.get("clip_min")
        clip_max = action.get("clip_max")
        common_norm = action.get("common_norm")
        warn_singular = action.get("warn_singular")

        if bw_adjust is not None:
            store._snapshot["kde_bw_adjust"] = _normalize_bw_adjust(bw_adjust)
        if bw_method is not None:
            store._snapshot["kde_bw_method"] = _normalize_kde_auto_bandwidth_method(bw_method)
        if gridsize is not None:
            store._snapshot["kde_gridsize"] = _normalize_gridsize(gridsize)
        if thresh is not None:
            store._snapshot["kde_thresh"] = _normalize_kde_thresh(thresh)
        if action.get("clear_clip"):
            store._snapshot["kde_clip_min"] = None
            store._snapshot["kde_clip_max"] = None
        elif clip_min is not None or clip_max is not None:
            if clip_min is not None:
                store._snapshot["kde_clip_min"] = _normalize_clip_bound(clip_min)
            if clip_max is not None:
                store._snapshot["kde_clip_max"] = _normalize_clip_bound(clip_max)
        if common_norm is not None:
            store._snapshot["kde_common_norm"] = bool(common_norm)
        if warn_singular is not None:
            store._snapshot["kde_warn_singular"] = bool(warn_singular)

    elif action_type == "SET_MARGINAL_KDE_COMPUTE_OPTIONS":
        max_points = action.get("max_points")
        bw_adjust = action.get("bw_adjust")
        bandwidth = action.get("bandwidth")
        kernel = action.get("kernel")
        auto_bandwidth_method = action.get("auto_bandwidth_method")
        gridsize = action.get("gridsize")
        cut = action.get("cut")
        log_transform = action.get("log_transform")
        clip_min = action.get("clip_min")
        clip_max = action.get("clip_max")
        cumulative = action.get("cumulative")

        if max_points is not None:
            store._snapshot["marginal_kde_max_points"] = _normalize_max_points(max_points)
        if bw_adjust is not None:
            store._snapshot["marginal_kde_bw_adjust"] = _normalize_bw_adjust(bw_adjust)
        if bandwidth is not None:
            store._snapshot["marginal_kde_bandwidth"] = _normalize_kde_bandwidth(bandwidth)
        if kernel is not None:
            store._snapshot["marginal_kde_kernel"] = _normalize_kde_kernel(kernel)
        if auto_bandwidth_method is not None:
            store._snapshot["marginal_kde_auto_bandwidth_method"] = (
                _normalize_kde_auto_bandwidth_method(auto_bandwidth_method)
            )
        if gridsize is not None:
            store._snapshot["marginal_kde_gridsize"] = _normalize_gridsize(gridsize)
        if cut is not None:
            store._snapshot["marginal_kde_cut"] = _normalize_cut(cut)
        if action.get("clear_clip"):
            store._snapshot["marginal_kde_clip_min"] = None
            store._snapshot["marginal_kde_clip_max"] = None
        elif clip_min is not None or clip_max is not None:
            if clip_min is not None:
                store._snapshot["marginal_kde_clip_min"] = _normalize_clip_bound(clip_min)
            if clip_max is not None:
                store._snapshot["marginal_kde_clip_max"] = _normalize_clip_bound(clip_max)
        if cumulative is not None:
            store._snapshot["marginal_kde_cumulative"] = bool(cumulative)
        if log_transform is not None:
            store._snapshot["marginal_kde_log_transform"] = bool(log_transform)












    elif action_type == "SET_LEGEND_OFFSET":
        offset = action.get("offset")
        store._snapshot["legend_offset"] = tuple(offset) if offset is not None else (0.0, 0.0)


    elif action_type == "SET_LEGEND_SNAPSHOT":
        store._snapshot["legend_last_title"] = action.get("title")
        store._snapshot["legend_last_handles"] = action.get("handles")
        store._snapshot["legend_last_labels"] = action.get("labels")

    elif action_type == "SET_RECENT_FILES":
        files = [str(f) for f in list(action.get("files") or [])]
        cap = int(CONFIG.get("max_recent_files", 8) or 8)
        store._snapshot["recent_files"] = files[:cap]












    elif action_type == "SET_SELECTED_INDICES":
        indices = _to_index_set(action.get("indices", []))
        store._snapshot["selected_indices"] = indices


    elif action_type == "ADD_SELECTED_INDICES":
        indices = _to_index_set(action.get("indices", []))
        store._snapshot["selected_indices"].update(indices)

    elif action_type == "REMOVE_SELECTED_INDICES":
        indices = _to_index_set(action.get("indices", []))
        for index in indices:
            store._snapshot["selected_indices"].discard(index)

    elif action_type == "CLEAR_SELECTED_INDICES":
        store._snapshot["selected_indices"].clear()

    elif action_type == "CLEAR_SELECTION":
        store._snapshot["selected_indices"].clear()
        store._snapshot["selection_mode"] = False


    elif action_type == "SET_SELECTION_TOOL":
        tool = action.get("tool")
        store._snapshot["selection_tool"] = str(tool) if tool is not None else None
        store._snapshot["selection_mode"] = tool is not None

    elif action_type == "SET_DATAFRAME_SOURCE":
        store._snapshot["df_global"] = action.get("df")
        store._snapshot["file_path"] = action.get("file_path")
        store._snapshot["sheet_name"] = action.get("sheet_name")



    elif action_type == "BUMP_DATA_VERSION":
        store._snapshot["data_version"] = int(store._snapshot.get("data_version", 0)) + 1
        cache = getattr(store._state, "embedding_cache", None)
        if cache is not None and hasattr(cache, "clear"):
            cache.clear()


    elif action_type == "SET_GROUP_DATA_COLUMNS":
        store._snapshot["group_cols"] = [str(col) for col in list(action.get("group_cols") or [])]
        store._snapshot["data_cols"] = [str(col) for col in list(action.get("data_cols") or [])]

    elif action_type == "SET_LAST_GROUP_COL":
        group_col = action.get("group_col")
        store._snapshot["last_group_col"] = str(group_col) if group_col is not None else None

    elif action_type == "SET_SELECTED_2D_COLUMNS":
        store._snapshot["selected_2d_cols"] = list(action.get("columns") or [])
        store._snapshot["selected_2d_confirmed"] = bool(action.get("confirmed", False))

    elif action_type == "SET_SELECTED_3D_COLUMNS":
        store._snapshot["selected_3d_cols"] = list(action.get("columns") or [])
        store._snapshot["selected_3d_confirmed"] = bool(action.get("confirmed", False))

    elif action_type == "SET_SELECTED_TERNARY_COLUMNS":
        store._snapshot["selected_ternary_cols"] = list(action.get("columns") or [])
        store._snapshot["selected_ternary_confirmed"] = bool(action.get("confirmed", False))







    elif action_type == "SET_TERNARY_VALUE_DISPLAY":
        from .coercers import _normalize_ternary_value_display as _normalize_value_display
        store._snapshot["ternary_value_display"] = _normalize_value_display(
            action.get("mode")
        )
















    elif action_type == "SET_MODEL_CURVE_MODELS":
        models = action.get("models")
        store._snapshot["model_curve_models"] = list(models or []) if models is not None else None


    elif action_type == "RESET_COLUMN_SELECTION":
        store._snapshot["selected_2d_cols"] = []
        store._snapshot["selected_3d_cols"] = []
        store._snapshot["selected_ternary_cols"] = []
        store._snapshot["selected_2d_confirmed"] = False
        store._snapshot["selected_3d_confirmed"] = False
        store._snapshot["selected_ternary_confirmed"] = False
        store._snapshot["available_groups"] = []
        store._snapshot["visible_groups"] = None

    elif action_type == "SYNC_AVAILABLE_VISIBLE_GROUPS":
        groups = [str(group) for group in list(action.get("all_groups") or [])]
        store._snapshot["available_groups"] = groups
        visible_groups = store._snapshot["visible_groups"]
        if visible_groups:
            filtered = [group for group in visible_groups if group in groups]
            store._snapshot["visible_groups"] = filtered if filtered else None








    elif action_type == "SET_EXPORT_IMAGE_OPTIONS":
        merged = dict(store._snapshot["export_image_options"])
        payload = dict(action.get("options") or {})
        for key, value in payload.items():
            if value is not None:
                merged[key] = value
        store._snapshot["export_image_options"] = _normalize_export_options(merged)

    else:
        logger.warning("Ignored unknown dispatch action type: %s", action_type)
