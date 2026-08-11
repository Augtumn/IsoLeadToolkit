"""Primary rendering facade for embeddings and scatter plots."""
from __future__ import annotations

from .rendering.embedding_plot import plot_embedding
from .rendering.raw import plot_2d_data, plot_3d_data


__all__ = [
    'plot_embedding',
    'plot_2d_data',
    'plot_3d_data',
]
