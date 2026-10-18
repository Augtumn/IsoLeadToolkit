"""Fitting a panel's view to the points it draws.

The numbers a fit needs - the finite points of an axes, and the limits that frame them - used to live in the canvas
mixin, so testing them meant building a window. They are pure here: an axes in, limits out. The mixin keeps the part
that is genuinely its own, which panels to frame and whether a view the user set may be touched.
"""
from __future__ import annotations

import logging
import math

logger = logging.getLogger(__name__)


def scatter_bounds(axis):
    """``(xs, ys, zs)`` of every finite point the axes currently draws.

    A point that cannot be read is left out and said so: this walks every point of every collection, so the report is
    one line per unreadable point rather than a count that hides which one it was - and the common case, a point with
    a NaN coordinate, is filtered without a report because that is data, not a failure.
    """
    xs: list[float] = []
    ys: list[float] = []
    zs: list[float] = []
    for collection in getattr(axis, "collections", []) or []:
        try:
            offsets = collection.get_offsets()
        except Exception as err:
            logger.warning("A collection could not be read for the fitted view: %s", err)
            continue
        for point in offsets if offsets is not None else []:
            try:
                x, y = float(point[0]), float(point[1])
            except (TypeError, ValueError, IndexError) as err:
                logger.warning("A point could not be read for the fitted view: %s", err)
                continue
            if not (math.isfinite(x) and math.isfinite(y)):
                continue
            xs.append(x)
            ys.append(y)
            if len(point) > 2:
                try:
                    z = float(point[2])
                except (TypeError, ValueError) as err:
                    logger.warning("A point's depth could not be read for the fitted view: %s", err)
                    continue
                if math.isfinite(z):
                    zs.append(z)
    return xs, ys, zs


def fit_axes(mode, axis) -> bool:
    """Frame *axis* around the points it draws; True when something was framed."""
    name = getattr(axis, "name", "")
    if name == "ternary" or str(mode).strip().upper() == "TERNARY":
        # The whole triangle is the widest view a ternary diagram has.
        axis.set_ternary_lim(0.0, 1.0, 0.0, 1.0, 0.0, 1.0)
        return True
    xs, ys, zs = scatter_bounds(axis)
    if not xs:
        return False
    if name == "3d":
        axis.set_xlim(min(xs), max(xs))
        axis.set_ylim(min(ys), max(ys))
        if zs:
            axis.set_zlim(min(zs), max(zs))
        return True
    span_x = max(xs) - min(xs)
    span_y = max(ys) - min(ys)
    pad_x = span_x * 0.05 if span_x > 0 else 1.0
    pad_y = span_y * 0.05 if span_y > 0 else 1.0
    axis.set_xlim(min(xs) - pad_x, max(xs) + pad_x)
    axis.set_ylim(min(ys) - pad_y, max(ys) + pad_y)
    return True


def panel_targets(windows, fallback_ax, fallback_mode):
    """The ``(mode, axes)`` a fit should frame: one per panel window, else the single figure's."""
    targets = []
    for record in list(windows or []):
        axis = record.axes
        if axis is not None:
            targets.append((record.mode, axis))
    if not targets and fallback_ax is not None:
        targets.append((str(fallback_mode or ""), fallback_ax))
    return targets
