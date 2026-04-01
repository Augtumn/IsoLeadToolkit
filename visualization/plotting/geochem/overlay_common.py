"""Common overlay helper utilities for geochemistry plotting."""
from __future__ import annotations

from core import app_state, state_gateway

def _is_overlay_label_style_visible(style_key: str | None) -> bool:
    """Return whether labels for the style key should be visible."""
    style = str(style_key or '').strip()
    if style.startswith('plumbotectonics_curve:'):
        group_visibility = getattr(app_state, 'plumbotectonics_group_visibility', {}) or {}
        return bool(
            getattr(app_state, 'show_plumbotectonics_curves', True)
            and group_visibility.get(style, True)
        )

    toggle_map = {
        'model_curve': 'show_model_curves',
        'paleoisochron': 'show_paleoisochrons',
        'model_age_line': 'show_model_age_lines',
        'isochron': 'show_isochrons',
        'growth_curve': 'show_growth_curves',
        'plumbotectonics_curve': 'show_plumbotectonics_curves',
    }
    attr = toggle_map.get(style)
    if attr:
        return bool(getattr(app_state, attr, True))
    return True


def _register_overlay_artist(style_key, artist):
    if artist is None:
        return
    if not hasattr(app_state, 'overlay_artists'):
        state_gateway.set_attr('overlay_artists', {})
    app_state.overlay_artists.setdefault(style_key, []).append(artist)


def _resolve_label_options(style_key, fallback):
    style = getattr(app_state, 'line_styles', {}).get(style_key, {}) or {}
    resolved = dict(fallback)
    for key in resolved:
        if key not in style:
            continue
        value = style[key]
        if value is None:
            continue
        if isinstance(value, str) and value.strip() == '':
            continue
        resolved[key] = value
    return resolved


def _format_label_text(template, age=None, **kwargs):
    if not template:
        return None
    fmt_kwargs = dict(kwargs)
    if age is not None:
        fmt_kwargs['age'] = age
    try:
        return template.format(**fmt_kwargs)
    except Exception:
        return template


def _label_bbox(label_opts, edgecolor=None):
    if not label_opts.get('label_background', False):
        return None
    facecolor = label_opts.get('label_bg_color', '#ffffff')
    alpha = float(label_opts.get('label_bg_alpha', 0.85))
    return dict(
        boxstyle='round,pad=0.25',
        facecolor=facecolor,
        edgecolor=edgecolor or 'none',
        alpha=alpha
    )


def _register_overlay_curve_label(
    text_artist,
    x_vals,
    y_vals,
    label_text,
    position_mode,
    style_key=None
):
    if text_artist is None:
        return
    if not hasattr(app_state, 'overlay_curve_label_data'):
        state_gateway.set_attr('overlay_curve_label_data', [])
    app_state.overlay_curve_label_data.append({
        'text': text_artist,
        'x_line': list(x_vals),
        'y_line': list(y_vals),
        'label_text': label_text,
        'position': position_mode or 'auto',
        'style_key': style_key,
    })
