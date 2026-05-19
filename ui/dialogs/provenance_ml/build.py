"""UI construction and column helpers for provenance ML dialog."""
from __future__ import annotations

import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)

from core import app_state, translate


class ProvenanceMLBuildMixin:
    """Build dialog widgets and lightweight column auto-detection helpers."""

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel(translate("Provenance ML"))
        title_font = QFont(title.font())
        title_font.setPointSize(title_font.pointSize() + 2)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        train_group = QGroupBox(translate("Training Data"))
        train_layout = QVBoxLayout()

        file_row = QHBoxLayout()
        file_row.addWidget(QLabel(translate("Training File:")))
        self.train_file_edit = QLineEdit()
        self.train_file_edit.setReadOnly(True)
        file_row.addWidget(self.train_file_edit, 1)

        browse_btn = QPushButton(translate("Browse..."))
        browse_btn.clicked.connect(self._browse_training_file)
        file_row.addWidget(browse_btn)
        train_layout.addLayout(file_row)

        sheet_row = QHBoxLayout()
        sheet_row.addWidget(QLabel(translate("Training Sheet:")))
        self.train_sheet_combo = QComboBox()
        self.train_sheet_combo.currentIndexChanged.connect(self._on_training_sheet_change)
        sheet_row.addWidget(self.train_sheet_combo, 1)

        load_btn = QPushButton(translate("Load Training File"))
        load_btn.clicked.connect(self._load_training_data)
        sheet_row.addWidget(load_btn)
        train_layout.addLayout(sheet_row)

        self.train_status_label = QLabel("")
        self.train_status_label.setWordWrap(True)
        train_layout.addWidget(self.train_status_label)

        cols_group = QGroupBox(translate("Training Columns"))
        cols_layout = QVBoxLayout()

        region_row = QHBoxLayout()
        region_row.addWidget(QLabel(translate("Region Column:")))
        self.train_region_combo = QComboBox()
        region_row.addWidget(self.train_region_combo, 1)
        cols_layout.addLayout(region_row)

        self.train_206_combo = QComboBox()
        self.train_207_combo = QComboBox()
        self.train_208_combo = QComboBox()

        pb_row1 = QHBoxLayout()
        pb_row1.addWidget(QLabel("206Pb/204Pb:"))
        pb_row1.addWidget(self.train_206_combo, 1)
        cols_layout.addLayout(pb_row1)

        pb_row2 = QHBoxLayout()
        pb_row2.addWidget(QLabel("207Pb/204Pb:"))
        pb_row2.addWidget(self.train_207_combo, 1)
        cols_layout.addLayout(pb_row2)

        pb_row3 = QHBoxLayout()
        pb_row3.addWidget(QLabel("208Pb/204Pb:"))
        pb_row3.addWidget(self.train_208_combo, 1)
        cols_layout.addLayout(pb_row3)

        cols_group.setLayout(cols_layout)
        train_layout.addWidget(cols_group)

        train_group.setLayout(train_layout)
        layout.addWidget(train_group)

        pred_group = QGroupBox(translate("Prediction Data"))
        pred_layout = QVBoxLayout()

        scope_group = QGroupBox(translate("Data Scope"))
        scope_layout = QVBoxLayout()
        self.radio_all = QRadioButton(translate("All data"))
        self.radio_selected = QRadioButton(translate("Selected data only"))

        selected_count = len(getattr(app_state, 'selected_indices', set()))
        total_count = len(app_state.df_global) if app_state.df_global is not None else 0

        if selected_count > 0:
            self.radio_selected.setText(translate("Selected data only") + f" ({selected_count}/{total_count})")
            self.radio_selected.setChecked(True)
        else:
            self.radio_all.setChecked(True)
            self.radio_selected.setEnabled(False)
            self.radio_selected.setText(translate("Selected data only") + f" ({translate('no selection')})")

        scope_layout.addWidget(self.radio_all)
        scope_layout.addWidget(self.radio_selected)
        scope_group.setLayout(scope_layout)
        pred_layout.addWidget(scope_group)

        pred_cols_group = QGroupBox(translate("Prediction Columns"))
        pred_cols_layout = QVBoxLayout()

        self.pred_206_combo = QComboBox()
        self.pred_207_combo = QComboBox()
        self.pred_208_combo = QComboBox()

        pred_row1 = QHBoxLayout()
        pred_row1.addWidget(QLabel("206Pb/204Pb:"))
        pred_row1.addWidget(self.pred_206_combo, 1)
        pred_cols_layout.addLayout(pred_row1)

        pred_row2 = QHBoxLayout()
        pred_row2.addWidget(QLabel("207Pb/204Pb:"))
        pred_row2.addWidget(self.pred_207_combo, 1)
        pred_cols_layout.addLayout(pred_row2)

        pred_row3 = QHBoxLayout()
        pred_row3.addWidget(QLabel("208Pb/204Pb:"))
        pred_row3.addWidget(self.pred_208_combo, 1)
        pred_cols_layout.addLayout(pred_row3)

        pred_cols_group.setLayout(pred_cols_layout)
        pred_layout.addWidget(pred_cols_group)

        pred_group.setLayout(pred_layout)
        layout.addWidget(pred_group)

        param_group = QGroupBox(translate("Parameters"))
        param_layout = QVBoxLayout()

        db_row = QHBoxLayout()
        db_row.addWidget(QLabel(translate("DBSCAN eps:")))
        self.eps_spin = QDoubleSpinBox()
        self.eps_spin.setRange(0.01, 2.0)
        self.eps_spin.setDecimals(3)
        self.eps_spin.setSingleStep(0.01)
        self.eps_spin.setValue(self._ml_params.get('dbscan_eps', 0.18))
        db_row.addWidget(self.eps_spin)
        param_layout.addLayout(db_row)

        ratio_row = QHBoxLayout()
        ratio_row.addWidget(QLabel(translate("DBSCAN min sample ratio:")))
        self.min_samples_ratio_spin = QDoubleSpinBox()
        self.min_samples_ratio_spin.setRange(0.01, 0.5)
        self.min_samples_ratio_spin.setDecimals(2)
        self.min_samples_ratio_spin.setSingleStep(0.01)
        self.min_samples_ratio_spin.setValue(self._ml_params.get('dbscan_min_samples_ratio', 0.1))
        ratio_row.addWidget(self.min_samples_ratio_spin)
        param_layout.addLayout(ratio_row)

        min_region_row = QHBoxLayout()
        min_region_row.addWidget(QLabel(translate("Min region samples:")))
        self.min_region_spin = QSpinBox()
        self.min_region_spin.setRange(3, 1000)
        self.min_region_spin.setValue(self._ml_params.get('min_region_samples', 5))
        min_region_row.addWidget(self.min_region_spin)
        param_layout.addLayout(min_region_row)

        db_min_region_row = QHBoxLayout()
        db_min_region_row.addWidget(QLabel(translate("DBSCAN min region samples:")))
        self.dbscan_min_region_spin = QSpinBox()
        self.dbscan_min_region_spin.setRange(5, 1000)
        self.dbscan_min_region_spin.setValue(self._ml_params.get('dbscan_min_region_samples', 20))
        db_min_region_row.addWidget(self.dbscan_min_region_spin)
        param_layout.addLayout(db_min_region_row)

        smote_row = QHBoxLayout()
        smote_row.addWidget(QLabel(translate("SMOTE k-neighbors:")))
        self.smote_k_spin = QSpinBox()
        self.smote_k_spin.setRange(1, 20)
        self.smote_k_spin.setValue(self._ml_params.get('smote_k_neighbors', 3))
        smote_row.addWidget(self.smote_k_spin)
        param_layout.addLayout(smote_row)

        threshold_row = QHBoxLayout()
        threshold_row.addWidget(QLabel(translate("Prediction threshold:")))
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0.5, 0.99)
        self.threshold_spin.setDecimals(2)
        self.threshold_spin.setSingleStep(0.01)
        self.threshold_spin.setValue(self._ml_params.get('predict_threshold', 0.9))
        threshold_row.addWidget(self.threshold_spin)
        param_layout.addLayout(threshold_row)

        self.smote_check = QCheckBox(translate("Enable SMOTE"))
        self.smote_check.setChecked(self._ml_params.get('smote_enabled', True))
        param_layout.addWidget(self.smote_check)

        self.standardize_check = QCheckBox(translate("Standardize data"))
        self.standardize_check.setChecked(self._ml_params.get('standardize', True))
        param_layout.addWidget(self.standardize_check)

        param_group.setLayout(param_layout)
        layout.addWidget(param_group)

        run_btn = QPushButton(translate("Run Provenance ML"))
        run_btn.setFixedWidth(220)
        run_btn.clicked.connect(self._on_run_ml)
        layout.addWidget(run_btn, 0, Qt.AlignHCenter)

        self.result_group = QGroupBox(translate("Results"))
        result_layout = QVBoxLayout()
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        result_layout.addWidget(self.result_text)
        self.result_group.setLayout(result_layout)
        self.result_group.setVisible(False)
        layout.addWidget(self.result_group)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        button_layout.addStretch()

        self.apply_btn = QPushButton(translate("Apply as Group Column"))
        self.apply_btn.clicked.connect(self._on_apply_group_column)
        self.apply_btn.setEnabled(False)
        button_layout.addWidget(self.apply_btn)

        self.export_btn = QPushButton(translate("Export Results"))
        self.export_btn.clicked.connect(self._on_export_results)
        self.export_btn.setEnabled(False)
        button_layout.addWidget(self.export_btn)

        close_btn = QPushButton(translate("Close"))
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def _refresh_prediction_columns(self):
        self.pred_206_combo.clear()
        self.pred_207_combo.clear()
        self.pred_208_combo.clear()

        if app_state.df_global is None:
            return

        numeric_cols = app_state.df_global.select_dtypes(include=[np.number]).columns.tolist()
        self.pred_206_combo.addItems(numeric_cols)
        self.pred_207_combo.addItems(numeric_cols)
        self.pred_208_combo.addItems(numeric_cols)
        self._auto_detect_pb_columns(numeric_cols, self.pred_206_combo, self.pred_207_combo, self.pred_208_combo)

    def _auto_detect_region_column(self, columns):
        for i, col in enumerate(columns):
            if col.lower().strip() in ('corrected region', 'region', 'corrected_region'):
                self.train_region_combo.setCurrentIndex(i)
                return
        for i, col in enumerate(columns):
            if 'region' in col.lower():
                self.train_region_combo.setCurrentIndex(i)
                return

    def _auto_detect_pb_columns(self, columns, combo_206, combo_207, combo_208):
        patterns = {
            '206': combo_206,
            '207': combo_207,
            '208': combo_208,
        }
        for key, combo in patterns.items():
            for i, col in enumerate(columns):
                col_lower = col.lower().replace(' ', '')
                if key in col_lower and '204' in col_lower:
                    combo.setCurrentIndex(i)
                    break
