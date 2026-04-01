"""Raw plotting compatibility facade.

This module keeps backward-compatible exports while implementation is split
across dedicated 2D and 3D plotting modules.
"""
from __future__ import annotations

from .raw_plot_2d import plot_2d_data
from .raw_plot_3d import plot_3d_data

__all__ = [
    'plot_2d_data',
    'plot_3d_data',
]
