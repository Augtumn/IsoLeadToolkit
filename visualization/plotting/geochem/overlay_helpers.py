"""Geochemistry overlay helper compatibility facade.

This module keeps backward-compatible imports while implementation is split
across overlay_common, model_overlays and plumbotectonics modules.
"""
from __future__ import annotations

from .overlay_common import (
    _format_label_text,
    _is_overlay_label_style_visible,
    _label_bbox,
    _register_overlay_artist,
    _register_overlay_curve_label,
    _resolve_label_options,
)
from .model_overlays import (
    _draw_model_curves,
    _draw_mu_kappa_paleoisochrons,
)
from .plumbotectonics import (
    _draw_plumbotectonics_curves,
    _draw_plumbotectonics_isoage_lines,
    get_overlay_default_color,
    get_plumbotectonics_group_entries,
    get_plumbotectonics_group_palette,
    get_plumbotectonics_variants,
)

__all__ = [
    '_draw_model_curves',
    '_draw_mu_kappa_paleoisochrons',
    '_draw_plumbotectonics_curves',
    '_draw_plumbotectonics_isoage_lines',
    '_format_label_text',
    '_is_overlay_label_style_visible',
    '_label_bbox',
    '_register_overlay_artist',
    '_register_overlay_curve_label',
    '_resolve_label_options',
    'get_overlay_default_color',
    'get_plumbotectonics_group_entries',
    'get_plumbotectonics_group_palette',
    'get_plumbotectonics_variants',
]
