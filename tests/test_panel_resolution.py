"""A panel is found by its figure, not only by the axes it was drawn into.

Reported: with several windows open, the tooltip and the box selection did nothing in some of them. The panel
record was looked up by its axes alone, and the axes of a panel is rebuilt when its plot type changes - so the
panels that had been rebuilt stopped resolving, and their handlers returned early.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

from matplotlib.figure import Figure  # noqa: E402

from core import app_state  # noqa: E402
from visualization.event_handlers.pointer_events import _panel_for  # noqa: E402


def test_a_rebuilt_panel_is_still_found(qapp, monkeypatch) -> None:
    figure = Figure()
    old_axes = figure.add_subplot(111)
    monkeypatch.setattr(
        app_state, "plot_panel_states", [{"ax": old_axes, "figure": figure, "mode": "2D"}], raising=False
    )

    # The panel is redrawn: same figure, new axes, the record left pointing at the old ones.
    figure.clf()
    new_axes = figure.add_subplot(111)

    assert _panel_for(new_axes) is not None, "the figure identifies the panel; its axes does not"


def test_an_unknown_axes_still_resolves_to_nothing(qapp, monkeypatch) -> None:
    figure = Figure()
    axes = figure.add_subplot(111)
    monkeypatch.setattr(app_state, "plot_panel_states", [], raising=False)
    assert _panel_for(axes) is None
