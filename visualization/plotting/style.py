"""Style helpers for plotting."""
import logging

import matplotlib.pyplot as plt
from matplotlib import font_manager

from core import CONFIG, app_state
from ..style_manager import apply_custom_style

logger = logging.getLogger(__name__)

# Legend bbox offsets for outside layouts
_LEGEND_BBOX_RIGHT = 1.08
_LEGEND_BBOX_RIGHT_KDE = 1.32
_LEGEND_BBOX_LEFT = -0.28
_LEGEND_BBOX_LEFT_KDE = -0.32
_LEGEND_BBOX_TOP_Y = 1.10
_LEGEND_BBOX_BOTTOM_Y = -0.30


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
        logger.warning(f"Failed to apply styles: {e}")
        apply_custom_style(False, 'vibrant')

    try:
        plt.rcParams['figure.dpi'] = float(getattr(app_state, 'plot_dpi', 130))
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
        logger.warning(f"Failed to apply rcParams style: {err}")


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
    ax.spines['top'].set_visible(getattr(app_state, 'show_top_spine', True))
    ax.spines['right'].set_visible(getattr(app_state, 'show_right_spine', True))


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


def _legend_layout_config(ax=None, show_marginal_kde=False):
    """Resolve legend location, bbox, and layout options."""
    loc = getattr(app_state, 'legend_location', 'outside_right') or 'outside_right'
    mode = None
    borderaxespad = None
    if loc == 'outside_right':
        bbox_x = _LEGEND_BBOX_RIGHT_KDE if show_marginal_kde else _LEGEND_BBOX_RIGHT
        return 'upper left', (bbox_x, 0.0, 0.2, 1.0), 'expand', 0.0
    if loc == 'outside_left':
        bbox_x = _LEGEND_BBOX_LEFT_KDE if show_marginal_kde else _LEGEND_BBOX_LEFT
        return 'upper right', (bbox_x, 0.0, 0.2, 1.0), 'expand', 0.0
    if loc == 'outside_top':
        return 'lower left', (0.0, _LEGEND_BBOX_TOP_Y, 1.0, 0.2), 'expand', 0.0
    if loc == 'outside_bottom':
        return 'upper left', (0.0, _LEGEND_BBOX_BOTTOM_Y, 1.0, 0.2), 'expand', 0.0
    return loc, None, mode, borderaxespad


def _legend_location_config(show_marginal_kde=False):
    """Resolve legend location and optional bbox anchor."""
    loc, bbox, _mode, _pad = _legend_layout_config(show_marginal_kde=show_marginal_kde)
    return loc, bbox


def _legend_columns_for_layout(labels, ax, location_key):
    """Compute legend columns for outside layouts."""
    if not labels:
        return 1
    if location_key in {'outside_left', 'outside_right'}:
        return 1
    if location_key in {'outside_top', 'outside_bottom'}:
        fig = getattr(ax, 'figure', None)
        dpi = getattr(fig, 'dpi', 100) if fig is not None else 100
        fig_width_px = (fig.get_figwidth() * dpi) if fig is not None else 800
        legend_size = getattr(app_state, 'plot_font_sizes', {}).get('legend', 10)
        avg_len = sum(len(str(label)) for label in labels) / max(len(labels), 1)
        est_label_px = (avg_len * 0.6 + 2.0) * (legend_size * dpi / 72.0) + 26.0
        usable = fig_width_px * 0.9
        ncol = max(1, int(usable / max(est_label_px, 1.0)))
        return min(len(labels), max(1, ncol))
    return None


def _style_legend(legend, show_marginal_kde=False):
    """Apply legend styling from app_state."""
    if legend is None:
        return
    legend_ax = getattr(app_state, 'legend_ax', None)
    if legend_ax is None or legend.axes is not legend_ax:
        loc, bbox, _mode, _pad = _legend_layout_config(show_marginal_kde=show_marginal_kde)
        try:
            legend.set_loc(loc)
        except Exception:
            pass
        if bbox:
            try:
                legend.set_bbox_to_anchor(bbox, transform=legend.axes.transAxes)
            except Exception:
                pass

    frame_on = bool(getattr(app_state, 'legend_frame_on', True))
    legend.set_frame_on(frame_on)
    frame = legend.get_frame()
    if frame_on:
        try:
            frame.set_facecolor(getattr(app_state, 'legend_frame_facecolor', '#ffffff'))
            frame.set_edgecolor(getattr(app_state, 'legend_frame_edgecolor', '#cbd5f5'))
            frame.set_alpha(float(getattr(app_state, 'legend_frame_alpha', 0.95)))
        except Exception:
            pass

    legend_size = getattr(app_state, 'plot_font_sizes', {}).get('legend', 10)
    text_color = getattr(app_state, 'label_color', '#1f2937')
    for text in legend.get_texts():
        try:
            text.set_fontsize(legend_size)
            text.set_color(text_color)
        except Exception:
            pass
    try:
        title = legend.get_title()
        title.set_fontsize(getattr(app_state, 'plot_font_sizes', {}).get('label', 12))
        title.set_color(text_color)
        title.set_fontweight(getattr(app_state, 'label_weight', 'normal'))
    except Exception:
        pass


def refresh_plot_style():
    """Refresh plot styling without recomputing embeddings."""
    try:
        _apply_current_style()
    except Exception:
        pass

    ax = getattr(app_state, 'ax', None)
    fig = getattr(app_state, 'fig', None)

    axes = []
    if fig is not None:
        axes.extend(list(getattr(fig, 'axes', [])))
    if ax is not None and ax not in axes:
        axes.append(ax)

    for target_ax in axes:
        try:
            _enforce_plot_style(target_ax)
        except Exception:
            pass
        try:
            _apply_axis_text_style(target_ax)
        except Exception:
            pass
        try:
            _style_legend(target_ax.get_legend(), show_marginal_kde=getattr(app_state, 'show_marginal_kde', False))
        except Exception:
            pass

    try:
        base_size = getattr(app_state, 'plot_marker_size', 60)
        base_alpha = getattr(app_state, 'plot_marker_alpha', 0.8)
        edgecolor = getattr(app_state, 'scatter_edgecolor', '#1e293b')
        edgewidth = getattr(app_state, 'scatter_edgewidth', 0.4)

        for sc in list(getattr(app_state, 'scatter_collections', [])):
            if sc is None:
                continue
            try:
                sizes = sc.get_sizes()
                if sizes is None or len(sizes) == 0:
                    sc.set_sizes([base_size])
                else:
                    sc.set_sizes([base_size] * len(sizes))
                sc.set_alpha(base_alpha)
                sc.set_edgecolor(edgecolor)
                sc.set_linewidths(edgewidth)
            except Exception:
                pass
    except Exception:
        pass

    try:
        if getattr(app_state, 'selected_indices', None):
            from ..events import refresh_selection_overlay
            refresh_selection_overlay()
    except Exception:
        pass

    if fig is not None and fig.canvas:
        try:
            fig.canvas.draw_idle()
        except Exception:
            pass

