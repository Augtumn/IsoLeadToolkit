"""
Overlay rendering helpers
Shared utilities for drawing geochemistry overlays (curves, isochrons, labels)
"""
from __future__ import annotations
import logging
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.artist import Artist

logger = logging.getLogger(__name__)


def draw_curve(
    ax: Axes,
    x_data: np.ndarray,
    y_data: np.ndarray,
    style_key: str,
    line_styles: dict,
    label: str | None = None,
    zorder: int = 1,
) -> Artist | None:
    """Draw a single curve with style from line_styles dict.

    Args:
        ax: Matplotlib axes
        x_data: X coordinates
        y_data: Y coordinates
        style_key: Key in line_styles dict (e.g., 'model_curve', 'paleoisochron')
        line_styles: Style dictionary from app_state.line_styles
        label: Optional label for legend
        zorder: Drawing order

    Returns:
        Line2D artist or None if drawing failed
    """
    if len(x_data) == 0 or len(y_data) == 0:
        return None

    style = line_styles.get(style_key, {})
    color = style.get('color')
    linewidth = style.get('linewidth', 1.0)
    linestyle = style.get('linestyle', '-')
    alpha = style.get('alpha', 0.8)

    try:
        line, = ax.plot(
            x_data, y_data,
            color=color,
            linewidth=linewidth,
            linestyle=linestyle,
            alpha=alpha,
            label=label,
            zorder=zorder,
            picker=5
        )
        return line
    except Exception as e:
        logger.warning(f"Failed to draw curve {style_key}: {e}")
        return None


def draw_label(
    ax: Axes,
    x: float,
    y: float,
    text: str,
    fontsize: int = 9,
    color: str = '#64748b',
    weight: str = 'normal',
    ha: str = 'center',
    va: str = 'center',
    bbox_style: dict | None = None,
    zorder: int = 3,
    rotation: float = 0.0,
) -> Artist | None:
    """Draw a text label with optional background box.

    Args:
        ax: Matplotlib axes
        x, y: Label position in data coordinates
        text: Label text
        fontsize: Font size
        color: Text color
        weight: Font weight ('normal', 'bold')
        ha: Horizontal alignment
        va: Vertical alignment
        bbox_style: Optional dict for bbox (e.g., {'boxstyle': 'round,pad=0.3', 'facecolor': 'white', 'alpha': 0.7})
        zorder: Drawing order
        rotation: Text rotation in degrees

    Returns:
        Text artist or None if drawing failed
    """
    try:
        txt = ax.text(
            x, y, text,
            fontsize=fontsize,
            color=color,
            weight=weight,
            ha=ha,
            va=va,
            bbox=bbox_style,
            zorder=zorder,
            rotation=rotation,
            picker=True
        )
        return txt
    except Exception as e:
        logger.warning(f"Failed to draw label '{text}': {e}")
        return None


def compute_label_position(
    x_data: np.ndarray,
    y_data: np.ndarray,
    position: str = 'end',
    offset_fraction: float = 0.0
) -> tuple[float, float] | None:
    """Compute label position along a curve.

    Args:
        x_data: Curve X coordinates
        y_data: Curve Y coordinates
        position: 'start', 'end', 'middle', or 'auto'
        offset_fraction: Offset along curve (0.0 = no offset, 0.1 = 10% from position)

    Returns:
        (x, y) tuple or None if computation failed
    """
    if len(x_data) == 0 or len(y_data) == 0:
        return None

    try:
        if position == 'start':
            idx = int(len(x_data) * offset_fraction)
        elif position == 'middle':
            idx = len(x_data) // 2
        elif position == 'end':
            idx = len(x_data) - 1 - int(len(x_data) * offset_fraction)
        else:  # auto
            idx = len(x_data) - 1

        idx = max(0, min(idx, len(x_data) - 1))
        return float(x_data[idx]), float(y_data[idx])
    except Exception as e:
        logger.warning(f"Failed to compute label position: {e}")
        return None


def filter_valid_points(x_data: np.ndarray, y_data: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Remove NaN and infinite values from curve data.

    Args:
        x_data: X coordinates
        y_data: Y coordinates

    Returns:
        (x_filtered, y_filtered) tuple with only finite values
    """
    mask = np.isfinite(x_data) & np.isfinite(y_data)
    return x_data[mask], y_data[mask]


def clip_to_axes_limits(
    x_data: np.ndarray,
    y_data: np.ndarray,
    ax: Axes,
    margin: float = 0.0
) -> tuple[np.ndarray, np.ndarray]:
    """Clip curve data to axes limits with optional margin.

    Args:
        x_data: X coordinates
        y_data: Y coordinates
        ax: Matplotlib axes
        margin: Margin fraction (0.0 = no margin, 0.1 = 10% margin)

    Returns:
        (x_clipped, y_clipped) tuple
    """
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()

    x_range = xlim[1] - xlim[0]
    y_range = ylim[1] - ylim[0]

    x_min = xlim[0] - margin * x_range
    x_max = xlim[1] + margin * x_range
    y_min = ylim[0] - margin * y_range
    y_max = ylim[1] + margin * y_range

    mask = (
        (x_data >= x_min) & (x_data <= x_max) &
        (y_data >= y_min) & (y_data <= y_max)
    )

    return x_data[mask], y_data[mask]


def store_overlay_artist(
    overlay_artists: dict,
    category: str,
    key: str,
    artist: Artist
) -> None:
    """Store overlay artist in app_state.overlay_artists structure.

    Args:
        overlay_artists: app_state.overlay_artists dict
        category: Category key (e.g., 'model_curves', 'paleoisochrons')
        key: Item key (e.g., model name, age value)
        artist: Matplotlib artist to store
    """
    if category not in overlay_artists:
        overlay_artists[category] = {}
    if key not in overlay_artists[category]:
        overlay_artists[category][key] = []
    overlay_artists[category][key].append(artist)


def clear_overlay_category(
    overlay_artists: dict,
    category: str
) -> None:
    """Remove all artists in a category and clear from dict.

    Args:
        overlay_artists: app_state.overlay_artists dict
        category: Category key to clear
    """
    if category in overlay_artists:
        for key, artists in overlay_artists[category].items():
            for artist in artists:
                try:
                    artist.remove()
                except Exception:
                    pass
        overlay_artists[category].clear()


__all__ = [
    'draw_curve',
    'draw_label',
    'compute_label_position',
    'filter_valid_points',
    'clip_to_axes_limits',
    'store_overlay_artist',
    'clear_overlay_category',
]
