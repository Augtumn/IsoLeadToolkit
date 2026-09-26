"""Style helpers for plotting (facade)."""
from __future__ import annotations
import logging

from typing import Any

from core import app_state
from .event_bridge import refresh_selection_overlay_safe
from .styling.core import _apply_current_style, _apply_axis_text_style, _enforce_plot_style
from .styling.legend import _legend_columns_for_layout, _legend_layout_config, _style_legend
from .styling.overlays import refresh_overlay_styles, refresh_overlay_visibility

logger = logging.getLogger(__name__)

_last_style_params: dict[str, Any] = {}

def configure_constrained_layout(
    fig: Any,
    *,
    w_pad: float = 0.02,
    h_pad: float = 0.02,
    wspace: float = 0.02,
    hspace: float = 0.02,
) -> None:
    """Configure constrained layout using modern engine API with fallback."""
    if fig is None:
        return

    try:
        set_layout_engine = getattr(fig, 'set_layout_engine', None)
        get_layout_engine = getattr(fig, 'get_layout_engine', None)
        if callable(set_layout_engine):
            set_layout_engine('constrained')
            if callable(get_layout_engine):
                layout_engine = get_layout_engine()
                if layout_engine is not None:
                    engine_set = getattr(layout_engine, 'set', None)
                    if callable(engine_set):
                        engine_set(
                            w_pad=w_pad,
                            h_pad=h_pad,
                            wspace=wspace,
                            hspace=hspace,
                        )
            return
    except Exception as err:
        logger.warning("configure_constrained_layout failed: %s", err)

    try:
        fig.set_constrained_layout(True)
        fig.set_constrained_layout_pads(
            w_pad=w_pad,
            h_pad=h_pad,
            wspace=wspace,
            hspace=hspace,
        )
    except Exception as err:
        logger.warning("configure_constrained_layout failed: %s", err)


def refresh_plot_style() -> None:
    """Refresh plot styling without recomputing embeddings."""
    _apply_current_style()

    ax = app_state.ax
    fig = app_state.fig

    axes = []
    if fig is not None:
        axes.extend(list(getattr(fig, 'axes', [])))
    if ax is not None and ax not in axes:
        axes.append(ax)

    for target_ax in axes:
        _enforce_plot_style(target_ax)
        _apply_axis_text_style(target_ax)
        _style_legend(target_ax.get_legend(), show_marginal_kde=app_state.show_marginal_kde)
        # Keep title show/hide responsive via style-only refresh.
        if target_ax is ax:
            try:
                show_title = bool(app_state.show_plot_title)
                title_pad = float(app_state.title_pad)
                current_title = getattr(app_state, 'current_plot_title', '') or target_ax.get_title()
                if show_title:
                    target_ax.set_title(current_title, pad=title_pad)
                else:
                    target_ax.set_title("")
            except Exception as err:
                logger.warning("refresh_plot_style failed: %s", err)

    try:
        base_size = app_state.plot_marker_size
        base_alpha = app_state.plot_marker_alpha
        edgecolor = app_state.scatter_edgecolor
        edgewidth = app_state.scatter_edgewidth
        show_edge = bool(app_state.scatter_show_edge)
        resolved_edgecolor = edgecolor if show_edge else 'none'
        resolved_edgewidth = edgewidth if show_edge else 0.0

        current_params = {
            'size': base_size,
            'alpha': base_alpha,
            'edgecolor': resolved_edgecolor,
            'edgewidth': resolved_edgewidth,
        }

        if current_params != _last_style_params:
            for sc in list(app_state.scatter_collections):
                if sc is None:
                    continue
                try:
                    # matplotlib >=3.10 rejects scalar sizes (len() of 0-d
                    # array raises TypeError); broadcast to per-point sizes.
                    sc.set_sizes([base_size] * len(sc.get_offsets()))
                    sc.set_alpha(base_alpha)
                    sc.set_edgecolor(resolved_edgecolor)
                    sc.set_linewidths(resolved_edgewidth)
                except Exception as err:
                    logger.warning("refresh_plot_style failed: %s", err)
            _last_style_params.update(current_params)
    except Exception as err:
        logger.warning("refresh_plot_style failed: %s", err)

    try:
        if app_state.selected_indices:
            refresh_selection_overlay_safe()
    except Exception as err:
        logger.warning("refresh_plot_style failed: %s", err)

    if fig is not None and fig.canvas:
        try:
            fig.canvas.draw_idle()
        except Exception as err:
            logger.warning("refresh_plot_style failed: %s", err)


# refresh_overlay_styles and refresh_overlay_visibility are re-exported from styling.overlays.
