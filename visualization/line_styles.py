"""Line style utilities for geochemical overlays."""
from __future__ import annotations


def resolve_line_style(app_state, style_key: str, fallback: dict) -> dict:
    """Resolve line style with app_state overrides."""
    style = {}
    try:
        style = getattr(app_state, 'line_styles', {}).get(style_key, {}) or {}
    except Exception:
        style = {}

    resolved = dict(fallback)
    for key, value in style.items():
        if key == 'color':
            if value is not None and value != '':
                resolved['color'] = value
        elif value is not None:
            resolved[key] = value
    return resolved


def ensure_line_style(app_state, style_key: str, fallback: dict) -> dict:
    """Ensure a line style entry exists and return the resolved style."""
    if not hasattr(app_state, 'line_styles'):
        app_state.line_styles = {}
    style_ref = app_state.line_styles.setdefault(style_key, {})
    for key, value in fallback.items():
        if key not in style_ref:
            style_ref[key] = value
    return resolve_line_style(app_state, style_key, fallback)


__all__ = ["resolve_line_style", "ensure_line_style"]
