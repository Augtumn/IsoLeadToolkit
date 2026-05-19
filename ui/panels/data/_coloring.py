"""Data panel coloring/grouping UI construction."""
from __future__ import annotations

import logging

from PyQt5.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core import app_state, translate

logger = logging.getLogger(__name__)


class _DataPanelColoringBuild:
    """Build coloring/grouping and tooltip UI controls for data panel."""

    def _build_coloring_grouping(self, layout):
        """Build Coloring/Grouping and Tooltip Settings groups.

        Args:
            layout: The parent layout to add widgets into.
        """
        group_group = QGroupBox(translate("Coloring / Grouping"))
        group_group.setProperty("translate_key", "Coloring / Grouping")
        group_layout = QVBoxLayout()

        self.group_radio_group = QButtonGroup(self)
        self.group_radio_group.setExclusive(True)
        self.group_radio_group.buttonClicked.connect(self._on_group_col_selected)

        group_container = QWidget()
        self.group_radio_layout = QVBoxLayout(group_container)
        self.group_radio_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.addWidget(group_container)

        group_config_btn = QPushButton(translate("Configure Group Columns"))
        group_config_btn.setProperty("translate_key", "Configure Group Columns")
        group_config_btn.clicked.connect(self._on_configure_group_columns)
        group_layout.addWidget(group_config_btn)

        group_group.setLayout(group_layout)
        layout.addWidget(group_group)

        self._refresh_group_column_radios()

        tooltip_group = QGroupBox(translate("Tooltip Settings"))
        tooltip_group.setProperty("translate_key", "Tooltip Settings")
        tooltip_layout = QVBoxLayout()

        tooltip_check_layout = QHBoxLayout()
        self.tooltip_check = QCheckBox(translate("Show Tooltip"))
        self.tooltip_check.setProperty("translate_key", "Show Tooltip")
        self.tooltip_check.setChecked(getattr(app_state, "show_tooltip", True))
        self.tooltip_check.stateChanged.connect(self._on_tooltip_change)
        tooltip_check_layout.addWidget(self.tooltip_check)

        tooltip_config_btn = QPushButton(translate("Configure"))
        tooltip_config_btn.setProperty("translate_key", "Configure")
        tooltip_config_btn.setFixedWidth(100)
        tooltip_config_btn.clicked.connect(self._on_configure_tooltip)
        tooltip_check_layout.addWidget(tooltip_config_btn)
        tooltip_check_layout.addStretch()
        tooltip_layout.addLayout(tooltip_check_layout)

        tooltip_group.setLayout(tooltip_layout)
        layout.addWidget(tooltip_group)
        layout.addStretch()
