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
from ui.panels.base_panel import BasePanel
from ui.widgets import labeled_checkbox

#: Methods this class expects from the classes it is composed with
#: (explicit interface, UI review item I).
REQUIRES_DisplayKdeBuildMixin = (
    "_open_kde_style_dialog",
)


class DisplayKdeBuildMixin:
    """Build the Kernel Density toolbox page for the display panel."""

    def _build_kde_page(self, section_toolbox) -> None:
        """Add the KDE visibility checkboxes and their style buttons."""
        kde_group = QGroupBox(translate("Kernel Density"))
        kde_group.setProperty('translate_key', 'Kernel Density')
        kde_layout = QVBoxLayout()

        kde_row = QHBoxLayout()
        kde_check_row, self.tools_kde_check = labeled_checkbox("Show Kernel Density",
                                                   app_state.show_kde,
                                                   self._on_kde_change)
        kde_row.addWidget(kde_check_row)

        # The style dialog owns the KDE line style; its only entry point used to be a
        # bare 16x16 swatch with no label and no tooltip, which hid the feature. The
        # swatch itself is gone: no renderer reads style['color'], so it had nothing
        # to show and was passed to the dialog as None.
        kde_style_btn = QPushButton(translate("KDE Style"))
        kde_style_btn.setProperty('translate_key', 'KDE Style')
        kde_style_btn.setToolTip(translate("Edit the KDE overlay style"))
        kde_style_btn.clicked.connect(
            lambda _checked=False: self._open_kde_style_dialog('kde', None)
        )
        kde_row.addWidget(kde_style_btn)
        kde_row.addStretch()
        kde_layout.addLayout(kde_row)

        mkde_row = QHBoxLayout()
        mkde_check_row, self.tools_marginal_kde_check = labeled_checkbox("Show Marginal KDE",
                                                            app_state.show_marginal_kde,
                                                            self._on_marginal_kde_change)
        mkde_row.addWidget(mkde_check_row)

        mkde_style_btn = QPushButton(translate("Marginal KDE Style"))
        mkde_style_btn.setProperty('translate_key', 'Marginal KDE Style')
        mkde_style_btn.setToolTip(translate("Edit the marginal KDE overlay style"))
        mkde_style_btn.clicked.connect(
            lambda _checked=False: self._open_kde_style_dialog('marginal_kde', None)
        )
        mkde_row.addWidget(mkde_style_btn)
        mkde_row.addStretch()
        kde_layout.addLayout(mkde_row)

        kde_group.setLayout(kde_layout)
        BasePanel.add_group_page(section_toolbox, kde_group, 'Kernel Density')

