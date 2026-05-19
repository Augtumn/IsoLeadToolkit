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
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
)

from core import app_state, state_gateway, translate

logger = logging.getLogger(__name__)


class _DataPanelProjectionBuild:
    """Build UMAP/t-SNE/PCA/RobustPCA/Ternary parameter UI controls for data panel."""

    def _build_projection_params(self, layout):
        """Build projection algorithm parameter groups.

        Creates UMAP, t-SNE, PCA, RobustPCA, and Ternary parameter groups.

        Args:
            layout: The parent layout to add widgets into.
        """
        self.umap_group = QGroupBox(translate("UMAP Parameters"))
        self.umap_group.setProperty("translate_key", "UMAP Parameters")
        umap_layout = QVBoxLayout()

        n_label = QLabel(translate("n_neighbors: {value}").format(value=app_state.umap_params["n_neighbors"]))
        umap_layout.addWidget(n_label)

        n_slider = QSlider(Qt.Horizontal)
        n_slider.setMinimum(2)
        n_slider.setMaximum(50)
        n_neighbors = min(app_state.umap_params["n_neighbors"], 50)
        if app_state.umap_params["n_neighbors"] != n_neighbors:
            state_gateway.set_umap_params(app_state.umap_params | {"n_neighbors": n_neighbors})
        n_slider.setValue(n_neighbors)
        n_slider.valueChanged.connect(lambda v: self._on_umap_slider_changed("n_neighbors", v, n_label, n_slider))
        n_slider.sliderReleased.connect(self._on_change)
        umap_layout.addWidget(n_slider)

        self.sliders["umap_n_neighbors"] = n_slider
        self.labels["umap_n_neighbors"] = n_label

        min_dist_label = QLabel(translate("min_dist: {value:.2f}").format(value=app_state.umap_params["min_dist"]))
        umap_layout.addWidget(min_dist_label)

        min_dist_slider = QSlider(Qt.Horizontal)
        min_dist_slider.setMinimum(0)
        min_dist_slider.setMaximum(100)
        min_dist_slider.setValue(int(app_state.umap_params["min_dist"] * 100))
        min_dist_slider.valueChanged.connect(
            lambda v: self._on_umap_slider_changed("min_dist", v / 100.0, min_dist_label, min_dist_slider)
        )
        min_dist_slider.sliderReleased.connect(self._on_change)
        umap_layout.addWidget(min_dist_slider)

        self.sliders["umap_min_dist"] = min_dist_slider
        self.labels["umap_min_dist"] = min_dist_label

        metric_label = QLabel(translate("metric:"))
        metric_label.setProperty("translate_key", "metric:")
        umap_layout.addWidget(metric_label)

        self.metric_combo = QComboBox()
        metric_options = ["euclidean", "manhattan", "cosine"]
        self.metric_combo.addItems(metric_options)
        current_metric = app_state.umap_params.get("metric", "euclidean")
        if current_metric in metric_options:
            self.metric_combo.setCurrentText(current_metric)
        self.metric_combo.currentTextChanged.connect(lambda v: self._on_umap_param_change("metric", v, metric_label))
        umap_layout.addWidget(self.metric_combo)

        self.umap_group.setLayout(umap_layout)
        layout.addWidget(self.umap_group)

        self.tsne_group = QGroupBox(translate("t-SNE Parameters"))
        self.tsne_group.setProperty("translate_key", "t-SNE Parameters")
        tsne_layout = QVBoxLayout()

        perp_label = QLabel(translate("perplexity: {value}").format(value=app_state.tsne_params["perplexity"]))
        tsne_layout.addWidget(perp_label)

        perp_slider = QSlider(Qt.Horizontal)
        perp_slider.setMinimum(5)
        perp_slider.setMaximum(100)
        perplexity = min(int(app_state.tsne_params["perplexity"]), 100)
        if app_state.tsne_params["perplexity"] != perplexity:
            state_gateway.set_tsne_params(app_state.tsne_params | {"perplexity": perplexity})
        perp_slider.setValue(perplexity)
        perp_slider.valueChanged.connect(lambda v: self._on_tsne_slider_changed("perplexity", v, perp_label))
        perp_slider.sliderReleased.connect(self._on_change)
        tsne_layout.addWidget(perp_slider)

        self.sliders["tsne_perplexity"] = perp_slider
        self.labels["tsne_perplexity"] = perp_label

        lr_label = QLabel(translate("learning_rate: {value}").format(value=int(app_state.tsne_params["learning_rate"])))
        tsne_layout.addWidget(lr_label)

        lr_slider = QSlider(Qt.Horizontal)
        lr_slider.setMinimum(1)
        lr_slider.setMaximum(100)
        lr_slider.setValue(int(app_state.tsne_params["learning_rate"] / 10))
        lr_slider.valueChanged.connect(lambda v: self._on_tsne_slider_changed("learning_rate", v * 10, lr_label))
        lr_slider.sliderReleased.connect(self._on_change)
        tsne_layout.addWidget(lr_slider)

        self.sliders["tsne_learning_rate"] = lr_slider
        self.labels["tsne_learning_rate"] = lr_label

        tsne_rs_label = QLabel(
            translate("random_state: {value}").format(value=app_state.tsne_params.get("random_state", 42))
        )
        tsne_layout.addWidget(tsne_rs_label)

        tsne_rs_spin = QSpinBox()
        tsne_rs_spin.setRange(0, 200)
        tsne_rs_spin.setValue(app_state.tsne_params.get("random_state", 42))
        self._connect_spinbox_deferred(
            tsne_rs_spin,
            lambda v: self._on_tsne_param_change("random_state", v, tsne_rs_label),
        )
        tsne_layout.addWidget(tsne_rs_spin)

        self.tsne_group.setLayout(tsne_layout)
        layout.addWidget(self.tsne_group)

        self.pca_group = QGroupBox(translate("PCA Parameters"))
        self.pca_group.setProperty("translate_key", "PCA Parameters")
        pca_layout = QVBoxLayout()

        n_comp_label = QLabel(translate("n_components:"))
        n_comp_label.setProperty("translate_key", "n_components:")

        n_comp_spin = QSpinBox()
        n_comp_spin.setRange(2, 10)
        n_comp_spin.setValue(app_state.pca_params.get("n_components", 2))
        self._connect_spinbox_deferred(n_comp_spin, lambda v: self._on_pca_param_change("n_components", v))
        pca_layout.addWidget(n_comp_spin)

        pca_rs_label = QLabel(translate("random_state: {value}").format(value=app_state.pca_params.get("random_state", 42)))
        pca_layout.addWidget(pca_rs_label)

        pca_rs_spin = QSpinBox()
        pca_rs_spin.setRange(0, 200)
        pca_rs_spin.setValue(app_state.pca_params.get("random_state", 42))
        self._connect_spinbox_deferred(
            pca_rs_spin,
            lambda v: self._on_pca_param_change("random_state", v, pca_rs_label),
        )
        pca_layout.addWidget(pca_rs_spin)

        standardize_check = QCheckBox(translate("Standardize data"))
        standardize_check.setProperty("translate_key", "Standardize data")
        standardize_check.setChecked(app_state.standardize_data)
        standardize_check.stateChanged.connect(self._on_standardize_change)
        pca_layout.addWidget(standardize_check)

        pca_tools_layout = QHBoxLayout()

        scree_btn = QPushButton(translate("Scree Plot"))
        scree_btn.setProperty("translate_key", "Scree Plot")
        scree_btn.clicked.connect(self._on_show_scree_plot)
        pca_tools_layout.addWidget(scree_btn)

        loadings_btn = QPushButton(translate("Loadings"))
        loadings_btn.setProperty("translate_key", "Loadings")
        loadings_btn.clicked.connect(self._on_show_pca_loadings)
        pca_tools_layout.addWidget(loadings_btn)

        pca_layout.addLayout(pca_tools_layout)

        dim_layout = QHBoxLayout()

        x_label = QLabel(translate("X:"))
        dim_layout.addWidget(x_label)

        self.pca_x_spin = QSpinBox()
        self.pca_x_spin.setRange(1, 10)
        self.pca_x_spin.setValue(app_state.pca_component_indices[0] + 1)
        self.pca_x_spin.setMaximumWidth(60)
        self._connect_spinbox_deferred(self.pca_x_spin, self._on_pca_dim_change, pass_value=False)
        dim_layout.addWidget(self.pca_x_spin)

        y_label = QLabel(translate("Y:"))
        dim_layout.addWidget(y_label)

        self.pca_y_spin = QSpinBox()
        self.pca_y_spin.setRange(1, 10)
        self.pca_y_spin.setValue(app_state.pca_component_indices[1] + 1)
        self.pca_y_spin.setMaximumWidth(60)
        self._connect_spinbox_deferred(self.pca_y_spin, self._on_pca_dim_change, pass_value=False)
        dim_layout.addWidget(self.pca_y_spin)

        dim_layout.addStretch()
        pca_layout.addLayout(dim_layout)

        self.pca_group.setLayout(pca_layout)
        layout.addWidget(self.pca_group)

        self.robust_pca_group = QGroupBox(translate("RobustPCA Parameters"))
        self.robust_pca_group.setProperty("translate_key", "RobustPCA Parameters")
        robust_pca_layout = QVBoxLayout()

        robust_n_comp_label = QLabel(translate("n_components:"))
        robust_n_comp_label.setProperty("translate_key", "n_components:")
        robust_pca_layout.addWidget(robust_n_comp_label)

        robust_n_comp_spin = QSpinBox()
        robust_n_comp_spin.setRange(2, 10)
        robust_n_comp_spin.setValue(app_state.robust_pca_params.get("n_components", 2))
        self._connect_spinbox_deferred(
            robust_n_comp_spin,
            lambda v: self._on_robust_pca_param_change("n_components", v),
        )
        robust_pca_layout.addWidget(robust_n_comp_spin)

        support_label = QLabel(
            translate("support_fraction: {value:.2f}").format(
                value=app_state.robust_pca_params.get("support_fraction", 0.75)
            )
        )
        robust_pca_layout.addWidget(support_label)

        support_spin = QDoubleSpinBox()
        support_spin.setRange(0.1, 1.0)
        support_spin.setSingleStep(0.05)
        support_spin.setDecimals(2)
        support_spin.setValue(app_state.robust_pca_params.get("support_fraction", 0.75))
        self._connect_spinbox_deferred(
            support_spin,
            lambda v: self._on_robust_pca_param_change("support_fraction", v, support_label)
        )
        robust_pca_layout.addWidget(support_spin)

        self.labels["robust_pca_support"] = support_label

        robust_rs_label = QLabel(translate("random_state:"))
        robust_rs_label.setProperty("translate_key", "random_state:")
        robust_pca_layout.addWidget(robust_rs_label)

        robust_rs_spin = QSpinBox()
        robust_rs_spin.setRange(0, 9999)
        robust_rs_spin.setValue(app_state.robust_pca_params.get("random_state", 42))
        self._connect_spinbox_deferred(
            robust_rs_spin,
            lambda v: self._on_robust_pca_param_change("random_state", v),
        )
        robust_pca_layout.addWidget(robust_rs_spin)

        rpca_tools_layout = QHBoxLayout()

        rpca_scree_btn = QPushButton(translate("Scree Plot"))
        rpca_scree_btn.setProperty("translate_key", "Scree Plot")
        rpca_scree_btn.clicked.connect(self._on_show_scree_plot)
        rpca_tools_layout.addWidget(rpca_scree_btn)

        rpca_loadings_btn = QPushButton(translate("Loadings"))
        rpca_loadings_btn.setProperty("translate_key", "Loadings")
        rpca_loadings_btn.clicked.connect(self._on_show_pca_loadings)
        rpca_tools_layout.addWidget(rpca_loadings_btn)

        robust_pca_layout.addLayout(rpca_tools_layout)

        rpca_dim_layout = QHBoxLayout()

        rpca_x_label = QLabel(translate("X:"))
        rpca_dim_layout.addWidget(rpca_x_label)

        self.rpca_x_spin = QSpinBox()
        self.rpca_x_spin.setRange(1, 10)
        self.rpca_x_spin.setValue(app_state.pca_component_indices[0] + 1)
        self.rpca_x_spin.setMaximumWidth(60)
        self._connect_spinbox_deferred(self.rpca_x_spin, self._on_pca_dim_change, pass_value=False)
        rpca_dim_layout.addWidget(self.rpca_x_spin)

        rpca_y_label = QLabel(translate("Y:"))
        rpca_dim_layout.addWidget(rpca_y_label)

        self.rpca_y_spin = QSpinBox()
        self.rpca_y_spin.setRange(1, 10)
        self.rpca_y_spin.setValue(app_state.pca_component_indices[1] + 1)
        self.rpca_y_spin.setMaximumWidth(60)
        self._connect_spinbox_deferred(self.rpca_y_spin, self._on_pca_dim_change, pass_value=False)
        rpca_dim_layout.addWidget(self.rpca_y_spin)

        rpca_dim_layout.addStretch()
        robust_pca_layout.addLayout(rpca_dim_layout)

        self.robust_pca_group.setLayout(robust_pca_layout)
        layout.addWidget(self.robust_pca_group)

        self.ternary_group = QGroupBox(translate("Ternary Plot"))
        self.ternary_group.setProperty("translate_key", "Ternary Plot")
        ternary_layout = QVBoxLayout()

        info_label = QLabel(translate("Using Standard Ternary Plot.\nData is plotted as relative proportions."))
        info_label.setProperty(
            "translate_key",
            "Using Standard Ternary Plot.\nData is plotted as relative proportions.",
        )
        info_label.setWordWrap(True)
        ternary_layout.addWidget(info_label)

        self.ternary_auto_zoom_check = QCheckBox(translate("Auto-Zoom to Data"))
        self.ternary_auto_zoom_check.setProperty("translate_key", "Auto-Zoom to Data")
        self.ternary_auto_zoom_check.setChecked(getattr(app_state, "ternary_auto_zoom", False))
        self.ternary_auto_zoom_check.stateChanged.connect(self._on_ternary_zoom_change)
        ternary_layout.addWidget(self.ternary_auto_zoom_check)

        margin_row = QHBoxLayout()
        margin_label = QLabel(translate("Edge Margin"))
        margin_label.setProperty("translate_key", "Edge Margin")
        margin_row.addWidget(margin_label)
        self.ternary_render_margin_spin = QDoubleSpinBox()
        self.ternary_render_margin_spin.setRange(0.0, 0.05)
        self.ternary_render_margin_spin.setDecimals(3)
        self.ternary_render_margin_spin.setSingleStep(0.001)
        self.ternary_render_margin_spin.setValue(float(getattr(app_state, "ternary_render_margin", 0.002)))
        self.ternary_render_margin_spin.setToolTip(
            translate("Expand ternary axis limits to prevent edge data clipping when figure is enlarged")
        )
        self.ternary_render_margin_spin.valueChanged.connect(self._on_ternary_render_margin_change)
        margin_row.addWidget(self.ternary_render_margin_spin)
        ternary_layout.addLayout(margin_row)

        limit_mode_row = QHBoxLayout()
        limit_mode_label = QLabel(translate("Limit Mode"))
        limit_mode_label.setProperty("translate_key", "Limit Mode")
        limit_mode_row.addWidget(limit_mode_label)

        self.ternary_limit_mode_combo = QComboBox()
        self.ternary_limit_mode_combo.addItem(translate("Minimum Only"), "min")
        self.ternary_limit_mode_combo.addItem(translate("Maximum Only"), "max")
        self.ternary_limit_mode_combo.addItem(translate("Both Ends"), "both")
        limit_mode_row.addWidget(self.ternary_limit_mode_combo)
        ternary_layout.addLayout(limit_mode_row)

        current_limit_mode = str(getattr(app_state, "ternary_limit_mode", "min")).strip().lower()
        if current_limit_mode not in ("min", "max", "both"):
            current_limit_mode = "min"
        self._set_combo_value(self.ternary_limit_mode_combo, current_limit_mode)
        self.ternary_limit_mode_combo.currentIndexChanged.connect(self._on_ternary_limit_mode_change)

        self.ternary_manual_limits_check = QCheckBox(translate("Manual Limit Parameters"))
        self.ternary_manual_limits_check.setProperty("translate_key", "Manual Limit Parameters")
        self.ternary_manual_limits_check.setChecked(bool(getattr(app_state, "ternary_manual_limits_enabled", False)))
        self.ternary_manual_limits_check.stateChanged.connect(self._on_ternary_manual_limits_change)
        ternary_layout.addWidget(self.ternary_manual_limits_check)

        manual_limits = getattr(app_state, "ternary_manual_limits", None) or {}
        default_limits = {
            "tmin": 0.0,
            "tmax": 1.0,
            "lmin": 0.0,
            "lmax": 1.0,
            "rmin": 0.0,
            "rmax": 1.0,
        }
        default_limits.update({k: v for k, v in manual_limits.items() if k in default_limits})

        manual_grid = QGridLayout()

        def _add_limit_spin(row, title, key):
            label = QLabel(translate(title))
            label.setProperty("translate_key", title)
            manual_grid.addWidget(label, row, 0)

            spin = QDoubleSpinBox()
            spin.setRange(0.0, 1.0)
            spin.setDecimals(3)
            spin.setSingleStep(0.01)
            spin.setValue(float(default_limits[key]))
            self._connect_spinbox_deferred(
                spin,
                lambda v, name=key: self._on_ternary_limit_param_change(name, v),
            )
            manual_grid.addWidget(spin, row, 1)
            self.ternary_limit_spins[key] = spin

        _add_limit_spin(0, "Top Min", "tmin")
        _add_limit_spin(1, "Top Max", "tmax")
        _add_limit_spin(2, "Left Min", "lmin")
        _add_limit_spin(3, "Left Max", "lmax")
        _add_limit_spin(4, "Right Min", "rmin")
        _add_limit_spin(5, "Right Max", "rmax")
        ternary_layout.addLayout(manual_grid)

        self._refresh_ternary_limit_controls_enabled()
        self.ternary_group.setLayout(ternary_layout)
        layout.addWidget(self.ternary_group)
