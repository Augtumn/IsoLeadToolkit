"""
Visualization module - Plotting, algorithms, and style management

This module provides a bridge to the visualization components.
The main plotting functions are in plotting.py (migrated from the root visualization.py).
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
    draw_confidence_ellipse,
)

# Plotting functions will be imported from plotting.py once created
# For now, import from root level for backward compatibility
try:
    from .plotting import (
        plot_embedding,
        plot_umap,
        plot_2d_data,
        plot_3d_data,
        refresh_plot_style,
        get_embedding,
        get_umap_embedding,
        get_tsne_embedding,
        get_pca_embedding,
        get_robust_pca_embedding,
        show_scree_plot,
        show_pca_loadings,
        show_embedding_correlation,
        show_shepard_diagram,
        show_correlation_heatmap,
        calculate_auto_ternary_factors,
    )
except ImportError:
    # Fallback: plotting.py not yet created
    plot_embedding = None
    plot_umap = None
    plot_2d_data = None
    plot_3d_data = None

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
    'plot_umap',
    'plot_2d_data',
    'plot_3d_data',
    'refresh_plot_style',
    'get_embedding',
    'get_umap_embedding',
    'get_tsne_embedding',
    'get_pca_embedding',
    'get_robust_pca_embedding',
    'show_scree_plot',
    'show_pca_loadings',
    'show_embedding_correlation',
    'show_shepard_diagram',
    'show_correlation_heatmap',
    'calculate_auto_ternary_factors',
]
