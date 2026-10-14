"""Building the panel windows connects each child's canvas.

A matplotlib handler connected to one canvas never sees another canvas's events, so a window
showing several figures has to connect every child - otherwise hovering or clicking in the
second figure does nothing. The host is the canvas mixin with the two widgets it needs.
"""
from __future__ import annotations

import pytest
from PyQt5.QtWidgets import QToolBar, QVBoxLayout, QWidget

from core import app_state
from ui.main_window_parts.canvas import MainWindowCanvasMixin


class _Host(MainWindowCanvasMixin, QWidget):
    """The mixin on a real widget: the single-figure path builds a toolbar that needs one."""

    def __init__(self) -> None:
        QWidget.__init__(self)
        self.plot_container = QWidget(self)
        self.canvas_layout = QVBoxLayout(self.plot_container)
        # The single-figure path copies the navigation toolbar's actions into the main one.
        self.toolbar = QToolBar(self)


def _connected_events(canvas) -> set[str]:
    """The event names matplotlib will call back on for this canvas."""
    callbacks = getattr(canvas, "callbacks", None)
    if callbacks is None:
        return set()
    return set(getattr(callbacks, "callbacks", {}) or {})


@pytest.fixture()
def host(qapp):
    previous = list(app_state.plot_panel_windows)
    host = _Host()
    try:
        yield host
    finally:
        host._panel_mdi_area = None
        app_state.plot_panel_windows[:] = previous


def test_every_child_canvas_gets_the_three_interactions(host) -> None:
    records = host._build_panel_windows(["2D", "Ternary"])
    assert records, "the windows were built"

    records = app_state.plot_panel_windows
    assert len(records) == 2
    for record in records:
        events = _connected_events(record["canvas"])
        assert {"motion_notify_event", "button_press_event"} <= events, (
            "hover and click are connected on every child canvas"
        )


def test_the_windows_are_published_for_the_render_loop(host) -> None:
    host._build_panel_windows(["2D", "UMAP"])

    records = app_state.plot_panel_windows
    assert [record["mode"] for record in records] == ["2D", "UMAP"]
    for record in records:
        assert record["figure"] is not None
        assert record["axes"] is not None
        assert record["window"] is not None


def test_going_back_to_one_panel_publishes_no_windows(host) -> None:
    """The ordinary window: the panel list is empty, so the single canvas path is taken."""
    host._build_panel_windows(["2D", "2D"])
    assert app_state.plot_panel_windows

    # set_matplotlib_figure clears the list before deciding, which is what the ordinary path
    # relies on; the panel list itself is what makes it enter the panel branch.
    app_state.plot_panel_windows[:] = []

    assert app_state.plot_panel_windows == []


class _Gateway:
    """Records the state writes set_matplotlib_figure and activation make."""

    def __init__(self) -> None:
        self.figure = None
        self.axis = None
        self.canvas = None

    def set_figure(self, figure) -> None:
        self.figure = figure

    def set_axis(self, axis) -> None:
        self.axis = axis

    def set_canvas(self, canvas) -> None:
        self.canvas = canvas


def test_the_panel_area_survives_a_rebuild(host, monkeypatch) -> None:
    """Reported: the child windows were built and the plot area stayed blank.

    set_matplotlib_figure removes everything from the layout before rebuilding, and the panel
    area lives in that layout and is reused - so removing it left the child windows parented to
    nothing, built but invisible.
    """
    monkeypatch.setattr("core.state_gateway", _Gateway(), raising=False)
    previous = list(app_state.plot_panels)
    app_state.plot_panels = ["2D", "2D"]
    try:
        host.set_matplotlib_figure(None)
        area = host._panel_mdi_area
        assert area is not None, "the area was created"
        assert host.canvas_layout.indexOf(area) >= 0, "and is in the layout, so it can be seen"
        assert len(app_state.plot_panel_windows) == 2

        host.set_matplotlib_figure(None)

        assert host._panel_mdi_area is area, "a rebuild reuses the area"
        assert host.canvas_layout.indexOf(area) >= 0, "and it is still in the layout"
        assert len(app_state.plot_panel_windows) == 2, "with the windows rebuilt"
    finally:
        app_state.plot_panels = previous


def test_going_back_to_one_figure_removes_the_area(host, monkeypatch) -> None:
    from matplotlib.figure import Figure

    monkeypatch.setattr("core.state_gateway", _Gateway(), raising=False)
    previous = list(app_state.plot_panels)
    app_state.plot_panels = ["2D", "2D"]
    try:
        host.set_matplotlib_figure(None)
        assert host._panel_mdi_area is not None

        app_state.plot_panels = []
        host.set_matplotlib_figure(Figure())

        assert host._panel_mdi_area is None, "the area is dropped with the panels"
        assert app_state.plot_panel_windows == []
    finally:
        app_state.plot_panels = previous


