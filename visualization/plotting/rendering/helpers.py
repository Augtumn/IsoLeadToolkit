"""Compatibility facade for rendering helper symbols."""
from __future__ import annotations

from .geo_layers import _render_geo_overlays
from .kde import _render_kde_overlay, _resolve_kde_style
from .legend_helpers import (
    _build_legend_proxies,
    _build_overlay_legend_entries,
    _notify_legend_panel,
    _place_inline_legend,
    _render_legend,
)
from .scatter_helpers import _render_scatter_groups
from .state_access import _active_subset_indices, _data_cols, _data_state, _df_global
from .title_helpers import _render_title_labels

__all__ = [
    '_active_subset_indices',
    '_build_legend_proxies',
    '_build_overlay_legend_entries',
    '_data_cols',
    '_data_state',
    '_df_global',
    '_notify_legend_panel',
    '_place_inline_legend',
    '_render_geo_overlays',
    '_render_kde_overlay',
    '_render_legend',
    '_render_scatter_groups',
    '_render_title_labels',
    '_resolve_kde_style',
]



