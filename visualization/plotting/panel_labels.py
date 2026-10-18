"""Laying the overlay labels out again after a view changes.

Only the labels: a full re-render would recompute the axes from the data and throw the user's zoom away. The label data
is one list of text artists belonging to different figures, so the panels to refresh are found from the artists
themselves, each laid out on its own axes.

A module function because the window (during a fit) and the zoom filter (after a wheel or a drag) both need it, and one
implementation is what keeps them in step. It lived in the canvas mixin; it is here so the zoom filter can use it
without importing the window that owns it.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def refresh_panel_labels(axes=None) -> None:
    """Lay every panel's overlay labels out again for the view it now has.

    Only the labels: a full re-render recomputes the axes from the data and throws the user's zoom
    away. The label data is one list of text artists belonging to different figures, so the panels
    to refresh are found from the artists themselves, each laid out on its own axes.

    A module function because both the window (during a fit) and the event filter (after a wheel or
    a drag) need it, and one implementation is what keeps them in step.
    """
    try:
        from visualization.plotting import refresh_paleoisochron_labels

        targets = []
        if axes is not None:
            targets.append(axes)
        for state in list(getattr(app_state, "plot_panel_states", []) or []):
            panel_axes = state.get("ax") if isinstance(state, dict) else None
            if panel_axes is not None and panel_axes not in targets:
                targets.append(panel_axes)
        for entry in list(getattr(app_state, "paleoisochron_label_data", None) or []):
            text = entry.get("text") if isinstance(entry, dict) else None
            owner = getattr(text, "axes", None)
            if owner is not None and owner not in targets:
                targets.append(owner)
        for target in targets:
            refresh_paleoisochron_labels(ax=target)
        # Repaint every panel whose labels were just moved: a label that moves without its canvas
        # being redrawn leaves the panel showing its old buffer, which looks blank until something
        # else triggers a repaint.
        for target in targets:
            figure = getattr(target, "figure", None)
            canvas = getattr(figure, "canvas", None)
            if canvas is not None:
                try:
                    canvas.draw_idle()
                except Exception as err:
                    logger.warning("Could not repaint a panel after moving its labels: %s", err)
        logger.info("Labels refreshed for %d panel(s)", len(targets))
    except Exception as err:
        logger.warning("Could not refresh the labels for the panel: %s", err)
