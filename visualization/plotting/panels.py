"""What a window needs to know about panels.

The panels themselves are independent child windows, one figure each
(:mod:`ui.main_window_parts.mdi_panels`); this module keeps the two facts the rest of the
application shares about them - how many a window may show, and which Matplotlib projection a
render mode asks for. It is pure, so it is tested without a figure.
"""
from __future__ import annotations

#: The largest number of panels one window may show.
MAX_PANELS = 9


def projection_for(mode: object) -> str | None:
    """The Matplotlib projection *mode* needs, or ``None`` for an ordinary 2D axes.

    The answer comes from the one mode table, not from a second map kept here: a projection only this file
    knew about could disagree with the capabilities and no guard would notice. ``"2d"`` means the ordinary
    axes, which is what this has always returned for it.
    """
    from core.render_modes import RENDER_MODE_VALUES, capabilities_for

    # Case-insensitive, because callers and stored sessions have used both "3D" and "3d"; an unknown mode has
    # no projection, which is what this has always answered for it.
    text = str(mode or "").strip().lower()
    resolved = next((value for value in RENDER_MODE_VALUES if value.lower() == text), None)
    if resolved is None:
        return None
    projection = capabilities_for(resolved).projection
    return None if projection in (None, "", "2d") else projection
