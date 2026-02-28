"""Style helpers for plotting."""
from __future__ import annotations

import logging

import matplotlib.pyplot as plt
from matplotlib import font_manager

from core import CONFIG, app_state
from .legend_model import OVERLAY_TOGGLE_MAP
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


def _legend_layout_config(ax=None, show_marginal_kde=False, location_key=None):
    """Resolve in-plot legend location, bbox, and layout options."""
    loc = location_key if location_key else getattr(app_state, 'legend_position', None)
    if not loc:
        return 'best', None, None, None
    if isinstance(loc, str) and loc.startswith('outside_'):
        return 'best', None, None, None
    offsets = getattr(app_state, 'legend_offset', (0.0, 0.0)) or (0.0, 0.0)
    try:
        dx, dy = float(offsets[0]), float(offsets[1])
    except Exception:
        dx, dy = 0.0, 0.0
    if dx == 0.0 and dy == 0.0:
        return loc, None, None, None

    anchor_map = {
        'upper left': (0.0, 1.0),
        'upper center': (0.5, 1.0),
        'upper right': (1.0, 1.0),
        'center left': (0.0, 0.5),
        'center': (0.5, 0.5),
        'center right': (1.0, 0.5),
        'lower left': (0.0, 0.0),
        'lower center': (0.5, 0.0),
        'lower right': (1.0, 0.0),
    }
    base = anchor_map.get(loc)
    if base is None:
        return loc, None, None, None
    bbox = (base[0] + dx, base[1] + dy)
    return loc, bbox, None, None


def _legend_columns_for_layout(labels, ax, location_key):
    """Compute legend columns for auto layouts."""
    if not labels:
        return 1
    if location_key in {'outside_left', 'outside_right'}:
        return 1
    return None


def _style_legend(legend, show_marginal_kde=False, location_key=None):
    """Apply legend styling from app_state."""
    if legend is None:
        return
    legend_ax = getattr(app_state, 'legend_ax', None)
    if legend_ax is None or legend.axes is not legend_ax:
        loc, bbox, _mode, _pad = _legend_layout_config(show_marginal_kde=show_marginal_kde, location_key=location_key)
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


def refresh_plot_style() -> None:
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


def refresh_overlay_styles():
    """Refresh overlay curve/label styles without full re-render.

    Updates line styles (color, width, linestyle, alpha) for all overlay artists
    stored in app_state.overlay_artists based on current app_state.line_styles.
    """
    if app_state.fig is None or app_state.ax is None:
        return

    try:
        overlay_artists = getattr(app_state, 'overlay_artists', {})
        line_styles = getattr(app_state, 'line_styles', {})

        # Map overlay category → style_key
        category_to_style = {
            'model_curves': 'model_curve',
            'plumbotectonics_curves': 'plumbotectonics_curve',
            'paleoisochrons': 'paleoisochron',
            'model_age_lines': 'model_age_line',
            'isochrons': 'isochron',
            'growth_curves': 'growth_curve',
        }

        for category, style_key in category_to_style.items():
            if category not in overlay_artists:
                continue

            style = line_styles.get(style_key, {})
            color = style.get('color')
            linewidth = style.get('linewidth', 1.0)
            linestyle = style.get('linestyle', '-')
            alpha = style.get('alpha', 0.8)

            for key, artists in overlay_artists[category].items():
                for artist in artists:
                    try:
                        # Update Line2D properties
                        if hasattr(artist, 'set_color') and color is not None:
                            artist.set_color(color)
                        if hasattr(artist, 'set_linewidth'):
                            artist.set_linewidth(linewidth)
                        if hasattr(artist, 'set_linestyle'):
                            artist.set_linestyle(linestyle)
                        if hasattr(artist, 'set_alpha'):
                            artist.set_alpha(alpha)
                    except Exception as e:
                        logger.debug(f"Failed to update artist in {category}/{key}: {e}")

        if app_state.fig.canvas is not None:
            app_state.fig.canvas.draw_idle()

    except Exception as e:
        logger.warning(f"Failed to refresh overlay styles: {e}")


def refresh_overlay_visibility():
    """Refresh overlay visibility based on app_state toggle flags.

    Shows/hides overlay artists based on show_model_curves, show_paleoisochrons, etc.
    without full re-render.
    """
    if app_state.fig is None or app_state.ax is None:
        return

    try:
        overlay_artists = getattr(app_state, 'overlay_artists', {}) or {}

        style_visibility = {
            style_key: bool(getattr(app_state, toggle_attr, True))
            for style_key, toggle_attr in OVERLAY_TOGGLE_MAP.items()
        }
        # Selected isochron remains visible when a selected-fit payload exists.
        style_visibility['selected_isochron'] = bool(
            getattr(app_state, 'show_isochrons', False)
            or getattr(app_state, 'selected_isochron_data', None) is not None
        )

        legacy_category_to_toggle = {
            'model_curves': 'show_model_curves',
            'plumbotectonics_curves': 'show_plumbotectonics_curves',
            'paleoisochrons': 'show_paleoisochrons',
            'model_age_lines': 'show_model_age_lines',
            'isochrons': 'show_isochrons',
            'growth_curves': 'show_growth_curves',
        }

        def _resolve_visible(style_key):
            if style_key in style_visibility:
                return style_visibility[style_key]
            toggle_attr = legacy_category_to_toggle.get(style_key)
            if toggle_attr:
                return bool(getattr(app_state, toggle_attr, True))
            return True

        def _set_artist_visible(style_key, artist):
            if artist is None:
                return
            try:
                artist.set_visible(_resolve_visible(style_key))
            except Exception as exc:
                logger.debug("Failed to set visibility for %s: %s", style_key, exc)

        for style_key, payload in overlay_artists.items():
            if isinstance(payload, dict):
                # Backward compatibility for historical nested structure.
                for artists in payload.values():
                    for artist in artists or []:
                        _set_artist_visible(style_key, artist)
                continue
            for artist in payload or []:
                _set_artist_visible(style_key, artist)

        def _set_label_visibility(entries, fallback_style_key):
            for entry in entries or []:
                if not isinstance(entry, dict):
                    continue
                text_artist = entry.get('text')
                style_key = entry.get('style_key') or fallback_style_key
                _set_artist_visible(style_key, text_artist)

        _set_label_visibility(getattr(app_state, 'overlay_curve_label_data', []), 'model_curve')
        _set_label_visibility(getattr(app_state, 'paleoisochron_label_data', []), 'paleoisochron')
        _set_label_visibility(getattr(app_state, 'plumbotectonics_label_data', []), 'plumbotectonics_curve')
        _set_label_visibility(getattr(app_state, 'plumbotectonics_isoage_label_data', []), 'paleoisochron')

        canvas = None
        if app_state.fig is not None and app_state.fig.canvas is not None:
            canvas = app_state.fig.canvas
        elif getattr(app_state, 'canvas', None) is not None:
            canvas = app_state.canvas
        if canvas is not None:
            canvas.draw_idle()

    except Exception as e:
        logger.warning(f"Failed to refresh overlay visibility: {e}")