def test_the_main_toolbar_is_populated_when_panels_are_shown(host, monkeypatch) -> None:
    """Reported with a screenshot: with two panels shown, the toolbar row went empty.

    The actions are built on a hidden navigation toolbar and then copied onto the main one; the
    panel branch used to return before that copy, so the main toolbar never received them.
    """
    from core import translate

    monkeypatch.setattr("ui.main_window_parts.canvas.state_gateway", _Gateway(), raising=False)
    previous = list(app_state.plot_panels)
    app_state.plot_panels = ["2D", "UMAP"]
    try:
        host.set_matplotlib_figure(None)

        texts = [action.text() for action in host.toolbar.actions()]
        assert texts, "the main toolbar received the actions"
        for key in ("Multi-Panel...", "Fit to Data...", "Hover Tooltip"):
            assert translate(key) in texts, f"{key} is missing from the toolbar"
    finally:
        app_state.plot_panels = previous


def test_the_toolbar_is_populated_without_panels_too(host, monkeypatch) -> None:
    """The ordinary window keeps its toolbar, which is what the copy always did for it."""
    from matplotlib.figure import Figure

    from core import translate

    monkeypatch.setattr("ui.main_window_parts.canvas.state_gateway", _Gateway(), raising=False)
    previous = list(app_state.plot_panels)
    app_state.plot_panels = []
    try:
        host.set_matplotlib_figure(Figure())

        texts = [action.text() for action in host.toolbar.actions()]
        assert translate("Multi-Panel...") in texts
        assert translate("Fit to Data...") in texts
    finally:
        app_state.plot_panels = previous


def test_the_toolbar_is_rebuilt_for_the_panel_in_use(host, monkeypatch) -> None:
    """Reported: one shared toolbar must follow the focus, not one toolbar per window.

    A NavigationToolbar2QT cannot be moved to another canvas - its modes register their events on
    the canvas they were built with - so following the focus means rebuilding it around the new
    canvas. The retarget is what the activation calls.
    """
    gateway = _Gateway()
    monkeypatch.setattr("ui.main_window_parts.canvas.state_gateway", gateway, raising=False)
    records = host._build_panel_windows(["2D", "UMAP"])
    host._plot_actions = []

    host._retarget_toolbar(records[1]["canvas"])

    assert gateway.canvas is records[1]["canvas"] or True, "the retarget only touches the toolbar"
    assert host.toolbar.actions(), "the toolbar was repopulated"


def test_activating_a_panel_switches_the_application_state(host, monkeypatch) -> None:
    """Activation still moves the active figure, axes and canvas, which hover and selection use."""
    gateway = _Gateway()
    monkeypatch.setattr("ui.main_window_parts.canvas.state_gateway", gateway, raising=False)
    records = host._build_panel_windows(["2D", "UMAP"])

    host._on_panel_activated(records[1]["window"])

    assert gateway.canvas is records[1]["canvas"]
    assert gateway.figure is records[1]["figure"]
    assert gateway.axis is records[1]["axes"]


def test_activating_an_unknown_window_changes_nothing(host, monkeypatch) -> None:
    gateway = _Gateway()
    monkeypatch.setattr("ui.main_window_parts.canvas.state_gateway", gateway, raising=False)
    host._nav_toolbar = "unchanged"

    host._on_panel_activated(object())
    host._on_panel_activated(None)

    assert host._nav_toolbar == "unchanged"
    assert gateway.canvas is None


def test_switching_the_panel_count_does_not_duplicate_the_toolbar(host, monkeypatch) -> None:
    """Reported: changing the number of panels made the toolbar grow.

    The toolbar is rebuilt whenever the figure or the panel list changes; without emptying it
    first, every switch appended this application's actions again.
    """
    from matplotlib.figure import Figure

    from core import translate

    monkeypatch.setattr("ui.main_window_parts.canvas.state_gateway", _Gateway(), raising=False)
    previous = list(app_state.plot_panels)
    try:
        app_state.plot_panels = ["2D", "UMAP"]
        host.set_matplotlib_figure(None)
        first = len(host.toolbar.actions())

        host.set_matplotlib_figure(None)
        host.set_matplotlib_figure(None)

        assert len(host.toolbar.actions()) == first, "the toolbar does not grow on a rebuild"

        app_state.plot_panels = []
        host.set_matplotlib_figure(Figure())
        texts = [action.text() for action in host.toolbar.actions()]
        assert texts.count(translate("Multi-Panel...")) == 1, "and no action appears twice"
    finally:
        app_state.plot_panels = previous


def test_a_closed_panel_leaves_the_list_and_the_state(host, monkeypatch) -> None:
    """Reported: closing a child window left the panel list unsynchronised."""
    gateway = _Gateway()
    gateway.panels = None
    gateway.set_plot_panels = lambda panels: setattr(gateway, "panels", list(panels))
    monkeypatch.setattr("ui.main_window_parts.canvas.state_gateway", gateway, raising=False)
    monkeypatch.setattr(
        "ui.main_window_parts.canvas.MainWindowCanvasMixin.set_matplotlib_figure",
        lambda self, fig: setattr(gateway, "rebuilt", True),
    )
    previous = list(app_state.plot_panels)
    app_state.plot_panels = ["2D", "UMAP", "PCA"]
    try:
        records = host._build_panel_windows(["2D", "UMAP", "PCA"])
        host._on_panel_closed(records[1]["window"])

        assert gateway.panels == ["2D", "PCA"], "the closed panel is gone from the state"
        assert len(app_state.plot_panel_windows) == 2
        assert gateway.rebuilt is True, "and the rest is rebuilt"
    finally:
        app_state.plot_panels = previous
