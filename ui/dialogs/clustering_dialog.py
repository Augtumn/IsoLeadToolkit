"""HDBSCAN clustering parameter configuration dialog."""
from __future__ import annotations

from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

import numpy as np

from core import app_state, state_gateway, translate


class ClusteringDialog(QDialog):
    """Dialog to configure and run HDBSCAN clustering on embedding results."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._result: dict | None = None
        self.setWindowTitle(translate("HDBSCAN Clustering"))
        self.setMinimumWidth(420)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # --- embedding info ---
        embed = getattr(app_state, "last_embedding", None)
        embed_type = getattr(app_state, "last_embedding_type", "") or ""
        if embed is not None and hasattr(embed, "shape"):
            info = translate("Embedding: {type}  shape=({n},{d})").format(
                type=str(embed_type),
                n=embed.shape[0],
                d=embed.shape[1],
            )
        else:
            info = translate("No embedding available. Please run a dimensionality reduction first.")
        info_label = QLabel(info)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # --- parameters ---
        params_group = QGroupBox(translate("Clustering Parameters"))
        params_layout = QVBoxLayout(params_group)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel(translate("Min Cluster Size:")))
        self.min_cluster_spin = QSpinBox()
        self.min_cluster_spin.setRange(2, 5000)
        self.min_cluster_spin.setValue(5)
        self.min_cluster_spin.setToolTip(
            translate("Smallest number of points required to form a cluster.")
        )
        row1.addWidget(self.min_cluster_spin)
        params_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel(translate("Min Samples:")))
        self.min_samples_spin = QSpinBox()
        self.min_samples_spin.setRange(1, 5000)
        self.min_samples_spin.setValue(5)
        self.min_samples_spin.setToolTip(
            translate(
                "Number of points in a neighbourhood for core points. "
                "Lower values make clustering more conservative."
            )
        )
        row2.addWidget(self.min_samples_spin)
        params_layout.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel(translate("Cluster Selection Epsilon:")))
        self.epsilon_spin = QDoubleSpinBox()
        self.epsilon_spin.setRange(0.0, 100.0)
        self.epsilon_spin.setSingleStep(0.1)
        self.epsilon_spin.setDecimals(3)
        self.epsilon_spin.setValue(0.0)
        self.epsilon_spin.setToolTip(
            translate("Distance threshold to merge clusters. Larger = fewer clusters.")
        )
        row3.addWidget(self.epsilon_spin)
        params_layout.addLayout(row3)

        row4 = QHBoxLayout()
        row4.addWidget(QLabel(translate("Metric:")))
        self.metric_combo = QComboBox()
        self.metric_combo.addItems(["euclidean", "manhattan", "cosine", "chebyshev"])
        self.metric_combo.setToolTip(translate("Distance metric for clustering."))
        row4.addWidget(self.metric_combo)
        params_layout.addLayout(row4)

        layout.addWidget(params_group)

        # --- run button ---
        self.run_btn = QPushButton(translate("Run Clustering"))
        self.run_btn.clicked.connect(self._on_run)
        layout.addWidget(self.run_btn)

        # --- results ---
        self.result_label = QLabel("")
        self.result_label.setWordWrap(True)
        self.result_label.setVisible(False)
        layout.addWidget(self.result_label)

        # --- apply button ---
        self.apply_btn = QPushButton(translate("Apply as Group Column"))
        self.apply_btn.clicked.connect(self._on_apply)
        self.apply_btn.setVisible(False)
        layout.addWidget(self.apply_btn)

        layout.addStretch()

    def _on_run(self):
        embed = getattr(app_state, "last_embedding", None)
        if embed is None:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("No embedding data available. Please run a dimensionality reduction first."),
            )
            return

        from data.clustering import run_hdbscan_clustering

        result = run_hdbscan_clustering(
            embedding=np.asarray(embed),
            min_cluster_size=self.min_cluster_spin.value(),
            min_samples=self.min_samples_spin.value(),
            cluster_selection_epsilon=self.epsilon_spin.value(),
            metric=self.metric_combo.currentText(),
        )
        if result is None:
            QMessageBox.critical(
                self,
                translate("Error"),
                translate("Clustering failed. Check the log for details."),
            )
            return

        self._result = result
        self.result_label.setText(
            translate(
                "Clusters: {n_clusters}  |  Noise points: {n_noise} ({pct:.1f}%)"
            ).format(
                n_clusters=result["n_clusters"],
                n_noise=result["n_noise"],
                pct=100.0 * result["n_noise"] / max(1, len(result["labels"])),
            )
        )
        self.result_label.setVisible(True)
        self.apply_btn.setVisible(True)

    def _on_apply(self):
        if self._result is None:
            return
        df = getattr(app_state, "df_global", None)
        if df is None:
            return

        labels = self._result["labels"]
        probs = self._result["probabilities"]

        if len(labels) != len(df):
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate(
                    "Clustering result length ({n_labels}) does not match data rows ({n_rows})."
                ).format(n_labels=len(labels), n_rows=len(df)),
            )
            return

        # Map cluster labels: -1 → "Noise", otherwise "Cluster N"
        display_labels = [
            translate("Noise") if lbl == -1 else f"Cluster {lbl}"
            for lbl in labels
        ]

        col_label = "_HDBSCAN_Cluster"
        col_prob = "_HDBSCAN_Prob"
        df[col_label] = display_labels
        df[col_prob] = probs

        current_groups = list(getattr(app_state, "group_cols", []) or [])
        if col_label not in current_groups:
            current_groups.append(col_label)
        state_gateway.set_group_data_columns(
            current_groups,
            list(getattr(app_state, "data_cols", []) or []),
        )
        state_gateway.set_last_group_col(col_label)

        self.accept()

        try:
            from visualization.events import on_slider_change
            on_slider_change()
        except Exception:
            pass
