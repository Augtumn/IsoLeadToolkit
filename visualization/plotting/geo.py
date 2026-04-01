"""Geochemistry plotting facade exports.

This module preserves backward-compatible imports while implementation
is split across visualization.plotting.geochem.* submodules.
"""
from __future__ import annotations

from .geochem.overlay_helpers import (
    _draw_model_curves,
    _draw_mu_kappa_paleoisochrons,
    _draw_plumbotectonics_curves,
    _draw_plumbotectonics_isoage_lines,
    _format_label_text,
    _is_overlay_label_style_visible,
    _label_bbox,
    _register_overlay_artist,
    _register_overlay_curve_label,
    _resolve_label_options,
    get_overlay_default_color,
    get_plumbotectonics_group_entries,
    get_plumbotectonics_group_palette,
    get_plumbotectonics_variants,
)
from .geochem.isochron_overlays import (
    _build_isochron_label,
    _draw_isochron_overlays,
    _draw_model_age_lines,
    _draw_model_age_lines_86,
    _draw_paleoisochrons,
    _draw_selected_isochron,
    _resolve_model_age,
    refresh_paleoisochron_labels,
)
from .geochem.equation_overlays import (
    _draw_equation_overlays,
    _safe_eval_expression,
)

__all__ = [
    '_build_isochron_label',
    '_draw_equation_overlays',
    '_draw_isochron_overlays',
    '_draw_model_age_lines',
    '_draw_model_age_lines_86',
    '_draw_model_curves',
    '_draw_mu_kappa_paleoisochrons',
    '_draw_paleoisochrons',
    '_draw_plumbotectonics_curves',
    '_draw_plumbotectonics_isoage_lines',
    '_draw_selected_isochron',
    '_format_label_text',
    '_is_overlay_label_style_visible',
    '_label_bbox',
    '_register_overlay_artist',
    '_register_overlay_curve_label',
    '_resolve_label_options',
    '_resolve_model_age',
    '_safe_eval_expression',
    'get_overlay_default_color',
    'get_plumbotectonics_group_entries',
    'get_plumbotectonics_group_palette',
    'get_plumbotectonics_variants',
    'refresh_paleoisochron_labels',
]
