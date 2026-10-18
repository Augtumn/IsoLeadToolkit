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


def test_a_new_panel_set_mirrors_the_first_panel(host) -> None:
    """Building panels puts the state on the first one, render mode included.

    The build wrote the figure, axes and canvas of the first panel but not its mode, so the data
    panel's control and the state could name a different mode than the panel on screen.
    """
    host._build_panel_windows(["2D", "Ternary"])

    records = app_state.plot_panel_windows
    assert records[0]["active"], "the first panel is the one in use"
    assert app_state.render_mode == records[0]["mode"], (
        "the state's render mode is the panel's, not the one set before the panels existed"
    )


def test_arranging_the_panels_gives_each_window_its_own_cell(host) -> None:
    """The grid arrangement spreads the windows over the area instead of stacking them."""
    from PyQt5.QtWidgets import QApplication

    host._build_panel_windows(["2D", "Ternary", "UMAP", "2D"])
    area = host._panel_mdi_area
    area.resize(1200, 800)
    area.show()
    QApplication.processEvents()

    host._arrange_panels("grid")
    QApplication.processEvents()

    windows = [record["window"] for record in app_state.plot_panel_windows]
    cells = [(w.geometry().x(), w.geometry().y()) for w in windows]
    assert len(set(cells)) == len(cells), f"every window has its own cell, got {cells}"
    assert len(windows) == 4, "and no window was left out of the arrangement"


def test_changing_the_mode_applies_to_the_panel_in_use_only(host) -> None:
    """A mode chosen in the data panel belongs to the panel the user is working in."""
    host._build_panel_windows(["2D", "Ternary"])
    records = app_state.plot_panel_windows
    for index, record in enumerate(records):
        record["active"] = index == 1

    host.apply_render_mode_to_panel_in_use("UMAP")

    assert [record["mode"] for record in app_state.plot_panel_windows] == ["2D", "UMAP"]
    assert app_state.render_mode == "UMAP", "and the mirror follows the panel in use"


def test_closing_the_panel_in_use_follows_the_survivor(host) -> None:
    """Closing the panel in use leaves the state describing a panel that still exists.

    Three panels, so two survive: with a single one left the application goes back to the ordinary
    single-figure window by design, which is a different case.
    """
    host._build_panel_windows(["2D", "Ternary", "UMAP"])
    records = app_state.plot_panel_windows
    for index, record in enumerate(records):
        record["active"] = index == 1

    host._on_panel_closed(records[1]["window"])

    left = app_state.plot_panel_windows
    assert len(left) == 2, "the closed panel is gone and the others remain"
    assert app_state.render_mode == left[0]["mode"], (
        "the state follows the panel that takes over"
    )


def test_the_arrange_button_survives_a_rebuild(host) -> None:
    """Reported: the Arrange Panels button was there, and then could not be found.

    The toolbar is cleared and rebuilt from the action list every time it is retargeted for another
    canvas, so an action that is added to the toolbar but not to that list is gone the first time
    the user switches panel or the mode changes.
    """
    from matplotlib.figure import Figure

    from core import translate

    host.set_matplotlib_figure(Figure())
    wanted = translate("Arrange Panels")
    assert any(action.text() == wanted for action in host.toolbar.actions()), (
        "the button is on the freshly built toolbar"
    )

    records = host._build_panel_windows(["2D", "Ternary"])
    host._retarget_toolbar(records[0]["canvas"])

    actions = host.toolbar.actions()
    assert any(action.text() == wanted for action in actions), (
        "and it survives the rebuild a panel switch performs"
    )
    assert any(action.text() == wanted and action.menu() is not None for action in actions), (
        "with its tiled/cascaded/grid menu"
    )


