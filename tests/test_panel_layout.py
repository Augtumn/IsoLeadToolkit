"""The panel windows are laid out sensibly, whatever state they are in when they change."""
from __future__ import annotations

from PyQt5.QtWidgets import QApplication

from ui.main_window_parts.mdi_panels import PanelWindows, create_mdi_area


def _cells(records):
    return [
        (
            record["window"].geometry().x(),
            record["window"].geometry().y(),
            record["window"].geometry().width(),
        )
        for record in records
    ]


def _settle(rounds: int = 8) -> None:
    for _ in range(rounds):
        QApplication.processEvents()


def test_going_from_one_panel_to_two_lays_them_side_by_side(qapp) -> None:
    """Reported: single window, then two windows, and the arrangement is wrong.

    One panel is shown maximised - that is what filling the area means for a single panel - and a
    maximised child ignores setGeometry, so the second panel has to un-maximise the first.
    """
    area = create_mdi_area(None)
    area.resize(1200, 800)
    area.show()
    _settle()
    panels = PanelWindows(area)
    try:
        one = panels.sync(["2D"])
        panels.show_filling_area()
        _settle()
        assert one[0]["window"].isMaximized(), "a single panel fills the area"

        two = panels.sync(["2D", "UMAP"])
        panels.show_filling_area()
        _settle()

        cells = _cells(two)
        assert len({(x, y) for x, y, _width in cells}) == 2, f"two places, got {cells}"
        assert all(not record["window"].isMaximized() for record in two)
        assert all(width == 600 for _x, _y, width in cells), f"each half the area, got {cells}"
    finally:
        area.close()


def test_the_grid_waits_for_the_area_to_be_laid_out(qapp) -> None:
    """An area that has just been added has no size yet, so a grid now would overlap the children.

    The arrangement is deferred until the layout has given the area its real size.
    """
    area = create_mdi_area(None)
    panels = PanelWindows(area)
    try:
        records = panels.sync(["2D", "UMAP"])
        panels.show_filling_area()

        assert not area.isVisible(), "the area is not on screen yet"
        assert panels._grid_retries >= 1, "the grid was deferred instead of sizing from a placeholder"

        area.resize(1200, 800)
        area.show()
        _settle()

        cells = _cells(records)
        assert all(width == 600 for _x, _y, width in cells), f"sized from the real area, got {cells}"
        assert len({(x, y) for x, y, _width in cells}) == 2, f"and not stacked, got {cells}"
    finally:
        area.close()
