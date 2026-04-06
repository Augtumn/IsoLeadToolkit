"""Line style utilities for geochemical overlays."""
from __future__ import annotations

from core import app_state as _global_app_state, state_gateway


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
    state = app_state
    if not hasattr(state, 'line_styles') or getattr(state, 'line_styles') is None:
        if state is _global_app_state:
            state_gateway.set_line_styles({})
        else:
            setattr(state, 'line_styles', {})

    if state is _global_app_state:
        current = dict(getattr(state, 'line_styles', {}) or {})
        style_ref = dict(current.get(style_key, {}) or {})
        changed = False
        for key, value in fallback.items():
            if key not in style_ref:
                style_ref[key] = value
                changed = True
        if changed or style_key not in current:
            current[style_key] = style_ref
            state_gateway.set_line_styles(current)
    else:
        style_ref = state.line_styles.setdefault(style_key, {})
        for key, value in fallback.items():
            if key not in style_ref:
                style_ref[key] = value
    return resolve_line_style(state, style_key, fallback)


__all__ = ["resolve_line_style", "ensure_line_style"]
