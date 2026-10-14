"""The axis-scale lock: keep a chart's ranges while the data behind it changes.

Comparing two datasets means drawing both on the same axes, and the render path fits the axes to
whatever it was handed - ``autoscale`` in the raw 2-D renderer, ``set_autoscale_on(True)`` for an
embedding, :func:`configure_ternary_axis` for the triangle - so a second render throws the first
one's ranges away. This module records the ranges once and puts them back on every later render
while the lock is on; while it is off it does nothing at all and the axes autoscale as before.

**Where it hooks in.** ``draw_event`` on the canvas, and that choice is deliberate: it is the one
place *every* render ends at, whatever started it - the render use case, an asynchronous embedding
worker, a KDE or style toggle, a panel edit, a direct ``canvas.draw()`` in a test - and it is the
same hook the ternary tick refresh already uses. Hooking there leaves the renderers untouched:
they autoscale exactly as they always did and the lock corrects the frame that is about to be
shown. The single alternative - the end of ``RenderPlotUseCase.execute()`` - only sees the renders
that go through that one use case, and a re-render it does not know about would silently lose the
lock. The correction runs again only when the axes actually drifted, and only a correction that
took asks for the repaint that shows it, so a draw cannot loop.

**What is recorded.** The ranges are keyed per axes kind - ``"2d"`` for the cartesian x/y pair,
``"ternary"`` for the six-value view window - because ``_ensure_axes`` replaces the axes, and with
it the numbers that make sense, when the plot type changes. The first draw of a kind the lock has
no record for is what records it, so "the first render after locking defines the ranges" also
holds when the lock is switched on before anything is drawn.

**The ternary plot keeps its own rules.** The equilateral default and "a zoom survives a render"
belong to the renderer, not here: the locked window is drawn with
``apply_ternary_zoom_window(..., store=False)``, which moves the drawing without becoming the
window the renderer keeps, so a zoom taken before the lock is still there when it is switched off
again. While the lock is on it wins over a zoom gesture - the gesture moves the window and the
next draw puts the locked one back - because that is what "the ranges do not move" has to mean.
"""
from __future__ import annotations

import logging
import math
from typing import Any

from core import app_state, state_gateway

logger = logging.getLogger(__name__)

#: Key of the cartesian x/y pair in ``app_state.locked_axis_limits``.
CARTESIAN = "2d"
#: Key of the six-value ternary view window in ``app_state.locked_axis_limits``.
TERNARY = "ternary"

#: Where the draw handler is remembered on the canvas, so enabling the lock twice cannot stack two.
_HANDLER_ATTR = "_axis_scale_lock_handler"


def is_ternary_axes(axes: Any) -> bool:
    """True for mpltern axes, which have their own limit API."""
    return axes is not None and hasattr(axes, "set_ternary_lim")


def current_axes() -> Any:
    """The axes the lock applies to: the live one, or None before the first render."""
    return app_state.ax


def axes_kind(axes: Any) -> str:
    """The record key *axes* belongs under."""
    return TERNARY if is_ternary_axes(axes) else CARTESIAN


def read_axis_limits(axes: Any = None) -> dict[str, Any]:
    """The ranges *axes* (default ``app_state.ax``) currently draws, in the recorded shape.

    An empty mapping means "nothing readable here" - no axes yet, or limits that could not be
    read - and the callers treat that as "nothing to record", never as a range of its own.
    """
    axes = axes if axes is not None else current_axes()
    if axes is None:
        return {}
    if is_ternary_axes(axes):
        from visualization.plotting.ternary import ternary_axes_limits

        window = ternary_axes_limits(axes)
        if window is None:
            return {}
        return {TERNARY: [float(value) for value in window]}
    try:
        xlim = [float(value) for value in axes.get_xlim()]
        ylim = [float(value) for value in axes.get_ylim()]
    except Exception as err:
        logger.warning("Could not read the axis limits: %s", err)
        return {}
    if len(xlim) != 2 or len(ylim) != 2:
        return {}
    return {CARTESIAN: {"xlim": xlim, "ylim": ylim}}


