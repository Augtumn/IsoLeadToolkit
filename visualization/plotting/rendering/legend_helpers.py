"""Legend construction and placement helpers for rendering."""
from __future__ import annotations

import logging

from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from core import app_state, state_gateway, translate
from visualization.line_styles import resolve_line_style

from ..legend_model import group_legend_items, overlay_legend_items
from ..style import _legend_columns_for_layout, _legend_layout_config, _style_legend

logger = logging.getLogger(__name__)


def _notify_legend_panel(title, handles, labels):
    callback = getattr(app_state, 'legend_update_callback', None)
    if callable(callback):
        try:
            callback(title, handles, labels)
        except Exception:
            pass


def _build_legend_proxies(handles, labels):
    """Build proxy legend handles from group_legend_items data."""
    items = group_legend_items(all_groups=list(labels))
    use_patch = any(isinstance(h, Patch) for h in handles)
    proxies = []
    for item in items:
        color = item['color']
        if use_patch:
            proxies.append(Patch(facecolor=color, edgecolor='none'))
        else:
            proxies.append(
                Line2D(
                    [0],
                    [0],
                    marker=item['marker'],
                    linestyle='None',
                    markerfacecolor=color,
                    markeredgecolor=getattr(app_state, 'scatter_edgecolor', '#1e293b'),
                    markeredgewidth=getattr(app_state, 'scatter_edgewidth', 0.4),
                    markersize=8,
                )
            )
    return proxies


def _build_overlay_legend_entries(actual_algorithm):
    """Build legend entries for geochemistry overlay curves."""
    entries = []
    for item in overlay_legend_items(actual_algorithm=actual_algorithm):
        style = resolve_line_style(app_state, item['style_key'], item['fallback'])
        color = style.get('color') or item['default_color']
        handle = Line2D(
            [0], [0],
            color=color,
            linewidth=style['linewidth'],
            linestyle=style['linestyle'],
            alpha=style['alpha'],
        )
        entries.append((handle, translate(item['label_key'])))
    return entries


def _place_inline_legend(
    ax, group_col, legend_handles, legend_labels,
    *, show_marginal_kde=False, scatters=None, is_kde_mode=False,
):
    """Place in-plot legend and notify the outside legend panel."""
    state_gateway.set_attrs(
        {
            'legend_last_title': group_col,
            'legend_last_handles': legend_handles,
            'legend_last_labels': legend_labels,
        }
    )
    _notify_legend_panel(group_col, legend_handles, legend_labels)

    n_cats = len(legend_labels)
    if n_cats > 30:
        logger.info('Too many categories for standard legend. Use Control Panel legend.')
        return

    inside_location = getattr(app_state, 'legend_position', None)
    if not inside_location or str(inside_location).startswith('outside_'):
        return

    location_key = inside_location
    auto_ncol = _legend_columns_for_layout(legend_labels, ax, location_key)
    if auto_ncol is None:
        ncol = app_state.legend_columns if getattr(app_state, 'legend_columns', 0) > 0 else (2 if n_cats > 15 else 1)
    else:
        ncol = auto_ncol

    legend_kwargs = {
        'title': group_col,
        'frameon': True,
        'fancybox': True,
        'ncol': ncol,
    }

    loc, bbox, mode, borderaxespad = _legend_layout_config(
        ax, show_marginal_kde=show_marginal_kde, location_key=location_key,
    )
    legend_kwargs['loc'] = loc
    legend_kwargs['bbox_to_anchor'] = bbox if bbox else None
    if mode:
        legend_kwargs['mode'] = mode
    if borderaxespad is not None:
        legend_kwargs['borderaxespad'] = borderaxespad

    legend = ax.legend(handles=legend_handles, labels=legend_labels, **legend_kwargs)

    if legend is not None and bbox:
        try:
            legend.set_bbox_to_anchor(bbox, transform=ax.transAxes)
        except Exception:
            pass

    _style_legend(legend, show_marginal_kde=show_marginal_kde, location_key=location_key)

    if legend is not None and scatters and not is_kde_mode:
        try:
            for leg_patch, sc in zip(legend.get_patches(), scatters):
                app_state.legend_to_scatter[leg_patch] = sc
        except Exception:
            pass


def _render_legend(actual_algorithm, group_col, unique_cats, scatters):
    try:
        handles = []
        labels = []
        is_kde_mode = getattr(app_state, 'show_kde', False)
        show_marginal_kde = getattr(app_state, 'show_marginal_kde', False)

        if is_kde_mode:
            for cat in unique_cats:
                color = app_state.current_palette[cat]
                patch = Patch(facecolor=color, edgecolor='none', label=cat, alpha=0.6)
                handles.append(patch)
                labels.append(cat)

        legend_handles = handles if handles else list(scatters)
        legend_labels = labels if labels else list(unique_cats)
        for handle, label in _build_overlay_legend_entries(actual_algorithm):
            if label in legend_labels:
                continue
            legend_handles.append(handle)
            legend_labels.append(label)

        _place_inline_legend(
            app_state.ax,
            group_col,
            legend_handles,
            legend_labels,
            show_marginal_kde=show_marginal_kde,
            scatters=scatters,
            is_kde_mode=is_kde_mode,
        )
    except Exception as err:
        logger.warning('Legend creation error: %s', err)
