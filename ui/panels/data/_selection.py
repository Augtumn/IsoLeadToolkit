"""Data panel render mode / axis / V1V2 UI construction."""
from __future__ import annotations

import logging

from PyQt5.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)

from core import app_state, translate

logger = logging.getLogger(__name__)


class _DataPanelSelectionBuild:
    """Build render mode, V1V2, and axis selection UI controls for data panel."""

    def _build_render_controls(self, layout):
        """Build render mode and algorithm selection combos.

        Args:
            layout: The parent layout to add widgets into.
        """
        render_group = QGroupBox(translate("Render Mode"))
        render_group.setProperty("translate_key", "Render Mode")
        render_layout = QVBoxLayout()

        self.render_combo = QComboBox()
        render_modes = [
            (translate("UMAP"), "UMAP"),
            (translate("t-SNE"), "tSNE"),
            (translate("PCA"), "PCA"),
            (translate("RobustPCA"), "RobustPCA"),
            (translate("2D"), "2D"),
            (translate("3D"), "3D"),
            (translate("Ternary"), "Ternary"),
            (translate("V1-V2 Diagram"), "V1V2"),
            (translate("PB_EVOL_76"), "PB_EVOL_76"),
            (translate("PB_EVOL_86"), "PB_EVOL_86"),
            (translate("PLUMBOTECTONICS_76"), "PLUMBOTECTONICS_76"),
            (translate("PLUMBOTECTONICS_86"), "PLUMBOTECTONICS_86"),
            (translate("PB_MU_AGE"), "PB_MU_AGE"),
            (translate("PB_KAPPA_AGE"), "PB_KAPPA_AGE"),
        ]
        for label, value in render_modes:
            self.render_combo.addItem(label, value)
        self._set_combo_value(self.render_combo, self._normalize_render_mode(app_state.render_mode))
        self.render_combo.currentIndexChanged.connect(self._on_render_mode_change)
        render_layout.addWidget(self.render_combo)

        render_group.setLayout(render_layout)
        layout.addWidget(render_group)

        algo_group = QGroupBox(translate("Algorithm"))
        algo_group.setProperty("translate_key", "Algorithm")
        algo_layout = QVBoxLayout()

        self.algo_combo = QComboBox()
        algo_modes = [
            (translate("UMAP"), "UMAP"),
            (translate("t-SNE"), "tSNE"),
            (translate("PCA"), "PCA"),
            (translate("RobustPCA"), "RobustPCA"),
        ]
        for label, value in algo_modes:
            self.algo_combo.addItem(label, value)
        self._set_combo_value(self.algo_combo, self._normalize_algorithm(app_state.algorithm))
        self.algo_combo.currentIndexChanged.connect(self._on_algorithm_change)
        algo_layout.addWidget(self.algo_combo)

        algo_group.setLayout(algo_layout)
        layout.addWidget(algo_group)
        self.algo_group = algo_group

    def _build_v1v2_params(self, layout):
        """Build V1V2 time settings group.

        Args:
            layout: The parent layout to add widgets into.
        """
        self.v1v2_group = QGroupBox(translate("V1V2 Time Settings"))
        self.v1v2_group.setProperty("translate_key", "V1V2 Time Settings")
        v1v2_layout = QVBoxLayout()

        try:
            from data.geochemistry import engine

            params = engine.get_parameters()
        except Exception:
            params = {}

        t1_val = params.get("T1", 4430e6) / 1e6
        t2_val = params.get("T2", 4570e6) / 1e6

        t1_layout = QHBoxLayout()
        t1_label = QLabel(translate("T1 (Ma) - Model Age"))
        t1_label.setProperty("translate_key", "T1 (Ma) - Model Age")
        t1_layout.addWidget(t1_label)
        self.v1v2_t1_spin = QDoubleSpinBox()
        self.v1v2_t1_spin.setRange(0.0, 10000.0)
        self.v1v2_t1_spin.setDecimals(3)
        self.v1v2_t1_spin.setValue(t1_val)
        self._connect_spinbox_deferred(self.v1v2_t1_spin, self._on_v1v2_param_change, pass_value=False)
        t1_layout.addWidget(self.v1v2_t1_spin)
        v1v2_layout.addLayout(t1_layout)

        t2_layout = QHBoxLayout()
        t2_label = QLabel(translate("T2 (Ma) - Standard Earth Age"))
        t2_label.setProperty("translate_key", "T2 (Ma) - Standard Earth Age")
        t2_layout.addWidget(t2_label)
        self.v1v2_t2_spin = QDoubleSpinBox()
        self.v1v2_t2_spin.setRange(0.0, 10000.0)
        self.v1v2_t2_spin.setDecimals(3)
        self.v1v2_t2_spin.setValue(t2_val)
        self._connect_spinbox_deferred(self.v1v2_t2_spin, self._on_v1v2_param_change, pass_value=False)
        t2_layout.addWidget(self.v1v2_t2_spin)
        v1v2_layout.addLayout(t2_layout)

        self.v1v2_group.setLayout(v1v2_layout)
        layout.addWidget(self.v1v2_group)

    def _build_axis_selection(self, layout):
        """Build 2D scatter axis selection group.

        Args:
            layout: The parent layout to add widgets into.
        """
        self.twod_group = QGroupBox(translate("2D Scatter Parameters"))
        self.twod_group.setProperty("translate_key", "2D Scatter Parameters")
        twod_layout = QVBoxLayout()

        twod_grid = QGridLayout()

        x_label = QLabel(translate("X Axis:"))
        x_label.setProperty("translate_key", "X Axis:")
        twod_grid.addWidget(x_label, 0, 0)

        self.xaxis_combo = QComboBox()
        self.xaxis_combo.setEditable(False)
        self.xaxis_combo.setStyleSheet("QComboBox { combobox-popup: 0; }")
        self.xaxis_combo.setMinimumWidth(150)
        twod_grid.addWidget(self.xaxis_combo, 0, 1)

        y_label = QLabel(translate("Y Axis:"))
        y_label.setProperty("translate_key", "Y Axis:")
        twod_grid.addWidget(y_label, 1, 0)

        self.yaxis_combo = QComboBox()
        self.yaxis_combo.setEditable(False)
        self.yaxis_combo.setStyleSheet("QComboBox { combobox-popup: 0; }")
        self.yaxis_combo.setMinimumWidth(150)
        twod_grid.addWidget(self.yaxis_combo, 1, 1)

        twod_layout.addLayout(twod_grid)

        self._refresh_2d_axis_combos()

        self.twod_group.setLayout(twod_layout)
        layout.addWidget(self.twod_group)
