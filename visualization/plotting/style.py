"""Style helpers for plotting (facade)."""
from __future__ import annotations

from typing import Any

from core import app_state
from .event_bridge import refresh_selection_overlay_safe
from .styling.core import _apply_current_style, _apply_axis_text_style, _enforce_plot_style
from .styling.legend import _legend_columns_for_layout, _legend_layout_config, _style_legend
from .styling.overlays import refresh_overlay_styles, refresh_overlay_visibility


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
    except Exception:
        pass

    try:
        fig.set_constrained_layout(True)
        fig.set_constrained_layout_pads(
            w_pad=w_pad,
            h_pad=h_pad,
            wspace=wspace,
            hspace=hspace,
        )
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
        # Keep title show/hide responsive via style-only refresh.
        if target_ax is ax:
            try:
                show_title = bool(getattr(app_state, 'show_plot_title', True))
                title_pad = float(getattr(app_state, 'title_pad', 20.0))
                current_title = getattr(app_state, 'current_plot_title', '') or target_ax.get_title()
                if show_title:
                    target_ax.set_title(current_title, pad=title_pad)
                else:
                    target_ax.set_title("")
            except Exception:
                pass

    try:
        base_size = getattr(app_state, 'plot_marker_size', 60)
        base_alpha = getattr(app_state, 'plot_marker_alpha', 0.8)
        edgecolor = getattr(app_state, 'scatter_edgecolor', '#1e293b')
        edgewidth = getattr(app_state, 'scatter_edgewidth', 0.4)
        show_edge = bool(getattr(app_state, 'scatter_show_edge', True))
        resolved_edgecolor = edgecolor if show_edge else 'none'
        resolved_edgewidth = edgewidth if show_edge else 0.0

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
                sc.set_edgecolor(resolved_edgecolor)
                sc.set_linewidths(resolved_edgewidth)
            except Exception:
                pass
    except Exception:
        pass

    try:
        if getattr(app_state, 'selected_indices', None):
            refresh_selection_overlay_safe()
    except Exception:
        pass

    if fig is not None and fig.canvas:
        try:
            fig.canvas.draw_idle()
        except Exception:
            pass


# refresh_overlay_styles and refresh_overlay_visibility are re-exported from styling.overlays.
