"""Isochron label helpers and refresh routines."""
from __future__ import annotations

import logging
from typing import Any

from core import app_state, state_gateway
from ..label_layout import position_curve_label, apply_adjust_text_to_labels
from .overlay_helpers import _is_overlay_label_style_visible

logger = logging.getLogger(__name__)

def _build_isochron_label(result_dict: dict[str, Any]) -> str:
    """根据 isochron_label_options 动态构建等时线标注文本。"""
    opts = app_state.isochron_label_options
    parts = []
    age = result_dict.get('age')
    if age is None:
        age = result_dict.get('age_ma')
    if opts.get('show_age', True) and age is not None and age >= 0:
        parts.append(f"{age:.0f} Ma")
    if opts.get('show_n_points', True) and result_dict.get('n_points'):
        parts.append(f"n={result_dict['n_points']}")
    if opts.get('show_mswd', False) and result_dict.get('mswd') is not None:
        parts.append(f"MSWD={result_dict['mswd']:.2f}")
    if opts.get('show_r_squared', False) and result_dict.get('r_squared') is not None:
        parts.append(f"R²={result_dict['r_squared']:.3f}")
    if opts.get('show_slope', False) and result_dict.get('slope') is not None:
        parts.append(f"m={result_dict['slope']:.4f}")
    if opts.get('show_intercept', False) and result_dict.get('intercept') is not None:
        parts.append(f"b={result_dict['intercept']:.4f}")
    return ", ".join(parts) if parts else ""

def refresh_paleoisochron_labels(ax: Any = None) -> None:
    """Refresh paleoisochron label positions after zoom/pan.

    The axes to lay the labels out on. It defaults to the state's axes, which is what a
    single-figure window needs; a window showing several panels passes the axes of the panel whose
    view moved, because the state only ever mirrors one of them - laying the labels out on that one
    put them on another panel's figure, where they were not visible at all.
    """
    if ax is None:
        ax = app_state.ax
    if ax is None:
        return
    if bool(app_state.overlay_label_refreshing):
        return

    state_gateway.set_overlay_label_refreshing(True)
    try:
        adjusted_labels = []

        # This axes' own labels first: the state's list belongs to whichever panel rendered last,
        # so laying the others out from it used another panel's artists.
        label_data = getattr(ax, "_paleoisochron_label_data", None)
        if not label_data:
            label_data = app_state.paleoisochron_label_data
        if not label_data:
            label_data = []

        for entry in label_data:
            text_artist = entry.get('text')
            if text_artist is None:
                continue
            # Only the labels drawn on this axes: the data is one list of artists belonging to
            # different figures, and laying another panel's label out on this axes moved it to the
            # wrong place - which is why only one panel's labels came back into view.
            if getattr(text_artist, 'axes', None) is not ax:
                continue
            style_key = entry.get('style_key') or 'paleoisochron'
            if not _is_overlay_label_style_visible(style_key):
                try:
                    text_artist.set_visible(False)
                except Exception as err:
                    logger.warning("refresh_paleoisochron_labels failed: %s", err)
                continue
            position_curve_label(
                ax,
                text_artist,
                mode='paleo',
                slope=entry.get('slope', 0),
                intercept=entry.get('intercept', 0),
                age=entry.get('age'),
                label_text=entry.get('label_text'),
                position_mode=entry.get('position', 'auto'),
            )
            try:
                if text_artist.get_visible():
                    adjusted_labels.append(text_artist)
            except Exception as err:
                logger.warning("refresh_paleoisochron_labels failed: %s", err)

        curve_labels = app_state.plumbotectonics_label_data
        for entry in curve_labels:
            text_artist = entry.get('text')
            if text_artist is None:
                continue
            style_key = entry.get('style_key') or 'plumbotectonics_curve'
            if not _is_overlay_label_style_visible(style_key):
                try:
                    text_artist.set_visible(False)
                except Exception as err:
                    logger.warning("refresh_paleoisochron_labels failed: %s", err)
                continue
            position_curve_label(
                ax,
                text_artist,
                mode='curve_left',
                x_vals=entry.get('x_vals', entry.get('x_line', [])),
                y_vals=entry.get('y_vals', entry.get('y_line', [])),
                position_mode=entry.get('position', 'auto'),
            )
            try:
                if text_artist.get_visible():
                    adjusted_labels.append(text_artist)
            except Exception as err:
                logger.warning("refresh_paleoisochron_labels failed: %s", err)

        isoage_labels = app_state.plumbotectonics_isoage_label_data
        for entry in isoage_labels:
            text_artist = entry.get('text')
            if text_artist is None:
                continue
            style_key = entry.get('style_key') or 'paleoisochron'
            if not _is_overlay_label_style_visible(style_key):
                try:
                    text_artist.set_visible(False)
                except Exception as err:
                    logger.warning("refresh_paleoisochron_labels failed: %s", err)
                continue
            position_curve_label(
                ax,
                text_artist,
                mode='isoage',
                x_line=entry.get('x_line', []),
                y_line=entry.get('y_line', []),
                age_ma=entry.get('age'),
                label_text=entry.get('label_text'),
                position_mode=entry.get('position', 'auto'),
            )
            try:
                if text_artist.get_visible():
                    adjusted_labels.append(text_artist)
            except Exception as err:
                logger.warning("refresh_paleoisochron_labels failed: %s", err)

        curve_labels = app_state.overlay_curve_label_data
        for entry in curve_labels:
            text_artist = entry.get('text')
            if text_artist is None:
                continue
            style_key = entry.get('style_key') or 'model_curve'
            if not _is_overlay_label_style_visible(style_key):
                try:
                    text_artist.set_visible(False)
                except Exception as err:
                    logger.warning("refresh_paleoisochron_labels failed: %s", err)
                continue
            position_curve_label(
                ax,
                text_artist,
                mode='isoage',
                x_line=entry.get('x_line', []),
                y_line=entry.get('y_line', []),
                label_text=entry.get('label_text'),
                position_mode=entry.get('position', 'auto'),
            )
            try:
                if text_artist.get_visible():
                    adjusted_labels.append(text_artist)
            except Exception as err:
                logger.warning("refresh_paleoisochron_labels failed: %s", err)

        # adjustText decides where a label fits from the text's measured pixel extent, and that
        # only exists after the figure has been drawn. A panel figure is created fresh, so its
        # extents were empty and the labels were pushed far outside the view - exactly what was
        # reported once the plots became child windows of their own.
        try:
            ax.figure.canvas.draw()
        except Exception as err:
            logger.warning("Could not draw before laying out the labels: %s", err)
        apply_adjust_text_to_labels(ax, adjusted_labels)
    finally:
        state_gateway.set_overlay_label_refreshing(False)

