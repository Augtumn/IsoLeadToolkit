"""Overlay style and visibility refresh helpers."""
from __future__ import annotations

import logging

from core import app_state
from ..legend_model import OVERLAY_TOGGLE_MAP

logger = logging.getLogger(__name__)


def refresh_overlay_styles():
    """Refresh overlay curve/label styles without full re-render.

    Updates line styles (color, width, linestyle, alpha) for overlay artists
    stored in app_state.overlay_artists based on current app_state.line_styles.
    """
    if app_state.fig is None or app_state.ax is None:
        return

    try:
        overlay_artists = getattr(app_state, 'overlay_artists', {})
        line_styles = getattr(app_state, 'line_styles', {})

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
                        if hasattr(artist, 'set_color') and color is not None:
                            artist.set_color(color)
                        if hasattr(artist, 'set_linewidth'):
                            artist.set_linewidth(linewidth)
                        if hasattr(artist, 'set_linestyle'):
                            artist.set_linestyle(linestyle)
                        if hasattr(artist, 'set_alpha'):
                            artist.set_alpha(alpha)
                    except Exception as e:
                        logger.debug("Failed to update artist in %s/%s: %s", category, key, e)

        if app_state.fig.canvas is not None:
            app_state.fig.canvas.draw_idle()

    except Exception as e:
        logger.warning("Failed to refresh overlay styles: %s", e)


def refresh_overlay_visibility():
    """Refresh overlay visibility based on app_state toggle flags."""
    if app_state.fig is None or app_state.ax is None:
        return

    try:
        overlay_artists = getattr(app_state, 'overlay_artists', {}) or {}

        style_visibility = {
            style_key: bool(getattr(app_state, toggle_attr, True))
            for style_key, toggle_attr in OVERLAY_TOGGLE_MAP.items()
        }
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
            if isinstance(style_key, str) and style_key.startswith('plumbotectonics_curve:'):
                group_visibility = getattr(app_state, 'plumbotectonics_group_visibility', {}) or {}
                return bool(
                    getattr(app_state, 'show_plumbotectonics_curves', True)
                    and group_visibility.get(style_key, True)
                )
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
        logger.warning("Failed to refresh overlay visibility: %s", e)
