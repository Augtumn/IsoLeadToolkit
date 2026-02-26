"""数据面板 - 分组与投影设置"""
import logging

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QComboBox, QCheckBox, QSlider, QSpinBox,
    QDoubleSpinBox, QGridLayout, QListWidget, QListWidgetItem,
    QButtonGroup, QRadioButton, QDialog, QMessageBox,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor

from core import translate, app_state
from .base_panel import BasePanel

logger = logging.getLogger(__name__)


class DataPanel(BasePanel):
    """数据标签页"""

    def __init__(self, callback=None, parent=None):
        super().__init__(callback, parent)
        self.legend_panel = None
        self.geo_panel = None
        self._ternary_stretch_modes = ['power', 'minmax', 'hybrid']

    def reset_state(self):
        super().reset_state()
        self._ternary_stretch_modes = ['power', 'minmax', 'hybrid']
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
        self.ternary_stretch_check = None
        self.geochem_plot_group = None
        self.modeling_show_model_check = None
        self.modeling_show_paleoisochron_check = None
        self.modeling_show_model_age_check = None
        self.modeling_show_isochron_check = None
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

    def build(self) -> QWidget:
        widget = self._build_data_section()
        self._is_initialized = True
        return widget

    def _update_group_list(self):
        panel = getattr(self, 'legend_panel', None)
        if panel is not None and hasattr(panel, '_update_group_list'):
            panel._update_group_list()

    def _sync_geochem_model_for_mode(self, mode):
        panel = getattr(self, 'geo_panel', None)
        combo = getattr(panel, 'geo_model_combo', None) if panel is not None else None
        if combo is None:
            return
        try:
            from data.geochemistry import engine
        except Exception:
            return

        target_model = None
        if mode == 'V1V2':
            target_model = 'V1V2 (Zhu 1993)'
        elif mode in ('PB_EVOL_76', 'PB_EVOL_86', 'PB_MU_AGE', 'PB_KAPPA_AGE'):
            target_model = 'Stacey & Kramers (2nd Stage)'

        if not target_model:
            return

        current_model = getattr(engine, 'current_model_name', '')
        if current_model == target_model:
            return

        available_models = [combo.itemText(i) for i in range(combo.count())]
        if target_model in available_models:
            combo.setCurrentText(target_model)



    def _build_data_section(self):
        """构建数据部分"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)

        group_group = QGroupBox(translate("Coloring / Grouping"))
        group_group.setProperty('translate_key', 'Coloring / Grouping')
        group_layout = QVBoxLayout()

        self.group_radio_group = QButtonGroup(self)
        self.group_radio_group.setExclusive(True)
        self.group_radio_group.buttonClicked.connect(self._on_group_col_selected)

        group_container = QWidget()
        self.group_radio_layout = QVBoxLayout(group_container)
        self.group_radio_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.addWidget(group_container)

        group_config_btn = QPushButton(translate("Configure Group Columns"))
        group_config_btn.setProperty('translate_key', 'Configure Group Columns')
        group_config_btn.clicked.connect(self._on_configure_group_columns)
        group_layout.addWidget(group_config_btn)

        group_group.setLayout(group_layout)
        layout.addWidget(group_group)

        self._refresh_group_column_radios()

        tooltip_group = QGroupBox(translate("Tooltip Settings"))
        tooltip_group.setProperty('translate_key', 'Tooltip Settings')
        tooltip_layout = QVBoxLayout()

        tooltip_check_layout = QHBoxLayout()
        self.tooltip_check = QCheckBox(translate("Show Tooltip"))
        self.tooltip_check.setProperty('translate_key', 'Show Tooltip')
        self.tooltip_check.setChecked(getattr(app_state, 'show_tooltip', True))
        self.tooltip_check.stateChanged.connect(self._on_tooltip_change)
        tooltip_check_layout.addWidget(self.tooltip_check)

        tooltip_config_btn = QPushButton(translate("Configure"))
        tooltip_config_btn.setProperty('translate_key', 'Configure')
        tooltip_config_btn.setFixedWidth(100)
        tooltip_config_btn.clicked.connect(self._on_configure_tooltip)
        tooltip_check_layout.addWidget(tooltip_config_btn)
        tooltip_check_layout.addStretch()
        tooltip_layout.addLayout(tooltip_check_layout)

        tooltip_group.setLayout(tooltip_layout)
        layout.addWidget(tooltip_group)

        projection_widget = self._build_projection_section()
        layout.addWidget(projection_widget)

        layout.addStretch()
        return widget

    def _build_projection_section(self):
        """构建投影部分"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        render_group = QGroupBox(translate("Render Mode"))
        render_group.setProperty('translate_key', 'Render Mode')
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
        algo_group.setProperty('translate_key', 'Algorithm')
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
        self.umap_group.setProperty('translate_key', 'UMAP Parameters')
        umap_layout = QVBoxLayout()

        n_label = QLabel(translate("n_neighbors: {value}").format(value=app_state.umap_params['n_neighbors']))
        umap_layout.addWidget(n_label)

        n_slider = QSlider(Qt.Horizontal)
        n_slider.setMinimum(2)
        n_slider.setMaximum(50)
        n_neighbors = min(app_state.umap_params['n_neighbors'], 50)
        if app_state.umap_params['n_neighbors'] != n_neighbors:
            app_state.umap_params['n_neighbors'] = n_neighbors
        n_slider.setValue(n_neighbors)
        n_slider.valueChanged.connect(lambda v: self._on_umap_slider_changed('n_neighbors', v, n_label, n_slider))
        n_slider.sliderReleased.connect(self._on_change)
        umap_layout.addWidget(n_slider)

        self.sliders['umap_n_neighbors'] = n_slider
        self.labels['umap_n_neighbors'] = n_label

        min_dist_label = QLabel(translate("min_dist: {value:.2f}").format(value=app_state.umap_params['min_dist']))
        umap_layout.addWidget(min_dist_label)

        min_dist_slider = QSlider(Qt.Horizontal)
        min_dist_slider.setMinimum(0)
        min_dist_slider.setMaximum(100)
        min_dist_slider.setValue(int(app_state.umap_params['min_dist'] * 100))
        min_dist_slider.valueChanged.connect(lambda v: self._on_umap_slider_changed('min_dist', v / 100.0, min_dist_label, min_dist_slider))
        min_dist_slider.sliderReleased.connect(self._on_change)
        umap_layout.addWidget(min_dist_slider)

        self.sliders['umap_min_dist'] = min_dist_slider
        self.labels['umap_min_dist'] = min_dist_label

        metric_label = QLabel(translate("metric:"))
        metric_label.setProperty('translate_key', 'metric:')
        umap_layout.addWidget(metric_label)

        self.metric_combo = QComboBox()
        metric_options = ['euclidean', 'manhattan', 'cosine']
        self.metric_combo.addItems(metric_options)
        current_metric = app_state.umap_params.get('metric', 'euclidean')
        if current_metric in metric_options:
            self.metric_combo.setCurrentText(current_metric)
        self.metric_combo.currentTextChanged.connect(lambda v: self._on_umap_param_change('metric', v, metric_label))
        umap_layout.addWidget(self.metric_combo)

        self.umap_group.setLayout(umap_layout)
        layout.addWidget(self.umap_group)

        self.tsne_group = QGroupBox(translate("t-SNE Parameters"))
        self.tsne_group.setProperty('translate_key', 't-SNE Parameters')
        tsne_layout = QVBoxLayout()

        perp_label = QLabel(translate("perplexity: {value}").format(value=app_state.tsne_params['perplexity']))
        tsne_layout.addWidget(perp_label)

        perp_slider = QSlider(Qt.Horizontal)
        perp_slider.setMinimum(5)
        perp_slider.setMaximum(100)
        perplexity = min(int(app_state.tsne_params['perplexity']), 100)
        if app_state.tsne_params['perplexity'] != perplexity:
            app_state.tsne_params['perplexity'] = perplexity
        perp_slider.setValue(perplexity)
        perp_slider.valueChanged.connect(lambda v: self._on_tsne_slider_changed('perplexity', v, perp_label))
        perp_slider.sliderReleased.connect(self._on_change)
        tsne_layout.addWidget(perp_slider)

        self.sliders['tsne_perplexity'] = perp_slider
        self.labels['tsne_perplexity'] = perp_label

        lr_label = QLabel(translate("learning_rate: {value}").format(value=int(app_state.tsne_params['learning_rate'])))
        tsne_layout.addWidget(lr_label)

        lr_slider = QSlider(Qt.Horizontal)
        lr_slider.setMinimum(1)
        lr_slider.setMaximum(100)
        lr_slider.setValue(int(app_state.tsne_params['learning_rate'] / 10))
        lr_slider.valueChanged.connect(lambda v: self._on_tsne_slider_changed('learning_rate', v * 10, lr_label))
        lr_slider.sliderReleased.connect(self._on_change)
        tsne_layout.addWidget(lr_slider)

        self.sliders['tsne_learning_rate'] = lr_slider
        self.labels['tsne_learning_rate'] = lr_label

        tsne_rs_label = QLabel(translate("random_state: {value}").format(
            value=app_state.tsne_params.get('random_state', 42)
        ))
        tsne_layout.addWidget(tsne_rs_label)

        tsne_rs_spin = QSpinBox()
        tsne_rs_spin.setRange(0, 200)
        tsne_rs_spin.setValue(app_state.tsne_params.get('random_state', 42))
        tsne_rs_spin.valueChanged.connect(lambda v: self._on_tsne_param_change('random_state', v, tsne_rs_label))
        tsne_layout.addWidget(tsne_rs_spin)

        self.tsne_group.setLayout(tsne_layout)
        layout.addWidget(self.tsne_group)

        self.pca_group = QGroupBox(translate("PCA Parameters"))
        self.pca_group.setProperty('translate_key', 'PCA Parameters')
        pca_layout = QVBoxLayout()

        n_comp_label = QLabel(translate("n_components:"))
        n_comp_label.setProperty('translate_key', 'n_components:')

        n_comp_spin = QSpinBox()
        n_comp_spin.setRange(2, 10)
        n_comp_spin.setValue(app_state.pca_params.get('n_components', 2))
        n_comp_spin.valueChanged.connect(lambda v: self._on_pca_param_change('n_components', v))
        pca_layout.addWidget(n_comp_spin)

        pca_rs_label = QLabel(translate("random_state: {value}").format(
            value=app_state.pca_params.get('random_state', 42)
        ))
        pca_layout.addWidget(pca_rs_label)

        pca_rs_spin = QSpinBox()
        pca_rs_spin.setRange(0, 200)
        pca_rs_spin.setValue(app_state.pca_params.get('random_state', 42))
        pca_rs_spin.valueChanged.connect(lambda v: self._on_pca_param_change('random_state', v, pca_rs_label))
        pca_layout.addWidget(pca_rs_spin)

        standardize_check = QCheckBox(translate("Standardize data"))
        standardize_check.setProperty('translate_key', 'Standardize data')
        standardize_check.setChecked(app_state.standardize_data)
        standardize_check.stateChanged.connect(self._on_standardize_change)
        pca_layout.addWidget(standardize_check)

        pca_tools_layout = QHBoxLayout()

        scree_btn = QPushButton(translate("Scree Plot"))
        scree_btn.setProperty('translate_key', 'Scree Plot')
        scree_btn.clicked.connect(self._on_show_scree_plot)
        pca_tools_layout.addWidget(scree_btn)

        loadings_btn = QPushButton(translate("Loadings"))
        loadings_btn.setProperty('translate_key', 'Loadings')
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
        self.pca_x_spin.valueChanged.connect(self._on_pca_dim_change)
        dim_layout.addWidget(self.pca_x_spin)

        y_label = QLabel(translate("Y:"))
        dim_layout.addWidget(y_label)

        self.pca_y_spin = QSpinBox()
        self.pca_y_spin.setRange(1, 10)
        self.pca_y_spin.setValue(app_state.pca_component_indices[1] + 1)
        self.pca_y_spin.setMaximumWidth(60)
        self.pca_y_spin.valueChanged.connect(self._on_pca_dim_change)
        dim_layout.addWidget(self.pca_y_spin)

        dim_layout.addStretch()
        pca_layout.addLayout(dim_layout)

        self.pca_group.setLayout(pca_layout)
        layout.addWidget(self.pca_group)

        self.robust_pca_group = QGroupBox(translate("RobustPCA Parameters"))
        self.robust_pca_group.setProperty('translate_key', 'RobustPCA Parameters')
        robust_pca_layout = QVBoxLayout()

        robust_n_comp_label = QLabel(translate("n_components:"))
        robust_n_comp_label.setProperty('translate_key', 'n_components:')
        robust_pca_layout.addWidget(robust_n_comp_label)

        robust_n_comp_spin = QSpinBox()
        robust_n_comp_spin.setRange(2, 10)
        robust_n_comp_spin.setValue(app_state.robust_pca_params.get('n_components', 2))
        robust_n_comp_spin.valueChanged.connect(lambda v: self._on_robust_pca_param_change('n_components', v))
        robust_pca_layout.addWidget(robust_n_comp_spin)

        support_label = QLabel(translate("support_fraction: {value:.2f}").format(value=app_state.robust_pca_params.get('support_fraction', 0.75)))
        robust_pca_layout.addWidget(support_label)

        support_spin = QDoubleSpinBox()
        support_spin.setRange(0.1, 1.0)
        support_spin.setSingleStep(0.05)
        support_spin.setDecimals(2)
        support_spin.setValue(app_state.robust_pca_params.get('support_fraction', 0.75))
        support_spin.valueChanged.connect(lambda v: self._on_robust_pca_param_change('support_fraction', v, support_label))
        robust_pca_layout.addWidget(support_spin)

        self.labels['robust_pca_support'] = support_label

        robust_rs_label = QLabel(translate("random_state:"))
        robust_rs_label.setProperty('translate_key', 'random_state:')
        robust_pca_layout.addWidget(robust_rs_label)

        robust_rs_spin = QSpinBox()
        robust_rs_spin.setRange(0, 9999)
        robust_rs_spin.setValue(app_state.robust_pca_params.get('random_state', 42))
        robust_rs_spin.valueChanged.connect(lambda v: self._on_robust_pca_param_change('random_state', v))
        robust_pca_layout.addWidget(robust_rs_spin)

        rpca_tools_layout = QHBoxLayout()

        rpca_scree_btn = QPushButton(translate("Scree Plot"))
        rpca_scree_btn.setProperty('translate_key', 'Scree Plot')
        rpca_scree_btn.clicked.connect(self._on_show_scree_plot)
        rpca_tools_layout.addWidget(rpca_scree_btn)

        rpca_loadings_btn = QPushButton(translate("Loadings"))
        rpca_loadings_btn.setProperty('translate_key', 'Loadings')
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
        self.rpca_x_spin.valueChanged.connect(self._on_pca_dim_change)
        rpca_dim_layout.addWidget(self.rpca_x_spin)

        rpca_y_label = QLabel(translate("Y:"))
        rpca_dim_layout.addWidget(rpca_y_label)

        self.rpca_y_spin = QSpinBox()
        self.rpca_y_spin.setRange(1, 10)
        self.rpca_y_spin.setValue(app_state.pca_component_indices[1] + 1)
        self.rpca_y_spin.setMaximumWidth(60)
        self.rpca_y_spin.valueChanged.connect(self._on_pca_dim_change)
        rpca_dim_layout.addWidget(self.rpca_y_spin)

        rpca_dim_layout.addStretch()
        robust_pca_layout.addLayout(rpca_dim_layout)

        self.robust_pca_group.setLayout(robust_pca_layout)
        layout.addWidget(self.robust_pca_group)

        self.ternary_group = QGroupBox(translate("Ternary Plot"))
        self.ternary_group.setProperty('translate_key', 'Ternary Plot')
        ternary_layout = QVBoxLayout()

        info_label = QLabel(translate("Using Standard Ternary Plot.\nData is plotted as relative proportions."))
        info_label.setProperty('translate_key', 'Using Standard Ternary Plot.\nData is plotted as relative proportions.')
        info_label.setWordWrap(True)
        ternary_layout.addWidget(info_label)

        self.ternary_auto_zoom_check = QCheckBox(translate("Auto-Zoom to Data"))
        self.ternary_auto_zoom_check.setProperty('translate_key', 'Auto-Zoom to Data')
        self.ternary_auto_zoom_check.setChecked(getattr(app_state, 'ternary_auto_zoom', False))
        self.ternary_auto_zoom_check.stateChanged.connect(self._on_ternary_zoom_change)
        ternary_layout.addWidget(self.ternary_auto_zoom_check)

        stretch_header = QHBoxLayout()
        stretch_label = QLabel(translate("Stretch Mode"))
        stretch_label.setProperty('translate_key', 'Stretch Mode')
        stretch_header.addWidget(stretch_label)
        stretch_header.addStretch()
        self.ternary_scale_label = QLabel()
        stretch_header.addWidget(self.ternary_scale_label)
        ternary_layout.addLayout(stretch_header)

        current_mode = getattr(app_state, 'ternary_stretch_mode', 'power')
        if current_mode not in self._ternary_stretch_modes:
            current_mode = 'power'
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
        self.ternary_stretch_check.setProperty('translate_key', 'Stretch to Fill')
        self.ternary_stretch_check.setChecked(getattr(app_state, 'ternary_stretch', False))
        self.ternary_stretch_check.stateChanged.connect(self._on_ternary_stretch_change)
        ternary_layout.addWidget(self.ternary_stretch_check)

        self.ternary_group.setLayout(ternary_layout)
        layout.addWidget(self.ternary_group)

        self.v1v2_group = QGroupBox(translate("V1V2 Time Settings"))
        self.v1v2_group.setProperty('translate_key', 'V1V2 Time Settings')
        v1v2_layout = QVBoxLayout()

        try:
            from data.geochemistry import engine
            params = engine.get_parameters()
        except Exception:
            params = {}

        t1_val = params.get('T1', 4430e6) / 1e6
        t2_val = params.get('T2', 4570e6) / 1e6

        t1_layout = QHBoxLayout()
        t1_label = QLabel(translate("T1 (Ma) - Model Age"))
        t1_label.setProperty('translate_key', 'T1 (Ma) - Model Age')
        t1_layout.addWidget(t1_label)
        self.v1v2_t1_spin = QDoubleSpinBox()
        self.v1v2_t1_spin.setRange(0.0, 10000.0)
        self.v1v2_t1_spin.setDecimals(3)
        self.v1v2_t1_spin.setValue(t1_val)
        self.v1v2_t1_spin.valueChanged.connect(self._on_v1v2_param_change)
        t1_layout.addWidget(self.v1v2_t1_spin)
        v1v2_layout.addLayout(t1_layout)

        t2_layout = QHBoxLayout()
        t2_label = QLabel(translate("T2 (Ma) - Standard Earth Age"))
        t2_label.setProperty('translate_key', 'T2 (Ma) - Standard Earth Age')
        t2_layout.addWidget(t2_label)
        self.v1v2_t2_spin = QDoubleSpinBox()
        self.v1v2_t2_spin.setRange(0.0, 10000.0)
        self.v1v2_t2_spin.setDecimals(3)
        self.v1v2_t2_spin.setValue(t2_val)
        self.v1v2_t2_spin.valueChanged.connect(self._on_v1v2_param_change)
        t2_layout.addWidget(self.v1v2_t2_spin)
        v1v2_layout.addLayout(t2_layout)

        self.v1v2_group.setLayout(v1v2_layout)
        layout.addWidget(self.v1v2_group)

        self.geochem_plot_group = QGroupBox(translate("Geochemistry Plot Controls"))
        self.geochem_plot_group.setProperty('translate_key', 'Geochemistry Plot Controls')
        geochem_layout = QVBoxLayout()

        def _add_geochem_toggle(label_text, checked, handler, style_key=None):
            row = QHBoxLayout()
            chk = QCheckBox(translate(label_text))
            chk.setChecked(checked)
            chk.stateChanged.connect(handler)
            row.addWidget(chk)

            swatch = None
            if style_key:
                style = getattr(app_state, 'line_styles', {}).get(style_key, {}) or {}
                swatch_color = style.get('color') or '#e2e8f0'
                swatch = QLabel()
                swatch.setFixedSize(16, 16)
                swatch.setStyleSheet(f"background-color: {swatch_color}; border: 1px solid #111827;")
                swatch.mousePressEvent = lambda event, k=style_key, s=swatch: self._open_line_style_dialog(k, s)
                row.addWidget(swatch)
                chk._style_swatch = swatch

            row.addStretch()
            geochem_layout.addLayout(row)
            return chk

        self.modeling_show_model_check = _add_geochem_toggle(
            "Show Model Curves",
            getattr(app_state, 'show_model_curves', True),
            self._on_model_curves_change,
            style_key='model_curve'
        )

        self.modeling_show_paleoisochron_check = _add_geochem_toggle(
            "Show Paleoisochrons",
            getattr(app_state, 'show_paleoisochrons', True),
            self._on_paleoisochron_change,
            style_key='paleoisochron'
        )

        paleo_step_layout = QHBoxLayout()
        paleo_step_label = QLabel(translate("Paleoisochron Step (Ma):"))
        paleo_step_label.setProperty('translate_key', 'Paleoisochron Step (Ma):')
        paleo_step_layout.addWidget(paleo_step_label)
        self.paleo_step_spin = QSpinBox()
        self.paleo_step_spin.setRange(50, 5000)
        self.paleo_step_spin.setSingleStep(50)
        self.paleo_step_spin.setValue(getattr(app_state, 'paleoisochron_step', 1000))
        self.paleo_step_spin.valueChanged.connect(self._on_paleo_step_change)
        paleo_step_layout.addWidget(self.paleo_step_spin)
        paleo_step_layout.addStretch()
        geochem_layout.addLayout(paleo_step_layout)

        self.modeling_show_model_age_check = _add_geochem_toggle(
            "Show Model Age Lines",
            getattr(app_state, 'show_model_age_lines', True),
            self._on_model_age_change,
            style_key='model_age_line'
        )

        self.modeling_use_real_age_check = _add_geochem_toggle(
            "Use Real Age for Mu/Kappa",
            getattr(app_state, 'use_real_age_for_mu_kappa', False),
            self._on_mu_kappa_real_age_change,
        )

        age_row = QHBoxLayout()
        self.mu_kappa_age_title_label = QLabel(translate("Age Column"))
        self.mu_kappa_age_title_label.setProperty('translate_key', 'Age Column')
        age_row.addWidget(self.mu_kappa_age_title_label)

        self.mu_kappa_age_label = QLabel()
        age_row.addWidget(self.mu_kappa_age_label)
        age_row.addStretch()

        self.mu_kappa_age_button = QPushButton(translate("Select Age Column"))
        self.mu_kappa_age_button.setProperty('translate_key', 'Select Age Column')
        self.mu_kappa_age_button.clicked.connect(self._on_select_mu_kappa_age_column)
        age_row.addWidget(self.mu_kappa_age_button)
        geochem_layout.addLayout(age_row)

        self._refresh_mu_kappa_age_label()
        self._refresh_mu_kappa_age_controls()

        isochron_row = QHBoxLayout()
        self.calc_isochron_btn = QPushButton(translate("Calculate Isochron Age"))
        self.calc_isochron_btn.setProperty('translate_key', 'Calculate Isochron Age')
        self.calc_isochron_btn.clicked.connect(self._on_calculate_isochron)
        if getattr(app_state, 'show_isochrons', False):
            self.calc_isochron_btn.setText(translate("Hide Isochron"))
        isochron_row.addWidget(self.calc_isochron_btn)

        self.isochron_settings_btn = QPushButton(translate("Isochron Settings"))
        self.isochron_settings_btn.setProperty('translate_key', 'Isochron Settings')
        self.isochron_settings_btn.clicked.connect(self._on_isochron_settings)
        isochron_row.addWidget(self.isochron_settings_btn)

        iso_style = getattr(app_state, 'line_styles', {}).get('isochron', {}) or {}
        iso_color = iso_style.get('color') or '#e2e8f0'
        self.isochron_swatch = QLabel()
        self.isochron_swatch.setFixedSize(16, 16)
        self.isochron_swatch.setStyleSheet(f"background-color: {iso_color}; border: 1px solid #111827;")
        self.isochron_swatch.mousePressEvent = lambda event, s=self.isochron_swatch: self._open_line_style_dialog('isochron', s)
        isochron_row.addWidget(self.isochron_swatch)
        isochron_row.addStretch()
        geochem_layout.addLayout(isochron_row)

        self.geochem_plot_group.setLayout(geochem_layout)
        layout.addWidget(self.geochem_plot_group)

        self.twod_group = QGroupBox(translate("2D Scatter Parameters"))
        self.twod_group.setProperty('translate_key', '2D Scatter Parameters')
        twod_layout = QVBoxLayout()

        twod_grid = QGridLayout()

        x_label = QLabel(translate("X Axis:"))
        x_label.setProperty('translate_key', 'X Axis:')
        twod_grid.addWidget(x_label, 0, 0)

        self.xaxis_combo = QComboBox()
        self.xaxis_combo.setEditable(False)
        self.xaxis_combo.setStyleSheet("QComboBox { combobox-popup: 0; }")
        self.xaxis_combo.setMinimumWidth(150)
        twod_grid.addWidget(self.xaxis_combo, 0, 1)

        y_label = QLabel(translate("Y Axis:"))
        y_label.setProperty('translate_key', 'Y Axis:')
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

    def _on_render_mode_change(self, mode):
        """渲染模式变化处理"""
        mode = self._normalize_render_mode(self._combo_value(self.render_combo, mode))
        app_state.render_mode = mode

        # 如果是算法模式，同步算法选择
        if mode in ['UMAP', 'tSNE', 'PCA', 'RobustPCA']:
            app_state.algorithm = mode
            self._set_combo_value(self.algo_combo, mode)

        # 如果是 2D/3D/Ternary，可能需要弹出列选择对话框
        if mode == '2D' and not app_state.selected_2d_confirmed:
            self._show_2d_column_dialog()
        elif mode == '3D' and not app_state.selected_3d_confirmed:
            self._show_3d_column_dialog()
        elif mode == 'Ternary' and not app_state.selected_ternary_confirmed:
            self._show_ternary_column_dialog()

        self._sync_geochem_model_for_mode(mode)
        self._update_algorithm_visibility()

        self._on_change()

    def _on_algorithm_change(self, algorithm):
        """算法变化处理"""
        algorithm = self._normalize_algorithm(self._combo_value(self.algo_combo, algorithm))
        app_state.algorithm = algorithm
        app_state.render_mode = algorithm
        self._set_combo_value(self.render_combo, algorithm)
        self._update_algorithm_visibility()
        self._on_change()

    def _update_algorithm_visibility(self):
        """根据当前算法更新参数组可见性"""
        mode = self._normalize_render_mode(app_state.render_mode)

        # 算法下拉在 Qt5 中不作为渲染模式入口，保持隐藏以对齐 ttk
        self.algo_group.setVisible(False)

        # 显示/隐藏参数组
        self.umap_group.setVisible(mode == 'UMAP')
        self.tsne_group.setVisible(mode == 'tSNE')
        self.pca_group.setVisible(mode == 'PCA')
        self.robust_pca_group.setVisible(mode == 'RobustPCA')

        # 显示/隐藏 Ternary 参数
        self.ternary_group.setVisible(mode == 'Ternary')

        if self.v1v2_group is not None:
            self.v1v2_group.setVisible(mode == 'V1V2')

        # 显示/隐藏 2D 参数
        self.twod_group.setVisible(mode == '2D')
        if mode == '2D':
            self._refresh_2d_axis_combos()

        if self.geochem_plot_group is not None:
            self.geochem_plot_group.setVisible(mode in ('PB_EVOL_76', 'PB_EVOL_86', 'PB_MU_AGE', 'PB_KAPPA_AGE'))

        is_pb_evol = mode in ('PB_EVOL_76', 'PB_EVOL_86')
        is_pb_evol_76 = mode == 'PB_EVOL_76'

        if self.modeling_show_model_check is not None:
            self.modeling_show_model_check.setVisible(is_pb_evol)
            swatch = getattr(self.modeling_show_model_check, '_style_swatch', None)
            if swatch is not None:
                swatch.setVisible(is_pb_evol)
        if self.modeling_show_model_age_check is not None:
            self.modeling_show_model_age_check.setVisible(is_pb_evol)
            swatch = getattr(self.modeling_show_model_age_check, '_style_swatch', None)
            if swatch is not None:
                swatch.setVisible(is_pb_evol)

        if self.calc_isochron_btn is not None:
            self.calc_isochron_btn.setVisible(is_pb_evol_76)
        if self.isochron_settings_btn is not None:
            self.isochron_settings_btn.setVisible(is_pb_evol_76)
        if self.isochron_swatch is not None:
            self.isochron_swatch.setVisible(is_pb_evol_76)

        self._refresh_mu_kappa_age_controls()

    def _on_umap_slider_changed(self, param, value, label, slider):
        """UMAP 滑块拖动中 - 仅更新标签和状态，不触发重新计算"""
        app_state.umap_params[param] = value
        if label:
            if param == 'min_dist':
                label.setText(translate("{param}: {value:.2f}").format(param=param, value=value))
            else:
                label.setText(translate("{param}: {value}").format(param=param, value=value))

    def _on_umap_param_change(self, param, value, label):
        """UMAP 参数变化（非滑块控件，如 metric combo）"""
        app_state.umap_params[param] = value
        if label:
            if param == 'min_dist':
                label.setText(translate("{param}: {value:.2f}").format(param=param, value=value))
            else:
                label.setText(translate("{param}: {value}").format(param=param, value=value))
        self._schedule_slider_callback(f'umap_{param}')

    def _on_tsne_slider_changed(self, param, value, label):
        """t-SNE 滑块拖动中 - 仅更新标签和状态，不触发重新计算"""
        app_state.tsne_params[param] = value
        if label:
            label.setText(translate("{param}: {value}").format(param=param, value=int(value)))

    def _on_tsne_param_change(self, param, value, label):
        """t-SNE 参数变化（非滑块控件）"""
        app_state.tsne_params[param] = value
        if label:
            label.setText(translate("{param}: {value}").format(param=param, value=value))
        self._schedule_slider_callback(f'tsne_{param}')

    def _on_pca_param_change(self, param, value, label=None):
        """PCA 参数变化"""
        app_state.pca_params[param] = value
        if label and param == 'random_state':
            label.setText(translate("random_state: {value}").format(value=value))
        self._schedule_slider_callback(f'pca_{param}')

    def _on_robust_pca_param_change(self, param, value, label=None):
        """RobustPCA 参数变化"""
        app_state.robust_pca_params[param] = value
        if label and param == 'support_fraction':
            label.setText(translate("support_fraction: {value:.2f}").format(value=value))
        self._schedule_slider_callback(f'robust_pca_{param}')

    def _on_standardize_change(self, state):
        """标准化选项变化"""
        app_state.standardize_data = (state == Qt.Checked)
        self._on_change()

    def _on_pca_dim_change(self):
        """PCA 维度选择变化"""
        try:
            x_idx = self.pca_x_spin.value() - 1
            y_idx = self.pca_y_spin.value() - 1

            # 同步 RobustPCA 的维度选择
            if hasattr(self, 'rpca_x_spin'):
                self.rpca_x_spin.blockSignals(True)
                self.rpca_x_spin.setValue(x_idx + 1)
                self.rpca_x_spin.blockSignals(False)

            if hasattr(self, 'rpca_y_spin'):
                self.rpca_y_spin.blockSignals(True)
                self.rpca_y_spin.setValue(y_idx + 1)
                self.rpca_y_spin.blockSignals(False)

            # 更新状态
            app_state.pca_component_indices = [x_idx, y_idx]
            logger.info("PCA dimensions changed to: PC%d vs PC%d", x_idx+1, y_idx+1)

            # 如果当前是 PCA 或 RobustPCA 模式，刷新绘图
            if app_state.render_mode in ['PCA', 'RobustPCA']:
                self._on_change()

        except Exception as e:
            logger.error("Failed to change PCA dimensions: %s", e)

    def _on_show_scree_plot(self):
        """显示 Scree Plot"""
        try:
            from visualization import show_scree_plot
            show_scree_plot(None)  # 传入 None，函数内部会创建新窗口
        except Exception as e:
            logger.error("Failed to show scree plot: %s", e)
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Failed to show scree plot: {error}").format(error=str(e))
            )

    def _on_show_pca_loadings(self):
        """显示 PCA Loadings"""
        try:
            from visualization import show_pca_loadings
            show_pca_loadings(None)  # 传入 None，函数内部会创建新窗口
        except Exception as e:
            logger.error("Failed to show PCA loadings: %s", e)
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Failed to show PCA loadings: {error}").format(error=str(e))
            )

    def _on_ternary_zoom_change(self, state):
        """Ternary Auto-Zoom 变化"""
        app_state.ternary_auto_zoom = (state == Qt.Checked)
        self._on_change()

    def _on_ternary_stretch_mode_change(self, index):
        """Ternary Stretch Mode 变化"""
        modes = ['power', 'minmax', 'hybrid']
        if 0 <= index < len(modes):
            app_state.ternary_stretch_mode = modes[index]
            self._on_change()

    def _on_ternary_scale_change(self, value):
        """Ternary Stretch Mode slider change"""
        idx = max(0, min(2, int(value)))
        mode = self._ternary_stretch_modes[idx]
        app_state.ternary_stretch_mode = mode
        self._update_ternary_scale_label(mode)
        app_state.ternary_stretch = True
        if hasattr(self, 'ternary_stretch_check'):
            self.ternary_stretch_check.blockSignals(True)
            self.ternary_stretch_check.setChecked(True)
            self.ternary_stretch_check.blockSignals(False)
        self._on_change()

    def _on_ternary_stretch_change(self, state):
        """Ternary Stretch to Fill 变化"""
        app_state.ternary_stretch = (state == Qt.Checked)
        self._on_change()

    def _update_ternary_scale_label(self, mode):
        """更新 Ternary Stretch Mode 标签"""
        label_map = {
            'power': translate("Power"),
            'minmax': translate("Min-Max"),
            'hybrid': translate("Hybrid")
        }
        if self.ternary_scale_label is not None:
            self.ternary_scale_label.setText(label_map.get(mode, mode))

    def _refresh_2d_axis_combos(self):
        """刷新 2D 散点图轴选择下拉框"""
        if not hasattr(self, 'xaxis_combo') or not hasattr(self, 'yaxis_combo'):
            return

        cols = [c for c in getattr(app_state, 'data_cols', []) if c in app_state.df_global.columns]
        self.xaxis_combo.clear()
        self.yaxis_combo.clear()
        self.xaxis_combo.addItems(cols)
        self.yaxis_combo.addItems(cols)

        current = getattr(app_state, 'selected_2d_cols', [])

        # 如果没有当前选择，尝试选择前两列
        if (not current or len(current) != 2) and len(cols) >= 2:
            current = [cols[0], cols[1]]
            app_state.selected_2d_cols = current
            app_state.selected_2d_confirmed = True

        if len(current) == 2:
            if current[0] in cols:
                self.xaxis_combo.setCurrentText(current[0])
            if current[1] in cols:
                self.yaxis_combo.setCurrentText(current[1])

    def _on_2d_axis_change(self):
        """2D 轴选择变化"""
        x_col = self.xaxis_combo.currentText()
        y_col = self.yaxis_combo.currentText()

        if x_col and y_col:
            app_state.selected_2d_cols = [x_col, y_col]
            app_state.selected_2d_confirmed = True
            logger.debug("2D Axes Changed: X=%s, Y=%s", x_col, y_col)
            self._on_change()

    def _show_2d_column_dialog(self):
        """显示 2D 列选择对话框"""
        from ui.dialogs.two_d_dialog import get_2d_column_selection

        result = get_2d_column_selection()
        if result:
            app_state.selected_2d_cols = result
            app_state.selected_2d_confirmed = True
            logger.info("Selected 2D columns: %s", result)
            self._on_change()

    def _show_3d_column_dialog(self):
        """显示 3D 列选择对话框"""
        from ui.dialogs.three_d_dialog import get_3d_column_selection

        result = get_3d_column_selection()
        if result:
            app_state.selected_3d_cols = result
            app_state.selected_3d_confirmed = True
            logger.info("Selected 3D columns: %s", result)
            self._on_change()

    def _show_ternary_column_dialog(self):
        """显示三元图列选择对话框"""
        from ui.dialogs.ternary_dialog import get_ternary_column_selection

        result = get_ternary_column_selection()
        if result:
            app_state.selected_ternary_cols = result['columns']
            app_state.ternary_stretch = result['stretch']
            app_state.ternary_factors = result['factors']
            app_state.selected_ternary_confirmed = True
            logger.info("Selected ternary columns: %s", result['columns'])
            logger.info("Ternary stretch: %s, factors: %s", result['stretch'], result['factors'])
            self._on_change()

    def _on_model_curves_change(self, state):
        """模型曲线显示变化"""
        app_state.show_model_curves = (state == Qt.Checked)
        self._sync_geochem_toggle_widgets(
            app_state.show_model_curves,
            getattr(self, 'modeling_show_model_check', None),
            getattr(self, 'show_model_check', None)
        )
        self._on_change()

    def _on_paleoisochron_change(self, state):
        """古等时线显示变化"""
        app_state.show_paleoisochrons = (state == Qt.Checked)
        self._sync_geochem_toggle_widgets(
            app_state.show_paleoisochrons,
            getattr(self, 'modeling_show_paleoisochron_check', None),
            getattr(self, 'show_paleoisochron_check', None)
        )
        self._on_change()

    def _on_model_age_change(self, state):
        """模型年龄线显示变化"""
        app_state.show_model_age_lines = (state == Qt.Checked)
        self._sync_geochem_toggle_widgets(
            app_state.show_model_age_lines,
            getattr(self, 'modeling_show_model_age_check', None),
            getattr(self, 'show_model_age_check', None)
        )
        self._on_change()

    def _on_mu_kappa_real_age_change(self, state):
        """Mu/Kappa 图使用真实年龄列"""
        app_state.use_real_age_for_mu_kappa = (state == Qt.Checked)
        self._sync_geochem_toggle_widgets(
            app_state.use_real_age_for_mu_kappa,
            getattr(self, 'modeling_use_real_age_check', None),
        )
        self._refresh_mu_kappa_age_label()
        if app_state.render_mode in ('PB_MU_AGE', 'PB_KAPPA_AGE'):
            self._on_change()

    def _on_select_mu_kappa_age_column(self):
        """选择 Mu/Kappa 年龄列"""
        if app_state.df_global is None:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("Please load data first.")
            )
            return

        import pandas as pd

        df = app_state.df_global
        try:
            numeric_cols = df.select_dtypes(include='number').columns.tolist()
        except Exception:
            numeric_cols = []
            for col in df.columns:
                try:
                    pd.to_numeric(df[col], errors='raise')
                    numeric_cols.append(col)
                except Exception:
                    continue

        if not numeric_cols:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("No numeric columns available.")
            )
            return

        none_label = translate("None")
        items = [none_label] + numeric_cols

        current = getattr(app_state, 'mu_kappa_age_col', None)
        if current in items:
            current_index = items.index(current)
        else:
            current_index = 0

        from PyQt5.QtWidgets import QInputDialog
        selection, ok = QInputDialog.getItem(
            self,
            translate("Select Age Column"),
            translate("Select Age Column"),
            items,
            current_index,
            False
        )
        if not ok:
            return

        if selection == none_label:
            app_state.mu_kappa_age_col = None
        else:
            app_state.mu_kappa_age_col = selection

        app_state.use_real_age_for_mu_kappa = False
        self._sync_geochem_toggle_widgets(
            app_state.use_real_age_for_mu_kappa,
            getattr(self, 'modeling_use_real_age_check', None),
        )
        self._refresh_mu_kappa_age_label()
        self._refresh_mu_kappa_age_controls()
        if app_state.render_mode in ('PB_MU_AGE', 'PB_KAPPA_AGE'):
            self._on_change()

    def _refresh_mu_kappa_age_label(self):
        """刷新 Mu/Kappa 年龄列显示"""
        if self.mu_kappa_age_label is None:
            return
        label = getattr(app_state, 'mu_kappa_age_col', None) or translate("Not Selected")
        self.mu_kappa_age_label.setText(label)

    def _refresh_mu_kappa_age_controls(self):
        """刷新 Mu/Kappa 年龄列控件状态"""
        mode = self._normalize_render_mode(app_state.render_mode)
        enabled = mode in ('PB_MU_AGE', 'PB_KAPPA_AGE')
        has_col = bool(getattr(app_state, 'mu_kappa_age_col', None))

        if self.mu_kappa_age_title_label is not None:
            self.mu_kappa_age_title_label.setVisible(enabled)
            self.mu_kappa_age_title_label.setEnabled(enabled)
        if self.mu_kappa_age_label is not None:
            self.mu_kappa_age_label.setVisible(enabled)
            self.mu_kappa_age_label.setEnabled(enabled)
        if self.mu_kappa_age_button is not None:
            self.mu_kappa_age_button.setVisible(enabled)
            self.mu_kappa_age_button.setEnabled(enabled)

        if self.modeling_use_real_age_check is not None:
            if not has_col:
                app_state.use_real_age_for_mu_kappa = False
            self.modeling_use_real_age_check.blockSignals(True)
            self.modeling_use_real_age_check.setVisible(enabled)
            self.modeling_use_real_age_check.setEnabled(enabled and has_col)
            self.modeling_use_real_age_check.setChecked(
                bool(getattr(app_state, 'use_real_age_for_mu_kappa', False)) and has_col
            )
            self.modeling_use_real_age_check.blockSignals(False)

    def _on_isochron_change(self, state):
        """等时线显示变化"""
        app_state.show_isochrons = (state == Qt.Checked)
        self._sync_geochem_toggle_widgets(
            app_state.show_isochrons,
            getattr(self, 'modeling_show_isochron_check', None),
            getattr(self, 'show_isochron_check', None)
        )
        self._on_change()

    def _sync_geochem_toggle_widgets(self, checked, *widgets):
        """同步多个地球化学切换控件的状态"""
        for widget in widgets:
            if widget is None:
                continue
            if widget.isChecked() != checked:
                widget.blockSignals(True)
                widget.setChecked(checked)
                widget.blockSignals(False)

    def _sync_toggle_widgets(self, checked, *widgets):
        """同步多个切换控件的状态"""
        for widget in widgets:
            if widget is None:
                continue
            if widget.isChecked() != checked:
                widget.blockSignals(True)
                widget.setChecked(checked)
                widget.blockSignals(False)

    def _on_v1v2_param_change(self):
        """更新 V1V2 时间参数"""
        try:
            from data.geochemistry import engine
        except Exception:
            return

        try:
            params = {}
            if self.v1v2_t1_spin is not None:
                params['T1'] = self.v1v2_t1_spin.value() * 1e6
            if self.v1v2_t2_spin is not None:
                params['T2'] = self.v1v2_t2_spin.value() * 1e6

            if params:
                engine.update_parameters(params)
                if app_state.render_mode == 'V1V2':
                    self._on_change()
        except Exception:
            pass

    def _open_line_style_dialog(self, style_key, swatch):
        """打开曲线样式对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle(translate("Edit Line Style"))
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)

        style = getattr(app_state, 'line_styles', {}).get(style_key, {}) or {}
        color_val = style.get('color') or ''

        color_row = QHBoxLayout()
        color_row.addWidget(QLabel(translate("Line Color")))
        color_swatch = QLabel()
        color_swatch.setFixedSize(20, 16)
        swatch_color = color_val if color_val else '#e2e8f0'
        color_swatch.setStyleSheet(f"background-color: {swatch_color}; border: 1px solid #111827;")
        color_row.addWidget(color_swatch)

        auto_color_check = QCheckBox(translate("Auto Color"))
        auto_color_check.setChecked(color_val in ('', None))
        color_row.addWidget(auto_color_check)

        def _pick_color():
            from PyQt5.QtWidgets import QColorDialog
            chosen = QColorDialog.getColor(QColor(swatch_color), self, translate("Line Color"))
            if chosen.isValid():
                new_color = chosen.name()
                color_swatch.setStyleSheet(f"background-color: {new_color}; border: 1px solid #111827;")
                auto_color_check.setChecked(False)

        color_btn = QPushButton(translate("Choose Color"))
        color_btn.clicked.connect(_pick_color)
        color_row.addWidget(color_btn)
        color_row.addStretch()
        layout.addLayout(color_row)

        width_row = QHBoxLayout()
        width_row.addWidget(QLabel(translate("Line Width")))
        width_spin = QDoubleSpinBox()
        width_spin.setRange(0.2, 6.0)
        width_spin.setSingleStep(0.1)
        width_spin.setValue(float(style.get('linewidth', 1.0)))
        width_row.addWidget(width_spin)
        width_row.addStretch()
        layout.addLayout(width_row)

        style_row = QHBoxLayout()
        style_row.addWidget(QLabel(translate("Line Style")))
        style_combo = QComboBox()
        style_combo.addItems(['-', '--', '-.', ':'])
        style_combo.setCurrentText(style.get('linestyle', '-'))
        style_row.addWidget(style_combo)
        style_row.addStretch()
        layout.addLayout(style_row)

        alpha_row = QHBoxLayout()
        alpha_row.addWidget(QLabel(translate("Opacity")))
        alpha_spin = QDoubleSpinBox()
        alpha_spin.setRange(0.1, 1.0)
        alpha_spin.setSingleStep(0.05)
        alpha_spin.setValue(float(style.get('alpha', 0.85)))
        alpha_row.addWidget(alpha_spin)
        alpha_row.addStretch()
        layout.addLayout(alpha_row)

        # 等时线标注显示选项
        label_checks = {}
        if style_key == 'isochron':
            label_group = QGroupBox(translate("Label Display"))
            label_group.setProperty('translate_key', 'Label Display')
            label_layout = QVBoxLayout(label_group)
            label_layout.setContentsMargins(8, 6, 8, 6)
            label_layout.setSpacing(4)

            opts = getattr(app_state, 'isochron_label_options', {})
            label_items = [
                ('show_age', translate("Age")),
                ('show_n_points', translate("Sample Count (n)")),
                ('show_mswd', 'MSWD'),
                ('show_r_squared', 'R²'),
                ('show_slope', translate("Slope")),
                ('show_intercept', translate("Intercept")),
            ]
            for key, text in label_items:
                chk = QCheckBox(text)
                chk.setChecked(opts.get(key, False))
                label_layout.addWidget(chk)
                label_checks[key] = chk

            layout.addWidget(label_group)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton(translate("Cancel"))
        cancel_btn.clicked.connect(dialog.reject)
        btn_row.addWidget(cancel_btn)
        save_btn = QPushButton(translate("Save"))

        def _apply():
            if not hasattr(app_state, 'line_styles'):
                app_state.line_styles = {}
            style_ref = app_state.line_styles.setdefault(style_key, {})
            if auto_color_check.isChecked():
                style_ref['color'] = None
                new_swatch = '#e2e8f0'
            else:
                swatch_style = color_swatch.styleSheet()
                new_color = swatch_style.split('background-color:')[-1].split(';')[0].strip()
                style_ref['color'] = new_color or '#ef4444'
                new_swatch = style_ref['color']
            style_ref['linewidth'] = float(width_spin.value())
            style_ref['linestyle'] = style_combo.currentText()
            style_ref['alpha'] = float(alpha_spin.value())

            if style_key == 'model_curve':
                app_state.model_curve_width = style_ref['linewidth']
            elif style_key == 'paleoisochron':
                app_state.paleoisochron_width = style_ref['linewidth']
            elif style_key == 'model_age_line':
                app_state.model_age_line_width = style_ref['linewidth']
            elif style_key == 'isochron':
                app_state.isochron_line_width = style_ref['linewidth']
                # 保存标注显示选项
                if label_checks:
                    if not hasattr(app_state, 'isochron_label_options'):
                        app_state.isochron_label_options = {}
                    for key, chk in label_checks.items():
                        app_state.isochron_label_options[key] = chk.isChecked()
            elif style_key == 'selected_isochron':
                app_state.selected_isochron_line_width = style_ref['linewidth']

            if swatch is not None:
                swatch.setStyleSheet(f"background-color: {new_swatch}; border: 1px solid #111827;")
            dialog.accept()
            self._on_change()

        save_btn.clicked.connect(_apply)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

        dialog.exec_()

    def _on_calculate_isochron(self):
        """计算等时线年龄：切换显示/隐藏。"""
        try:
            from visualization.events import calculate_selected_isochron, on_slider_change
        except Exception as e:
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Failed to start isochron selection: {error}").format(error=str(e))
            )
            return

        # 如果等时线已显示，关闭它
        if getattr(app_state, 'show_isochrons', False) or getattr(app_state, 'selected_isochron_data', None):
            app_state.show_isochrons = False
            app_state.isochron_results = {}
            app_state.selected_isochron_data = None
            self._update_isochron_btn_text()
            try:
                on_slider_change()
            except Exception:
                pass
            return

        if app_state.render_mode == '3D':
            QMessageBox.information(
                self,
                translate("Isochron Age Calculation"),
                translate("Isochron calculation is only available in 2D views")
            )
            return

        if app_state.render_mode != 'PB_EVOL_76':
            QMessageBox.information(
                self,
                translate("Isochron Age Calculation"),
                translate("Isochron calculation is only available for Pb evolution plot (PB_EVOL_76)")
            )
            return

        if not self._ensure_isochron_error_settings():
            return

        selected = set(getattr(app_state, 'selected_indices', set()) or set())

        if selected:
            calculate_selected_isochron()
        else:
            app_state.show_isochrons = True

        try:
            on_slider_change()
        except Exception as refresh_err:
            logger.warning("Failed to refresh plot: %s", refresh_err)

        self._update_isochron_btn_text()

        # 显示结果
        self._on_isochron_settings()

    def _update_isochron_btn_text(self):
        """更新等时线按钮文本。"""
        btn = getattr(self, 'calc_isochron_btn', None)
        if btn is None:
            return
        if getattr(app_state, 'show_isochrons', False) or getattr(app_state, 'selected_isochron_data', None):
            btn.setText(translate("Hide Isochron"))
        else:
            btn.setText(translate("Calculate Isochron Age"))

    def _ensure_isochron_error_settings(self):
        """Ensure isochron error settings are usable before calculation."""
        mode = getattr(app_state, 'isochron_error_mode', 'fixed')
        if mode != 'columns':
            return True

        df = getattr(app_state, 'df_global', None)
        sx_col = getattr(app_state, 'isochron_sx_col', '')
        sy_col = getattr(app_state, 'isochron_sy_col', '')

        if df is None or not sx_col or not sy_col:
            return self._on_isochron_settings()

        if sx_col not in df.columns or sy_col not in df.columns:
            return self._on_isochron_settings()

        return True

    def _on_isochron_settings(self):
        """Open isochron regression settings dialog."""
        try:
            from ui.dialogs.isochron_dialog import get_isochron_error_settings
        except Exception as exc:
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Failed to open isochron settings: {error}").format(error=str(exc))
            )
            return False

        settings = get_isochron_error_settings(self)
        if not settings:
            return False

        mode = settings.get('mode')
        if mode == 'columns':
            app_state.isochron_error_mode = 'columns'
            app_state.isochron_sx_col = settings.get('sx_col', '')
            app_state.isochron_sy_col = settings.get('sy_col', '')
            app_state.isochron_rxy_col = settings.get('rxy_col', '')
        else:
            app_state.isochron_error_mode = 'fixed'
            app_state.isochron_sx_value = float(settings.get('sx_value', 0.001))
            app_state.isochron_sy_value = float(settings.get('sy_value', 0.001))
            app_state.isochron_rxy_value = float(settings.get('rxy_value', 0.0))

        self._on_change()
        return True

    def _on_paleo_step_change(self, value):
        """古等时线密度变化"""
        step_val = max(10, int(value))
        app_state.paleoisochron_step = step_val
        min_age = int(getattr(app_state, 'paleoisochron_min_age', 0))
        max_age = int(getattr(app_state, 'paleoisochron_max_age', 3000))
        if max_age < min_age:
            max_age, min_age = min_age, max_age
        ages = list(range(max_age, min_age - 1, -step_val))
        if not ages or ages[-1] != min_age:
            ages.append(min_age)
        app_state.paleoisochron_ages = ages
        self._on_change()

    def _refresh_group_column_radios(self):
        """刷新分组列单选按钮"""
        if self.group_radio_layout is None:
            return

        while self.group_radio_layout.count():
            item = self.group_radio_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)

        if self.group_radio_group is not None:
            for btn in list(self.group_radio_group.buttons()):
                self.group_radio_group.removeButton(btn)

        self.group_placeholder_label = None

        if app_state.group_cols:
            if app_state.last_group_col not in app_state.group_cols:
                app_state.last_group_col = app_state.group_cols[0]
                app_state.visible_groups = None

            for col in app_state.group_cols:
                btn = QRadioButton(col)
                btn.setChecked(col == app_state.last_group_col)
                btn.setProperty('group_col', col)
                self.group_radio_group.addButton(btn)
                self.group_radio_layout.addWidget(btn)
        else:
            placeholder = QLabel(translate("Load data to unlock grouping options."))
            placeholder.setWordWrap(True)
            self.group_radio_layout.addWidget(placeholder)
            self.group_placeholder_label = placeholder

    def _on_group_col_selected(self, button):
        """分组列选择变化"""
        if button is None:
            return

        col = button.property('group_col') or button.text()
        if col and app_state.last_group_col != col:
            app_state.last_group_col = col
            app_state.visible_groups = None
            self._update_group_list()
            self._on_change()

    def _on_configure_group_columns(self):
        """打开分组列配置"""
        if app_state.df_global is None:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("Please load data first.")
            )
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(translate("Group Columns Configuration"))
        dialog.resize(420, 520)

        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(translate("Select columns to use for grouping:")))

        list_widget = QListWidget()
        list_widget.setSelectionMode(QListWidget.MultiSelection)
        layout.addWidget(list_widget, 1)

        current = set(app_state.group_cols or [])
        for col in list(app_state.df_global.columns):
            item = QListWidgetItem(str(col))
            item.setData(Qt.UserRole, col)
            if col in current:
                item.setSelected(True)
            list_widget.addItem(item)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton(translate("Cancel"))
        cancel_btn.clicked.connect(dialog.reject)
        btn_row.addWidget(cancel_btn)
        apply_btn = QPushButton(translate("Apply"))

        def _apply():
            selected = [item.data(Qt.UserRole) for item in list_widget.selectedItems()]
            if not selected:
                QMessageBox.warning(
                    self,
                    translate("Validation Error"),
                    translate("Please select at least one grouping column.")
                )
                return
            app_state.group_cols = selected
            if app_state.last_group_col not in app_state.group_cols:
                app_state.last_group_col = app_state.group_cols[0]
                app_state.visible_groups = None

            self._refresh_group_column_radios()
            self._update_group_list()
            self._on_change()
            dialog.accept()

        apply_btn.clicked.connect(_apply)
        btn_row.addWidget(apply_btn)
        layout.addLayout(btn_row)

        dialog.exec_()

    def _normalize_render_mode(self, mode):
        """规范化渲染模式"""
        if not mode:
            return 'UMAP'
        value = str(mode)
        if value in ('t-SNE', 'TSNE', 'tSNE'):
            return 'tSNE'
        if value in ('PB_MODELS_76', 'PB_MODELS_86'):
            return 'PB_EVOL_76' if value.endswith('_76') else 'PB_EVOL_86'
        return value

    def _normalize_algorithm(self, algorithm):
        """规范化算法名称"""
        if not algorithm:
            return 'UMAP'
        value = str(algorithm)
        if value in ('t-SNE', 'TSNE', 'tSNE'):
            return 'tSNE'
        return value

    def _on_tooltip_change(self, state):
        """工具提示显示变化"""
        app_state.show_tooltip = (state == Qt.Checked)
        self._on_change()

    def _on_configure_tooltip(self):
        """打开工具提示配置对话框"""
        try:
            from ui.dialogs.tooltip_dialog import get_tooltip_configuration
            result = get_tooltip_configuration(self)
            if result:
                app_state.tooltip_columns = result
                logger.info("Tooltip columns configured: %s", result)
                self._on_change()
        except Exception as e:
            logger.error("Failed to open tooltip configuration dialog: %s", e)
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Failed to open tooltip configuration: {error}").format(error=str(e))
            )
