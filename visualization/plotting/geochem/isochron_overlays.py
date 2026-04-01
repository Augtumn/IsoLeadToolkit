"""Isochron overlay compatibility facade.

This module keeps backward-compatible symbol exports while the implementation
is split into smaller submodules under visualization.plotting.geochem.
"""

from __future__ import annotations

from .isochron_labels import _build_isochron_label, refresh_paleoisochron_labels
from .isochron_rendering import (
    _draw_isochron_overlays,
    _draw_paleoisochrons,
    _draw_selected_isochron,
)
from .model_age_lines import _draw_model_age_lines, _draw_model_age_lines_86, _resolve_model_age

__all__ = [
    '_build_isochron_label',
    '_draw_isochron_overlays',
    '_draw_model_age_lines',
    '_draw_model_age_lines_86',
    '_draw_paleoisochrons',
    '_draw_selected_isochron',
    '_resolve_model_age',
    'refresh_paleoisochron_labels',
]

