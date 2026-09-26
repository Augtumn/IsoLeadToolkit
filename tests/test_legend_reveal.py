"""The panel scrolls to the group revealed by a double click on the plot."""
from __future__ import annotations

import pytest

pytest.importorskip("PyQt5")

from PyQt5.QtCore import Qt  # noqa: E402
from PyQt5.QtWidgets import QApplication, QListWidget, QListWidgetItem  # noqa: E402

from ui.main_window_parts.legend_interaction import MainWindowLegendInteractionMixin  # noqa: E402

_APP = QApplication.instance() or QApplication([])


class _Host(MainWindowLegendInteractionMixin):
    """Only the legend list is needed for the reveal helper."""


def _list_with(groups: list[str]) -> QListWidget:
    widget = QListWidget()
    for group in groups:
        item = QListWidgetItem(str(group))
        item.setData(Qt.UserRole, {"type": "group", "key": group})
        widget.addItem(item)
    return widget


def test_reveal_selects_the_row_of_the_group() -> None:
    host = _Host()
    host._legend_list = _list_with(["A", "B", "Target", "C"])

    host._reveal_group_in_legend("Target")

    assert host._legend_list.currentItem() is host._legend_list.item(2)


def test_reveal_ignores_parent_and_overlay_rows() -> None:
    host = _Host()
    widget = _list_with(["A"])
    parent = QListWidgetItem("parent")
    parent.setData(Qt.UserRole, {"type": "parent", "key": "A"})
    widget.addItem(parent)
    host._legend_list = widget

    host._reveal_group_in_legend("A")

    assert widget.currentItem() is widget.item(0), "the group row, not the parent row"


def test_reveal_without_a_match_changes_nothing() -> None:
    host = _Host()
    host._legend_list = _list_with(["A", "B"])

    host._reveal_group_in_legend("Missing")

    assert host._legend_list.currentItem() is None