def _same_pair(drawn: Any, recorded: Any) -> bool:
    """True when two numeric pairs (or six-value windows) describe the same range."""
    try:
        if drawn is None or recorded is None or len(drawn) != len(recorded):
            return False
        return all(
            math.isclose(float(one), float(other), rel_tol=1e-9, abs_tol=1e-12)
            for one, other in zip(drawn, recorded)
        )
    except (TypeError, ValueError):
        return False


def _same_ranges(drawn: Any, recorded: Any) -> bool:
    """True when what is drawn and what was recorded are the same ranges."""
    if not isinstance(drawn, dict) or not isinstance(recorded, dict):
        return False
    if set(drawn) != set(recorded):
        return False
    for key, value in recorded.items():
        if key == CARTESIAN:
            other = drawn.get(key)
            if not isinstance(value, dict) or not isinstance(other, dict):
                return False
            if not _same_pair(other.get("xlim"), value.get("xlim")):
                return False
            if not _same_pair(other.get("ylim"), value.get("ylim")):
                return False
        elif not _same_pair(drawn.get(key), value):
            return False
    return True


def _recorded_for(recorded: dict, key: str) -> dict:
    """The part of *recorded* that describes *key*, as a one-entry mapping."""
    if isinstance(recorded, dict) and key in recorded:
        return {key: recorded[key]}
    return {}


def apply_axis_limits(limits: dict | None = None, axes: Any = None) -> bool:
    """Draw the recorded ranges on *axes*; True when they are what is drawn afterwards.

    The return value is the answer to "did it take", not "did we try": a window the renderer
    refuses (mpltern clips one that reaches past the triangle) reports False, which is what keeps
    the draw hook from asking for a repaint it would keep asking for forever.
    """
    axes = axes if axes is not None else current_axes()
    if axes is None:
        return False
    recorded = dict(
        limits
        if limits is not None
        else (app_state.locked_axis_limits or {})
    )
    if not recorded:
        return False

    key = axes_kind(axes)
    if key == TERNARY:
        window = recorded.get(TERNARY)
        if not window:
            return False
        from visualization.plotting.ternary import apply_ternary_zoom_window

        # store=False: the drawing moves to the locked window, the window the renderer keeps (an
        # explicit zoom) is left alone, so switching the lock off gives that one back.
        drawn = apply_ternary_zoom_window(axes, window, store=False)
        return drawn is not None and _same_pair(drawn, window)

    pair = recorded.get(CARTESIAN)
    if not isinstance(pair, dict):
        return False
    try:
        axes.set_xlim(*[float(value) for value in pair["xlim"]])
        axes.set_ylim(*[float(value) for value in pair["ylim"]])
    except Exception as err:
        logger.warning("Could not draw the locked axis limits: %s", err)
        return False
    return _same_ranges(read_axis_limits(axes), _recorded_for(recorded, CARTESIAN))


def apply_locked_axis_limits(axes: Any = None) -> bool:
    """Re-apply the recorded ranges while the lock is on; True when the frame has to be redrawn.

    This is what the draw hook calls on every draw. While the lock is off it returns immediately,
    which is the whole of "switching it off restores the old behaviour": nothing is read, nothing
    is written. The first draw of a kind with no record yet records what it draws instead of
    correcting it.
    """
    if not bool(app_state.axis_scale_locked):
        return False
    axes = axes if axes is not None else current_axes()
    if axes is None:
        return False

    recorded = dict(app_state.locked_axis_limits or {})
    key = axes_kind(axes)
    if key not in recorded:
        fresh = read_axis_limits(axes)
        if fresh:
            logger.info("Axis scale lock: recording %s ranges %s", key, fresh.get(key))
            state_gateway.set_locked_axis_limits({**recorded, **fresh})
        return False

    if _same_ranges(read_axis_limits(axes), _recorded_for(recorded, key)):
        return False
    return apply_axis_limits(recorded, axes)


