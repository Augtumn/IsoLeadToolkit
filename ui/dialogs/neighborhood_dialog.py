"""Neighborhood search dialog — interactive radius adjustment."""
from __future__ import annotations
import logging
import numpy as np

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSlider, QDoubleSpinBox, QSpinBox, QTableWidget,
    QTableWidgetItem, QGroupBox, QMessageBox, QCheckBox, QHeaderView,
    QLineEdit,
)
from PyQt5.QtCore import Qt

from core import app_state, state_gateway, translate

logger = logging.getLogger(__name__)


def show_neighborhood_search(parent=None):
    """Open the neighborhood search dialog."""
    if app_state.df_global is None:
        QMessageBox.warning(
            parent if parent else None,
            translate("Warning"),
            translate("Please load data first."),
        )
        return
    if getattr(app_state, "last_embedding", None) is None:
        QMessageBox.warning(
            parent if parent else None,
            translate("Warning"),
            translate("No embedding data. Run a dimensionality reduction first."),
        )
        return
    dialog = NeighborhoodSearchDialog(parent)
    dialog.exec_()


class NeighborhoodSearchDialog(QDialog):
    """Search for background points within radius of query group in embedding space."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(translate("Neighborhood Search"))
        self.setMinimumWidth(720)
        self.setMinimumHeight(560)
        self._result = None
        self._orig_indices: np.ndarray | None = None  # tracks original df indices
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # ── Query group selection ──────────────────────────────────
        group_row = QHBoxLayout()
        group_row.addWidget(QLabel(translate("Query Group:")))
        self.query_combo = QComboBox()
        self.query_combo.setMinimumWidth(200)
        group_row.addWidget(self.query_combo, 1)
        layout.addLayout(group_row)

        # ── Radius control ─────────────────────────────────────────
        radius_group = QGroupBox(translate("Search Radius"))
        radius_layout = QVBoxLayout(radius_group)

        # Radius slider + spin
        radius_row = QHBoxLayout()
        radius_row.addWidget(QLabel(translate("Radius:")))
        self.radius_slider = QSlider(Qt.Horizontal)
        self.radius_slider.setRange(1, 200)
        self.radius_slider.setValue(20)
        self.radius_spin = QDoubleSpinBox()
        self.radius_spin.setRange(0.01, 50.0)
        self.radius_spin.setSingleStep(0.05)
        self.radius_spin.setDecimals(3)
        self.radius_spin.setValue(0.5)
        radius_row.addWidget(self.radius_slider, 1)
        radius_row.addWidget(self.radius_spin)
        radius_layout.addLayout(radius_row)

        # Min neighbors
        min_row = QHBoxLayout()
        min_row.addWidget(QLabel(translate("Min Neighbors:")))
        self.min_neighbors_spin = QSpinBox()
        self.min_neighbors_spin.setRange(0, 100)
        self.min_neighbors_spin.setValue(1)
        min_row.addWidget(self.min_neighbors_spin)
        min_row.addStretch()
        radius_layout.addLayout(min_row)

        layout.addWidget(radius_group)

        # ── Column name ─────────────────────────────────────────────
        col_name_row = QHBoxLayout()
        col_name_row.addWidget(QLabel(translate("Column Name:")))
        self.col_name_edit = QLineEdit(f"_Neighbor_r{0.5:.2f}")
        col_name_row.addWidget(self.col_name_edit, 1)
        layout.addLayout(col_name_row)

        # ── Action buttons ─────────────────────────────────────────
        btn_row = QHBoxLayout()
        search_btn = QPushButton(translate("Search"))
        search_btn.clicked.connect(self._do_search)
        btn_row.addWidget(search_btn)

        self.apply_check = QCheckBox(translate("Add as group column"))
        self.apply_check.setChecked(True)
        btn_row.addWidget(self.apply_check)

        apply_btn = QPushButton(translate("Apply to Data"))
        apply_btn.clicked.connect(self._apply_as_group)
        btn_row.addWidget(apply_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        # ── Summary label ──────────────────────────────────────────
        self.info_label = QLabel("")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.info_label)

        # ── Results table ──────────────────────────────────────────
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(4)
        self.result_table.setHorizontalHeaderLabels([
            translate("Query Point"),
            translate("# Neighbors"),
            translate("Avg Distance"),
            translate("BG Indices"),
        ])
        self.result_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch)
        self.result_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.Stretch)
        layout.addWidget(self.result_table)

        # ── Wire radius sync ──────────────────────────────────────
        def _slider_to_spin(v):
            self.radius_spin.blockSignals(True)
            self.radius_spin.setValue(v / 200.0 * 10.0)
            self.radius_spin.blockSignals(False)

        def _spin_to_slider(v):
            self.radius_slider.blockSignals(True)
            self.radius_slider.setValue(int(v / 10.0 * 200))
            self.radius_slider.blockSignals(False)

        self.radius_slider.valueChanged.connect(_slider_to_spin)
        self.radius_spin.valueChanged.connect(_spin_to_slider)
        # Live preview on slider change
        self.radius_slider.valueChanged.connect(self._do_search)
        self.radius_spin.valueChanged.connect(self._do_search)
        self.min_neighbors_spin.valueChanged.connect(self._do_search)
        # Update column name when radius changes
        def _update_col_name(v):
            self.col_name_edit.setText(f"_Neighbor_r{float(v):.2f}")
        self.radius_spin.valueChanged.connect(_update_col_name)

        # Populate groups
        self._populate_groups()

    def _populate_groups(self):
        """Fill query group combo from current group column."""
        group_col = getattr(app_state, 'last_group_col', None)
        if not group_col:
            groups = getattr(app_state, 'group_cols', [])
            group_col = groups[0] if groups else None
        if not group_col:
            return
        df = getattr(app_state, 'df_global', None)
        if df is None or group_col not in df.columns:
            return
        for val in sorted(df[group_col].dropna().unique()):
            self.query_combo.addItem(str(val), str(val))
        if self.query_combo.count() > 0:
            # Skip the first few slots if we want to set default from selection
            pass

    def _get_embedding_and_groups(self):
        """Get the embedding array and group labels, handling subset."""
        embedding = getattr(app_state, 'last_embedding', None)
        if embedding is None:
            return None, None, None

        group_col = getattr(app_state, 'last_group_col', None)
        if not group_col:
            return None, None, None

        df = getattr(app_state, 'df_global', None)
        if df is None or group_col not in df.columns:
            return None, None, None

        groups = df[group_col].fillna("Unknown").astype(str).values

        indices = getattr(app_state, 'active_subset_indices', None)
        if indices and len(indices) > 0:
            idx_list = np.array(sorted(indices))
            emb = embedding[idx_list]  # slice embedding to match subset
            grp = groups[idx_list]
            self._orig_indices = idx_list
        else:
            emb = embedding
            grp = groups
            self._orig_indices = np.arange(len(groups))

        n = min(len(emb), len(grp))
        return emb[:n], grp[:n], group_col

    def _do_search(self):
        """Run the neighborhood search and update results table."""
        query_group = self.query_combo.currentText()
        if not query_group:
            return

        radius = self.radius_spin.value()
        min_neighbors = self.min_neighbors_spin.value()

        emb, grp, group_col = self._get_embedding_and_groups()
        if emb is None:
            QMessageBox.warning(
                self, translate("Warning"),
                translate("No embedding or group data available."))
            return

        from plugins.registry import plugin_manager
        plugin = plugin_manager.get("neighborhood_plugin")
        if plugin is None:
            QMessageBox.warning(
                self, translate("Warning"),
                translate("Neighborhood search plugin not loaded."))
            return

        self._result = plugin.search(
            emb, grp, query_group, radius, min_neighbors=min_neighbors,
        )

        matches = self._result.get("matches", [])
        summary = self._result.get("summary", "")
        self.info_label.setText(summary)

        self.result_table.setRowCount(len(matches))
        for i, m in enumerate(matches):
            self.result_table.setItem(
                i, 0, QTableWidgetItem(str(m["query_label"])))
            self.result_table.setItem(
                i, 1, QTableWidgetItem(str(m["neighbor_count"])))
            avg_d = float(np.mean(m["distances"])) if m["distances"] else 0.0
            self.result_table.setItem(i, 2, QTableWidgetItem(f"{avg_d:.4f}"))
            # Show first few neighbor indices
            nbr_str = ", ".join(str(ni) for ni in m["neighbor_indices"][:5])
            if len(m["neighbor_indices"]) > 5:
                nbr_str += f" … (+{len(m['neighbor_indices']) - 5})"
            self.result_table.setItem(i, 3, QTableWidgetItem(nbr_str))

        self.result_table.resizeColumnsToContents()

    def _apply_as_group(self):
        """Add a new column to the dataframe marking query/neighbor points."""
        if self._result is None:
            QMessageBox.warning(
                self, translate("Warning"),
                translate("Please run the search first."))
            return

        query_group = self.query_combo.currentText()
        radius = self.radius_spin.value()
        matches = self._result.get("matches", [])

        df = app_state.df_global
        if df is None:
            return
        n = len(df)
        new_col = np.full(n, "Other", dtype=object)

        for m in matches:
            qi_local = m["query_index"]
            if self._orig_indices is not None and qi_local < len(self._orig_indices):
                orig_qi = int(self._orig_indices[qi_local])
                if 0 <= orig_qi < n:
                    new_col[orig_qi] = f"Query_{query_group}"

        for m in matches:
            qi_local = m["query_index"]
            for ni_local in m.get("neighbor_indices", []):
                if self._orig_indices is not None and ni_local < len(self._orig_indices):
                    orig_ni = int(self._orig_indices[ni_local])
                    if 0 <= orig_ni < n and new_col[orig_ni] == "Other":
                        new_col[orig_ni] = f"Neighbor_{query_group}"

        col_name = self.col_name_edit.text().strip() or f"_Neighbor_r{radius:.2f}"
        df[col_name] = new_col

        # Use gateway for coordinated state updates
        state_gateway.set_dataframe_and_source(
            df,
            file_path=getattr(app_state, 'file_path', ''),
            sheet_name=getattr(app_state, 'sheet_name', None),
        )

        groups = list(getattr(app_state, 'group_cols', []) or [])
        if col_name not in groups:
            groups.append(col_name)
        data_cols = list(getattr(app_state, 'data_cols', []) or [])
        state_gateway.set_group_data_columns(groups, data_cols)
        state_gateway.set_last_group_col(col_name)
        state_gateway.bump_data_version()

        # Trigger plot refresh with new group column
        try:
            from visualization.events import on_slider_change
            on_slider_change()
        except Exception:
            pass

        QMessageBox.information(
            self, translate("Done"),
            translate("Neighborhood results added as group column: {col}").format(
                col=col_name))
