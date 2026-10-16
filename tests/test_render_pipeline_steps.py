"""The one sequence: what it does, in what order, and what it will not let a mode forget."""
from __future__ import annotations

import pytest
from matplotlib.figure import Figure

from core import app_state, state_gateway
from visualization.plotting.rendering import registry
from visualization.plotting.rendering.context import build_context
from visualization.plotting.rendering.pipeline import Ink, run


class _Adapter:
    """A mode that records the order of the calls the pipeline makes into it."""

    mode = "2D"

    def __init__(self, ink: Ink = Ink.DRAWN, groups=("A", "B")) -> None:
        self.calls: list[str] = []
        self._ink = ink
        self._groups = list(groups)

    def validate(self, context) -> None:
        self.calls.append("validate")

    def token(self, context):
        return ("fake",)

    def axes_dimensions(self, context):
        return 2

    def prepare(self, context):
        self.calls.append("prepare")
        return {"rows": 3}

    def groups(self, context, prepared):
        self.calls.append("groups")
        return self._groups

    def configure_axes(self, context, prepared) -> None:
        self.calls.append("configure_axes")

    def draw(self, context, prepared):
        self.calls.append("draw")
        context.axes.plot([0.0, 1.0], [0.0, 1.0])
        return self._ink

    def marginal(self, context, prepared) -> None:
        self.calls.append("marginal")

    def legend(self, context, prepared) -> None:
        self.calls.append("legend")

    def decorate(self, context, prepared) -> None:
        self.calls.append("decorate")
        context.axes.set_title("Fake")

    def finish(self, context, prepared) -> None:
        self.calls.append("finish")


@pytest.fixture(autouse=True)
def _clean_registry():
    registry.clear()
    yield
    registry.clear()


def _context(mode: str = "2D", figure: Figure | None = None):
    figure = figure or Figure()
    axes = figure.add_subplot(111)
    # The application keeps the figure and the axes in use mirrored in the state; a render reads the
    # axes that is in use, so a test that renders has to mirror both.
    state_gateway.set_figure(figure)
    state_gateway.set_axis(axes)
    return build_context(
        mode,
        group_col="Site",
        figure=figure,
        axes=axes,
        columns_2d=("x1", "x2"),
    )


def test_the_sequence_is_the_same_for_every_mode() -> None:
    adapter = _Adapter()
    context = _context()
    assert run(adapter, context) is True
    assert adapter.calls == [
        "validate",
        "prepare",
        "configure_axes",
        "groups",
        "draw",
        "marginal",
        "legend",
        "decorate",
        "finish",
    ]


def test_the_view_the_user_set_survives_a_render() -> None:
    adapter = _Adapter()
    context = _context()
    assert run(adapter, context) is True
    context.axes.set_xlim(0.2, 0.4)
    context.axes.set_ylim(0.3, 0.5)

    assert run(adapter, context) is True
    assert tuple(round(float(value), 2) for value in context.axes.get_xlim()) == (0.2, 0.4)
    assert tuple(round(float(value), 2) for value in context.axes.get_ylim()) == (0.3, 0.5)


def test_another_picture_gets_its_own_view() -> None:
    """A different picture - other columns - is not given the window of the one before it."""
    from visualization.plotting import view_state

    adapter = _Adapter()
    context = _context()
    assert run(adapter, context) is True
    assert view_state.drawn_last(context.axes) == context.token(*adapter.token(context))

    other = build_context(
        "2D",
        group_col="Site",
        figure=context.figure,
        axes=context.axes,
        columns_2d=("x3", "x4"),
    )
    assert run(adapter, other) is True
    assert view_state.drawn_last(context.axes) == other.token(*adapter.token(other)), (
        "the axes remembers the picture it now shows, so the next render is compared with that one"
    )
    assert other.token(*adapter.token(other)) != context.token(*adapter.token(context))


def test_an_empty_frame_keeps_the_mode_and_is_not_a_failure() -> None:
    adapter = _Adapter(ink=Ink.EMPTY)
    context = _context()
    assert run(adapter, context) is True, "an empty frame is this mode's frame, not a failed render"
    assert adapter.calls == [
        "validate",
        "prepare",
        "configure_axes",
        "groups",
        "draw",
        "decorate",
        "finish",
    ]
    assert "legend" not in adapter.calls and "marginal" not in adapter.calls


def test_a_mode_that_refuses_the_render_draws_nothing() -> None:
    class _Refusing(_Adapter):
        def prepare(self, context):
            self.calls.append("prepare")
            return False

    adapter = _Refusing()
    assert run(adapter, _context()) is False
    assert adapter.calls == ["validate", "prepare"]


def test_a_failing_mode_is_reported_and_leaves_the_canvas_consistent() -> None:
    class _Failing(_Adapter):
        def draw(self, context, prepared):
            raise RuntimeError("no data")

    figure = Figure()
    adapter = _Failing()
    assert run(adapter, _context(figure=figure)) is False


def test_the_plot_state_is_cleared_before_the_mode_draws() -> None:
    adapter = _Adapter()
    context = _context()

    app_state.scatter_collections.append(object())
    assert run(adapter, context) is True
    assert app_state.scatter_collections == [], "a render starts from a clean plot state"
