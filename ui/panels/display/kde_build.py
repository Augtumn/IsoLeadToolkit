"""Kernel Density toolbox page for the display panel."""
from __future__ import annotations

from PyQt5.QtCore import Qt

_CONFIDENCE_LEVEL_1SIGMA: float = 0.68
_CONFIDENCE_LEVEL_2SIGMA: float = 0.95
_CONFIDENCE_LEVEL_3SIGMA: float = 0.99
_CONFIDENCE_EPSILON: float = 0.01
from PyQt5.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QToolBox,
    QVBoxLayout,
    QWidget,
)

from core import app_state, translate
from ui.icons import apply_color_swatch
from ui.panels.base_panel import BasePanel
from ui.widgets import labeled_checkbox


class DisplayKdeBuildMixin:
    """Build the Kernel Density toolbox page for the display panel."""

    def _build_kde_page(self, section_toolbox) -> None:
        """Add the KDE visibility checkboxes and style swatches."""
        kde_group = QGroupBox(translate("Kernel Density"))
        kde_group.setProperty('translate_key', 'Kernel Density')
        kde_layout = QVBoxLayout()

        kde_row = QHBoxLayout()
        kde_check_row, self.tools_kde_check = labeled_checkbox("Show Kernel Density",
                                                   app_state.show_kde,
                                                   self._on_kde_change)
        kde_row.addWidget(kde_check_row)

        kde_swatch = QLabel()
        kde_swatch.setFixedSize(16, 16)
        apply_color_swatch(kde_swatch, '#e2e8f0')
        kde_swatch.setProperty("keepStyle", True)
        kde_swatch.mousePressEvent = lambda event, s=kde_swatch: self._open_kde_style_dialog('kde', s)
        kde_row.addWidget(kde_swatch)
        kde_row.addStretch()
        kde_layout.addLayout(kde_row)

        mkde_row = QHBoxLayout()
        mkde_check_row, self.tools_marginal_kde_check = labeled_checkbox("Show Marginal KDE",
                                                            app_state.show_marginal_kde,
                                                            self._on_marginal_kde_change)
        mkde_row.addWidget(mkde_check_row)

        mkde_swatch = QLabel()
        mkde_swatch.setFixedSize(16, 16)
        apply_color_swatch(mkde_swatch, '#e2e8f0')
        mkde_swatch.setProperty("keepStyle", True)
        mkde_swatch.mousePressEvent = lambda event, s=mkde_swatch: self._open_kde_style_dialog('marginal_kde', s)
        mkde_row.addWidget(mkde_swatch)
        mkde_row.addStretch()
        kde_layout.addLayout(mkde_row)

        kde_group.setLayout(kde_layout)
        BasePanel.add_group_page(section_toolbox, kde_group, 'Kernel Density')

