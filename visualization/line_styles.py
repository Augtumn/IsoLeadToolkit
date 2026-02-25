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


__all__ = ["resolve_line_style"]
