"""Keep the hover tooltip above every other artist.

The tooltip is recreated by each render, while data layers are re-stacked from the
legend order and overlays (e.g. the selected isochron) are drawn at zorder 100/101.
A measured zorder alone is not enough, because artists added after the tooltip would
not be included in the measurement, so the tooltip also has a floor well above the
overlays.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

TOOLTIP_ZORDER_OFFSET = 1
#: Above the overlays (100/101) and any legend-driven stacking (single digits).
TOOLTIP_MIN_ZORDER = 1000
#: zorder of the tooltip's arrow, kept just below the box.
TOOLTIP_ARROW_ZORDER = TOOLTIP_MIN_ZORDER - 1


def raise_tooltip_above_data(ax, annotation) -> None:
    """Put *annotation* (and its arrow) above every other artist of *ax*.

    Idempotent: the result only depends on the current maximum, so repeated calls
    cannot inflate the z-orders.
    """
    if ax is None or annotation is None:
        return

    highest = 0.0
    arrow = getattr(annotation, "arrow_patch", None)
    for artist in ax.get_children():
        if artist is annotation or (arrow is not None and artist is arrow):
            continue
        try:
            highest = max(highest, float(artist.get_zorder()))
        except Exception:
            continue

    annotation.set_zorder(max(highest + TOOLTIP_ZORDER_OFFSET, TOOLTIP_MIN_ZORDER))
    if arrow is not None:
        arrow.set_zorder(annotation.get_zorder() - TOOLTIP_ZORDER_OFFSET)

def place_tooltip(annotation, x: float, y: float) -> None:
    """Point *annotation* at (x, y) with its box placed where it covers least.

    The offset used to be a fixed (20, 20) points - up and to the right of the point - so near the top or right
    edge the box left the axes and was clipped, and elsewhere it covered the data it described. The box now goes
    away from the edge the point is nearest: in the right half it opens to the left, in the upper half it opens
    downward.

    Only the annotation moves. The axes limits are not touched: a tooltip must never cost the chart its view.
    """
    annotation.xy = (x, y)
    ax = getattr(annotation, "axes", None)
    try:
        x0, x1 = ax.get_xlim()
        y0, y1 = ax.get_ylim()
    except Exception as err:
        logger.warning(
            "Could not read the axes limits for the tooltip; using the default corner: %s", err
        )
        annotation.set_position((20, 20))
        return
    right_half = x1 > x0 and (x - x0) > (x1 - x0) / 2.0
    upper_half = y1 > y0 and (y - y0) > (y1 - y0) / 2.0
    # The box grows away from the point, not over it: with the default baseline anchor it extended downwards and
    # covered the very point it described, which the user saw as the tooltip hiding the selected sample.
    annotation.set_ha("right" if right_half else "left")
    annotation.set_va("top" if upper_half else "bottom")
    annotation.set_position((-20 if right_half else 20, -28 if upper_half else 20))
