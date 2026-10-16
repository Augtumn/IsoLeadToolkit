"""A mode that draws overlays through the old geochemistry layer still keeps the user's view.

The overlay layer remembered what an axes drew, unconditionally, with its own token - the algorithm
name, as the old embedding renderer used it. An adapter drawing through the sequence therefore had its
token overwritten, the sequence compared its own token with that other one, and the view the user had
set was never restored. The layer only remembers when it is the one that restored the view.
"""
from __future__ import annotations

import pandas as pd
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from core import app_state, state_gateway
from visualization.plotting import view_state
from visualization.plotting.rendering.context import build_context
from visualization.plotting.rendering.pipeline import Ink, run
from visualization.plotting.rendering.registry import Adapter


class _OverlayDrawingMode(Adapter):
    """A mode whose last step draws through the geochemistry overlay layer, as the geochem modes do."""

    mode = "V1V2"

    def token(self, context):
        return ("embedding", "V1V2")

    def prepare(self, context):
        return {"rows": 3}

    def groups(self, context, prepared):
        return ["A", "B", "C"]

    def draw(self, context, prepared):
        context.axes.plot([1.0, 3.0], [1.0, 3.0])
        return Ink.DRAWN

    def decorate(self, context, prepared):
        pass

    def finish(self, context, prepared):
        from visualization.plotting.rendering.geo_layers import _render_geo_overlays

        # The layer draws overlays; the sequence owns the view.
        _render_geo_overlays("V1V2")


def _context():
    frame = pd.DataFrame({"Site": ["A", "B", "C"], "x1": [1.0, 2.0, 3.0], "x2": [2.0, 3.0, 4.0]})
    state_gateway.set_dataframe_and_source(frame, file_path="x", sheet_name="s")
    state_gateway.set_group_data_columns(["Site"], ["x1", "x2"])
    state_gateway.set_last_group_col("Site")
    state_gateway.set_visible_groups(None)
    figure = Figure()
    canvas = FigureCanvas(figure)
    canvas.resize(500, 400)
    axes = figure.add_subplot(111)
    state_gateway.set_figure(figure)
    state_gateway.set_axis(axes)
    return build_context("V1V2", group_col="Site", figure=figure, axes=axes)


def test_a_mode_drawing_overlays_keeps_the_view(qapp) -> None:
    adapter = _OverlayDrawingMode()
    context = _context()
    assert run(adapter, context) is True

    context.axes.set_xlim(2.0, 4.0)
    context.axes.set_ylim(2.0, 4.0)
    assert run(adapter, context) is True

    assert tuple(round(float(value), 2) for value in context.axes.get_xlim()) == (2.0, 4.0), (
        "the overlay layer must not overwrite the token the sequence remembers with"
    )


def test_the_token_the_sequence_remembers_is_its_own(qapp) -> None:
    adapter = _OverlayDrawingMode()
    context = _context()
    assert run(adapter, context) is True
    assert view_state.drawn_last(context.axes) == context.token(*adapter.token(context))
