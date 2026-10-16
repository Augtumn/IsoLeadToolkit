"""What a re-render keeps: the view, and what the axes it belongs to has drawn.

Every renderer clears its axes before drawing again, which throws the view away, so each one restores
the limits it captured - and each one decided *when* to restore on its own. They disagreed: 2D asked
whether the data columns matched, the embedding renderer asked what the application had drawn last (a
single global, which is wrong as soon as two panels draw different modes), and 3D captured nothing at
all, so a refresh threw its zoom away.

The rule is the same for every plot type and lives here: a view belongs to an axes, and it is restored
for the same content on the same axes. Anything else - a different projection, data columns or
algorithm - is a new view, and the renderer sets its own ranges.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

#: Where an axes remembers what it drew, so the next render can tell "same content" from "new view".
_DRAWN_ATTR = "_isotopes_drawn"


def capture_view(axes: Any) -> dict[str, Any] | None:
    """The ranges to keep from *axes*, or ``None`` when there is nothing to keep."""
    if axes is None:
        return None
    try:
        captured = {"xlim": axes.get_xlim(), "ylim": axes.get_ylim()}
        if getattr(axes, "name", "") == "3d":
            captured["zlim"] = axes.get_zlim()
        return captured
    except Exception as err:
        logger.warning("Could not read the view of an axes: %s", err)
        return None


def drawn_last(axes: Any) -> Any:
    """What *axes* drew last, or ``None`` when this renderer has not drawn it yet."""
    return getattr(axes, _DRAWN_ATTR, None)


def mark_drawn(axes: Any, token: Any) -> None:
    """Remember what *axes* drew, for the next render's decision about the view."""
    if axes is None:
        return
    try:
        setattr(axes, _DRAWN_ATTR, token)
    except Exception as err:
        logger.warning("Could not record what an axes drew: %s", err)


def restore_view(axes: Any, captured: dict[str, Any] | None, token: Any) -> bool:
    """Put *captured* back when *axes* drew *token* last; ``True`` when it did.

    The token is what identifies the content: the same token means the user is looking at the same
    kind of plot they zoomed, so their view is theirs. A different token is a new view.
    """
    if axes is None or not captured:
        return False
    if token is None or drawn_last(axes) != token:
        return False
    try:
        axes.set_xlim(captured["xlim"])
        axes.set_ylim(captured["ylim"])
        if "zlim" in captured and hasattr(axes, "set_zlim"):
            axes.set_zlim(captured["zlim"])
        return True
    except Exception as err:
        logger.warning("Could not restore the view of an axes: %s", err)
        return False
