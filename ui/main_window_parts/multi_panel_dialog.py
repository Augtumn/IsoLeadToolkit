"""Choose how many panels the window shows, and which mode each one draws.

One window can hold several figures so the same data can be judged by different means at once.
This window asks how many panels and what each of them draws; the answer goes into
``app_state.plot_panels``, which the render cycle reads.

The modes come from the one list the projection control also uses, so a mode added there shows up
here without anyone remembering to add it twice. Each item carries the mode as its data, so a
saved panel is matched by mode rather than by the label it happened to be shown under.

The row labels are kept here rather than borrowed from the layout: asking a row widget for its
parent widget returns the dialog itself for a form row, and hiding that closes the window - which
is exactly what happened when the panel count was raised.
"""
from __future__ import annotations

from typing import Sequence

from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
)

from core import translate
from core.render_modes import RENDER_MODE_CHOICES, RENDER_MODE_VALUES
from visualization.plotting.panels import MAX_PANELS


def _fill_combo(combo: QComboBox, selected: str, label_for_mode: dict[str, str]) -> None:
    """Every mode as an item carrying its value, with *selected* chosen."""
    for label, value in RENDER_MODE_CHOICES:
        combo.addItem(translate(label), value)
    chosen = str(selected or "")
    if chosen and chosen not in RENDER_MODE_VALUES:
        # A saved panel may name something this build does not offer; show it rather than
        # silently replacing it, so the window never lies about the state it is editing.
        combo.addItem(chosen, chosen)
    index = combo.findData(chosen)
    combo.setCurrentIndex(index if index >= 0 else 0)


class MultiPanelDialog(QDialog):
    """How many panels, and the render mode of each."""

    def __init__(self, parent=None, *, panels: Sequence[str] = (), default_mode: str = "2D") -> None:
        super().__init__(parent)
        self.setWindowTitle(translate("Multi-Panel"))
        chosen = [str(mode) for mode in panels if str(mode)]
        count = len(chosen) if len(chosen) > 1 else 1
        self._default_mode = str(default_mode or "2D")
        labels = {value: label for label, value in RENDER_MODE_CHOICES}

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                translate(
                    "Show several figures at once. Hovering a point highlights the same "
                    "sample in every panel."
                ),
                self,
            )
        )

        self.count_spin = QSpinBox(self)
        self.count_spin.setRange(1, MAX_PANELS)
        self.count_spin.setValue(count)
        count_row = QFormLayout()
        count_row.addRow(QLabel(translate("Panels:"), self), self.count_spin)
        layout.addLayout(count_row)

        self.mode_combos: list[QComboBox] = []
        self.mode_labels: list[QLabel] = []
        form = QFormLayout()
        for index in range(MAX_PANELS):
            label = QLabel(translate("Panel {number}:").format(number=index + 1), self)
            combo = QComboBox(self)
            _fill_combo(combo, chosen[index] if index < len(chosen) else self._default_mode, labels)
            self.mode_labels.append(label)
            self.mode_combos.append(combo)
            form.addRow(label, combo)
        layout.addLayout(form)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.count_spin.valueChanged.connect(self._sync_visibility)
        self._sync_visibility(count)

    def _sync_visibility(self, count: int) -> None:
        """Only the chosen panels are shown and editable.

        The dialog itself is never hidden: only the rows the count does not reach, which is why
        the labels are owned here instead of being looked up from the layout.
        """
        for index, (label, combo) in enumerate(zip(self.mode_labels, self.mode_combos)):
            active = index < int(count)
            label.setVisible(active)
            combo.setVisible(active)
            combo.setEnabled(active)

    def selected_panels(self) -> list[str]:
        """The panels to show: empty means the ordinary one-figure window."""
        count = int(self.count_spin.value())
        modes = [str(combo.currentData()) for combo in self.mode_combos[:count]]
        return [] if count <= 1 else modes
