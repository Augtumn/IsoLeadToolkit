"""Dimensionality reduction visualization and plotting API.

Public facade for the plotting subpackage. Only public symbols are
imported and re-exported here; private helpers stay in their own modules.
"""

from .analysis_qt import (
    show_scree_plot,
    show_pca_loadings,
    show_embedding_correlation,
    show_shepard_diagram,
    show_correlation_heatmap,
)
from .style import refresh_plot_style

from .core import (
    get_umap_embedding,
    get_tsne_embedding,
    get_pca_embedding,
    get_robust_pca_embedding,
)
from .geo import refresh_paleoisochron_labels
from .render import (
    plot_embedding,
    plot_2d_data,
    plot_3d_data,
)

__all__ = [
    # Embedding computation
    'get_umap_embedding',
    'get_tsne_embedding',
    'get_pca_embedding',
    'get_robust_pca_embedding',
    # Rendering
    'plot_embedding',
    'plot_2d_data',
    'plot_3d_data',
    'refresh_plot_style',
    # Analysis dialogs
    'show_scree_plot',
    'show_pca_loadings',
    'show_embedding_correlation',
    'show_shepard_diagram',
    'show_correlation_heatmap',
    # Utilities
    'refresh_paleoisochron_labels',
]
