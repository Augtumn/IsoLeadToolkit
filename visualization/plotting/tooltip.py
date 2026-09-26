"""Keep the hover tooltip above every other artist.

The tooltip is recreated by each render, while data layers are re-stacked from the
legend order and overlays (e.g. the selected isochron) are drawn at zorder 100/101.
A measured zorder alone is not enough, because artists added after the tooltip would
not be included in the measurement, so the tooltip also has a floor well above the
overlays.
"""
from __future__ import annotations

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
