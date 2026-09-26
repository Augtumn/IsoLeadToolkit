"""Data panel projection parameter UI construction."""
from __future__ import annotations

import logging

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
)

from core import app_state, state_gateway, translate

logger = logging.getLogger(__name__)

from .projection_groups_build import DataPanelProjectionGroupsBuildMixin


class DataPanelProjectionBuildMixin(DataPanelProjectionGroupsBuildMixin):
    """Build UMAP/t-SNE/PCA/RobustPCA/Ternary parameter UI controls for data panel."""
    algo_combo = None
    metric_combo = None
    preset_combo = None
    robust_support_spin = None
    spinboxes = None
    standardize_check = None

    # Declared by the class that uses them, so no probe is needed for widgets
    # that build() creates later (UI review item B).

    def _build_projection_params(self, layout):
        """Build projection algorithm parameter groups.

        Creates UMAP, t-SNE, PCA, RobustPCA, and Ternary parameter groups.

        Args:
            layout: The parent layout to add widgets into.
        """
        if not self.spinboxes is not None:
            self.spinboxes = {}
        self._build_preset_bar(layout)
        self._build_umap_group(layout)
        self._build_tsne_group(layout)
        self._build_pca_group(layout)
        self._build_robust_pca_group(layout)
        self._build_ternary_group(layout)

    # ------------------------------------------------------------------ #
    #  Projection preset save / load
    # ------------------------------------------------------------------ #

    def _preset_combo_refresh(self):
        """Refresh the preset combo box from saved presets."""
        if not self.preset_combo is not None or self.preset_combo is None:
            return
        self.preset_combo.blockSignals(True)
        current = self.preset_combo.currentText()
        self.preset_combo.clear()
        self.preset_combo.addItem(translate("Custom"))
        presets = dict(app_state.param_presets or {})
        for name in sorted(presets.keys()):
            self.preset_combo.addItem(name)
        idx = self.preset_combo.findText(current)
        self.preset_combo.setCurrentText(current if idx >= 0 else translate("Custom"))
        self.preset_combo.blockSignals(False)

    def _collect_params_snapshot(self) -> dict:
        """Snapshot current projection params from app_state for preset storage."""
        return {
            "algorithm": str(app_state.algorithm),
            "umap_params": dict(app_state.umap_params),
            "tsne_params": dict(app_state.tsne_params),
            "pca_params": dict(app_state.pca_params),
            "robust_pca_params": dict(app_state.robust_pca_params),
            "ml_params": dict(app_state.ml_params),
            "v1v2_params": dict(app_state.v1v2_params),
            "standardize_data": bool(app_state.standardize_data),
        }

    def _save_preset(self):
        """Prompt for preset name and save current projection params.

        Presets live in ``app_state.param_presets`` (persisted via the
        autosave path into ui_state.json) — they no longer share the theme
        container ``saved_themes`` / user_themes.json.
        """
        name, ok = QInputDialog.getText(
            self,
            translate("Save Preset"),
            translate("Preset name:"),
        )
        if not ok or not name:
            return

        name = name.strip()
        if not name:
            return

        presets = dict(app_state.param_presets or {})
        presets[name] = self._collect_params_snapshot()
        state_gateway.set_param_presets(presets)
        logger.info("Saved projection preset '%s' (%s presets total)", name, len(presets))

        self._preset_combo_refresh()
        idx = self.preset_combo.findText(name)
        if idx >= 0:
            self.preset_combo.setCurrentIndex(idx)

    def _apply_params_to_ui(self, snapshot: dict):
        """Apply a parameter snapshot to all projection UI controls."""
        params = snapshot.get("params", snapshot)

        # --- UMAP ---
        umap = params.get("umap_params", {})
        if umap:
            if "n_neighbors" in umap and "umap_n_neighbors" in self.sliders:
                self.sliders["umap_n_neighbors"].setValue(umap["n_neighbors"])
            if "min_dist" in umap and "umap_min_dist" in self.sliders:
                self.sliders["umap_min_dist"].setValue(int(umap["min_dist"] * 100))
            if "metric" in umap and self.metric_combo is not None and self.metric_combo:
                self.metric_combo.setCurrentText(umap["metric"])

        # --- t-SNE ---
        tsne = params.get("tsne_params", {})
        if tsne:
            if "perplexity" in tsne and "tsne_perplexity" in self.sliders:
                self.sliders["tsne_perplexity"].setValue(tsne["perplexity"])
            if "learning_rate" in tsne and "tsne_learning_rate" in self.sliders:
                self.sliders["tsne_learning_rate"].setValue(int(tsne["learning_rate"] / 10))
            if "random_state" in tsne and "tsne_random_state" in self.spinboxes:
                self.spinboxes["tsne_random_state"].setValue(tsne["random_state"])

        # --- PCA ---
        pca = params.get("pca_params", {})
        if pca:
            if "n_components" in pca and "pca_n_components" in self.spinboxes:
                self.spinboxes["pca_n_components"].setValue(pca["n_components"])
            if "random_state" in pca and "pca_random_state" in self.spinboxes:
                self.spinboxes["pca_random_state"].setValue(pca["random_state"])

        # --- Robust PCA ---
        rpca = params.get("robust_pca_params", {})
        if rpca:
            if "n_components" in rpca and "robust_pca_n_components" in self.spinboxes:
                self.spinboxes["robust_pca_n_components"].setValue(rpca["n_components"])
            if "support_fraction" in rpca and self.robust_support_spin is not None:
                self.robust_support_spin.setValue(rpca["support_fraction"])
            if "random_state" in rpca and "robust_pca_random_state" in self.spinboxes:
                self.spinboxes["robust_pca_random_state"].setValue(rpca["random_state"])

        # --- Standardize checkbox ---
        if "standardize_data" in params and self.standardize_check is not None:
            self.standardize_check.setChecked(params["standardize_data"])

    def _load_preset(self):
        """Load the selected preset into projection controls."""
        if not self.preset_combo is not None or self.preset_combo is None:
            return
        name = self.preset_combo.currentText()
        if not name or name == translate("Custom"):
            return
        presets = dict(app_state.param_presets or {})
        if name not in presets:
            return

        snapshot = presets[name]

        # Sync app_state directly
        params = snapshot.get("params", snapshot)
        algo = snapshot.get("algorithm", "")
        if algo:
            state_gateway.set_algorithm(algo)
            # Also update the algorithm combo
            if self.algo_combo is not None and self.algo_combo is not None:
                self._set_combo_value(self.algo_combo, algo)

        param_setters = {
            "umap_params": state_gateway.set_umap_params,
            "tsne_params": state_gateway.set_tsne_params,
            "pca_params": state_gateway.set_pca_params,
            "robust_pca_params": state_gateway.set_robust_pca_params,
            "ml_params": state_gateway.set_ml_params,
            "v1v2_params": state_gateway.set_v1v2_params,
        }
        for key, setter in param_setters.items():
            if key in params:
                setter(dict(params[key]))

        if "standardize_data" in params:
            state_gateway.set_standardize_data(params["standardize_data"])

        self._apply_params_to_ui(snapshot)

        self._on_change()

    def _build_preset_bar(self, layout):
        """Build preset save/load combo + buttons at the top of projection params."""
        bar = QHBoxLayout()
        bar.setContentsMargins(0, 0, 0, 4)

        preset_label = QLabel(translate("Preset:"))
        preset_label.setProperty("translate_key", "Preset:")
        bar.addWidget(preset_label)

        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(140)
        self.preset_combo.addItem(translate("Custom"))
        bar.addWidget(self.preset_combo)

        self.save_preset_btn = QPushButton(translate("Save"))
        self.save_preset_btn.setProperty("translate_key", "Save")
        self.save_preset_btn.clicked.connect(self._save_preset)
        bar.addWidget(self.save_preset_btn)

        self.load_preset_btn = QPushButton(translate("Load"))
        self.load_preset_btn.setProperty("translate_key", "Load")
        self.load_preset_btn.clicked.connect(self._load_preset)
        bar.addWidget(self.load_preset_btn)

        bar.addStretch()
        layout.addLayout(bar)

        self._preset_combo_refresh()
