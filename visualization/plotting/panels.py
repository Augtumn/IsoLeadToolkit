"""What a window needs to know about panels.

The panels themselves are independent child windows, one figure each
(:mod:`ui.main_window_parts.mdi_panels`); this module keeps the two facts the rest of the
application shares about them - how many a window may show, and which Matplotlib projection a
render mode asks for. It is pure, so it is tested without a figure.
"""
from __future__ import annotations

#: Render modes that need a specific Matplotlib projection.
PROJECTIONS: dict[str, str] = {
    "3D": "3d",
    "TERNARY": "ternary",
}

#: The largest number of panels one window may show.
MAX_PANELS = 9


def projection_for(mode: object) -> str | None:
    """The Matplotlib projection *mode* needs, or ``None`` for an ordinary 2D axes."""
    return PROJECTIONS.get(str(mode or "").strip().upper())
