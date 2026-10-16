"""Choose the column that refines a legend group.

The window lists every column the data can be grouped by. The ones that are already in use -
the active grouping column and anything already used in the chain - are shown **disabled**
rather than hidden, so it is clear why they cannot be picked.
"""
from __future__ import annotations

from typing import Iterable, Sequence

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)

from core import translate


class LegendDecomposeDialog(QDialog):
    """Pick the column that refines one legend entry."""

    def __init__(
        self,
        parent=None,
        columns: Sequence[str] = (),
        *,
        used: Iterable[str] = (),
        group_label: str = "",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(translate("Decompose by…"))
        self._used = {str(column) for column in used}

        layout = QVBoxLayout(self)
        if group_label:
            layout.addWidget(
                QLabel(
                    translate("Refine {group} by:").format(group=str(group_label)),
                    self,
                )
            )
        else:
            layout.addWidget(QLabel(translate("Choose a column to refine this group by:"), self))

        self.list_widget = QListWidget(self)
        for column in columns:
            name = str(column)
            item = QListWidgetItem(name, self.list_widget)
            if name in self._used:
                # Disabled rather than hidden: the window says why it is not available.
                item.setFlags(
                    (item.flags() & ~Qt.ItemIsEnabled) | Qt.ItemIsSelectable
                )
                item.setToolTip(translate("Already used by this decomposition"))
        layout.addWidget(self.list_widget)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        first = self._first_enabled_row()
        if first is None:
            # Nothing can be picked, so Ok would be a lie.
            self.buttons.button(QDialogButtonBox.Ok).setEnabled(False)
        else:
            self.list_widget.setCurrentRow(first)
        self.list_widget.itemDoubleClicked.connect(lambda _item: self.accept())

    def _first_enabled_row(self):
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            if item is not None and item.flags() & Qt.ItemIsEnabled:
                return row
        return None

    def selected_column(self):
        """The chosen column, or ``None`` when the selection is not usable."""
        item = self.list_widget.currentItem()
        if item is None or not (item.flags() & Qt.ItemIsEnabled):
            return None
        return item.text()
