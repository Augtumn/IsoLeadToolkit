"""Primary rendering facade for embeddings and scatter plots."""
from __future__ import annotations

from .rendering.embedding_plot import plot_embedding
from .rendering.raw import plot_2d_data, plot_3d_data


def plot_umap(group_col: str, params: dict, size: int) -> bool:
    """Deprecated: Use plot_embedding instead."""
    return plot_embedding(group_col, 'UMAP', umap_params=params, size=size)


__all__ = [
    'plot_embedding',
    'plot_umap',
    'plot_2d_data',
    'plot_3d_data',
]
