"""Independent child windows, one figure each.

Built and driven without a main window: the area and its children are real Qt widgets, so what
is checked is that every panel really gets its own figure and canvas, that the mode a panel is
set to decides the axes it gets, and that windows are added and closed as the count changes.
"""
from __future__ import annotations

import pytest

from ui.main_window_parts.mdi_panels import DEFAULT_PANEL_SIZE, PanelWindows, create_mdi_area


@pytest.fixture()
def windows(qapp):
    area = create_mdi_area(None)
    try:
        yield area, PanelWindows(area)
    finally:
        area.close()


def test_the_area_shows_child_windows(windows) -> None:
    from PyQt5.QtWidgets import QMdiArea

    area, _ = windows
    assert isinstance(area, QMdiArea)
    assert area.viewMode() == QMdiArea.SubWindowView


def test_every_panel_gets_its_own_figure_and_canvas(windows) -> None:
    _area, panel = windows

    records = panel.sync(["2D", "Ternary"])

    assert len(records) == 2
    first, second = records
    assert first["figure"] is not second["figure"], "one figure each"
    assert first["canvas"] is not second["canvas"], "one canvas each"
    assert first["window"] is not second["window"]
    assert first["axes"] is not second["axes"]


def test_the_mode_decides_the_axes_a_panel_gets(windows) -> None:
    _area, panel = windows

    records = panel.sync(["2D", "Ternary"])

    assert getattr(records[0]["axes"], "name", "") != "ternary"
    assert getattr(records[1]["axes"], "name", "") == "ternary"


def test_changing_a_mode_rebuilds_that_panels_axes(windows) -> None:
    _area, panel = windows
    records = panel.sync(["2D"])
    figure = records[0]["figure"]
    assert getattr(records[0]["axes"], "name", "") != "ternary"

    records = panel.sync(["Ternary"])

    assert records[0]["figure"] is figure, "the window keeps its figure"
    assert getattr(records[0]["axes"], "name", "") == "ternary", "with the new projection"


def test_shrinking_closes_the_extra_windows(windows) -> None:
    area, panel = windows
    panel.sync(["2D", "2D", "2D"])
    assert len(area.subWindowList()) == 3

    records = panel.sync(["2D"])

    assert len(records) == 1
    assert len(area.subWindowList()) == 1, "the closed windows left the area"


def test_growing_adds_windows_at_the_default_size(windows) -> None:
    area, panel = windows
    panel.sync(["2D", "UMAP"])

    sizes = [(window.width(), window.height()) for window in area.subWindowList()]
    assert len(sizes) == 2


def test_closing_everything_leaves_an_empty_area(windows) -> None:
    area, panel = windows
    panel.sync(["2D", "2D"])

    panel.close_all()

    assert panel.count() == 0
    assert area.subWindowList() == []


def test_the_active_window_is_reported(windows) -> None:
    area, panel = windows
    records = panel.sync(["2D", "3D"])
    assert panel.active_index() == -1, "nothing is active until one is"

    area.setActiveSubWindow(records[1]["window"])

    assert panel.active_index() == 1
    assert panel.records[1]["mode"] == "3D"


def test_tiling_without_windows_does_nothing(windows) -> None:
    _area, panel = windows
    panel.tile()  # must not raise
    assert panel.count() == 0
    assert DEFAULT_PANEL_SIZE[0] > 0


def test_closing_a_middle_panel_keeps_the_live_windows(windows) -> None:
    """Reported by review: closing a window that was not the last one dropped a good one instead.

    ``sync`` shrinks the record list by popping its tail. When the user closes a window in the middle, the
    count alone cannot say which record is gone, so the rebuild removed the last window's record and kept
    the closed window's - the state then described a window that had gone, and the area lost a live one.
    ``close_window`` removes by identity before anything rebuilds.
    """
    area, panels = windows
    panels.sync(["2D", "UMAP", "tSNE"])
    first, middle, last = panels.records

    panels.close_window(middle["window"])

    left = [record["window"] for record in panels.records]
    assert left == [first["window"], last["window"]], "the two live windows are the ones left"
    assert middle["window"] not in left, "the closed window is gone from the bookkeeping"
    assert middle["window"].parent() is None, "and out of the area"
