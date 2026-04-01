"""Data panel build mixin."""

import logging

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QToolBox,
    QVBoxLayout,
    QWidget,
)

from core import app_state, translate
from ui.icons import apply_color_swatch

logger = logging.getLogger(__name__)


class DataPanelBuildMixin:
    """Construct and initialize the data panel UI."""

    def __init__(self, callback=None, parent=None):
        super().__init__(callback, parent)
        self.legend_panel = None
        self.geo_panel = None
        self._ternary_stretch_modes = ["power", "minmax", "hybrid"]

    def reset_state(self):
        super().reset_state()
        self._ternary_stretch_modes = ["power", "minmax", "hybrid"]
        self.group_radio_group = None
        self.group_radio_layout = None
        self.group_placeholder_label = None
        self.tooltip_check = None
        self.render_combo = None
        self.algo_combo = None
        self.algo_group = None
        self.umap_group = None
        self.tsne_group = None
        self.pca_group = None
        self.robust_pca_group = None
        self.ternary_group = None
        self.ternary_scale_label = None
        self.ternary_scale_slider = None
        self.ternary_auto_zoom_check = None
        self.ternary_limit_mode_combo = None
        self.ternary_boundary_percent_spin = None
        self.ternary_auto_optimize_btn = None
        self.ternary_manual_limits_check = None
        self.ternary_limit_spins = {}
        self.ternary_stretch_check = None
        self.geochem_plot_group = None
        self.modeling_show_model_check = None
        self.modeling_show_paleoisochron_check = None
        self.modeling_show_plumbotectonics_check = None
        self.modeling_show_model_age_check = None
        self.modeling_show_isochron_check = None
        self.modeling_show_growth_curve_check = None
        self.modeling_use_real_age_check = None
        self.mu_kappa_age_title_label = None
        self.mu_kappa_age_label = None
        self.mu_kappa_age_button = None
        self.show_model_check = None
        self.show_paleoisochron_check = None
        self.show_model_age_check = None
        self.show_isochron_check = None
        self.paleo_step_spin = None
        self.calc_isochron_btn = None
        self.isochron_settings_btn = None
        self.isochron_swatch = None
        self.v1v2_group = None
        self.v1v2_t1_spin = None
        self.v1v2_t2_spin = None
        self.twod_group = None
        self.xaxis_combo = None
        self.yaxis_combo = None
        self.pca_x_spin = None
        self.pca_y_spin = None
        self.rpca_x_spin = None
        self.rpca_y_spin = None
        self.metric_combo = None
        self.plumbotectonics_model_label = None
        self.plumbotectonics_model_combo = None
        self.plumbotectonics_model_keys = []

    def _update_translations(self, root: QWidget | None = None) -> None:
        """Refresh translated widget text and ternary mode combo options."""
        super()._update_translations(root)

        combo = getattr(self, "ternary_limit_mode_combo", None)
        if combo is not None:
            current_mode = str(combo.currentData()).strip().lower() if combo.currentData() is not None else "min"
            if current_mode not in ("min", "max", "both"):
                current_mode = "min"

            combo.blockSignals(True)
            combo.clear()
            combo.addItem(translate("Minimum Only"), "min")
            combo.addItem(translate("Maximum Only"), "max")
            combo.addItem(translate("Both Ends"), "both")
            self._set_combo_value(combo, current_mode)
            combo.blockSignals(False)

    def _connect_spinbox_deferred(self, spinbox, callback, *, pass_value: bool = True) -> None:
        """Apply spinbox changes only when editing is finished."""
        try:
            spinbox.setKeyboardTracking(False)
        except Exception:
            pass

        if pass_value:
            spinbox.editingFinished.connect(lambda s=spinbox: callback(s.value()))
        else:
            spinbox.editingFinished.connect(callback)

    def build(self) -> QWidget:
        widget = self._build_data_section()
        self._is_initialized = True
        return widget

    def _build_data_section(self):
        """Construct data tab content."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        section_toolbox = QToolBox()
        section_toolbox.setObjectName("data_section_toolbox")

        basics_page = QWidget()
        basics_layout = QVBoxLayout(basics_page)
        basics_layout.setContentsMargins(6, 6, 6, 6)
        basics_layout.setSpacing(8)

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
        basics_layout.addWidget(group_group)

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
        basics_layout.addWidget(tooltip_group)
        basics_layout.addStretch()

        projection_widget = self._build_projection_section()
        section_toolbox.addItem(basics_page, translate("Coloring / Grouping"))
        section_toolbox.addItem(projection_widget, translate("Render Mode"))

        layout.addWidget(section_toolbox)
        layout.addStretch()
        return widget

    def _build_projection_section(self):
        """Construct projection controls."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
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
            app_state.umap_params["n_neighbors"] = n_neighbors
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
            app_state.tsne_params["perplexity"] = perplexity
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

        boundary_row = QHBoxLayout()
        boundary_label = QLabel(translate("Boundary Percent (%)"))
        boundary_label.setProperty("translate_key", "Boundary Percent (%)")
        boundary_row.addWidget(boundary_label)

        self.ternary_boundary_percent_spin = QDoubleSpinBox()
        self.ternary_boundary_percent_spin.setRange(0.0, 30.0)
        self.ternary_boundary_percent_spin.setDecimals(1)
        self.ternary_boundary_percent_spin.setSingleStep(0.5)
        self.ternary_boundary_percent_spin.setSuffix("%")
        self.ternary_boundary_percent_spin.setValue(float(getattr(app_state, "ternary_boundary_percent", 5.0)))
        self._connect_spinbox_deferred(self.ternary_boundary_percent_spin, self._on_ternary_boundary_percent_change)
        boundary_row.addWidget(self.ternary_boundary_percent_spin)
        ternary_layout.addLayout(boundary_row)

        self.ternary_auto_optimize_btn = QPushButton(translate("Auto Optimize"))
        self.ternary_auto_optimize_btn.setProperty("translate_key", "Auto Optimize")
        self.ternary_auto_optimize_btn.clicked.connect(self._on_ternary_auto_optimize)
        ternary_layout.addWidget(self.ternary_auto_optimize_btn)

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

        stretch_header = QHBoxLayout()
        stretch_label = QLabel(translate("Stretch Mode"))
        stretch_label.setProperty("translate_key", "Stretch Mode")
        stretch_header.addWidget(stretch_label)
        stretch_header.addStretch()
        self.ternary_scale_label = QLabel()
        stretch_header.addWidget(self.ternary_scale_label)
        ternary_layout.addLayout(stretch_header)

        current_mode = getattr(app_state, "ternary_stretch_mode", "power")
        if current_mode not in self._ternary_stretch_modes:
            current_mode = "power"
        current_idx = self._ternary_stretch_modes.index(current_mode)
        self._update_ternary_scale_label(current_mode)

        self.ternary_scale_slider = QSlider(Qt.Horizontal)
        self.ternary_scale_slider.setRange(0, 2)
        self.ternary_scale_slider.setSingleStep(1)
        self.ternary_scale_slider.setPageStep(1)
        self.ternary_scale_slider.setTickInterval(1)
        self.ternary_scale_slider.setValue(current_idx)
        self.ternary_scale_slider.valueChanged.connect(self._on_ternary_scale_change)
        ternary_layout.addWidget(self.ternary_scale_slider)

        self.ternary_stretch_check = QCheckBox(translate("Stretch to Fill"))
        self.ternary_stretch_check.setProperty("translate_key", "Stretch to Fill")
        self.ternary_stretch_check.setChecked(getattr(app_state, "ternary_stretch", False))
        self.ternary_stretch_check.stateChanged.connect(self._on_ternary_stretch_change)
        ternary_layout.addWidget(self.ternary_stretch_check)

        self._refresh_ternary_limit_controls_enabled()
        self.ternary_group.setLayout(ternary_layout)
        layout.addWidget(self.ternary_group)

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

        self.geochem_plot_group = QGroupBox(translate("Geochemistry Plot Controls"))
        self.geochem_plot_group.setProperty("translate_key", "Geochemistry Plot Controls")
        geochem_layout = QVBoxLayout()

        def _add_geochem_toggle(label_text, checked, handler, style_key=None):
            row = QHBoxLayout()
            chk = QCheckBox(translate(label_text))
            chk.setChecked(checked)
            chk.stateChanged.connect(handler)
            row.addWidget(chk)

            if style_key:
                style = getattr(app_state, "line_styles", {}).get(style_key, {}) or {}
                swatch_color = style.get("color") or "#e2e8f0"
                swatch = QLabel()
                swatch.setFixedSize(16, 16)
                apply_color_swatch(swatch, swatch_color)
                swatch.mousePressEvent = lambda event, k=style_key, s=swatch: self._open_line_style_dialog(k, s)
                row.addWidget(swatch)
                chk._style_swatch = swatch

            row.addStretch()
            geochem_layout.addLayout(row)
            return chk

        self.modeling_show_model_check = _add_geochem_toggle(
            "Show Model Curves",
            getattr(app_state, "show_model_curves", True),
            self._on_model_curves_change,
            style_key="model_curve",
        )

        self.modeling_show_paleoisochron_check = _add_geochem_toggle(
            "Show Paleoisochrons",
            getattr(app_state, "show_paleoisochrons", True),
            self._on_paleoisochron_change,
            style_key="paleoisochron",
        )

        self.modeling_show_plumbotectonics_check = _add_geochem_toggle(
            "Show Plumbotectonics Curves",
            getattr(app_state, "show_plumbotectonics_curves", True),
            self._on_plumbotectonics_curves_change,
            style_key="plumbotectonics_curve",
        )

        plumb_row = QHBoxLayout()
        self.plumbotectonics_model_label = QLabel(translate("Plumbotectonics Model"))
        self.plumbotectonics_model_label.setProperty("translate_key", "Plumbotectonics Model")
        plumb_row.addWidget(self.plumbotectonics_model_label)

        self.plumbotectonics_model_combo = QComboBox()
        self.plumbotectonics_model_combo.currentIndexChanged.connect(self._on_plumbotectonics_model_change)
        plumb_row.addWidget(self.plumbotectonics_model_combo)
        plumb_row.addStretch()
        geochem_layout.addLayout(plumb_row)

        self._refresh_plumbotectonics_models()

        paleo_step_layout = QHBoxLayout()
        paleo_step_label = QLabel(translate("Paleoisochron Step (Ma):"))
        paleo_step_label.setProperty("translate_key", "Paleoisochron Step (Ma):")
        paleo_step_layout.addWidget(paleo_step_label)
        self.paleo_step_spin = QSpinBox()
        self.paleo_step_spin.setRange(50, 5000)
        self.paleo_step_spin.setSingleStep(50)
        self.paleo_step_spin.setValue(getattr(app_state, "paleoisochron_step", 1000))
        self._connect_spinbox_deferred(self.paleo_step_spin, self._on_paleo_step_change)
        paleo_step_layout.addWidget(self.paleo_step_spin)
        paleo_step_layout.addStretch()
        geochem_layout.addLayout(paleo_step_layout)

        self.modeling_show_model_age_check = _add_geochem_toggle(
            "Show Model Age Lines",
            getattr(app_state, "show_model_age_lines", True),
            self._on_model_age_change,
            style_key="model_age_line",
        )

        self.modeling_show_growth_curve_check = _add_geochem_toggle(
            "Show Growth Curves",
            getattr(app_state, "show_growth_curves", True),
            self._on_growth_curves_change,
            style_key="growth_curve",
        )

        self.modeling_use_real_age_check = _add_geochem_toggle(
            "Use Real Age for Mu/Kappa",
            getattr(app_state, "use_real_age_for_mu_kappa", False),
            self._on_mu_kappa_real_age_change,
        )

        age_row = QHBoxLayout()
        self.mu_kappa_age_title_label = QLabel(translate("Age Column"))
        self.mu_kappa_age_title_label.setProperty("translate_key", "Age Column")
        age_row.addWidget(self.mu_kappa_age_title_label)

        self.mu_kappa_age_label = QLabel()
        age_row.addWidget(self.mu_kappa_age_label)
        age_row.addStretch()

        self.mu_kappa_age_button = QPushButton(translate("Select Age Column"))
        self.mu_kappa_age_button.setProperty("translate_key", "Select Age Column")
        self.mu_kappa_age_button.clicked.connect(self._on_select_mu_kappa_age_column)
        age_row.addWidget(self.mu_kappa_age_button)
        geochem_layout.addLayout(age_row)

        self._refresh_mu_kappa_age_label()
        self._refresh_mu_kappa_age_controls()

        isochron_row = QHBoxLayout()
        self.calc_isochron_btn = QPushButton(translate("Calculate Isochron Age"))
        self.calc_isochron_btn.setProperty("translate_key", "Calculate Isochron Age")
        self.calc_isochron_btn.clicked.connect(self._on_calculate_isochron)
        if getattr(app_state, "show_isochrons", False):
            self.calc_isochron_btn.setText(translate("Hide Isochron"))
        isochron_row.addWidget(self.calc_isochron_btn)

        self.isochron_settings_btn = QPushButton(translate("Isochron Settings"))
        self.isochron_settings_btn.setProperty("translate_key", "Isochron Settings")
        self.isochron_settings_btn.clicked.connect(self._on_isochron_settings)
        isochron_row.addWidget(self.isochron_settings_btn)

        iso_style = getattr(app_state, "line_styles", {}).get("isochron", {}) or {}
        iso_color = iso_style.get("color") or "#e2e8f0"
        self.isochron_swatch = QLabel()
        self.isochron_swatch.setFixedSize(16, 16)
        apply_color_swatch(self.isochron_swatch, iso_color)
        self.isochron_swatch.mousePressEvent = lambda event, s=self.isochron_swatch: self._open_line_style_dialog(
            "isochron", s
        )
        isochron_row.addWidget(self.isochron_swatch)
        isochron_row.addStretch()
        geochem_layout.addLayout(isochron_row)

        self.geochem_plot_group.setLayout(geochem_layout)
        layout.addWidget(self.geochem_plot_group)

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

        self._update_algorithm_visibility()

        layout.addStretch()
        return widget








