"""Core plotting style application helpers."""
from __future__ import annotations

import logging
from typing import Any

import matplotlib.pyplot as plt

from core import CONFIG, app_state
from ...style_manager import apply_custom_style

logger = logging.getLogger(__name__)


def _apply_current_style() -> None:
    """Apply the current plot style and color scheme from app_state."""
    show_grid = app_state.plot_style_grid
    color_scheme = app_state.color_scheme
    primary_font = app_state.custom_primary_font
    cjk_font = app_state.custom_cjk_font
    font_sizes = app_state.plot_font_sizes

    try:
        apply_custom_style(show_grid, color_scheme, primary_font, cjk_font, font_sizes)
    except Exception as e:
        logger.warning("Failed to apply styles: %s", e)
        apply_custom_style(False, 'vibrant')

    try:
        figure_dpi = float(app_state.plot_dpi)
        savefig_dpi = float(CONFIG.get('savefig_dpi', 300))
        plt.rcParams['figure.dpi'] = figure_dpi
        plt.rcParams['savefig.dpi'] = max(figure_dpi, savefig_dpi)
        plt.rcParams['figure.facecolor'] = app_state.plot_facecolor
        plt.rcParams['axes.facecolor'] = app_state.axes_facecolor
        plt.rcParams['axes.grid'] = bool(show_grid)
        plt.rcParams['grid.color'] = app_state.grid_color
        plt.rcParams['grid.linewidth'] = float(app_state.grid_linewidth)
        plt.rcParams['grid.alpha'] = float(app_state.grid_alpha)
        plt.rcParams['grid.linestyle'] = app_state.grid_linestyle
        tick_dir = app_state.tick_direction
        tick_color = app_state.tick_color
        plt.rcParams['xtick.direction'] = tick_dir
        plt.rcParams['ytick.direction'] = tick_dir
        plt.rcParams['xtick.color'] = tick_color
        plt.rcParams['ytick.color'] = tick_color
        plt.rcParams['xtick.major.size'] = float(app_state.tick_length)
        plt.rcParams['ytick.major.size'] = float(app_state.tick_length)
        plt.rcParams['xtick.major.width'] = float(app_state.tick_width)
        plt.rcParams['ytick.major.width'] = float(app_state.tick_width)
        plt.rcParams['xtick.minor.size'] = float(app_state.minor_tick_length)
        plt.rcParams['ytick.minor.size'] = float(app_state.minor_tick_length)
        plt.rcParams['xtick.minor.width'] = float(app_state.minor_tick_width)
        plt.rcParams['ytick.minor.width'] = float(app_state.minor_tick_width)
        plt.rcParams['axes.linewidth'] = float(app_state.axis_linewidth)
        plt.rcParams['axes.labelcolor'] = app_state.label_color
        plt.rcParams['axes.labelweight'] = app_state.label_weight
        plt.rcParams['axes.titlecolor'] = app_state.title_color
        plt.rcParams['axes.titleweight'] = app_state.title_weight
    except Exception as err:
        logger.warning("Failed to apply rcParams style: %s", err)


def _enforce_plot_style(ax: Any) -> None:
    """Enforce style settings on the specific axes instance."""
    if ax is None:
        return

    show_grid = app_state.plot_style_grid
    if show_grid:
        ax.grid(
            True,
            which='major',
            color=app_state.grid_color,
            linewidth=app_state.grid_linewidth,
            alpha=app_state.grid_alpha,
            linestyle=app_state.grid_linestyle
        )
    else:
        ax.grid(False, which='major')

    minor_ticks = app_state.minor_ticks
    minor_grid = app_state.minor_grid
    if minor_ticks or minor_grid:
        try:
            ax.minorticks_on()
        except Exception:
            pass
    else:
        try:
            ax.minorticks_off()
        except Exception:
            pass

    if minor_grid:
        ax.grid(
            True,
            which='minor',
            color=app_state.minor_grid_color,
            linewidth=app_state.minor_grid_linewidth,
            alpha=app_state.minor_grid_alpha,
            linestyle=app_state.minor_grid_linestyle
        )
    else:
        ax.grid(False, which='minor')
    try:
        ax.set_axisbelow(True)
    except Exception:
        pass

    if app_state.fig is not None:
        app_state.fig.patch.set_facecolor(plt.rcParams.get('figure.facecolor', 'white'))

    ax.set_facecolor(plt.rcParams.get('axes.facecolor', 'white'))
    tick_color = app_state.tick_color
    ax.tick_params(
        direction=app_state.tick_direction,
        length=app_state.tick_length,
        width=app_state.tick_width,
        colors=tick_color,
        labelcolor=tick_color,
        which='major'
    )
    if minor_ticks:
        ax.tick_params(
            length=app_state.minor_tick_length,
            width=app_state.minor_tick_width,
            colors=tick_color,
            which='minor'
        )
    for spine in ax.spines.values():
        spine.set_linewidth(app_state.axis_linewidth)
        spine.set_color(app_state.axis_line_color)

    top_spine = ax.spines.get('top')
    if top_spine is not None:
        top_spine.set_visible(app_state.show_top_spine)

    right_spine = ax.spines.get('right')
    if right_spine is not None:
        right_spine.set_visible(app_state.show_right_spine)


def _apply_axis_text_style(ax: Any) -> None:
    """Apply axis label/title styling without changing text."""
    if ax is None:
        return
    label_color = app_state.label_color
    label_weight = app_state.label_weight
    label_pad = app_state.label_pad
    title_color = app_state.title_color
    title_weight = app_state.title_weight

    try:
        ax.xaxis.label.set_color(label_color)
        ax.xaxis.label.set_fontweight(label_weight)
        ax.xaxis.labelpad = label_pad
    except Exception:
        pass
    try:
        ax.yaxis.label.set_color(label_color)
        ax.yaxis.label.set_fontweight(label_weight)
        ax.yaxis.labelpad = label_pad
    except Exception:
        pass
    if hasattr(ax, 'zaxis'):
        try:
            ax.zaxis.label.set_color(label_color)
            ax.zaxis.label.set_fontweight(label_weight)
            ax.zaxis.labelpad = label_pad
        except Exception:
            pass
    try:
        title = ax.title
        title.set_color(title_color)
        title.set_fontweight(title_weight)
    except Exception:
        pass

