"""The view the user set belongs to the user, not to the render."""
from __future__ import annotations

import matplotlib

matplotlib.use("Qt5Agg")

from matplotlib.figure import Figure  # noqa: E402

from core import app_state  # noqa: E402
from ui.main_window_parts.canvas import MainWindowCanvasMixin  # noqa: E402


class _Axes:
    def __init__(self, number: int) -> None:
        self.number = number


class _FitHost(MainWindowCanvasMixin):
    """A host whose fit records what it framed, without needing a real plot."""

    def __init__(self) -> None:
        self.framed: list[int] = []

    def _panels_for_fit(self):
        return [("2D", record["axes"]) for record in app_state.plot_panel_windows]

    def _fit_one_axes(self, mode, axis) -> bool:
        self.framed.append(axis.number)
        return True


def _ignore_label_refresh(monkeypatch) -> None:
    import ui.main_window_parts.canvas as canvas

    monkeypatch.setattr(canvas, "refresh_panel_labels", lambda *args, **kwargs: None)


def test_the_automatic_fit_leaves_a_view_the_user_set_alone(qapp, monkeypatch) -> None:
    """Reported as a warning: an automatic fit must not reset the zoom.

    The fit runs when the panels are built and after a reload. A panel records the data version it
    was framed for, so the same data never frames it twice - while a genuinely new dataset does.
    """
    _ignore_label_refresh(monkeypatch)
    host = _FitHost()
    app_state.plot_panel_windows[:] = [
        {"axes": _Axes(index), "mode": "2D"} for index in range(2)
    ]
    app_state.data_version = 1
    try:
        host._fit_panels_to_data()
        assert sorted(host.framed) == [0, 1], "the first automatic fit frames the panels"

        host.framed.clear()
        host._fit_panels_to_data()
        assert host.framed == [], "the same data does not frame them again - the view is the user's"

        app_state.data_version = 2
        host._fit_panels_to_data()
        assert sorted(host.framed) == [0, 1], "a new dataset is framed again"

        host.framed.clear()
        host._fit_panels_to_data(force=True)
        assert sorted(host.framed) == [0, 1], "and the command always frames"
    finally:
        app_state.plot_panel_windows[:] = []


def test_a_redraw_of_the_same_data_keeps_the_limits() -> None:
    """What the whole policy rests on: re-drawing the same data does not reset the limits."""
    xs = [1.0, 2.0, 3.0]
    ys = [2.0, 4.0, 6.0]

    figure = Figure()
    axes = figure.add_subplot(111)
    axes.scatter(xs, ys)
    axes.set_xlim(1.5, 2.5)
    axes.set_ylim(3.0, 5.0)
    before = (axes.get_xlim(), axes.get_ylim())

    axes.scatter(xs, ys)

    assert (axes.get_xlim(), axes.get_ylim()) == before

    figure3d = Figure()
    axes3d = figure3d.add_subplot(111, projection="3d")
    axes3d.scatter(xs, ys, [1.0, 1.5, 2.0])
    axes3d.set_xlim(1.5, 2.5)
    axes3d.set_ylim(3.0, 5.0)
    axes3d.set_zlim(0.5, 1.5)
    before3d = (axes3d.get_xlim(), axes3d.get_ylim(), axes3d.get_zlim())

    axes3d.scatter(xs, ys, [1.0, 1.5, 2.0])

    assert (axes3d.get_xlim(), axes3d.get_ylim(), axes3d.get_zlim()) == before3d
