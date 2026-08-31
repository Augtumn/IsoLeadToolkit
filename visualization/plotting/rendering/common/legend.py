"""Legend construction and placement helpers for rendering."""
from __future__ import annotations

import logging
from typing import Any

from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from core import app_state, state_gateway, translate
from visualization.line_styles import resolve_line_style

from ...legend_model import group_legend_items, overlay_legend_items
from ...style import _legend_columns_for_layout, _legend_layout_config, _style_legend

logger = logging.getLogger(__name__)


def _notify_legend_panel(title: str, handles: list[Any], labels: list[str]) -> None:
    callback = getattr(app_state, 'legend_update_callback', None)
    if callable(callback):
        try:
            callback(title, handles, labels)
        except Exception:
            pass


def _build_legend_proxies(handles: list[Any], labels: list[str]) -> list[Any]:
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


def _build_overlay_legend_entries(actual_algorithm: str) -> list[tuple[Line2D, str]]:
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


def _merge_parent_groups_for_inline(
    handles: list[Any],
    labels: list[str],
) -> tuple[list[Any], list[str]] | None:
    """Collapse parent-group children into single in-plot legend entries.

    Returns ``(merged_handles, merged_labels)`` or None when no parent
    groups exist. Overlay entries (Line2D handles) are passed through
    unchanged; each top-level parent becomes one entry using the parent's
    shared shape, followed by the ungrouped groups in their original order.
    """
    from matplotlib.lines import Line2D as _Line2D

    from visualization.plotting.grouping import (
        all_parents,
        parent_children,
        parent_shape,
    )

    parents = all_parents(app_state)
    if not parents:
        return None

    child_to_parent: dict[str, str] = {}
    for parent in parents:
        for child in parent_children(app_state, parent):
            child_to_parent[str(child)] = parent
    if not child_to_parent:
        return None

    group_handles: list[Any] = []
    group_labels: list[str] = []
    overlay_handles: list[Any] = []
    overlay_labels: list[str] = []
    for handle, label in zip(handles, labels):
        if isinstance(handle, _Line2D):
            overlay_handles.append(handle)
            overlay_labels.append(str(label))
        else:
            group_handles.append(handle)
            group_labels.append(str(label))

    merged_handles: list[Any] = []
    merged_labels: list[str] = []
    for parent in parents:
        color = '#94a3b8'
        for child in parent_children(app_state, parent):
            if str(child) in group_labels:
                color = app_state.current_palette.get(str(child), '#94a3b8')
                break
        marker = parent_shape(app_state, parent)
        merged_handles.append(
            Line2D(
                [0],
                [0],
                marker=marker,
                linestyle='None',
                markerfacecolor=color,
                markeredgecolor=getattr(app_state, 'scatter_edgecolor', '#1e293b'),
                markeredgewidth=getattr(app_state, 'scatter_edgewidth', 0.4),
                markersize=8,
            )
        )
        merged_labels.append(f"{translate('Parent')}: {parent}")

    for group_label, group_handle in zip(group_labels, group_handles):
        if group_label not in child_to_parent:
            merged_handles.append(group_handle)
            merged_labels.append(group_label)

    merged_handles.extend(overlay_handles)
    merged_labels.extend(overlay_labels)
    return merged_handles, merged_labels


def _place_inline_legend(
    ax: Any,
    group_col: str,
    legend_handles: list[Any],
    legend_labels: list[str],
    *,
    show_marginal_kde: bool = False,
    scatters: list[Any] | None = None,
    is_kde_mode: bool = False,
    inline_handles: list[Any] | None = None,
    inline_labels: list[str] | None = None,
) -> None:
    """Place in-plot legend and notify the outside legend panel.

    *inline_handles*/*inline_labels* optionally override what is drawn
    inside the plot (e.g. parent-merged entries) while the snapshot and the
    outside panel keep the full original list.
    """
    state_gateway.set_legend_snapshot(group_col, legend_handles, legend_labels)
    _notify_legend_panel(group_col, legend_handles, legend_labels)

    draw_handles = inline_handles if inline_handles is not None else legend_handles
    draw_labels = inline_labels if inline_labels is not None else legend_labels
    merged = inline_handles is not None

    n_cats = len(draw_labels)
    if n_cats > 30:
        logger.debug('Too many categories for standard legend. Use Control Panel legend.')
        return

    inside_location = getattr(app_state, 'legend_position', None)
    if not inside_location or str(inside_location).startswith('outside_'):
        return

    location_key = inside_location
    auto_ncol = _legend_columns_for_layout(draw_labels, ax, location_key)
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

    legend = ax.legend(handles=draw_handles, labels=draw_labels, **legend_kwargs)

    if legend is not None and bbox:
        try:
            legend.set_bbox_to_anchor(bbox, transform=ax.transAxes)
        except Exception:
            pass

    _style_legend(legend, show_marginal_kde=show_marginal_kde, location_key=location_key)

    # Only map patch->scatter when the entry order is untouched; parent
    # merging reorders entries so a zip would map wrongly.
    if legend is not None and scatters and not is_kde_mode and not merged:
        try:
            for leg_patch, sc in zip(legend.get_patches(), scatters):
                app_state.legend_to_scatter[leg_patch] = sc
        except Exception:
            pass


def _render_legend(
    actual_algorithm: str,
    group_col: str,
    unique_cats: list[str],
    scatters: list[Any],
) -> None:
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

        # In-plot legend honors parent groups: children collapse into one
        # entry per parent, which also keeps the entry count under the
        # 30-category cap (the outside panel keeps the full list).
        inline_handles = inline_labels = None
        if not is_kde_mode:
            merged = _merge_parent_groups_for_inline(legend_handles, legend_labels)
            if merged is not None:
                inline_handles, inline_labels = merged

        _place_inline_legend(
            app_state.ax,
            group_col,
            legend_handles,
            legend_labels,
            show_marginal_kde=show_marginal_kde,
            scatters=scatters,
            is_kde_mode=is_kde_mode,
            inline_handles=inline_handles,
            inline_labels=inline_labels,
        )
    except Exception as err:
        logger.warning('Legend creation error: %s', err)