class AxisScaleLockHandler:
    """The canvas' draw hook: puts the recorded ranges back while the lock is on."""

    def __init__(self, canvas: Any) -> None:
        self._canvas = canvas
        self._running = False
        #: The id ``mpl_connect`` returned, which is what ``mpl_disconnect`` needs.
        self.cid: Any = None

    def __call__(self, _event: Any = None) -> None:
        # Re-entrancy: the repaint asked for below draws again and would call this again. The
        # ranges are already applied by then, so one pass is enough.
        if self._running:
            return
        self._running = True
        try:
            if apply_locked_axis_limits():
                # The frame that was just rendered used the ranges the render chose; the locked
                # ranges are on the axes now, so this asks for the paint that shows them.
                self._canvas.draw_idle()
        except Exception as err:  # pragma: no cover - a lock must never break a draw
            logger.warning("The axis scale lock could not be applied: %s", err)
        finally:
            self._running = False


def axis_scale_lock_handler(canvas: Any) -> AxisScaleLockHandler | None:
    """The lock handler installed on *canvas*, or None while there is none."""
    return getattr(canvas, _HANDLER_ATTR, None)


def install_axis_scale_lock(canvas: Any) -> AxisScaleLockHandler | None:
    """Connect the draw hook to *canvas*, once; a repeated call reuses the handler."""
    if canvas is None:
        return None
    existing = axis_scale_lock_handler(canvas)
    if existing is not None:
        return existing

    handler = AxisScaleLockHandler(canvas)
    try:
        handler.cid = canvas.mpl_connect("draw_event", handler)
        setattr(canvas, _HANDLER_ATTR, handler)
    except Exception as err:
        logger.warning("Could not install the axis scale lock: %s", err)
        return None
    logger.info("Axis scale lock installed: canvas id=%s cid=%s", id(canvas), handler.cid)
    return handler


def uninstall_axis_scale_lock(canvas: Any) -> bool:
    """Drop the draw hook from *canvas*; True when there was one to drop.

    Off means off: with no hook connected there is nothing left that could touch the axes, so the
    next render autoscales exactly as it did before the lock ever existed.
    """
    handler = axis_scale_lock_handler(canvas)
    if handler is None:
        return False
    try:
        if handler.cid is not None:
            canvas.mpl_disconnect(handler.cid)
        setattr(canvas, _HANDLER_ATTR, None)
    except Exception as err:
        logger.warning("Could not remove the axis scale lock: %s", err)
        return False
    logger.info("Axis scale lock removed: canvas id=%s", id(canvas))
    return True


def enable_axis_scale_lock(canvas: Any = None) -> dict[str, Any]:
    """Turn the lock on: record what is drawn and start re-applying it on every render.

    Nothing readable yet (no axes) leaves the record empty on purpose - the first draw of the
    axes kind that appears is what defines the ranges then.
    """
    state_gateway.set_axis_scale_locked(True)
    recorded = read_axis_limits()
    state_gateway.set_locked_axis_limits(recorded)
    if canvas is not None:
        install_axis_scale_lock(canvas)
    logger.info("Axis scale lock on: recorded %s", sorted(recorded))
    return recorded


def disable_axis_scale_lock(canvas: Any = None) -> None:
    """Turn the lock off: drop the record and put the axes back to their unlocked view.

    The record goes first, so nothing can re-apply it, and the hook is disconnected with it.
    What is on screen is then the locked view until something draws again, so this also walks
    the axes back by hand: the ternary view returns to the whole triangle (or to the zoom that
    was there before the lock, which the lock deliberately left recorded on the axes), and a
    cartesian axes simply has autoscaling switched on again.
    """
    state_gateway.set_axis_scale_locked(False)
    state_gateway.set_locked_axis_limits({})
    uninstall_axis_scale_lock(canvas)

    axes = current_axes()
    if axes is None:
        return
    if is_ternary_axes(axes):
        from visualization.plotting.ternary import (
            apply_ternary_zoom_window,
            reset_ternary_view,
            stored_ternary_view_window,
        )

        window = stored_ternary_view_window(axes)
        try:
            if window is None:
                reset_ternary_view(axes)
            else:
                apply_ternary_zoom_window(axes, window, store=False)
        except Exception as err:
            logger.warning("Could not restore the ternary view: %s", err)
        return
    try:
        axes.set_autoscale_on(True)
    except Exception as err:
        logger.warning("Could not re-enable autoscaling: %s", err)
