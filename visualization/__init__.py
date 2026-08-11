"""
Visualization module - Plotting, algorithms, and style management

This module provides a bridge to the visualization components.
The main plotting functions live in the plotting subpackage (plotting/api.py).
"""

# Re-export from submodules
from .style_manager import (
    StyleManager,
    style_manager_instance,
    apply_custom_style,
    COLORS,
    STYLES,
)

from .events import (
    on_hover,
    on_click,
    on_legend_click,
    on_slider_change,
    refresh_selection_overlay,
    toggle_selection_mode,
    sync_selection_tools,
)
from .selection_overlay import draw_confidence_ellipse

from .plotting import (
    plot_embedding,
    plot_2d_data,
    plot_3d_data,
    refresh_plot_style,
    get_umap_embedding,
    get_tsne_embedding,
    get_pca_embedding,
    get_robust_pca_embedding,
    show_scree_plot,
    show_pca_loadings,
    show_embedding_correlation,
    show_shepard_diagram,
    show_correlation_heatmap,
)

__all__ = [
    # Style
    'StyleManager',
    'style_manager_instance',
    'apply_custom_style',
    'COLORS',
    'STYLES',
    # Events
    'on_hover',
    'on_click',
    'on_legend_click',
    'on_slider_change',
    'refresh_selection_overlay',
    'toggle_selection_mode',
    'sync_selection_tools',
    'draw_confidence_ellipse',
    # Plotting
    'plot_embedding',
    'plot_2d_data',
    'plot_3d_data',
    'refresh_plot_style',
    'get_umap_embedding',
    'get_tsne_embedding',
    'get_pca_embedding',
    'get_robust_pca_embedding',
    'show_scree_plot',
    'show_pca_loadings',
    'show_embedding_correlation',
    'show_shepard_diagram',
    'show_correlation_heatmap',
]
