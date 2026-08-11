"""Common rendering helper subpackage."""

from .legend import (
    _build_legend_proxies,
    _build_overlay_legend_entries,
    _notify_legend_panel,
    _place_inline_legend,
    _render_legend,
)
from .scatter import _render_scatter_groups
from .state_access import _active_subset_indices, _data_cols, _data_state, _df_global, _group_cols
from .title import _render_title_labels

__all__ = [
    '_active_subset_indices',
    '_build_legend_proxies',
    '_build_overlay_legend_entries',
    '_data_cols',
    '_data_state',
    '_df_global',
    '_group_cols',
    '_notify_legend_panel',
    '_place_inline_legend',
    '_render_legend',
    '_render_scatter_groups',
    '_render_title_labels',
]
