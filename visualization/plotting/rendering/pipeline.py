"""The one sequence every render follows.

Each renderer used to spell out the same steps in its own order - ensure the axes, prepare the data,
apply the style, clear, enforce the axes style, clear the plot state, build the palette, draw, marginal
KDE, legend, title and axis labels, restore the view, finish - and they drifted: one of them forgot to
restore the view at all, another re-implemented the title inline, a third did without the axis
configuration the others had.

Here the sequence is written once. A mode contributes only the parts that differ, through its adapter,
and the parts that must not differ - the view the user set, the plot state, the style, the error path -
cannot be forgotten by a mode because no mode writes them.
"""
from __future__ import annotations

import enum
import logging
from typing import Any

from .context import RenderContext
from .registry import ModeAdapter

logger = logging.getLogger(__name__)


class Ink(enum.Enum):
    """What a mode's draw produced."""

    #: The plot was drawn.
    DRAWN = "drawn"
    #: There was nothing to plot. Not a failure: the frame stays and the mode and legend selection
    #: are kept, because a render must not change the mode behind the user's back.
    EMPTY = "empty"
    #: The mode could not draw at all.
    FAILED = "failed"


def run(adapter: ModeAdapter, context: RenderContext) -> bool:
    """Draw one render of *context* with *adapter*, following the one sequence."""
    from core import app_state

    from ..core import _ensure_axes, _build_group_palette
    from ..styling.core import _apply_current_style, _enforce_plot_style
    from ..view_state import capture_view, mark_drawn, restore_view

    try:
        adapter.validate(context)

        captured = capture_view(context.axes)
        _ensure_axes(dimensions=adapter.axes_dimensions(context))
        # Ensuring the axes may have created one; from here the render draws into what exists.
        context = context.with_axes(app_state.ax)
        if context.axes is None:
            logger.error("Failed to configure the axes for %s", context.mode)
            return False

        prepared = adapter.prepare(context)
        if prepared is False or prepared is None:
            return False

        _apply_current_style()
        context.axes.clear()
        adapter.configure_axes(context)
        _enforce_plot_style(context.axes)
        app_state.clear_plot_state()

        _build_group_palette(adapter.groups(context, prepared))

        ink = adapter.draw(context, prepared)

        if ink is Ink.EMPTY:
            # The empty frame is still this mode's frame: name it, keep the mode, and tell the legend
            # panel, whose checkboxes have to match the selection that produced it.
            adapter.decorate(context, prepared)
            adapter.finish(context, prepared)
            return True

        if ink is not Ink.DRAWN:
            logger.error("No points were plotted in %s", context.mode)
            _repaint(context)
            return False

        adapter.marginal(context, prepared)
        adapter.legend(context, prepared)
        adapter.decorate(context, prepared)
        adapter.finish(context, prepared)

        # A restored view is not autoscaled away: the mode keeps the window the user set for the same
        # picture, and a mode that already restored it restores the same numbers again. Autoscale is
        # turned on only when there was nothing to restore - a new picture on a new axes - because
        # matplotlib's autoscale(enable=True) rescales immediately.
        token = context.token(*adapter.token(context))
        if not restore_view(context.axes, captured, token):
            try:
                context.axes.autoscale(enable=True, axis="both")
            except Exception as err:
                logger.warning("Could not autoscale %s: %s", context.mode, err)
        mark_drawn(context.axes, token)
        return True

    except Exception as err:
        logger.exception("%s plot failed: %s", context.mode, err)
        _repaint(context)
        return False


def _repaint(context: RenderContext) -> None:
    """Keep the canvas consistent with the state after a render gave up."""
    try:
        figure = context.figure
        if figure is not None and figure.canvas is not None:
            figure.canvas.draw_idle()
    except Exception as err:
        logger.warning("Could not repaint %s: %s", context.mode, err)