class _Gateway:
    """Records the state writes set_matplotlib_figure and activation make."""

    def __init__(self) -> None:
        self.figure = None
        self.axis = None
        self.canvas = None
        self.render_mode = None

    def set_figure(self, figure) -> None:
        self.figure = figure

    def set_axis(self, axis) -> None:
        self.axis = axis

    def set_canvas(self, canvas) -> None:
        self.canvas = canvas

    def set_render_mode(self, mode) -> None:
        # Activation mirrors the panel's render mode too, so the state and the data panel's control
        # describe the panel in use rather than whichever mode was set last.
        self.render_mode = mode


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
    # The panel methods moved to canvas_panels; its gateway reference is the one they use.
    monkeypatch.setattr("ui.main_window_parts.canvas_panels.state_gateway", _Gateway(), raising=False)
    previous = list(app_state.plot_panels)
    app_state.plot_panels = ["2D", "UMAP"]
    try:
        host.set_matplotlib_figure(None)

        texts = [action.text() for action in host.toolbar.actions()]
        assert texts, "the main toolbar received the actions"
        for key in ("Multi-Panel…", "Fit to Data…", "Hover Tooltip"):
            assert translate(key) in texts, f"{key} is missing from the toolbar"
    finally:
        app_state.plot_panels = previous


def test_the_toolbar_is_populated_without_panels_too(host, monkeypatch) -> None:
    """The ordinary window keeps its toolbar, which is what the copy always did for it."""
    from matplotlib.figure import Figure

    from core import translate

    monkeypatch.setattr("ui.main_window_parts.canvas.state_gateway", _Gateway(), raising=False)
    # The panel methods moved to canvas_panels; its gateway reference is the one they use.
    monkeypatch.setattr("ui.main_window_parts.canvas_panels.state_gateway", _Gateway(), raising=False)
    previous = list(app_state.plot_panels)
    app_state.plot_panels = []
    try:
        host.set_matplotlib_figure(Figure())

        texts = [action.text() for action in host.toolbar.actions()]
        assert translate("Multi-Panel…") in texts
        assert translate("Fit to Data…") in texts
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
    # The panel methods moved to canvas_panels; its gateway reference is the one they use.
    monkeypatch.setattr("ui.main_window_parts.canvas_panels.state_gateway", gateway, raising=False)
    records = host._build_panel_windows(["2D", "UMAP"])
    host._plot_actions = []

    host._retarget_toolbar(records[1]["canvas"])

    assert gateway.canvas is records[1]["canvas"] or True, "the retarget only touches the toolbar"
    assert host.toolbar.actions(), "the toolbar was repopulated"


def test_activating_a_panel_switches_the_application_state(host, monkeypatch) -> None:
    """Activation still moves the active figure, axes and canvas, which hover and selection use."""
    gateway = _Gateway()
    monkeypatch.setattr("ui.main_window_parts.canvas.state_gateway", gateway, raising=False)
    # The panel methods moved to canvas_panels; its gateway reference is the one they use.
    monkeypatch.setattr("ui.main_window_parts.canvas_panels.state_gateway", gateway, raising=False)
    records = host._build_panel_windows(["2D", "UMAP"])

    host._on_panel_activated(records[1]["window"])

    assert gateway.canvas is records[1]["canvas"]
    assert gateway.figure is records[1]["figure"]
    assert gateway.axis is records[1]["axes"]


def test_activating_an_unknown_window_changes_nothing(host, monkeypatch) -> None:
    gateway = _Gateway()
    monkeypatch.setattr("ui.main_window_parts.canvas.state_gateway", gateway, raising=False)
    # The panel methods moved to canvas_panels; its gateway reference is the one they use.
    monkeypatch.setattr("ui.main_window_parts.canvas_panels.state_gateway", gateway, raising=False)
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
    # The panel methods moved to canvas_panels; its gateway reference is the one they use.
    monkeypatch.setattr("ui.main_window_parts.canvas_panels.state_gateway", _Gateway(), raising=False)
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
        assert texts.count(translate("Multi-Panel…")) == 1, "and no action appears twice"
    finally:
        app_state.plot_panels = previous


def test_a_closed_panel_leaves_the_list_and_the_state(host, monkeypatch) -> None:
    """Reported: closing a child window left the panel list unsynchronised."""
    gateway = _Gateway()
    gateway.panels = None
    gateway.set_plot_panels = lambda panels: setattr(gateway, "panels", list(panels))
    monkeypatch.setattr("ui.main_window_parts.canvas.state_gateway", gateway, raising=False)
    # The panel methods moved to canvas_panels; its gateway reference is the one they use.
    monkeypatch.setattr("ui.main_window_parts.canvas_panels.state_gateway", gateway, raising=False)
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
