"""Core plotting style application helpers."""
from __future__ import annotations

import logging

import matplotlib.pyplot as plt

from core import CONFIG, app_state
from ...style_manager import apply_custom_style

logger = logging.getLogger(__name__)


def _apply_current_style():
    """Apply the current plot style and color scheme from app_state."""
    show_grid = getattr(app_state, 'plot_style_grid', False)
    color_scheme = getattr(app_state, 'color_scheme', 'vibrant')
    primary_font = getattr(app_state, 'custom_primary_font', '')
    cjk_font = getattr(app_state, 'custom_cjk_font', '')
    font_sizes = getattr(app_state, 'plot_font_sizes', None)

    try:
        apply_custom_style(show_grid, color_scheme, primary_font, cjk_font, font_sizes)
    except Exception as e:
        logger.warning("Failed to apply styles: %s", e)
        apply_custom_style(False, 'vibrant')

    try:
        figure_dpi = float(getattr(app_state, 'plot_dpi', 130))
        savefig_dpi = float(CONFIG.get('savefig_dpi', 300))
        plt.rcParams['figure.dpi'] = figure_dpi
        plt.rcParams['savefig.dpi'] = max(figure_dpi, savefig_dpi)
        plt.rcParams['figure.facecolor'] = getattr(app_state, 'plot_facecolor', '#ffffff')
        plt.rcParams['axes.facecolor'] = getattr(app_state, 'axes_facecolor', '#ffffff')
        plt.rcParams['axes.grid'] = bool(show_grid)
        plt.rcParams['grid.color'] = getattr(app_state, 'grid_color', '#e2e8f0')
        plt.rcParams['grid.linewidth'] = float(getattr(app_state, 'grid_linewidth', 0.6))
        plt.rcParams['grid.alpha'] = float(getattr(app_state, 'grid_alpha', 0.7))
        plt.rcParams['grid.linestyle'] = getattr(app_state, 'grid_linestyle', '--')
        tick_dir = getattr(app_state, 'tick_direction', 'out')
        tick_color = getattr(app_state, 'tick_color', '#1f2937')
        plt.rcParams['xtick.direction'] = tick_dir
        plt.rcParams['ytick.direction'] = tick_dir
        plt.rcParams['xtick.color'] = tick_color
        plt.rcParams['ytick.color'] = tick_color
        plt.rcParams['xtick.major.size'] = float(getattr(app_state, 'tick_length', 4.0))
        plt.rcParams['ytick.major.size'] = float(getattr(app_state, 'tick_length', 4.0))
        plt.rcParams['xtick.major.width'] = float(getattr(app_state, 'tick_width', 0.8))
        plt.rcParams['ytick.major.width'] = float(getattr(app_state, 'tick_width', 0.8))
        plt.rcParams['xtick.minor.size'] = float(getattr(app_state, 'minor_tick_length', 2.5))
        plt.rcParams['ytick.minor.size'] = float(getattr(app_state, 'minor_tick_length', 2.5))
        plt.rcParams['xtick.minor.width'] = float(getattr(app_state, 'minor_tick_width', 0.6))
        plt.rcParams['ytick.minor.width'] = float(getattr(app_state, 'minor_tick_width', 0.6))
        plt.rcParams['axes.linewidth'] = float(getattr(app_state, 'axis_linewidth', 1.0))
        plt.rcParams['axes.labelcolor'] = getattr(app_state, 'label_color', '#1f2937')
        plt.rcParams['axes.labelweight'] = getattr(app_state, 'label_weight', 'normal')
        plt.rcParams['axes.titlecolor'] = getattr(app_state, 'title_color', '#111827')
        plt.rcParams['axes.titleweight'] = getattr(app_state, 'title_weight', 'bold')
    except Exception as err:
        logger.warning("Failed to apply rcParams style: %s", err)


def _enforce_plot_style(ax):
    """Enforce style settings on the specific axes instance."""
    if ax is None:
        return

    show_grid = getattr(app_state, 'plot_style_grid', False)
    if show_grid:
        ax.grid(
            True,
            which='major',
            color=getattr(app_state, 'grid_color', '#e2e8f0'),
            linewidth=getattr(app_state, 'grid_linewidth', 0.6),
            alpha=getattr(app_state, 'grid_alpha', 0.7),
            linestyle=getattr(app_state, 'grid_linestyle', '--')
        )
    else:
        ax.grid(False, which='major')

    minor_ticks = getattr(app_state, 'minor_ticks', False)
    minor_grid = getattr(app_state, 'minor_grid', False)
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
            color=getattr(app_state, 'minor_grid_color', '#e2e8f0'),
            linewidth=getattr(app_state, 'minor_grid_linewidth', 0.4),
            alpha=getattr(app_state, 'minor_grid_alpha', 0.4),
            linestyle=getattr(app_state, 'minor_grid_linestyle', ':')
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
    tick_color = getattr(app_state, 'tick_color', '#1f2937')
    ax.tick_params(
        direction=getattr(app_state, 'tick_direction', 'out'),
        length=getattr(app_state, 'tick_length', 4.0),
        width=getattr(app_state, 'tick_width', 0.8),
        colors=tick_color,
        labelcolor=tick_color,
        which='major'
    )
    if minor_ticks:
        ax.tick_params(
            length=getattr(app_state, 'minor_tick_length', 2.5),
            width=getattr(app_state, 'minor_tick_width', 0.6),
            colors=tick_color,
            which='minor'
        )
    for spine in ax.spines.values():
        spine.set_linewidth(getattr(app_state, 'axis_linewidth', 1.0))
        spine.set_color(getattr(app_state, 'axis_line_color', '#1f2937'))

    top_spine = ax.spines.get('top')
    if top_spine is not None:
        top_spine.set_visible(getattr(app_state, 'show_top_spine', True))

    right_spine = ax.spines.get('right')
    if right_spine is not None:
        right_spine.set_visible(getattr(app_state, 'show_right_spine', True))


def _apply_axis_text_style(ax):
    """Apply axis label/title styling without changing text."""
    if ax is None:
        return
    label_color = getattr(app_state, 'label_color', '#1f2937')
    label_weight = getattr(app_state, 'label_weight', 'normal')
    label_pad = getattr(app_state, 'label_pad', 6.0)
    title_color = getattr(app_state, 'title_color', '#111827')
    title_weight = getattr(app_state, 'title_weight', 'bold')

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

