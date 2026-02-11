"""
Qt5 控制面板
提供算法参数调整和可视化设置
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                              QPushButton, QLabel,
                              QFrame, QScrollArea, QToolButton,
                              QComboBox, QCheckBox, QRadioButton,
                              QSlider, QProgressBar, QGroupBox,
                              QLineEdit, QSpinBox, QDoubleSpinBox,
                              QTabWidget, QGridLayout, QListWidget,
                              QListWidgetItem, QSizePolicy, QMessageBox,
                              QButtonGroup, QDialog)
from PyQt5.QtCore import Qt, QSize, QPointF, QRectF, pyqtSignal, QTimer, pyqtSlot
from PyQt5.QtGui import QIcon, QFont, QPalette, QColor, QCursor, QPainter, QPen, QBrush, QPixmap, QPolygonF

import ast
import json
import math
import uuid

from core import translate, app_state, CONFIG
from core.localization import available_languages


class Qt5ControlPanel(QWidget):
    """Qt5 控制面板"""

    # 信号定义
    parameter_changed = pyqtSignal(str, object)

    def __init__(self, callback=None, parent=None, build_ui=True):
        super().__init__(parent)
        self.callback = callback
        self._translations = {}
        self._is_initialized = False
        self._is_rebuilding = False
        self._language_change_pending = False

        # 初始化变量
        self.sliders = {}
        self.labels = {}
        self.radio_vars = {}
        self.check_vars = {}
        self._slider_steps = {}
        self._slider_delay_ms = 350
        self._slider_timers = {}
        self._ternary_stretch_modes = ['power', 'minmax', 'hybrid']

        if build_ui:
            self._setup_ui()
            self._setup_styles()
            self._update_data_count_label()
            self.update_selection_controls()
            self._is_initialized = True
            try:
                app_state.register_language_listener(self._refresh_language)
            except Exception:
                pass

    def _setup_ui(self):
        """初始化控制面板 UI"""
        self.setWindowTitle(translate("Control Panel"))
        self.resize(560, 860)
        self.setMinimumSize(520, 740)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(12)

        header = QFrame()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        title = QLabel(translate("Visualization Controls"))
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        self.data_count_label = QLabel("")
        header_layout.addWidget(self.data_count_label)

        lang_label = QLabel(f"{translate('Language')}:")
        header_layout.addWidget(lang_label)

        self.lang_combo = QComboBox()
        self.lang_combo.setFixedWidth(140)
        lang_map = dict(available_languages())
        for code, label in lang_map.items():
            self.lang_combo.addItem(label, code)
        current_lang = getattr(app_state, 'language', None)
        if current_lang:
            idx = self.lang_combo.findData(current_lang)
            if idx >= 0:
                self.lang_combo.setCurrentIndex(idx)
        self.lang_combo.currentIndexChanged.connect(self._on_language_change)
        header_layout.addWidget(self.lang_combo)

        root_layout.addWidget(header)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFrameShadow(QFrame.Sunken)
        root_layout.addWidget(divider)

        status_group = QGroupBox(translate("Status"))
        status_layout = QHBoxLayout(status_group)
        status_layout.setContentsMargins(12, 8, 12, 8)
        status_layout.setSpacing(16)

        status_summary = QVBoxLayout()
        status_summary.setSpacing(6)

        self.status_data_label = QLabel("")
        self.status_render_label = QLabel("")
        self.status_algo_label = QLabel("")
        self.status_group_label = QLabel("")
        self.status_selected_label = QLabel("")

        for lbl in (
            self.status_data_label,
            self.status_render_label,
            self.status_algo_label,
            self.status_group_label,
            self.status_selected_label,
        ):
            lbl.setWordWrap(True)
            status_summary.addWidget(lbl)

        status_layout.addLayout(status_summary, 1)

        status_actions = QGroupBox(translate("Quick Actions"))
        actions_layout = QVBoxLayout()

        clear_btn = QPushButton(translate("Clear Selection"))
        clear_btn.setFixedWidth(170)
        clear_btn.clicked.connect(self._clear_selection_only)
        actions_layout.addWidget(clear_btn, 0, Qt.AlignHCenter)

        self.status_export_button = QPushButton(translate("Export Selected"))
        self.status_export_button.setFixedWidth(170)
        self.status_export_button.clicked.connect(self._on_export_clicked)
        actions_layout.addWidget(self.status_export_button, 0, Qt.AlignHCenter)

        refresh_btn = QPushButton(translate("Replot"))
        refresh_btn.setFixedWidth(170)
        refresh_btn.clicked.connect(self._on_change)
        actions_layout.addWidget(refresh_btn, 0, Qt.AlignHCenter)

        status_actions.setLayout(actions_layout)
        status_layout.addWidget(status_actions, 0)

        root_layout.addWidget(status_group)

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)
        self.tab_widget.setMovable(False)

        sections = [
            (translate("Data"), self._build_data_section),
            (translate("Display"), self._build_display_section),
            (translate("Analysis"), self._build_analysis_section),
            (translate("Export"), self._build_export_section),
            (translate("Legend"), self._build_legend_section),
            (translate("Geochemistry"), self._build_geo_section),
        ]

        for label, builder in sections:
            content = builder()
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.NoFrame)
            scroll.setWidget(content)
            self.tab_widget.addTab(scroll, label)

        root_layout.addWidget(self.tab_widget, 1)

        self._update_status_panel()

    def _setup_styles(self):
        """应用基础样式"""
        self.setStyleSheet(
            "QFrame { background: transparent; }"
            "QGroupBox { margin-top: 10px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 6px; }"
            "QScrollArea { border: none; }"
            "QTabWidget::pane { border: 1px solid #e2e8f0; border-radius: 6px; }"
            "QTabBar::tab { padding: 6px 12px; margin-right: 2px; }"
            "QTabBar::tab:selected { background-color: #e2e8f0; }"
            "QPushButton { text-align: left; padding: 6px 10px; }"
        )

    def _switch_section(self, index):
        """切换到指定分区"""
        tab_widget = getattr(self, 'tab_widget', None)
        if tab_widget is not None:
            tab_widget.setCurrentIndex(index)
            return
        if not hasattr(self, 'stacked_widget'):
            return
        self.stacked_widget.setCurrentIndex(index)
        for idx, btn in self.section_buttons.items():
            btn.setChecked(idx == index)

    def _on_language_change(self, _index):
        """语言切换"""
        code = self.lang_combo.currentData() if self.lang_combo else None
        if not code:
            return
        if self._is_rebuilding or self._language_change_pending:
            return

        if code == getattr(app_state, 'language', None):
            return

        self._language_change_pending = True
        try:
            from core.localization import set_language
            set_language(code)
        finally:
            QTimer.singleShot(0, self._rebuild_ui)

    def _refresh_language(self):
        """刷新语言"""
        self._update_data_count_label()
        if not self._is_initialized or self._is_rebuilding:
            return
        if self._language_change_pending:
            return
        QTimer.singleShot(0, self._rebuild_ui)

    def _rebuild_ui(self):
        """重建 UI 以刷新翻译"""
        self._is_rebuilding = True
        try:
            layout = self.layout()
            if layout is not None:
                while layout.count():
                    item = layout.takeAt(0)
                    widget = item.widget()
                    if widget is not None:
                        widget.deleteLater()

            self._reset_ui_state()
            self._setup_ui()
            self._setup_styles()
            self._update_data_count_label()
        finally:
            self._is_rebuilding = False
            self._language_change_pending = False

    def _reset_ui_state(self):
        """重置 UI 相关引用以便重建"""
        self.sliders = {}
        self.labels = {}
        self.radio_vars = {}
        self.check_vars = {}
        self._slider_steps = {}
        self._slider_timers = {}
        self._ternary_stretch_modes = ['power', 'minmax', 'hybrid']
        self.group_radio_group = None
        self.group_radio_layout = None
        self.group_placeholder_label = None
        self.geochem_plot_group = None
        self.group_kde_check = None
        self.v1v2_group = None
        self.v1v2_t1_spin = None
        self.v1v2_t2_spin = None
        self.ternary_scale_label = None
        self.ternary_scale_slider = None
        self.section_buttons = {}
        self.tab_widget = None
        self.selection_button = None
        self.ellipse_selection_button = None
        self.lasso_selection_button = None
        self.selection_status_label = None
        self.export_csv_button = None
        self.export_excel_button = None
        self.export_selected_button = None
        self.status_data_label = None
        self.status_render_label = None
        self.status_algo_label = None
        self.status_group_label = None
        self.status_selected_label = None
        self.status_export_button = None
        self.status_data_label = None
        self.status_render_label = None
        self.status_algo_label = None
        self.status_group_label = None
        self.status_selected_label = None
        self.status_export_button = None
        self.tools_kde_check = None
        self.tools_marginal_kde_check = None
        self.tools_equation_overlays_check = None
        self.equation_overlays_container = None
        self.equation_overlays_layout = None
        self.tooltip_check = None
        self.ui_theme_combo = None
        self.theme_name_edit = None
        self.theme_load_combo = None
        self.grid_check = None
        self.color_combo = None
        self.primary_font_combo = None
        self.cjk_font_combo = None
        self.font_size_spins = {}
        self.show_title_check = None
        self.marker_size_spin = None
        self.marker_alpha_spin = None
        self.figure_dpi_spin = None
        self.figure_bg_edit = None
        self.axes_bg_edit = None
        self.grid_color_edit = None
        self.grid_width_spin = None
        self.grid_alpha_spin = None
        self.grid_style_combo = None
        self.tick_dir_combo = None
        self.tick_color_edit = None
        self.tick_length_spin = None
        self.tick_width_spin = None
        self.minor_ticks_check = None
        self.minor_tick_length_spin = None
        self.minor_tick_width_spin = None
        self.axis_linewidth_spin = None
        self.axis_line_color_edit = None
        self.show_top_spine_check = None
        self.show_right_spine_check = None
        self.minor_grid_check = None
        self.minor_grid_color_edit = None
        self.minor_grid_width_spin = None
        self.minor_grid_alpha_spin = None
        self.minor_grid_style_combo = None
        self.scatter_edgecolor_edit = None
        self.scatter_edgewidth_spin = None
        self.model_curve_width_spin = None
        self.paleoisochron_width_spin = None
        self.model_age_width_spin = None
        self.isochron_width_spin = None
        self.label_color_edit = None
        self.label_weight_combo = None
        self.label_pad_spin = None
        self.title_color_edit = None
        self.title_weight_combo = None
        self.title_pad_spin = None
        self.legend_location_combo = None
        self.legend_location_map = {}
        self.legend_frame_on_check = None
        self.legend_frame_alpha_spin = None
        self.legend_frame_face_edit = None
        self.legend_frame_edge_edit = None

    def _update_data_count_label(self):
        """更新数据计数标签"""
        if app_state.df_global is not None:
            count = len(app_state.df_global)
            text = translate("Loaded Data: {count} rows", count=count)
            self.data_count_label.setText(text)
        else:
            self.data_count_label.setText("")
        self._update_status_panel()

    def _on_change(self):
        """参数变化回调"""
        self._update_status_panel()
        if self.callback:
            self.callback()

    def _schedule_slider_callback(self, key):
        """计划滑块回调（防抖）"""
        if key in self._slider_timers:
            self._slider_timers[key].stop()

        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self._apply_slider_change(key))
        timer.start(self._slider_delay_ms)
        self._slider_timers[key] = timer

    def _apply_slider_change(self, key):
        """应用滑块变化"""
        if key in self._slider_timers:
            self._slider_timers[key].stop()
            del self._slider_timers[key]
        self._on_change()

    # ========== 内容构建方法 ==========

    def _build_modeling_section(self):
        """构建建模部分"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)

        # 分组/着色选择
        group_group = QGroupBox(translate("Coloring / Grouping"))
        group_layout = QVBoxLayout()

        self.group_radio_group = QButtonGroup(self)
        self.group_radio_group.setExclusive(True)
        self.group_radio_group.buttonClicked.connect(self._on_group_col_selected)

        group_container = QWidget()
        self.group_radio_layout = QVBoxLayout(group_container)
        self.group_radio_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.addWidget(group_container)

        group_config_btn = QPushButton(translate("Configure Group Columns"))
        group_config_btn.clicked.connect(self._on_configure_group_columns)
        group_layout.addWidget(group_config_btn)

        group_group.setLayout(group_layout)
        layout.addWidget(group_group)

        self._refresh_group_column_radios()

        # 渲染模式选择
        render_group = QGroupBox(translate("Render Mode"))
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

        # 算法选择（用于 UMAP/t-SNE/PCA）
        algo_group = QGroupBox(translate("Algorithm"))
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

        # UMAP 参数
        self.umap_group = QGroupBox(translate("UMAP Parameters"))
        umap_layout = QVBoxLayout()

        # n_neighbors
        n_label = QLabel(translate("n_neighbors: {value}").format(value=app_state.umap_params['n_neighbors']))
        umap_layout.addWidget(n_label)

        n_slider = QSlider(Qt.Horizontal)
        n_slider.setMinimum(2)
        n_slider.setMaximum(50)
        n_neighbors = min(app_state.umap_params['n_neighbors'], 50)
        if app_state.umap_params['n_neighbors'] != n_neighbors:
            app_state.umap_params['n_neighbors'] = n_neighbors
        n_slider.setValue(n_neighbors)
        n_slider.valueChanged.connect(lambda v: self._on_umap_param_change('n_neighbors', v, n_label))
        umap_layout.addWidget(n_slider)

        self.sliders['umap_n_neighbors'] = n_slider
        self.labels['umap_n_neighbors'] = n_label

        # min_dist
        min_dist_label = QLabel(translate("min_dist: {value:.3f}").format(value=app_state.umap_params['min_dist']))
        umap_layout.addWidget(min_dist_label)

        min_dist_spin = QDoubleSpinBox()
        min_dist_spin.setRange(0.0, 1.0)
        min_dist_spin.setSingleStep(0.01)
        min_dist_spin.setDecimals(3)
        min_dist_spin.setValue(app_state.umap_params['min_dist'])
        min_dist_spin.valueChanged.connect(lambda v: self._on_umap_param_change('min_dist', v, min_dist_label))
        umap_layout.addWidget(min_dist_spin)

        self.labels['umap_min_dist'] = min_dist_label

        # metric
        metric_label = QLabel(translate("metric:"))
        umap_layout.addWidget(metric_label)

        metric_combo = QComboBox()
        metric_combo.addItems(['euclidean', 'manhattan', 'cosine', 'correlation'])
        metric_combo.setCurrentText(app_state.umap_params.get('metric', 'euclidean'))
        metric_combo.currentTextChanged.connect(lambda v: self._on_umap_param_change('metric', v, None))
        umap_layout.addWidget(metric_combo)

        self.umap_group.setLayout(umap_layout)
        layout.addWidget(self.umap_group)

        # t-SNE 参数
        self.tsne_group = QGroupBox(translate("t-SNE Parameters"))
        tsne_layout = QVBoxLayout()

        # perplexity
        perp_label = QLabel(translate("perplexity: {value}").format(value=app_state.tsne_params['perplexity']))
        tsne_layout.addWidget(perp_label)

        perp_slider = QSlider(Qt.Horizontal)
        perp_slider.setMinimum(5)
        perp_slider.setMaximum(100)
        perplexity = min(int(app_state.tsne_params['perplexity']), 100)
        if app_state.tsne_params['perplexity'] != perplexity:
            app_state.tsne_params['perplexity'] = perplexity
        perp_slider.setValue(perplexity)
        perp_slider.valueChanged.connect(lambda v: self._on_tsne_param_change('perplexity', v, perp_label))
        tsne_layout.addWidget(perp_slider)

        self.sliders['tsne_perplexity'] = perp_slider
        self.labels['tsne_perplexity'] = perp_label

        # learning_rate
        lr_label = QLabel(translate("learning_rate: {value}").format(value=app_state.tsne_params['learning_rate']))
        tsne_layout.addWidget(lr_label)

        lr_spin = QDoubleSpinBox()
        lr_spin.setRange(10.0, 1000.0)
        lr_spin.setSingleStep(10.0)
        lr_spin.setValue(app_state.tsne_params['learning_rate'])
        lr_spin.valueChanged.connect(lambda v: self._on_tsne_param_change('learning_rate', v, lr_label))
        tsne_layout.addWidget(lr_spin)

        self.labels['tsne_learning_rate'] = lr_label

        # random_state
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

        # PCA 参数
        self.pca_group = QGroupBox(translate("PCA Parameters"))
        pca_layout = QVBoxLayout()

        # n_components
        n_comp_label = QLabel(translate("n_components:"))
        pca_layout.addWidget(n_comp_label)

        n_comp_spin = QSpinBox()
        n_comp_spin.setRange(2, 10)
        n_comp_spin.setValue(app_state.pca_params.get('n_components', 2))
        n_comp_spin.valueChanged.connect(lambda v: self._on_pca_param_change('n_components', v))
        pca_layout.addWidget(n_comp_spin)

        # random_state
        pca_rs_label = QLabel(translate("random_state: {value}").format(
            value=app_state.pca_params.get('random_state', 42)
        ))
        pca_layout.addWidget(pca_rs_label)

        pca_rs_spin = QSpinBox()
        pca_rs_spin.setRange(0, 200)
        pca_rs_spin.setValue(app_state.pca_params.get('random_state', 42))
        pca_rs_spin.valueChanged.connect(lambda v: self._on_pca_param_change('random_state', v, pca_rs_label))
        pca_layout.addWidget(pca_rs_spin)

        # standardize
        standardize_check = QCheckBox(translate("Standardize data"))
        standardize_check.setChecked(app_state.standardize_data)
        standardize_check.stateChanged.connect(self._on_standardize_change)
        pca_layout.addWidget(standardize_check)

        # PCA 工具按钮
        pca_tools_layout = QHBoxLayout()

        scree_btn = QPushButton(translate("Scree Plot"))
        scree_btn.clicked.connect(self._on_show_scree_plot)
        pca_tools_layout.addWidget(scree_btn)

        loadings_btn = QPushButton(translate("Loadings"))
        loadings_btn.clicked.connect(self._on_show_pca_loadings)
        pca_tools_layout.addWidget(loadings_btn)

        pca_layout.addLayout(pca_tools_layout)

        # PCA 维度选择
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

        # RobustPCA 参数
        self.robust_pca_group = QGroupBox(translate("RobustPCA Parameters"))
        robust_pca_layout = QVBoxLayout()

        # n_components
        robust_n_comp_label = QLabel(translate("n_components:"))
        robust_pca_layout.addWidget(robust_n_comp_label)

        robust_n_comp_spin = QSpinBox()
        robust_n_comp_spin.setRange(2, 10)
        robust_n_comp_spin.setValue(app_state.robust_pca_params.get('n_components', 2))
        robust_n_comp_spin.valueChanged.connect(lambda v: self._on_robust_pca_param_change('n_components', v))
        robust_pca_layout.addWidget(robust_n_comp_spin)

        # support_fraction
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

        # random_state
        robust_rs_label = QLabel(translate("random_state:"))
        robust_pca_layout.addWidget(robust_rs_label)

        robust_rs_spin = QSpinBox()
        robust_rs_spin.setRange(0, 9999)
        robust_rs_spin.setValue(app_state.robust_pca_params.get('random_state', 42))
        robust_rs_spin.valueChanged.connect(lambda v: self._on_robust_pca_param_change('random_state', v))
        robust_pca_layout.addWidget(robust_rs_spin)

        # RobustPCA 工具按钮
        rpca_tools_layout = QHBoxLayout()

        rpca_scree_btn = QPushButton(translate("Scree Plot"))
        rpca_scree_btn.clicked.connect(self._on_show_scree_plot)
        rpca_tools_layout.addWidget(rpca_scree_btn)

        rpca_loadings_btn = QPushButton(translate("Loadings"))
        rpca_loadings_btn.clicked.connect(self._on_show_pca_loadings)
        rpca_tools_layout.addWidget(rpca_loadings_btn)

        robust_pca_layout.addLayout(rpca_tools_layout)

        # RobustPCA 维度选择（共享 PCA 的维度选择）
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

        # Ternary Plot 参数
        self.ternary_group = QGroupBox(translate("Ternary Plot"))
        ternary_layout = QVBoxLayout()

        info_label = QLabel(translate("Using Standard Ternary Plot.\nData is plotted as relative proportions."))
        info_label.setWordWrap(True)
        ternary_layout.addWidget(info_label)

        # Auto-Zoom
        self.ternary_auto_zoom_check = QCheckBox(translate("Auto-Zoom to Data"))
        self.ternary_auto_zoom_check.setChecked(getattr(app_state, 'ternary_auto_zoom', False))
        self.ternary_auto_zoom_check.stateChanged.connect(self._on_ternary_zoom_change)
        ternary_layout.addWidget(self.ternary_auto_zoom_check)

        # Stretch Mode (slider)
        stretch_header = QHBoxLayout()
        stretch_label = QLabel(translate("Stretch Mode"))
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

        # Stretch to Fill
        self.ternary_stretch_check = QCheckBox(translate("Stretch to Fill"))
        self.ternary_stretch_check.setChecked(getattr(app_state, 'ternary_stretch', False))
        self.ternary_stretch_check.stateChanged.connect(self._on_ternary_stretch_change)
        ternary_layout.addWidget(self.ternary_stretch_check)

        self.ternary_group.setLayout(ternary_layout)
        layout.addWidget(self.ternary_group)

        # V1V2 参数
        self.v1v2_group = QGroupBox(translate("V1V2 Time Settings"))
        v1v2_layout = QVBoxLayout()

        try:
            from data.geochemistry import engine
            params = engine.get_parameters()
        except Exception:
            params = {}

        t1_val = params.get('T1', 4430e6) / 1e6
        t2_val = params.get('T2', 4570e6) / 1e6

        t1_layout = QHBoxLayout()
        t1_layout.addWidget(QLabel(translate("T1 (Ma) - Model Age")))
        self.v1v2_t1_spin = QDoubleSpinBox()
        self.v1v2_t1_spin.setRange(0.0, 10000.0)
        self.v1v2_t1_spin.setDecimals(3)
        self.v1v2_t1_spin.setValue(t1_val)
        self.v1v2_t1_spin.valueChanged.connect(self._on_v1v2_param_change)
        t1_layout.addWidget(self.v1v2_t1_spin)
        v1v2_layout.addLayout(t1_layout)

        t2_layout = QHBoxLayout()
        t2_layout.addWidget(QLabel(translate("T2 (Ma) - Standard Earth Age")))
        self.v1v2_t2_spin = QDoubleSpinBox()
        self.v1v2_t2_spin.setRange(0.0, 10000.0)
        self.v1v2_t2_spin.setDecimals(3)
        self.v1v2_t2_spin.setValue(t2_val)
        self.v1v2_t2_spin.valueChanged.connect(self._on_v1v2_param_change)
        t2_layout.addWidget(self.v1v2_t2_spin)
        v1v2_layout.addLayout(t2_layout)

        self.v1v2_group.setLayout(v1v2_layout)
        layout.addWidget(self.v1v2_group)

        # 地球化学绘图控制
        self.geochem_plot_group = QGroupBox(translate("Geochemistry Plot Controls"))
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
                swatch.setProperty("keepStyle", True)
                swatch.mousePressEvent = lambda event, k=style_key, s=swatch: self._open_line_style_dialog(k, s)
                row.addWidget(swatch)

            row.addStretch()
            geochem_layout.addLayout(row)
            return chk

        self.modeling_show_isochron_check = _add_geochem_toggle(
            "Show Age Isochrons",
            getattr(app_state, 'show_isochrons', True),
            self._on_isochron_change,
            style_key='isochron'
        )

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
        paleo_step_layout.addWidget(QLabel(translate("Paleoisochron Step (Ma):")))
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

        isochron_row = QHBoxLayout()
        calc_isochron_btn = QPushButton(translate("Calculate Isochron Age"))
        calc_isochron_btn.clicked.connect(self._on_calculate_isochron)
        isochron_row.addWidget(calc_isochron_btn)

        isochron_settings_btn = QPushButton(translate("Isochron Settings"))
        isochron_settings_btn.clicked.connect(self._on_isochron_settings)
        isochron_row.addWidget(isochron_settings_btn)

        selected_style = getattr(app_state, 'line_styles', {}).get('selected_isochron', {}) or {}
        selected_color = selected_style.get('color') or '#ef4444'
        isochron_swatch = QLabel()
        isochron_swatch.setFixedSize(16, 16)
        isochron_swatch.setStyleSheet(f"background-color: {selected_color}; border: 1px solid #111827;")
        isochron_swatch.mousePressEvent = lambda event, s=isochron_swatch: self._open_line_style_dialog('selected_isochron', s)
        isochron_row.addWidget(isochron_swatch)
        isochron_row.addStretch()
        geochem_layout.addLayout(isochron_row)

        self.geochem_plot_group.setLayout(geochem_layout)
        layout.addWidget(self.geochem_plot_group)

        # 2D Scatter 参数
        self.twod_group = QGroupBox(translate("2D Scatter Parameters"))
        twod_layout = QVBoxLayout()

        twod_grid = QGridLayout()

        x_label = QLabel(translate("X Axis:"))
        twod_grid.addWidget(x_label, 0, 0)

        self.xaxis_combo = QComboBox()
        self.xaxis_combo.setEditable(False)
        self.xaxis_combo.setStyleSheet("QComboBox { combobox-popup: 0; }")
        self.xaxis_combo.setMinimumWidth(150)
        twod_grid.addWidget(self.xaxis_combo, 0, 1)

        y_label = QLabel(translate("Y Axis:"))
        twod_grid.addWidget(y_label, 1, 0)

        self.yaxis_combo = QComboBox()
        self.yaxis_combo.setEditable(False)
        self.yaxis_combo.setStyleSheet("QComboBox { combobox-popup: 0; }")
        self.yaxis_combo.setMinimumWidth(150)
        twod_grid.addWidget(self.yaxis_combo, 1, 1)

        twod_layout.addLayout(twod_grid)

        # 刷新2D轴选择
        self._refresh_2d_axis_combos()

        self.twod_group.setLayout(twod_layout)
        layout.addWidget(self.twod_group)

        # 根据当前算法显示/隐藏参数组
        self._update_algorithm_visibility()

        layout.addStretch()
        return widget

    def _build_data_section(self):
        """构建数据部分"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)

        group_group = QGroupBox(translate("Coloring / Grouping"))
        group_layout = QVBoxLayout()

        self.group_radio_group = QButtonGroup(self)
        self.group_radio_group.setExclusive(True)
        self.group_radio_group.buttonClicked.connect(self._on_group_col_selected)

        group_container = QWidget()
        self.group_radio_layout = QVBoxLayout(group_container)
        self.group_radio_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.addWidget(group_container)

        group_config_btn = QPushButton(translate("Configure Group Columns"))
        group_config_btn.clicked.connect(self._on_configure_group_columns)
        group_layout.addWidget(group_config_btn)

        group_group.setLayout(group_layout)
        layout.addWidget(group_group)

        self._refresh_group_column_radios()

        tooltip_group = QGroupBox(translate("Tooltip Settings"))
        tooltip_layout = QVBoxLayout()

        tooltip_check_layout = QHBoxLayout()
        self.tooltip_check = QCheckBox(translate("Show Tooltip"))
        self.tooltip_check.setChecked(getattr(app_state, 'show_tooltip', True))
        self.tooltip_check.stateChanged.connect(self._on_tooltip_change)
        tooltip_check_layout.addWidget(self.tooltip_check)

        tooltip_config_btn = QPushButton(translate("Configure"))
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
        n_slider.valueChanged.connect(lambda v: self._on_umap_param_change('n_neighbors', v, n_label))
        umap_layout.addWidget(n_slider)

        self.sliders['umap_n_neighbors'] = n_slider
        self.labels['umap_n_neighbors'] = n_label

        min_dist_label = QLabel(translate("min_dist: {value:.3f}").format(value=app_state.umap_params['min_dist']))
        umap_layout.addWidget(min_dist_label)

        min_dist_spin = QDoubleSpinBox()
        min_dist_spin.setRange(0.0, 1.0)
        min_dist_spin.setSingleStep(0.01)
        min_dist_spin.setDecimals(3)
        min_dist_spin.setValue(app_state.umap_params['min_dist'])
        min_dist_spin.valueChanged.connect(lambda v: self._on_umap_param_change('min_dist', v, min_dist_label))
        umap_layout.addWidget(min_dist_spin)

        self.labels['umap_min_dist'] = min_dist_label

        metric_label = QLabel(translate("metric:"))
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
        perp_slider.valueChanged.connect(lambda v: self._on_tsne_param_change('perplexity', v, perp_label))
        tsne_layout.addWidget(perp_slider)

        self.sliders['tsne_perplexity'] = perp_slider
        self.labels['tsne_perplexity'] = perp_label

        lr_label = QLabel(translate("learning_rate: {value}").format(value=app_state.tsne_params['learning_rate']))
        tsne_layout.addWidget(lr_label)

        lr_spin = QDoubleSpinBox()
        lr_spin.setRange(10.0, 1000.0)
        lr_spin.setSingleStep(10.0)
        lr_spin.setValue(app_state.tsne_params['learning_rate'])
        lr_spin.valueChanged.connect(lambda v: self._on_tsne_param_change('learning_rate', v, lr_label))
        tsne_layout.addWidget(lr_spin)

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
        pca_layout = QVBoxLayout()

        n_comp_label = QLabel(translate("n_components:"))
        pca_layout.addWidget(n_comp_label)

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
        standardize_check.setChecked(app_state.standardize_data)
        standardize_check.stateChanged.connect(self._on_standardize_change)
        pca_layout.addWidget(standardize_check)

        pca_tools_layout = QHBoxLayout()

        scree_btn = QPushButton(translate("Scree Plot"))
        scree_btn.clicked.connect(self._on_show_scree_plot)
        pca_tools_layout.addWidget(scree_btn)

        loadings_btn = QPushButton(translate("Loadings"))
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
        robust_pca_layout = QVBoxLayout()

        robust_n_comp_label = QLabel(translate("n_components:"))
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
        robust_pca_layout.addWidget(robust_rs_label)

        robust_rs_spin = QSpinBox()
        robust_rs_spin.setRange(0, 9999)
        robust_rs_spin.setValue(app_state.robust_pca_params.get('random_state', 42))
        robust_rs_spin.valueChanged.connect(lambda v: self._on_robust_pca_param_change('random_state', v))
        robust_pca_layout.addWidget(robust_rs_spin)

        rpca_tools_layout = QHBoxLayout()

        rpca_scree_btn = QPushButton(translate("Scree Plot"))
        rpca_scree_btn.clicked.connect(self._on_show_scree_plot)
        rpca_tools_layout.addWidget(rpca_scree_btn)

        rpca_loadings_btn = QPushButton(translate("Loadings"))
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
        ternary_layout = QVBoxLayout()

        info_label = QLabel(translate("Using Standard Ternary Plot.\nData is plotted as relative proportions."))
        info_label.setWordWrap(True)
        ternary_layout.addWidget(info_label)

        self.ternary_auto_zoom_check = QCheckBox(translate("Auto-Zoom to Data"))
        self.ternary_auto_zoom_check.setChecked(getattr(app_state, 'ternary_auto_zoom', False))
        self.ternary_auto_zoom_check.stateChanged.connect(self._on_ternary_zoom_change)
        ternary_layout.addWidget(self.ternary_auto_zoom_check)

        stretch_header = QHBoxLayout()
        stretch_label = QLabel(translate("Stretch Mode"))
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
        self.ternary_stretch_check.setChecked(getattr(app_state, 'ternary_stretch', False))
        self.ternary_stretch_check.stateChanged.connect(self._on_ternary_stretch_change)
        ternary_layout.addWidget(self.ternary_stretch_check)

        self.ternary_group.setLayout(ternary_layout)
        layout.addWidget(self.ternary_group)

        self.v1v2_group = QGroupBox(translate("V1V2 Time Settings"))
        v1v2_layout = QVBoxLayout()

        try:
            from data.geochemistry import engine
            params = engine.get_parameters()
        except Exception:
            params = {}

        t1_val = params.get('T1', 4430e6) / 1e6
        t2_val = params.get('T2', 4570e6) / 1e6

        t1_layout = QHBoxLayout()
        t1_layout.addWidget(QLabel(translate("T1 (Ma) - Model Age")))
        self.v1v2_t1_spin = QDoubleSpinBox()
        self.v1v2_t1_spin.setRange(0.0, 10000.0)
        self.v1v2_t1_spin.setDecimals(3)
        self.v1v2_t1_spin.setValue(t1_val)
        self.v1v2_t1_spin.valueChanged.connect(self._on_v1v2_param_change)
        t1_layout.addWidget(self.v1v2_t1_spin)
        v1v2_layout.addLayout(t1_layout)

        t2_layout = QHBoxLayout()
        t2_layout.addWidget(QLabel(translate("T2 (Ma) - Standard Earth Age")))
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

            row.addStretch()
            geochem_layout.addLayout(row)
            return chk

        self.modeling_show_isochron_check = _add_geochem_toggle(
            "Show Age Isochrons",
            getattr(app_state, 'show_isochrons', True),
            self._on_isochron_change,
            style_key='isochron'
        )

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
        paleo_step_layout.addWidget(QLabel(translate("Paleoisochron Step (Ma):")))
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

        isochron_row = QHBoxLayout()
        calc_isochron_btn = QPushButton(translate("Calculate Isochron Age"))
        calc_isochron_btn.clicked.connect(self._on_calculate_isochron)
        isochron_row.addWidget(calc_isochron_btn)

        isochron_settings_btn = QPushButton(translate("Isochron Settings"))
        isochron_settings_btn.clicked.connect(self._on_isochron_settings)
        isochron_row.addWidget(isochron_settings_btn)

        selected_style = getattr(app_state, 'line_styles', {}).get('selected_isochron', {}) or {}
        selected_color = selected_style.get('color') or '#ef4444'
        isochron_swatch = QLabel()
        isochron_swatch.setFixedSize(16, 16)
        isochron_swatch.setStyleSheet(f"background-color: {selected_color}; border: 1px solid #111827;")
        isochron_swatch.mousePressEvent = lambda event, s=isochron_swatch: self._open_line_style_dialog('selected_isochron', s)
        isochron_row.addWidget(isochron_swatch)
        isochron_row.addStretch()
        geochem_layout.addLayout(isochron_row)

        self.geochem_plot_group.setLayout(geochem_layout)
        layout.addWidget(self.geochem_plot_group)

        self.twod_group = QGroupBox(translate("2D Scatter Parameters"))
        twod_layout = QVBoxLayout()

        twod_grid = QGridLayout()

        x_label = QLabel(translate("X Axis:"))
        twod_grid.addWidget(x_label, 0, 0)

        self.xaxis_combo = QComboBox()
        self.xaxis_combo.setEditable(False)
        self.xaxis_combo.setStyleSheet("QComboBox { combobox-popup: 0; }")
        self.xaxis_combo.setMinimumWidth(150)
        twod_grid.addWidget(self.xaxis_combo, 0, 1)

        y_label = QLabel(translate("Y Axis:"))
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

    def _build_analysis_section(self):
        """构建分析部分"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)

        kde_group = QGroupBox(translate("Kernel Density"))
        kde_layout = QVBoxLayout()

        kde_row = QHBoxLayout()
        self.tools_kde_check = QCheckBox(translate("Show Kernel Density"))
        self.tools_kde_check.setChecked(getattr(app_state, 'show_kde', False))
        self.tools_kde_check.stateChanged.connect(self._on_kde_change)
        kde_row.addWidget(self.tools_kde_check)

        kde_swatch = QLabel()
        kde_swatch.setFixedSize(16, 16)
        kde_swatch.setStyleSheet("background-color: #e2e8f0; border: 1px solid #111827;")
        kde_swatch.setProperty("keepStyle", True)
        kde_swatch.mousePressEvent = lambda event, s=kde_swatch: self._open_kde_style_dialog('kde', s)
        kde_row.addWidget(kde_swatch)
        kde_row.addStretch()
        kde_layout.addLayout(kde_row)

        mkde_row = QHBoxLayout()
        self.tools_marginal_kde_check = QCheckBox(translate("Show Marginal KDE"))
        self.tools_marginal_kde_check.setChecked(getattr(app_state, 'show_marginal_kde', False))
        self.tools_marginal_kde_check.stateChanged.connect(self._on_marginal_kde_change)
        mkde_row.addWidget(self.tools_marginal_kde_check)

        mkde_swatch = QLabel()
        mkde_swatch.setFixedSize(16, 16)
        mkde_swatch.setStyleSheet("background-color: #e2e8f0; border: 1px solid #111827;")
        mkde_swatch.setProperty("keepStyle", True)
        mkde_swatch.mousePressEvent = lambda event, s=mkde_swatch: self._open_kde_style_dialog('marginal_kde', s)
        mkde_row.addWidget(mkde_swatch)
        mkde_row.addStretch()
        kde_layout.addLayout(mkde_row)

        kde_group.setLayout(kde_layout)
        layout.addWidget(kde_group)

        equation_group = QGroupBox(translate("Equation Overlays"))
        equation_layout = QVBoxLayout()

        equation_hint = QLabel(translate("Manage equations and visibility."))
        equation_hint.setWordWrap(True)
        equation_layout.addWidget(equation_hint)

        add_eq_btn = QPushButton(translate("Add Equation"))
        add_eq_btn.clicked.connect(self._open_add_equation_dialog)
        equation_layout.addWidget(add_eq_btn)

        equation_group.setLayout(equation_layout)
        layout.addWidget(equation_group)

        selection_group = QGroupBox(translate("Selection Tools"))
        selection_layout = QVBoxLayout()

        self.selection_button = QPushButton(translate("Enable Selection"))
        self.selection_button.setCheckable(True)
        self.selection_button.setFixedWidth(200)
        self.selection_button.clicked.connect(self._on_toggle_selection)
        selection_layout.addWidget(self.selection_button, 0, Qt.AlignHCenter)

        self.lasso_selection_button = QPushButton(translate("Custom Shape"))
        self.lasso_selection_button.setCheckable(True)
        self.lasso_selection_button.setFixedWidth(200)
        self.lasso_selection_button.clicked.connect(self._on_toggle_lasso_selection)
        selection_layout.addWidget(self.lasso_selection_button, 0, Qt.AlignHCenter)

        self.selection_status_label = QLabel(translate("Selected Samples: {count}").format(count=0))
        selection_layout.addWidget(self.selection_status_label)

        selection_group.setLayout(selection_layout)
        layout.addWidget(selection_group)

        analysis_group = QGroupBox(translate("Data Analysis"))
        analysis_layout = QVBoxLayout()

        corr_btn = QPushButton(translate("Correlation Heatmap"))
        corr_btn.setFixedWidth(200)
        corr_btn.clicked.connect(self._on_show_correlation_heatmap)
        analysis_layout.addWidget(corr_btn, 0, Qt.AlignHCenter)

        axis_corr_btn = QPushButton(translate("Show Axis Corr."))
        axis_corr_btn.setFixedWidth(200)
        axis_corr_btn.clicked.connect(self._on_show_axis_correlation)
        analysis_layout.addWidget(axis_corr_btn, 0, Qt.AlignHCenter)

        shepard_btn = QPushButton(translate("Show Shepard Plot"))
        shepard_btn.setFixedWidth(200)
        shepard_btn.clicked.connect(self._on_show_shepard_diagram)
        analysis_layout.addWidget(shepard_btn, 0, Qt.AlignHCenter)

        analysis_group.setLayout(analysis_layout)
        layout.addWidget(analysis_group)

        subset_group = QGroupBox(translate("Subset Analysis"))
        subset_layout = QVBoxLayout()

        analyze_btn = QPushButton(translate("Analyze Subset"))
        analyze_btn.setFixedWidth(200)
        analyze_btn.clicked.connect(self._on_analyze_subset)
        subset_layout.addWidget(analyze_btn, 0, Qt.AlignHCenter)

        reset_btn = QPushButton(translate("Reset Data"))
        reset_btn.setFixedWidth(200)
        reset_btn.clicked.connect(self._on_reset_data)
        subset_layout.addWidget(reset_btn, 0, Qt.AlignHCenter)

        subset_group.setLayout(subset_layout)
        layout.addWidget(subset_group)

        mixing_group = QGroupBox(translate("Mixing Groups"))
        mixing_layout = QVBoxLayout()

        group_name_layout = QHBoxLayout()
        group_name_layout.addWidget(QLabel(translate("Group Name:")))
        self.mixing_group_name_edit = QLineEdit()
        self.mixing_group_name_edit.setPlaceholderText(translate("Enter group name"))
        group_name_layout.addWidget(self.mixing_group_name_edit)
        mixing_layout.addLayout(group_name_layout)

        mixing_btn_layout = QHBoxLayout()

        endmember_btn = QPushButton(translate("Set as Endmember"))
        endmember_btn.setFixedWidth(170)
        endmember_btn.clicked.connect(self._on_set_endmember)
        mixing_btn_layout.addWidget(endmember_btn)

        mixture_btn = QPushButton(translate("Set as Mixture"))
        mixture_btn.setFixedWidth(170)
        mixture_btn.clicked.connect(self._on_set_mixture)
        mixing_btn_layout.addWidget(mixture_btn)

        mixing_layout.addLayout(mixing_btn_layout)

        self.mixing_status_label = QLabel(translate("No mixing groups defined"))
        self.mixing_status_label.setWordWrap(True)
        mixing_layout.addWidget(self.mixing_status_label)

        mixing_action_layout = QHBoxLayout()

        clear_mixing_btn = QPushButton(translate("Clear Mixing Groups"))
        clear_mixing_btn.setFixedWidth(170)
        clear_mixing_btn.clicked.connect(self._on_clear_mixing_groups)
        mixing_action_layout.addWidget(clear_mixing_btn)

        compute_mixing_btn = QPushButton(translate("Compute Mixing"))
        compute_mixing_btn.setFixedWidth(170)
        compute_mixing_btn.clicked.connect(self._on_compute_mixing)
        mixing_action_layout.addWidget(compute_mixing_btn)

        mixing_layout.addLayout(mixing_action_layout)

        mixing_group.setLayout(mixing_layout)
        layout.addWidget(mixing_group)

        confidence_group = QGroupBox(translate("Confidence Ellipse"))
        confidence_layout = QVBoxLayout()

        self.ellipse_selection_button = QPushButton(translate("Draw Ellipse"))
        self.ellipse_selection_button.setCheckable(True)
        self.ellipse_selection_button.setFixedWidth(200)
        self.ellipse_selection_button.clicked.connect(self._on_toggle_ellipse_selection)
        confidence_layout.addWidget(self.ellipse_selection_button, 0, Qt.AlignHCenter)

        self.confidence_68_radio = QRadioButton(translate("68% (1σ)"))
        self.confidence_95_radio = QRadioButton(translate("95% (2σ)"))
        self.confidence_99_radio = QRadioButton(translate("99% (3σ)"))

        current_level = getattr(app_state, 'confidence_level', 0.95)
        if abs(current_level - 0.68) < 0.01:
            self.confidence_68_radio.setChecked(True)
        elif abs(current_level - 0.99) < 0.01:
            self.confidence_99_radio.setChecked(True)
        else:
            self.confidence_95_radio.setChecked(True)

        self.confidence_68_radio.toggled.connect(lambda: self._on_confidence_change(0.68))
        self.confidence_95_radio.toggled.connect(lambda: self._on_confidence_change(0.95))
        self.confidence_99_radio.toggled.connect(lambda: self._on_confidence_change(0.99))

        confidence_layout.addWidget(self.confidence_68_radio)
        confidence_layout.addWidget(self.confidence_95_radio)
        confidence_layout.addWidget(self.confidence_99_radio)

        confidence_group.setLayout(confidence_layout)
        layout.addWidget(confidence_group)

        layout.addStretch()
        return widget

    def _build_export_section(self):
        """构建导出部分"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)

        export_group = QGroupBox(translate("Export"))
        export_layout = QVBoxLayout()

        self.export_csv_button = QPushButton(translate("Export CSV"))
        self.export_csv_button.setFixedWidth(200)
        self.export_csv_button.clicked.connect(self._on_export_csv)
        export_layout.addWidget(self.export_csv_button, 0, Qt.AlignHCenter)

        self.export_excel_button = QPushButton(translate("Export Excel"))
        self.export_excel_button.setFixedWidth(200)
        self.export_excel_button.clicked.connect(self._on_export_excel)
        export_layout.addWidget(self.export_excel_button, 0, Qt.AlignHCenter)

        self.export_selected_button = QPushButton(translate("Export Selected"))
        self.export_selected_button.setFixedWidth(200)
        self.export_selected_button.clicked.connect(self._on_export_clicked)
        export_layout.addWidget(self.export_selected_button, 0, Qt.AlignHCenter)

        export_group.setLayout(export_layout)
        layout.addWidget(export_group)

        layout.addStretch()
        return widget

    def _build_display_section(self):
        """构建显示部分"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)

        # Interface Theme
        theme_group = QGroupBox(translate("Interface Theme"))
        theme_layout = QVBoxLayout()
        theme_row = QHBoxLayout()
        theme_row.addWidget(QLabel(translate("UI Theme:")))
        self.ui_theme_combo = QComboBox()
        try:
            from visualization.style_manager import style_manager_instance
            theme_names = style_manager_instance.get_ui_theme_names()
        except Exception:
            theme_names = ["Modern Light", "Modern Dark"]
        self.ui_theme_combo.addItems(theme_names)
        current_theme = getattr(app_state, 'ui_theme', 'Modern Light')
        if current_theme in theme_names:
            self.ui_theme_combo.setCurrentText(current_theme)
        self.ui_theme_combo.currentTextChanged.connect(self._on_ui_theme_change)
        theme_row.addWidget(self.ui_theme_combo)
        theme_layout.addLayout(theme_row)
        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)

        # Saved Plot Settings
        saved_group = QGroupBox(translate("Saved Plot Settings"))
        saved_layout = QVBoxLayout()
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel(translate("Theme Name:")))
        self.theme_name_edit = QLineEdit()
        name_row.addWidget(self.theme_name_edit)
        save_btn = QPushButton(translate("Save"))
        save_btn.clicked.connect(self._save_theme)
        name_row.addWidget(save_btn)
        saved_layout.addLayout(name_row)

        load_row = QHBoxLayout()
        load_row.addWidget(QLabel(translate("Load Theme:")))
        self.theme_load_combo = QComboBox()
        self.theme_load_combo.currentTextChanged.connect(self._load_theme)
        load_row.addWidget(self.theme_load_combo)
        delete_btn = QPushButton(translate("Delete"))
        delete_btn.clicked.connect(self._delete_theme)
        load_row.addWidget(delete_btn)
        saved_layout.addLayout(load_row)
        saved_group.setLayout(saved_layout)
        layout.addWidget(saved_group)
        self._refresh_theme_list()

        # General Settings
        general_group = QGroupBox(translate("General Settings"))
        general_layout = QVBoxLayout()

        palette_row = QHBoxLayout()
        palette_row.addWidget(QLabel(translate("Palette")))
        self.color_combo = QComboBox()
        try:
            from visualization.style_manager import style_manager_instance
            palette_names = style_manager_instance.get_palette_names()
        except Exception:
            palette_names = ['vibrant', 'bright', 'muted']
        self.color_combo.addItems(palette_names)
        self.color_combo.setCurrentText(getattr(app_state, 'color_scheme', 'vibrant'))
        self.color_combo.currentTextChanged.connect(self._on_style_change)
        palette_row.addWidget(self.color_combo)
        general_layout.addLayout(palette_row)
        general_group.setLayout(general_layout)
        layout.addWidget(general_group)

        # Font Settings
        font_group = QGroupBox(translate("Font Settings"))
        font_layout = QVBoxLayout()
        try:
            from visualization.style_manager import style_manager_instance
            all_fonts = ['<Default>'] + sorted(style_manager_instance.get_available_fonts())
        except Exception:
            all_fonts = ['<Default>']

        primary_row = QHBoxLayout()
        primary_row.addWidget(QLabel(translate("Primary Font (English)")))
        self.primary_font_combo = QComboBox()
        self.primary_font_combo.addItems(all_fonts)
        current_primary = getattr(app_state, 'custom_primary_font', '') or '<Default>'
        self.primary_font_combo.setCurrentText(current_primary)
        self.primary_font_combo.currentTextChanged.connect(self._on_style_change)
        primary_row.addWidget(self.primary_font_combo)
        font_layout.addLayout(primary_row)

        cjk_row = QHBoxLayout()
        cjk_row.addWidget(QLabel(translate("CJK Font (Chinese)")))
        self.cjk_font_combo = QComboBox()
        self.cjk_font_combo.addItems(all_fonts)
        current_cjk = getattr(app_state, 'custom_cjk_font', '') or '<Default>'
        self.cjk_font_combo.setCurrentText(current_cjk)
        self.cjk_font_combo.currentTextChanged.connect(self._on_style_change)
        cjk_row.addWidget(self.cjk_font_combo)
        font_layout.addLayout(cjk_row)

        size_grid = QGridLayout()
        self.font_size_spins = {}
        size_defs = [
            ('title', "Title", 14, 0),
            ('label', "Label", 12, 1),
            ('tick', "Tick", 10, 2),
            ('legend', "Legend", 10, 3),
        ]
        for key, label_key, default, row in size_defs:
            size_grid.addWidget(QLabel(translate(label_key)), row, 0)
            spin = QSpinBox()
            spin.setRange(6, 36)
            spin.setValue(getattr(app_state, 'plot_font_sizes', {}).get(key, default))
            spin.valueChanged.connect(self._on_style_change)
            size_grid.addWidget(spin, row, 1)
            self.font_size_spins[key] = spin
        font_layout.addLayout(size_grid)

        self.show_title_check = QCheckBox(translate("Show Plot Title"))
        self.show_title_check.setChecked(getattr(app_state, 'show_plot_title', False))
        self.show_title_check.stateChanged.connect(self._on_style_change)
        font_layout.addWidget(self.show_title_check)

        font_group.setLayout(font_layout)
        layout.addWidget(font_group)

        # Marker Settings
        marker_group = QGroupBox(translate("Marker Settings"))
        marker_layout = QVBoxLayout()
        marker_size_row = QHBoxLayout()
        marker_size_row.addWidget(QLabel(translate("Size")))
        self.marker_size_spin = QSpinBox()
        self.marker_size_spin.setRange(10, 500)
        self.marker_size_spin.setValue(int(getattr(app_state, 'plot_marker_size', 60)))
        self.marker_size_spin.valueChanged.connect(self._on_style_change)
        marker_size_row.addWidget(self.marker_size_spin)
        marker_layout.addLayout(marker_size_row)

        marker_alpha_row = QHBoxLayout()
        marker_alpha_row.addWidget(QLabel(translate("Opacity")))
        self.marker_alpha_spin = QDoubleSpinBox()
        self.marker_alpha_spin.setRange(0.1, 1.0)
        self.marker_alpha_spin.setSingleStep(0.05)
        self.marker_alpha_spin.setValue(float(getattr(app_state, 'plot_marker_alpha', 0.8)))
        self.marker_alpha_spin.valueChanged.connect(self._on_style_change)
        marker_alpha_row.addWidget(self.marker_alpha_spin)
        marker_layout.addLayout(marker_alpha_row)
        marker_group.setLayout(marker_layout)
        layout.addWidget(marker_group)

        # Axes & Lines
        axes_group = QGroupBox(translate("Axes & Lines"))
        axes_layout = QVBoxLayout()
        auto_layout_btn = QPushButton(translate("Auto Layout"))
        auto_layout_btn.clicked.connect(self._apply_auto_layout)
        axes_layout.addWidget(auto_layout_btn)

        def add_row(grid, label_key, widget, row_idx):
            grid.addWidget(QLabel(translate(label_key)), row_idx, 0)
            grid.addWidget(widget, row_idx, 1)
            return row_idx + 1

        def make_group(title_key):
            group = QGroupBox(translate(title_key))
            grid = QGridLayout()
            grid.setColumnStretch(0, 1)
            grid.setColumnStretch(1, 2)
            group.setLayout(grid)
            axes_layout.addWidget(group)
            return grid

        figure_grid = make_group("Figure")
        row = 0
        self.figure_dpi_spin = QSpinBox()
        self.figure_dpi_spin.setRange(50, 600)
        self.figure_dpi_spin.setValue(int(getattr(app_state, 'plot_dpi', 130)))
        self.figure_dpi_spin.valueChanged.connect(self._on_style_change)
        row = add_row(figure_grid, "Figure DPI", self.figure_dpi_spin, row)

        self.figure_bg_edit = QLineEdit(getattr(app_state, 'plot_facecolor', '#ffffff'))
        self.figure_bg_edit.editingFinished.connect(self._on_style_change)
        row = add_row(figure_grid, "Figure Background", self.figure_bg_edit, row)

        self.axes_bg_edit = QLineEdit(getattr(app_state, 'axes_facecolor', '#ffffff'))
        self.axes_bg_edit.editingFinished.connect(self._on_style_change)
        row = add_row(figure_grid, "Axes Background", self.axes_bg_edit, row)

        grid_grid = make_group("Grid")
        row = 0
        self.grid_check = QCheckBox(translate("Show Grid"))
        self.grid_check.setChecked(getattr(app_state, 'plot_style_grid', False))
        self.grid_check.stateChanged.connect(self._on_style_change)
        row = add_row(grid_grid, "Show Grid", self.grid_check, row)

        self.grid_color_edit = QLineEdit(getattr(app_state, 'grid_color', '#e2e8f0'))
        self.grid_color_edit.editingFinished.connect(self._on_style_change)
        row = add_row(grid_grid, "Grid Color", self.grid_color_edit, row)

        self.grid_width_spin = QDoubleSpinBox()
        self.grid_width_spin.setRange(0.1, 3.0)
        self.grid_width_spin.setSingleStep(0.1)
        self.grid_width_spin.setValue(float(getattr(app_state, 'grid_linewidth', 0.6)))
        self.grid_width_spin.valueChanged.connect(self._on_style_change)
        row = add_row(grid_grid, "Grid Linewidth", self.grid_width_spin, row)

        self.grid_alpha_spin = QDoubleSpinBox()
        self.grid_alpha_spin.setRange(0.0, 1.0)
        self.grid_alpha_spin.setSingleStep(0.05)
        self.grid_alpha_spin.setValue(float(getattr(app_state, 'grid_alpha', 0.7)))
        self.grid_alpha_spin.valueChanged.connect(self._on_style_change)
        row = add_row(grid_grid, "Grid Alpha", self.grid_alpha_spin, row)

        self.grid_style_combo = QComboBox()
        self.grid_style_combo.addItems(['-', '--', '-.', ':'])
        self.grid_style_combo.setCurrentText(getattr(app_state, 'grid_linestyle', '--'))
        self.grid_style_combo.currentTextChanged.connect(self._on_style_change)
        row = add_row(grid_grid, "Grid Style", self.grid_style_combo, row)

        self.minor_grid_check = QCheckBox()
        self.minor_grid_check.setChecked(getattr(app_state, 'minor_grid', False))
        self.minor_grid_check.stateChanged.connect(self._on_style_change)
        row = add_row(grid_grid, "Minor Grid", self.minor_grid_check, row)

        self.minor_grid_color_edit = QLineEdit(getattr(app_state, 'minor_grid_color', '#e2e8f0'))
        self.minor_grid_color_edit.editingFinished.connect(self._on_style_change)
        row = add_row(grid_grid, "Minor Grid Color", self.minor_grid_color_edit, row)

        self.minor_grid_width_spin = QDoubleSpinBox()
        self.minor_grid_width_spin.setRange(0.1, 2.0)
        self.minor_grid_width_spin.setSingleStep(0.1)
        self.minor_grid_width_spin.setValue(float(getattr(app_state, 'minor_grid_linewidth', 0.4)))
        self.minor_grid_width_spin.valueChanged.connect(self._on_style_change)
        row = add_row(grid_grid, "Minor Grid Linewidth", self.minor_grid_width_spin, row)

        self.minor_grid_alpha_spin = QDoubleSpinBox()
        self.minor_grid_alpha_spin.setRange(0.0, 1.0)
        self.minor_grid_alpha_spin.setSingleStep(0.05)
        self.minor_grid_alpha_spin.setValue(float(getattr(app_state, 'minor_grid_alpha', 0.4)))
        self.minor_grid_alpha_spin.valueChanged.connect(self._on_style_change)
        row = add_row(grid_grid, "Minor Grid Alpha", self.minor_grid_alpha_spin, row)

        self.minor_grid_style_combo = QComboBox()
        self.minor_grid_style_combo.addItems(['-', '--', '-.', ':'])
        self.minor_grid_style_combo.setCurrentText(getattr(app_state, 'minor_grid_linestyle', ':'))
        self.minor_grid_style_combo.currentTextChanged.connect(self._on_style_change)
        row = add_row(grid_grid, "Minor Grid Style", self.minor_grid_style_combo, row)

        tick_grid = make_group("Ticks")
        row = 0
        self.tick_dir_combo = QComboBox()
        self.tick_dir_combo.addItems(['out', 'in', 'inout'])
        self.tick_dir_combo.setCurrentText(getattr(app_state, 'tick_direction', 'out'))
        self.tick_dir_combo.currentTextChanged.connect(self._on_style_change)
        row = add_row(tick_grid, "Tick Direction", self.tick_dir_combo, row)

        self.tick_color_edit = QLineEdit(getattr(app_state, 'tick_color', '#1f2937'))
        self.tick_color_edit.editingFinished.connect(self._on_style_change)
        row = add_row(tick_grid, "Tick Color", self.tick_color_edit, row)

        self.tick_length_spin = QDoubleSpinBox()
        self.tick_length_spin.setRange(0.0, 12.0)
        self.tick_length_spin.setSingleStep(0.5)
        self.tick_length_spin.setValue(float(getattr(app_state, 'tick_length', 4.0)))
        self.tick_length_spin.valueChanged.connect(self._on_style_change)
        row = add_row(tick_grid, "Tick Length", self.tick_length_spin, row)

        self.tick_width_spin = QDoubleSpinBox()
        self.tick_width_spin.setRange(0.2, 3.0)
        self.tick_width_spin.setSingleStep(0.1)
        self.tick_width_spin.setValue(float(getattr(app_state, 'tick_width', 0.8)))
        self.tick_width_spin.valueChanged.connect(self._on_style_change)
        row = add_row(tick_grid, "Tick Width", self.tick_width_spin, row)

        self.minor_ticks_check = QCheckBox()
        self.minor_ticks_check.setChecked(getattr(app_state, 'minor_ticks', False))
        self.minor_ticks_check.stateChanged.connect(self._on_style_change)
        row = add_row(tick_grid, "Minor Ticks", self.minor_ticks_check, row)

        self.minor_tick_length_spin = QDoubleSpinBox()
        self.minor_tick_length_spin.setRange(0.0, 8.0)
        self.minor_tick_length_spin.setSingleStep(0.5)
        self.minor_tick_length_spin.setValue(float(getattr(app_state, 'minor_tick_length', 2.5)))
        self.minor_tick_length_spin.valueChanged.connect(self._on_style_change)
        row = add_row(tick_grid, "Minor Tick Length", self.minor_tick_length_spin, row)

        self.minor_tick_width_spin = QDoubleSpinBox()
        self.minor_tick_width_spin.setRange(0.2, 2.0)
        self.minor_tick_width_spin.setSingleStep(0.1)
        self.minor_tick_width_spin.setValue(float(getattr(app_state, 'minor_tick_width', 0.6)))
        self.minor_tick_width_spin.valueChanged.connect(self._on_style_change)
        row = add_row(tick_grid, "Minor Tick Width", self.minor_tick_width_spin, row)

        spine_grid = make_group("Spines")
        row = 0
        self.axis_linewidth_spin = QDoubleSpinBox()
        self.axis_linewidth_spin.setRange(0.2, 3.0)
        self.axis_linewidth_spin.setSingleStep(0.1)
        self.axis_linewidth_spin.setValue(float(getattr(app_state, 'axis_linewidth', 1.0)))
        self.axis_linewidth_spin.valueChanged.connect(self._on_style_change)
        row = add_row(spine_grid, "Axis Line Width", self.axis_linewidth_spin, row)

        self.axis_line_color_edit = QLineEdit(getattr(app_state, 'axis_line_color', '#1f2937'))
        self.axis_line_color_edit.editingFinished.connect(self._on_style_change)
        row = add_row(spine_grid, "Axis Line Color", self.axis_line_color_edit, row)

        self.show_top_spine_check = QCheckBox()
        self.show_top_spine_check.setChecked(getattr(app_state, 'show_top_spine', True))
        self.show_top_spine_check.stateChanged.connect(self._on_style_change)
        row = add_row(spine_grid, "Show Top Spine", self.show_top_spine_check, row)

        self.show_right_spine_check = QCheckBox()
        self.show_right_spine_check.setChecked(getattr(app_state, 'show_right_spine', True))
        self.show_right_spine_check.stateChanged.connect(self._on_style_change)
        row = add_row(spine_grid, "Show Right Spine", self.show_right_spine_check, row)

        text_grid = make_group("Text")
        row = 0
        self.label_color_edit = QLineEdit(getattr(app_state, 'label_color', '#1f2937'))
        self.label_color_edit.editingFinished.connect(self._on_style_change)
        row = add_row(text_grid, "Label Color", self.label_color_edit, row)

        self.label_weight_combo = QComboBox()
        self.label_weight_combo.addItems(['normal', 'bold'])
        self.label_weight_combo.setCurrentText(getattr(app_state, 'label_weight', 'normal'))
        self.label_weight_combo.currentTextChanged.connect(self._on_style_change)
        row = add_row(text_grid, "Label Weight", self.label_weight_combo, row)

        self.label_pad_spin = QDoubleSpinBox()
        self.label_pad_spin.setRange(0.0, 30.0)
        self.label_pad_spin.setSingleStep(1.0)
        self.label_pad_spin.setValue(float(getattr(app_state, 'label_pad', 6.0)))
        self.label_pad_spin.valueChanged.connect(self._on_style_change)
        row = add_row(text_grid, "Label Pad", self.label_pad_spin, row)

        self.title_color_edit = QLineEdit(getattr(app_state, 'title_color', '#111827'))
        self.title_color_edit.editingFinished.connect(self._on_style_change)
        row = add_row(text_grid, "Title Color", self.title_color_edit, row)

        self.title_weight_combo = QComboBox()
        self.title_weight_combo.addItems(['normal', 'bold'])
        self.title_weight_combo.setCurrentText(getattr(app_state, 'title_weight', 'bold'))
        self.title_weight_combo.currentTextChanged.connect(self._on_style_change)
        row = add_row(text_grid, "Title Weight", self.title_weight_combo, row)

        self.title_pad_spin = QDoubleSpinBox()
        self.title_pad_spin.setRange(0.0, 40.0)
        self.title_pad_spin.setSingleStep(1.0)
        self.title_pad_spin.setValue(float(getattr(app_state, 'title_pad', 20.0)))
        self.title_pad_spin.valueChanged.connect(self._on_style_change)
        row = add_row(text_grid, "Title Pad", self.title_pad_spin, row)

        axes_group.setLayout(axes_layout)
        layout.addWidget(axes_group)

        layout.addStretch()
        return widget

    def _build_legend_section(self):
        """构建图例部分"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)

        # 刷新按钮
        refresh_btn = QPushButton(translate("Refresh Legend"))
        refresh_btn.clicked.connect(self._update_group_list)
        layout.addWidget(refresh_btn)

        # 分组可见性管理
        group_visibility_group = QGroupBox(translate("Group Visibility"))
        group_layout = QVBoxLayout()

        # 分组列表 - 增强版：包含颜色和形状
        self.group_list = QListWidget()
        self.group_list.setMaximumHeight(200)
        self.group_list.itemChanged.connect(self._on_group_visibility_change)
        group_layout.addWidget(self.group_list)

        # 全选/全不选按钮
        btn_layout = QHBoxLayout()
        show_all_btn = QPushButton(translate("Show All"))
        show_all_btn.clicked.connect(self._show_all_groups)
        btn_layout.addWidget(show_all_btn)

        hide_all_btn = QPushButton(translate("Hide All"))
        hide_all_btn.clicked.connect(self._hide_all_groups)
        btn_layout.addWidget(hide_all_btn)

        group_layout.addLayout(btn_layout)
        group_visibility_group.setLayout(group_layout)
        layout.addWidget(group_visibility_group)

        # 图例位置
        position_group = QGroupBox(translate("Legend Position"))
        position_layout = QVBoxLayout()

        position_grid = QGridLayout()
        position_grid.setHorizontalSpacing(6)
        position_grid.setVerticalSpacing(6)

        outer_grid = QGridLayout()
        outer_grid.setHorizontalSpacing(6)
        outer_grid.setVerticalSpacing(6)

        self.legend_position_buttons = {}
        self.legend_position_group = QButtonGroup(self)
        self.legend_position_group.setExclusive(True)

        grid_positions = [
            (0, 0, 'upper left', 'NW'),
            (0, 1, 'upper center', 'N'),
            (0, 2, 'upper right', 'NE'),
            (1, 0, 'center left', 'W'),
            (1, 1, 'center', 'C'),
            (1, 2, 'center right', 'E'),
            (2, 0, 'lower left', 'SW'),
            (2, 1, 'lower center', 'S'),
            (2, 2, 'lower right', 'SE'),
        ]

        for row, col, value, label in grid_positions:
            btn = QToolButton()
            btn.setText(label)
            btn.setCheckable(True)
            btn.setFixedSize(40, 32)
            btn.clicked.connect(lambda checked=False, loc=value: self._on_legend_position_change(loc))
            self.legend_position_group.addButton(btn)
            self.legend_position_buttons[value] = btn
            position_grid.addWidget(btn, row, col)

        outside_top_btn = QToolButton()
        outside_top_btn.setText('OUT T')
        outside_top_btn.setCheckable(True)
        outside_top_btn.setFixedSize(56, 32)
        outside_top_btn.clicked.connect(lambda checked=False: self._on_legend_position_change('outside_top'))
        self.legend_position_group.addButton(outside_top_btn)
        self.legend_position_buttons['outside_top'] = outside_top_btn

        outside_left_btn = QToolButton()
        outside_left_btn.setText('OUT L')
        outside_left_btn.setCheckable(True)
        outside_left_btn.setFixedSize(56, 32)
        outside_left_btn.clicked.connect(lambda checked=False: self._on_legend_position_change('outside_left'))
        self.legend_position_group.addButton(outside_left_btn)
        self.legend_position_buttons['outside_left'] = outside_left_btn

        outside_right_btn = QToolButton()
        outside_right_btn.setText('OUT R')
        outside_right_btn.setCheckable(True)
        outside_right_btn.setFixedSize(56, 32)
        outside_right_btn.clicked.connect(lambda checked=False: self._on_legend_position_change('outside_right'))
        self.legend_position_group.addButton(outside_right_btn)
        self.legend_position_buttons['outside_right'] = outside_right_btn

        outside_bottom_btn = QToolButton()
        outside_bottom_btn.setText('OUT B')
        outside_bottom_btn.setCheckable(True)
        outside_bottom_btn.setFixedSize(56, 32)
        outside_bottom_btn.clicked.connect(lambda checked=False: self._on_legend_position_change('outside_bottom'))
        self.legend_position_group.addButton(outside_bottom_btn)
        self.legend_position_buttons['outside_bottom'] = outside_bottom_btn

        outer_grid.addWidget(outside_top_btn, 0, 1, Qt.AlignHCenter)
        outer_grid.addWidget(outside_left_btn, 1, 0, Qt.AlignHCenter)
        outer_grid.addLayout(position_grid, 1, 1)
        outer_grid.addWidget(outside_right_btn, 1, 2, Qt.AlignHCenter)
        outer_grid.addWidget(outside_bottom_btn, 2, 1, Qt.AlignHCenter)

        position_layout.addLayout(outer_grid)

        initial_location = getattr(app_state, 'legend_location', '') or getattr(app_state, 'legend_position', 'outside_left')
        if initial_location == 'outside right':
            initial_location = 'outside_right'
        if initial_location == 'outside left':
            initial_location = 'outside_left'
        if initial_location == 'outside top':
            initial_location = 'outside_top'
        if initial_location == 'outside bottom':
            initial_location = 'outside_bottom'
        if initial_location not in self.legend_position_buttons:
            initial_location = 'outside_left'
        self._set_legend_position_button(initial_location)

        position_group.setLayout(position_layout)
        layout.addWidget(position_group)

        # 图例列数
        columns_group = QGroupBox(translate("Legend Columns"))
        columns_layout = QVBoxLayout()

        self.legend_columns_spin = QSpinBox()
        self.legend_columns_spin.setRange(1, 5)
        self.legend_columns_spin.setValue(app_state.legend_columns)
        self.legend_columns_spin.valueChanged.connect(self._on_legend_columns_change)
        columns_layout.addWidget(self.legend_columns_spin)

        columns_group.setLayout(columns_layout)
        layout.addWidget(columns_group)

        # 更新分组列表
        self._update_group_list()

        layout.addStretch()
        return widget

    def _ensure_marker_shape_map(self):
        """确保标记形状映射存在"""
        if not hasattr(self, '_marker_shape_map'):
            self._marker_shape_map = {
                translate("Circle (o)"): 'o',
                translate("Square (s)"): 's',
                translate("Triangle Up (^)"): '^',
                translate("Triangle Down (v)"): 'v',
                translate("Diamond (D)"): 'D',
                translate("Pentagon (P)"): 'P',
                translate("Star (*)"): '*',
                translate("Plus (+)"): '+',
                translate("Cross (x)"): 'x',
                translate("X (X)"): 'X',
            }

    def _marker_label_for_value(self, marker_value):
        """获取标记的显示标签"""
        self._ensure_marker_shape_map()
        for label, value in self._marker_shape_map.items():
            if value == marker_value:
                return label
        return next(iter(self._marker_shape_map.keys()))

    def _set_legend_position_button(self, location):
        """Sync legend position button state."""
        buttons = getattr(self, 'legend_position_buttons', {})
        if not buttons:
            return
        if location == 'outside right':
            location = 'outside_right'
        target = buttons.get(location)
        for value, btn in buttons.items():
            btn.blockSignals(True)
            btn.setChecked(btn is target)
            btn.blockSignals(False)

    def _pick_color(self, group, swatch):
        """打开颜色选择器"""
        from PyQt5.QtWidgets import QColorDialog
        from PyQt5.QtGui import QColor

        current_color = app_state.current_palette.get(group, '#cccccc')
        color = QColorDialog.getColor(QColor(current_color), self, f"Color for {group}")

        if color.isValid():
            new_hex = color.name()
            app_state.current_palette[group] = new_hex

            # 更新颜色块
            self._update_marker_swatch(group, swatch)

            # 如果有对应的scatter，更新颜色
            if hasattr(app_state, 'group_to_scatter') and group in app_state.group_to_scatter:
                sc = app_state.group_to_scatter[group]
                try:
                    sc.set_color(new_hex)
                    sc.set_edgecolor("#1e293b")
                    if app_state.fig:
                        app_state.fig.canvas.draw_idle()
                except Exception as e:
                    print(f"[WARN] Failed to update color for {group}: {e}")

    def _apply_marker_shape(self, group, shape_combo, swatch):
        """应用标记形状"""
        self._ensure_marker_shape_map()
        label = shape_combo.currentText()
        marker = self._marker_shape_map.get(label, getattr(app_state, 'plot_marker_shape', 'o'))
        app_state.group_marker_map[group] = marker

        # 重新绘制颜色块（保持颜色但更新形状）
        self._update_marker_swatch(group, swatch)

        self._on_change()

    def _update_marker_swatch(self, group, swatch):
        """Update the legend swatch to reflect marker shape and color."""
        color = app_state.current_palette.get(group, '#cccccc')
        marker = app_state.group_marker_map.get(group, getattr(app_state, 'plot_marker_shape', 'o'))
        icon = self._build_marker_icon(color, marker)
        swatch.setIcon(icon)
        swatch.setIconSize(QSize(16, 16))
        swatch.setStyleSheet("border: 1px solid #111827; border-radius: 3px; background: transparent;")

    def _build_marker_icon(self, color, marker, size=16):
        """Render a small icon for the marker preview."""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)
        pen = QPen(QColor('#111827'))
        pen.setWidthF(1.0)
        painter.setPen(pen)

        brush = QBrush(QColor(color))
        filled_markers = {'o', 's', '^', 'v', 'D', 'P', '*'}
        painter.setBrush(brush if marker in filled_markers else Qt.NoBrush)

        cx = size / 2.0
        cy = size / 2.0
        r = size * 0.35

        if marker == 'o':
            painter.drawEllipse(QPointF(cx, cy), r, r)
        elif marker == 's':
            painter.drawRect(QRectF(cx - r, cy - r, r * 2, r * 2))
        elif marker == '^':
            points = [QPointF(cx, cy - r), QPointF(cx - r, cy + r), QPointF(cx + r, cy + r)]
            painter.drawPolygon(QPolygonF(points))
        elif marker == 'v':
            points = [QPointF(cx - r, cy - r), QPointF(cx + r, cy - r), QPointF(cx, cy + r)]
            painter.drawPolygon(QPolygonF(points))
        elif marker == 'D':
            points = [QPointF(cx, cy - r), QPointF(cx + r, cy), QPointF(cx, cy + r), QPointF(cx - r, cy)]
            painter.drawPolygon(QPolygonF(points))
        elif marker == 'P':
            points = []
            for i in range(5):
                angle = (math.pi / 2.0) + (i * 2.0 * math.pi / 5.0)
                points.append(QPointF(cx + r * math.cos(angle), cy - r * math.sin(angle)))
            painter.drawPolygon(QPolygonF(points))
        elif marker == '*':
            points = []
            outer = r
            inner = r * 0.5
            for i in range(10):
                angle = (math.pi / 2.0) + (i * math.pi / 5.0)
                radius = outer if i % 2 == 0 else inner
                points.append(QPointF(cx + radius * math.cos(angle), cy - radius * math.sin(angle)))
            painter.drawPolygon(QPolygonF(points))
        elif marker in {'+', 'x', 'X'}:
            if marker == '+':
                painter.drawLine(QPointF(cx - r, cy), QPointF(cx + r, cy))
                painter.drawLine(QPointF(cx, cy - r), QPointF(cx, cy + r))
            else:
                painter.drawLine(QPointF(cx - r, cy - r), QPointF(cx + r, cy + r))
                painter.drawLine(QPointF(cx - r, cy + r), QPointF(cx + r, cy - r))
        else:
            painter.drawEllipse(QPointF(cx, cy), r, r)

        painter.end()
        return QIcon(pixmap)

    def _build_tools_section(self):
        """构建工具部分"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)

        # Plot Enhancements
        plot_group = QGroupBox(translate("Plot Enhancements"))
        plot_layout = QVBoxLayout()

        kde_row = QHBoxLayout()
        self.tools_kde_check = QCheckBox(translate("Show Kernel Density"))
        self.tools_kde_check.setChecked(getattr(app_state, 'show_kde', False))
        self.tools_kde_check.stateChanged.connect(self._on_kde_change)
        kde_row.addWidget(self.tools_kde_check)

        kde_swatch = QLabel()
        kde_swatch.setFixedSize(16, 16)
        kde_swatch.setStyleSheet("background-color: #e2e8f0; border: 1px solid #111827;")
        kde_swatch.mousePressEvent = lambda event, s=kde_swatch: self._open_kde_style_dialog('kde', s)
        kde_row.addWidget(kde_swatch)
        kde_row.addStretch()
        plot_layout.addLayout(kde_row)

        mkde_row = QHBoxLayout()
        self.tools_marginal_kde_check = QCheckBox(translate("Show Marginal KDE"))
        self.tools_marginal_kde_check.setChecked(getattr(app_state, 'show_marginal_kde', False))
        self.tools_marginal_kde_check.stateChanged.connect(self._on_marginal_kde_change)
        mkde_row.addWidget(self.tools_marginal_kde_check)

        mkde_swatch = QLabel()
        mkde_swatch.setFixedSize(16, 16)
        mkde_swatch.setStyleSheet("background-color: #e2e8f0; border: 1px solid #111827;")
        mkde_swatch.mousePressEvent = lambda event, s=mkde_swatch: self._open_kde_style_dialog('marginal_kde', s)
        mkde_row.addWidget(mkde_swatch)
        mkde_row.addStretch()
        plot_layout.addLayout(mkde_row)

        self.tools_equation_overlays_check = QCheckBox(translate("Show Equation Overlays"))
        self.tools_equation_overlays_check.setChecked(getattr(app_state, 'show_equation_overlays', False))
        self.tools_equation_overlays_check.stateChanged.connect(self._on_equation_overlays_change)
        plot_layout.addWidget(self.tools_equation_overlays_check)

        self.equation_overlays_container = QWidget()
        self.equation_overlays_layout = QVBoxLayout(self.equation_overlays_container)
        self.equation_overlays_layout.setContentsMargins(0, 0, 0, 0)
        plot_layout.addWidget(self.equation_overlays_container)

        self._refresh_equation_overlays()

        add_eq_btn = QPushButton(translate("Add Equation"))
        add_eq_btn.clicked.connect(self._open_add_equation_dialog)
        plot_layout.addWidget(add_eq_btn)

        plot_group.setLayout(plot_layout)
        layout.addWidget(plot_group)

        # 工具提示设置
        tooltip_group = QGroupBox(translate("Tooltip Settings"))
        tooltip_layout = QVBoxLayout()

        tooltip_check_layout = QHBoxLayout()
        self.tooltip_check = QCheckBox(translate("Show Tooltip"))
        self.tooltip_check.setChecked(getattr(app_state, 'show_tooltip', True))
        self.tooltip_check.stateChanged.connect(self._on_tooltip_change)
        tooltip_check_layout.addWidget(self.tooltip_check)

        tooltip_config_btn = QPushButton(translate("Configure"))
        tooltip_config_btn.setFixedWidth(100)
        tooltip_config_btn.clicked.connect(self._on_configure_tooltip)
        tooltip_check_layout.addWidget(tooltip_config_btn)
        tooltip_check_layout.addStretch()
        tooltip_layout.addLayout(tooltip_check_layout)

        tooltip_group.setLayout(tooltip_layout)
        layout.addWidget(tooltip_group)

        # 数据分析工具
        analysis_group = QGroupBox(translate("Data Analysis"))
        analysis_layout = QVBoxLayout()

        # Correlation Heatmap
        corr_btn = QPushButton(translate("Correlation Heatmap"))
        corr_btn.setFixedWidth(200)
        corr_btn.clicked.connect(self._on_show_correlation_heatmap)
        analysis_layout.addWidget(corr_btn, 0, Qt.AlignHCenter)

        # Axis Correlation
        axis_corr_btn = QPushButton(translate("Show Axis Corr."))
        axis_corr_btn.setFixedWidth(200)
        axis_corr_btn.clicked.connect(self._on_show_axis_correlation)
        analysis_layout.addWidget(axis_corr_btn, 0, Qt.AlignHCenter)

        # Shepard Plot
        shepard_btn = QPushButton(translate("Show Shepard Plot"))
        shepard_btn.setFixedWidth(200)
        shepard_btn.clicked.connect(self._on_show_shepard_diagram)
        analysis_layout.addWidget(shepard_btn, 0, Qt.AlignHCenter)

        analysis_group.setLayout(analysis_layout)
        layout.addWidget(analysis_group)

        # 选择工具
        selection_group = QGroupBox(translate("Selection Tools"))
        selection_layout = QVBoxLayout()

        # 启用选择按钮
        self.selection_button = QPushButton(translate("Enable Selection"))
        self.selection_button.setCheckable(True)
        self.selection_button.setFixedWidth(200)
        self.selection_button.clicked.connect(self._on_toggle_selection)
        selection_layout.addWidget(self.selection_button, 0, Qt.AlignHCenter)

        # 椭圆选择按钮
        self.ellipse_selection_button = QPushButton(translate("Draw Ellipse"))
        self.ellipse_selection_button.setCheckable(True)
        self.ellipse_selection_button.setFixedWidth(200)
        self.ellipse_selection_button.clicked.connect(self._on_toggle_ellipse_selection)
        selection_layout.addWidget(self.ellipse_selection_button, 0, Qt.AlignHCenter)

        # 选择状态
        self.selection_status_label = QLabel(translate("Selected Samples: {count}").format(count=0))
        selection_layout.addWidget(self.selection_status_label)

        selection_group.setLayout(selection_layout)
        layout.addWidget(selection_group)

        # 导出选项
        export_group = QGroupBox(translate("Export"))
        export_layout = QVBoxLayout()

        # 导出CSV
        self.export_csv_button = QPushButton(translate("Export CSV"))
        self.export_csv_button.setFixedWidth(200)
        self.export_csv_button.clicked.connect(self._on_export_csv)
        export_layout.addWidget(self.export_csv_button, 0, Qt.AlignHCenter)

        # 导出Excel
        self.export_excel_button = QPushButton(translate("Export Excel"))
        self.export_excel_button.setFixedWidth(200)
        self.export_excel_button.clicked.connect(self._on_export_excel)
        export_layout.addWidget(self.export_excel_button, 0, Qt.AlignHCenter)

        # 导出选中数据按钮
        self.export_selected_button = QPushButton(translate("Export Selected"))
        self.export_selected_button.setFixedWidth(200)
        self.export_selected_button.clicked.connect(self._on_export_clicked)
        export_layout.addWidget(self.export_selected_button, 0, Qt.AlignHCenter)

        export_group.setLayout(export_layout)
        layout.addWidget(export_group)

        # 子集分析
        subset_group = QGroupBox(translate("Subset Analysis"))
        subset_layout = QVBoxLayout()

        analyze_btn = QPushButton(translate("Analyze Subset"))
        analyze_btn.setFixedWidth(200)
        analyze_btn.clicked.connect(self._on_analyze_subset)
        subset_layout.addWidget(analyze_btn, 0, Qt.AlignHCenter)

        reset_btn = QPushButton(translate("Reset Data"))
        reset_btn.setFixedWidth(200)
        reset_btn.clicked.connect(self._on_reset_data)
        subset_layout.addWidget(reset_btn, 0, Qt.AlignHCenter)

        subset_group.setLayout(subset_layout)
        layout.addWidget(subset_group)

        # 混合组管理
        mixing_group = QGroupBox(translate("Mixing Groups"))
        mixing_layout = QVBoxLayout()

        # 组名输入
        group_name_layout = QHBoxLayout()
        group_name_layout.addWidget(QLabel(translate("Group Name:")))
        self.mixing_group_name_edit = QLineEdit()
        self.mixing_group_name_edit.setPlaceholderText(translate("Enter group name"))
        group_name_layout.addWidget(self.mixing_group_name_edit)
        mixing_layout.addLayout(group_name_layout)

        # 端元和混合物按钮
        mixing_btn_layout = QHBoxLayout()

        endmember_btn = QPushButton(translate("Set as Endmember"))
        endmember_btn.setFixedWidth(170)
        endmember_btn.clicked.connect(self._on_set_endmember)
        mixing_btn_layout.addWidget(endmember_btn)

        mixture_btn = QPushButton(translate("Set as Mixture"))
        mixture_btn.setFixedWidth(170)
        mixture_btn.clicked.connect(self._on_set_mixture)
        mixing_btn_layout.addWidget(mixture_btn)

        mixing_layout.addLayout(mixing_btn_layout)

        # 状态标签
        self.mixing_status_label = QLabel(translate("No mixing groups defined"))
        self.mixing_status_label.setWordWrap(True)
        mixing_layout.addWidget(self.mixing_status_label)

        # 清除和计算按钮
        mixing_action_layout = QHBoxLayout()

        clear_mixing_btn = QPushButton(translate("Clear Mixing Groups"))
        clear_mixing_btn.setFixedWidth(170)
        clear_mixing_btn.clicked.connect(self._on_clear_mixing_groups)
        mixing_action_layout.addWidget(clear_mixing_btn)

        compute_mixing_btn = QPushButton(translate("Compute Mixing"))
        compute_mixing_btn.setFixedWidth(170)
        compute_mixing_btn.clicked.connect(self._on_compute_mixing)
        mixing_action_layout.addWidget(compute_mixing_btn)

        mixing_layout.addLayout(mixing_action_layout)

        mixing_group.setLayout(mixing_layout)
        layout.addWidget(mixing_group)

        # 置信椭圆
        confidence_group = QGroupBox(translate("Confidence Ellipse"))
        confidence_layout = QVBoxLayout()

        self.confidence_68_radio = QRadioButton(translate("68% (1σ)"))
        self.confidence_95_radio = QRadioButton(translate("95% (2σ)"))
        self.confidence_99_radio = QRadioButton(translate("99% (3σ)"))

        current_level = getattr(app_state, 'confidence_level', 0.95)
        if abs(current_level - 0.68) < 0.01:
            self.confidence_68_radio.setChecked(True)
        elif abs(current_level - 0.99) < 0.01:
            self.confidence_99_radio.setChecked(True)
        else:
            self.confidence_95_radio.setChecked(True)

        self.confidence_68_radio.toggled.connect(lambda: self._on_confidence_change(0.68))
        self.confidence_95_radio.toggled.connect(lambda: self._on_confidence_change(0.95))
        self.confidence_99_radio.toggled.connect(lambda: self._on_confidence_change(0.99))

        confidence_layout.addWidget(self.confidence_68_radio)
        confidence_layout.addWidget(self.confidence_95_radio)
        confidence_layout.addWidget(self.confidence_99_radio)

        confidence_group.setLayout(confidence_layout)
        layout.addWidget(confidence_group)

        layout.addStretch()
        return widget

    def _on_show_correlation_heatmap(self):
        """显示相关性热力图"""
        try:
            from visualization.plotting_analysis_qt import show_correlation_heatmap
            show_correlation_heatmap(self)
        except Exception as e:
            print(f"[ERROR] Failed to show correlation heatmap: {e}", flush=True)

    def _on_show_axis_correlation(self):
        """显示轴相关性"""
        try:
            from visualization.plotting_analysis_qt import show_embedding_correlation
            show_embedding_correlation(self)
        except Exception as e:
            print(f"[ERROR] Failed to show axis correlation: {e}", flush=True)

    def _on_show_shepard_diagram(self):
        """显示Shepard图"""
        try:
            from visualization.plotting_analysis_qt import show_shepard_diagram
            show_shepard_diagram(self)
        except Exception as e:
            print(f"[ERROR] Failed to show Shepard diagram: {e}", flush=True)

    def _sync_selection_buttons(self):
        """Sync selection button states with active tool."""
        tool = getattr(app_state, 'selection_tool', None)

        selection_button = getattr(self, 'selection_button', None)
        if selection_button is not None:
            selection_button.blockSignals(True)
            selection_button.setChecked(tool == 'export')
            selection_button.setText(
                translate("Disable Selection") if tool == 'export' else translate("Enable Selection")
            )
            selection_button.blockSignals(False)

        ellipse_button = getattr(self, 'ellipse_selection_button', None)
        if ellipse_button is not None:
            ellipse_button.blockSignals(True)
            ellipse_button.setChecked(tool == 'ellipse')
            ellipse_button.setText(
                translate("Disable Ellipse") if tool == 'ellipse' else translate("Draw Ellipse")
            )
            ellipse_button.blockSignals(False)

        lasso_button = getattr(self, 'lasso_selection_button', None)
        if lasso_button is not None:
            lasso_button.blockSignals(True)
            lasso_button.setChecked(tool == 'lasso')
            lasso_button.setText(
                translate("Disable Custom Shape") if tool == 'lasso' else translate("Custom Shape")
            )
            lasso_button.blockSignals(False)

    def update_selection_controls(self):
        """Refresh selection UI state from app_state."""
        count = len(getattr(app_state, 'selected_indices', []))
        if getattr(self, 'selection_status_label', None) is not None:
            self.selection_status_label.setText(
                translate("Selected Samples: {count}").format(count=count)
            )

        enable_exports = count > 0
        for btn in (
            getattr(self, 'export_csv_button', None),
            getattr(self, 'export_excel_button', None),
            getattr(self, 'export_selected_button', None),
        ):
            if btn is not None:
                btn.setEnabled(enable_exports)
        status_export = getattr(self, 'status_export_button', None)
        if status_export is not None:
            status_export.setEnabled(enable_exports)

        if hasattr(self, '_sync_selection_buttons'):
            self._sync_selection_buttons()
        self._update_status_panel()

    def _update_status_panel(self):
        """Refresh right-side status panel."""
        status_data_label = getattr(self, 'status_data_label', None)
        status_render_label = getattr(self, 'status_render_label', None)
        status_algo_label = getattr(self, 'status_algo_label', None)
        status_group_label = getattr(self, 'status_group_label', None)
        status_selected_label = getattr(self, 'status_selected_label', None)
        if any(label is None for label in (
            status_data_label,
            status_render_label,
            status_algo_label,
            status_group_label,
            status_selected_label,
        )):
            return

        data_count = len(app_state.df_global) if app_state.df_global is not None else 0
        render_mode = getattr(app_state, 'render_mode', '')
        algorithm = getattr(app_state, 'algorithm', '')
        group_col = getattr(app_state, 'last_group_col', '')
        selected_count = len(getattr(app_state, 'selected_indices', []))

        status_data_label.setText(
            translate("Loaded Data: {count} rows", count=data_count)
        )
        status_render_label.setText(
            translate("Render Mode: {mode}").format(mode=render_mode)
        )
        status_algo_label.setText(
            translate("Algorithm: {mode}").format(mode=algorithm)
        )
        status_group_label.setText(
            translate("Group Column: {col}").format(col=group_col)
        )
        status_selected_label.setText(
            translate("Selected Samples: {count}").format(count=selected_count)
        )

    def _clear_selection_only(self):
        """Clear selection and refresh overlays."""
        if app_state.selected_indices:
            app_state.selected_indices.clear()
        try:
            from visualization.events import refresh_selection_overlay
            refresh_selection_overlay()
        except Exception:
            pass
        self.update_selection_controls()

    def _on_toggle_selection(self):
        """切换选择模式"""
        try:
            from visualization.events import toggle_selection_mode
            toggle_selection_mode('export')
        except Exception as err:
            print(f"[WARN] Failed to toggle selection mode: {err}", flush=True)
        self._sync_selection_buttons()

    def _on_toggle_ellipse_selection(self):
        """切换椭圆选择模式"""
        try:
            from visualization.events import toggle_selection_mode
            toggle_selection_mode('ellipse')
        except Exception as err:
            print(f"[WARN] Failed to toggle ellipse selection: {err}", flush=True)
        self._sync_selection_buttons()

    def _on_toggle_lasso_selection(self):
        """切换自定义图形选择模式"""
        try:
            from visualization.events import toggle_selection_mode
            toggle_selection_mode('lasso')
        except Exception as err:
            print(f"[WARN] Failed to toggle custom shape selection: {err}", flush=True)
        self._sync_selection_buttons()

    def _on_export_csv(self):
        """导出CSV"""
        from PyQt5.QtWidgets import QFileDialog

        if not app_state.selected_indices:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("No data selected. Please select data points first.")
            )
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            translate("Export Selected Data as CSV"),
            "",
            "CSV Files (*.csv);;All Files (*.*)"
        )

        if file_path:
            try:
                selected_df = app_state.df_global.iloc[list(app_state.selected_indices)]
                selected_df.to_csv(file_path, index=False)
                QMessageBox.information(
                    self,
                    translate("Success"),
                    translate("Data exported successfully to {file}").format(file=file_path)
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    translate("Error"),
                    translate("Failed to export data: {error}").format(error=str(e))
                )

    def _on_export_excel(self):
        """导出Excel"""
        from PyQt5.QtWidgets import QFileDialog

        if not app_state.selected_indices:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("No data selected. Please select data points first.")
            )
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            translate("Export Selected Data as Excel"),
            "",
            "Excel Files (*.xlsx);;All Files (*.*)"
        )

        if file_path:
            try:
                selected_df = app_state.df_global.iloc[list(app_state.selected_indices)]
                selected_df.to_excel(file_path, index=False)
                QMessageBox.information(
                    self,
                    translate("Success"),
                    translate("Data exported successfully to {file}").format(file=file_path)
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    translate("Error"),
                    translate("Failed to export data: {error}").format(error=str(e))
                )

    def _on_analyze_subset(self):
        """子集分析"""
        if not app_state.selected_indices:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("No data selected for analysis.")
            )
            return

        QMessageBox.information(
            self,
            translate("Info"),
            translate("Subset analysis will be implemented.")
        )

    def _on_reset_data(self):
        """重置数据"""
        # TODO: 实现数据重置
        QMessageBox.information(
            self,
            translate("Info"),
            translate("Data reset will be implemented.")
        )

    def _build_geo_section(self):
        """构建地球化学部分"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)

        # 存储地球化学参数的字典
        self.geo_params = {}

        # 模型选择
        model_select_group = QGroupBox(translate("Geochemistry Model"))
        model_select_layout = QVBoxLayout()

        model_label = QLabel(translate("Select Model:"))
        model_select_layout.addWidget(model_label)

        self.geo_model_combo = QComboBox()
        # 获取可用模型列表
        try:
            from data.geochemistry import engine
            available_models = engine.get_available_models()
            self.geo_model_combo.addItems(available_models)
            # 设置当前模型
            current_model = getattr(app_state, 'geo_model_name', 'Stacey & Kramers (2nd Stage)')
            if current_model in available_models:
                self.geo_model_combo.setCurrentText(current_model)
        except Exception as e:
            print(f"[WARN] Failed to load geochemistry models: {e}")
            self.geo_model_combo.addItem("Default")

        self.geo_model_combo.currentTextChanged.connect(self._on_geo_model_change)
        model_select_layout.addWidget(self.geo_model_combo)

        model_select_group.setLayout(model_select_layout)
        layout.addWidget(model_select_group)

        # 时间参数
        time_group = QGroupBox(translate("Time Parameters (Ma)"))
        time_layout = QGridLayout()

        self._add_geo_param(time_layout, "T1", translate("T1 (1st Stage):"), 0, 0, 0.0, 10000.0, 4430.0)
        self._add_geo_param(time_layout, "T2", translate("T2 (Earth Age):"), 0, 2, 0.0, 10000.0, 4570.0)
        self._add_geo_param(time_layout, "Tsec", translate("Tsec (2nd Stage):"), 1, 0, 0.0, 10000.0, 3700.0)

        time_group.setLayout(time_layout)
        layout.addWidget(time_group)

        # 衰变常数
        decay_group = QGroupBox(translate("Decay Constants (a^-1)"))
        decay_layout = QGridLayout()

        self._add_geo_param(decay_layout, "lambda_238", translate("λ (238U):"), 0, 0, 0.0, 1.0, 1.55125e-10, scientific=True)
        self._add_geo_param(decay_layout, "lambda_235", translate("λ (235U):"), 0, 2, 0.0, 1.0, 9.8485e-10, scientific=True)
        self._add_geo_param(decay_layout, "lambda_232", translate("λ (232Th):"), 1, 0, 0.0, 1.0, 4.94752e-11, scientific=True)

        decay_group.setLayout(decay_layout)
        layout.addWidget(decay_group)

        # 初始铅组成
        init_group = QGroupBox(translate("Initial Lead Compositions"))
        init_layout = QVBoxLayout()

        # Primordial
        prim_label = QLabel(translate("Primordial (T1/T2):"))
        prim_label.setStyleSheet("font-weight: bold;")
        init_layout.addWidget(prim_label)

        prim_grid = QGridLayout()
        self._add_geo_param(prim_grid, "a0", translate("a0 (206/204):"), 0, 0, 0.0, 100.0, 9.307)
        self._add_geo_param(prim_grid, "b0", translate("b0 (207/204):"), 0, 2, 0.0, 100.0, 10.294)
        self._add_geo_param(prim_grid, "c0", translate("c0 (208/204):"), 1, 0, 0.0, 100.0, 29.476)
        init_layout.addLayout(prim_grid)

        # Stacey-Kramers 2nd Stage
        sk_label = QLabel(translate("Stacey-Kramers 2nd Stage:"))
        sk_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        init_layout.addWidget(sk_label)

        sk_grid = QGridLayout()
        self._add_geo_param(sk_grid, "a1", translate("a1 (206/204):"), 0, 0, 0.0, 100.0, 11.152)
        self._add_geo_param(sk_grid, "b1", translate("b1 (207/204):"), 0, 2, 0.0, 100.0, 12.998)
        self._add_geo_param(sk_grid, "c1", translate("c1 (208/204):"), 1, 0, 0.0, 100.0, 31.23)
        init_layout.addLayout(sk_grid)

        init_group.setLayout(init_layout)
        layout.addWidget(init_group)

        # 地幔参数
        mantle_group = QGroupBox(translate("Mantle & Production"))
        mantle_layout = QGridLayout()

        self._add_geo_param(mantle_layout, "mu_M", translate("μ (Mantle):"), 0, 0, 0.0, 100.0, 9.74)
        self._add_geo_param(mantle_layout, "omega_M", translate("ω (Mantle):"), 0, 2, 0.0, 100.0, 36.84)
        self._add_geo_param(mantle_layout, "U_ratio", translate("U Ratio (235/238):"), 1, 0, 0.0, 1.0, 1.0/137.88, scientific=True)

        mantle_group.setLayout(mantle_layout)
        layout.addWidget(mantle_group)

        # 按钮组
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        apply_btn = QPushButton(translate("Apply Changes"))
        apply_btn.setFixedWidth(180)
        apply_btn.clicked.connect(self._on_apply_geo_params)
        button_layout.addWidget(apply_btn)

        reset_btn = QPushButton(translate("Reset Defaults"))
        reset_btn.setFixedWidth(180)
        reset_btn.clicked.connect(self._on_reset_geo_params)
        button_layout.addWidget(reset_btn)

        button_layout.addStretch()

        layout.addLayout(button_layout)

        layout.addStretch()
        return widget

    def _add_geo_param(self, grid_layout, param_name, label_text, row, col, min_val, max_val, default_val, scientific=False):
        """添加地球化学参数控件"""
        label = QLabel(label_text)
        grid_layout.addWidget(label, row, col)

        spinbox = QDoubleSpinBox()
        spinbox.setRange(min_val, max_val)
        spinbox.setDecimals(6 if scientific else 3)
        if scientific:
            spinbox.setDecimals(12)
        spinbox.setSingleStep(0.001 if not scientific else 1e-11)
        spinbox.setValue(default_val)

        grid_layout.addWidget(spinbox, row, col + 1)

        # 存储控件引用
        self.geo_params[param_name] = spinbox

    # ========== 事件处理 ==========

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

    def _on_umap_param_change(self, param, value, label):
        """UMAP 参数变化"""
        app_state.umap_params[param] = value
        if label:
            if param == 'min_dist':
                label.setText(translate("{param}: {value:.3f}").format(param=param, value=value))
            else:
                label.setText(translate("{param}: {value}").format(param=param, value=value))
        self._schedule_slider_callback(f'umap_{param}')

    def _on_tsne_param_change(self, param, value, label):
        """t-SNE 参数变化"""
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
            print(f"[INFO] PCA dimensions changed to: PC{x_idx+1} vs PC{y_idx+1}")

            # 如果当前是 PCA 或 RobustPCA 模式，刷新绘图
            if app_state.render_mode in ['PCA', 'RobustPCA']:
                self._on_change()

        except Exception as e:
            print(f"[ERROR] Failed to change PCA dimensions: {e}")

    def _on_show_scree_plot(self):
        """显示 Scree Plot"""
        try:
            from visualization import show_scree_plot
            show_scree_plot(None)  # 传入 None，函数内部会创建新窗口
        except Exception as e:
            print(f"[ERROR] Failed to show scree plot: {e}")
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
            print(f"[ERROR] Failed to show PCA loadings: {e}")
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Failed to show PCA loadings: {error}").format(error=str(e))
            )

    def _on_point_size_change(self, value, label):
        """点大小变化"""
        app_state.point_size = value
        label.setText(translate("Size: {value}").format(value=value))
        self._schedule_slider_callback('point_size')

    def _on_grid_change(self, state):
        """网格显示变化"""
        app_state.plot_style_grid = (state == Qt.Checked)
        self._on_change()

    def _on_kde_change(self, state):
        """KDE 显示变化"""
        app_state.show_kde = (state == Qt.Checked)
        self._sync_toggle_widgets(
            app_state.show_kde,
            getattr(self, 'kde_check', None),
            getattr(self, 'group_kde_check', None),
            getattr(self, 'tools_kde_check', None)
        )
        self._on_change()

    def _on_marginal_kde_change(self, state):
        """边际 KDE 显示变化"""
        app_state.show_marginal_kde = (state == Qt.Checked)
        self._sync_toggle_widgets(
            app_state.show_marginal_kde,
            getattr(self, 'marginal_kde_check', None),
            getattr(self, 'tools_marginal_kde_check', None)
        )
        self._on_change()

    def _on_ellipse_change(self, state):
        """椭圆显示变化"""
        app_state.show_ellipses = (state == Qt.Checked)
        self._on_change()

    def _on_color_scheme_change(self, scheme):
        """颜色方案变化"""
        app_state.color_scheme = scheme
        self._on_change()

    def _on_kde_style_clicked(self):
        """打开 KDE 样式对话框"""
        try:
            self._open_kde_style_dialog('kde', None)
            self._on_change()
        except Exception as e:
            print(f"[ERROR] Failed to open KDE style dialog: {e}")
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Failed to open KDE style dialog: {error}").format(error=str(e))
            )

    def _on_marginal_kde_style_clicked(self):
        """打开边际 KDE 样式对话框"""
        try:
            self._open_kde_style_dialog('marginal_kde', None)
            self._on_change()
        except Exception as e:
            print(f"[ERROR] Failed to open marginal KDE style dialog: {e}")
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Failed to open marginal KDE style dialog: {error}").format(error=str(e))
            )

    def _on_marker_opacity_change(self, value, label):
        """标记透明度变化"""
        opacity = value / 100.0
        app_state.marker_alpha = opacity
        label.setText(translate("Opacity: {value:.2f}").format(value=opacity))
        self._schedule_slider_callback('marker_opacity')

    def _on_primary_font_change(self, font):
        """主字体变化"""
        if font == '<Default>':
            font = ''
        app_state.custom_primary_font = font
        self._on_change()

    def _on_cjk_font_change(self, font):
        """CJK 字体变化"""
        if font == '<Default>':
            font = ''
        app_state.custom_cjk_font = font
        self._on_change()

    def _on_font_size_change(self, key, value):
        """字体大小变化"""
        app_state.plot_font_sizes[key] = value
        self._on_change()

    def _refresh_theme_list(self):
        """从磁盘加载主题并刷新下拉列表"""
        if not hasattr(app_state, 'saved_themes'):
            app_state.saved_themes = {}

        theme_file = CONFIG['temp_dir'] / 'user_themes.json'
        if theme_file.exists():
            try:
                with open(theme_file, 'r', encoding='utf-8') as handle:
                    app_state.saved_themes = json.load(handle)
            except Exception as exc:
                print(f"[WARN] Failed to load themes: {exc}")
                app_state.saved_themes = {}

        if self.theme_load_combo is None:
            return
        self.theme_load_combo.blockSignals(True)
        self.theme_load_combo.clear()
        self.theme_load_combo.addItems(sorted(app_state.saved_themes.keys()))
        self.theme_load_combo.setCurrentIndex(-1)
        self.theme_load_combo.blockSignals(False)

    def _save_theme(self):
        """保存当前样式为主题"""
        name = self.theme_name_edit.text().strip() if self.theme_name_edit else ""
        if not name:
            QMessageBox.warning(self, translate("Warning"), translate("Please enter a theme name."))
            return

        if not hasattr(app_state, 'saved_themes'):
            app_state.saved_themes = {}

        theme_data = {
            'grid': bool(self.grid_check.isChecked()) if self.grid_check else False,
            'color_scheme': self.color_combo.currentText() if self.color_combo else 'vibrant',
            'primary_font': self.primary_font_combo.currentText() if self.primary_font_combo else '',
            'cjk_font': self.cjk_font_combo.currentText() if self.cjk_font_combo else '',
            'font_sizes': {k: v.value() for k, v in self.font_size_spins.items()},
            'marker_size': self.marker_size_spin.value() if self.marker_size_spin else 60,
            'marker_alpha': self.marker_alpha_spin.value() if self.marker_alpha_spin else 0.8,
            'figure_dpi': self.figure_dpi_spin.value() if self.figure_dpi_spin else 130,
            'figure_bg': self.figure_bg_edit.text() if self.figure_bg_edit else '#ffffff',
            'axes_bg': self.axes_bg_edit.text() if self.axes_bg_edit else '#ffffff',
            'grid_color': self.grid_color_edit.text() if self.grid_color_edit else '#e2e8f0',
            'grid_linewidth': self.grid_width_spin.value() if self.grid_width_spin else 0.6,
            'grid_alpha': self.grid_alpha_spin.value() if self.grid_alpha_spin else 0.7,
            'grid_linestyle': self.grid_style_combo.currentText() if self.grid_style_combo else '--',
            'tick_direction': self.tick_dir_combo.currentText() if self.tick_dir_combo else 'out',
            'tick_color': self.tick_color_edit.text() if self.tick_color_edit else '#1f2937',
            'tick_length': self.tick_length_spin.value() if self.tick_length_spin else 4.0,
            'tick_width': self.tick_width_spin.value() if self.tick_width_spin else 0.8,
            'minor_ticks': bool(self.minor_ticks_check.isChecked()) if self.minor_ticks_check else False,
            'minor_tick_length': self.minor_tick_length_spin.value() if self.minor_tick_length_spin else 2.5,
            'minor_tick_width': self.minor_tick_width_spin.value() if self.minor_tick_width_spin else 0.6,
            'axis_linewidth': self.axis_linewidth_spin.value() if self.axis_linewidth_spin else 1.0,
            'axis_line_color': self.axis_line_color_edit.text() if self.axis_line_color_edit else '#1f2937',
            'show_top_spine': bool(self.show_top_spine_check.isChecked()) if self.show_top_spine_check else True,
            'show_right_spine': bool(self.show_right_spine_check.isChecked()) if self.show_right_spine_check else True,
            'minor_grid': bool(self.minor_grid_check.isChecked()) if self.minor_grid_check else False,
            'minor_grid_color': self.minor_grid_color_edit.text() if self.minor_grid_color_edit else '#e2e8f0',
            'minor_grid_linewidth': self.minor_grid_width_spin.value() if self.minor_grid_width_spin else 0.4,
            'minor_grid_alpha': self.minor_grid_alpha_spin.value() if self.minor_grid_alpha_spin else 0.4,
            'minor_grid_linestyle': self.minor_grid_style_combo.currentText() if self.minor_grid_style_combo else ':',
            'scatter_edgecolor': self.scatter_edgecolor_edit.text() if self.scatter_edgecolor_edit else '#1e293b',
            'scatter_edgewidth': self.scatter_edgewidth_spin.value() if self.scatter_edgewidth_spin else 0.4,
            'model_curve_width': self.model_curve_width_spin.value() if self.model_curve_width_spin else 1.2,
            'paleoisochron_width': self.paleoisochron_width_spin.value() if self.paleoisochron_width_spin else 0.9,
            'model_age_line_width': self.model_age_width_spin.value() if self.model_age_width_spin else 0.7,
            'isochron_line_width': self.isochron_width_spin.value() if self.isochron_width_spin else 1.5,
            'line_styles': getattr(app_state, 'line_styles', {}),
            'label_color': self.label_color_edit.text() if self.label_color_edit else '#1f2937',
            'label_weight': self.label_weight_combo.currentText() if self.label_weight_combo else 'normal',
            'label_pad': self.label_pad_spin.value() if self.label_pad_spin else 6.0,
            'title_color': self.title_color_edit.text() if self.title_color_edit else '#111827',
            'title_weight': self.title_weight_combo.currentText() if self.title_weight_combo else 'bold',
            'title_pad': self.title_pad_spin.value() if self.title_pad_spin else 20.0,
            'legend_location': getattr(app_state, 'legend_location', 'outside_right'),
            'legend_frame_on': bool(self.legend_frame_on_check.isChecked()) if self.legend_frame_on_check else True,
            'legend_frame_alpha': self.legend_frame_alpha_spin.value() if self.legend_frame_alpha_spin else 0.95,
            'legend_frame_facecolor': self.legend_frame_face_edit.text() if self.legend_frame_face_edit else '#ffffff',
            'legend_frame_edgecolor': self.legend_frame_edge_edit.text() if self.legend_frame_edge_edit else '#cbd5f5',
        }

        app_state.saved_themes[name] = theme_data

        theme_file = CONFIG['temp_dir'] / 'user_themes.json'
        try:
            with open(theme_file, 'w', encoding='utf-8') as handle:
                json.dump(app_state.saved_themes, handle, indent=2)
            QMessageBox.information(
                self,
                translate("Success"),
                translate("Theme '{name}' saved.").format(name=name)
            )
            self._refresh_theme_list()
        except Exception as exc:
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Failed to save theme: {error}").format(error=exc)
            )

    def _load_theme(self, *_args):
        """加载选中的主题"""
        if self.theme_load_combo is None or not hasattr(app_state, 'saved_themes'):
            return

        name = self.theme_load_combo.currentText()
        if not name or name not in app_state.saved_themes:
            return

        data = app_state.saved_themes[name]

        if self.grid_check:
            self.grid_check.setChecked(bool(data.get('grid', False)))
        if self.color_combo:
            self.color_combo.setCurrentText(data.get('color_scheme', 'vibrant'))

        primary_font = data.get('primary_font', '') or '<Default>'
        if self.primary_font_combo:
            self.primary_font_combo.setCurrentText(primary_font)
        cjk_font = data.get('cjk_font', '') or '<Default>'
        if self.cjk_font_combo:
            self.cjk_font_combo.setCurrentText(cjk_font)

        sizes = data.get('font_sizes', {})
        for key, spin in self.font_size_spins.items():
            if key in sizes:
                spin.setValue(int(sizes[key]))

        if self.marker_size_spin:
            self.marker_size_spin.setValue(int(data.get('marker_size', 60)))
        if self.marker_alpha_spin:
            self.marker_alpha_spin.setValue(float(data.get('marker_alpha', 0.8)))

        if self.figure_dpi_spin:
            self.figure_dpi_spin.setValue(int(data.get('figure_dpi', 130)))
        if self.figure_bg_edit:
            self.figure_bg_edit.setText(data.get('figure_bg', '#ffffff'))
        if self.axes_bg_edit:
            self.axes_bg_edit.setText(data.get('axes_bg', '#ffffff'))
        if self.grid_color_edit:
            self.grid_color_edit.setText(data.get('grid_color', '#e2e8f0'))
        if self.grid_width_spin:
            self.grid_width_spin.setValue(float(data.get('grid_linewidth', 0.6)))
        if self.grid_alpha_spin:
            self.grid_alpha_spin.setValue(float(data.get('grid_alpha', 0.7)))
        if self.grid_style_combo:
            self.grid_style_combo.setCurrentText(data.get('grid_linestyle', '--'))
        if self.tick_dir_combo:
            self.tick_dir_combo.setCurrentText(data.get('tick_direction', 'out'))
        if self.tick_color_edit:
            self.tick_color_edit.setText(data.get('tick_color', '#1f2937'))
        if self.tick_length_spin:
            self.tick_length_spin.setValue(float(data.get('tick_length', 4.0)))
        if self.tick_width_spin:
            self.tick_width_spin.setValue(float(data.get('tick_width', 0.8)))
        if self.minor_ticks_check:
            self.minor_ticks_check.setChecked(bool(data.get('minor_ticks', False)))
        if self.minor_tick_length_spin:
            self.minor_tick_length_spin.setValue(float(data.get('minor_tick_length', 2.5)))
        if self.minor_tick_width_spin:
            self.minor_tick_width_spin.setValue(float(data.get('minor_tick_width', 0.6)))
        if self.axis_linewidth_spin:
            self.axis_linewidth_spin.setValue(float(data.get('axis_linewidth', 1.0)))
        if self.axis_line_color_edit:
            self.axis_line_color_edit.setText(data.get('axis_line_color', '#1f2937'))
        if self.show_top_spine_check:
            self.show_top_spine_check.setChecked(bool(data.get('show_top_spine', True)))
        if self.show_right_spine_check:
            self.show_right_spine_check.setChecked(bool(data.get('show_right_spine', True)))
        if self.minor_grid_check:
            self.minor_grid_check.setChecked(bool(data.get('minor_grid', False)))
        if self.minor_grid_color_edit:
            self.minor_grid_color_edit.setText(data.get('minor_grid_color', '#e2e8f0'))
        if self.minor_grid_width_spin:
            self.minor_grid_width_spin.setValue(float(data.get('minor_grid_linewidth', 0.4)))
        if self.minor_grid_alpha_spin:
            self.minor_grid_alpha_spin.setValue(float(data.get('minor_grid_alpha', 0.4)))
        if self.minor_grid_style_combo:
            self.minor_grid_style_combo.setCurrentText(data.get('minor_grid_linestyle', ':'))
        if self.scatter_edgecolor_edit:
            self.scatter_edgecolor_edit.setText(data.get('scatter_edgecolor', '#1e293b'))
        if self.scatter_edgewidth_spin:
            self.scatter_edgewidth_spin.setValue(float(data.get('scatter_edgewidth', 0.4)))
        if self.model_curve_width_spin:
            self.model_curve_width_spin.setValue(float(data.get('model_curve_width', 1.2)))
        if self.paleoisochron_width_spin:
            self.paleoisochron_width_spin.setValue(float(data.get('paleoisochron_width', 0.9)))
        if self.model_age_width_spin:
            self.model_age_width_spin.setValue(float(data.get('model_age_line_width', 0.7)))
        if self.isochron_width_spin:
            self.isochron_width_spin.setValue(float(data.get('isochron_line_width', 1.5)))
        if 'line_styles' in data:
            app_state.line_styles = data.get('line_styles', {})
        if self.label_color_edit:
            self.label_color_edit.setText(data.get('label_color', '#1f2937'))
        if self.label_weight_combo:
            self.label_weight_combo.setCurrentText(data.get('label_weight', 'normal'))
        if self.label_pad_spin:
            self.label_pad_spin.setValue(float(data.get('label_pad', 6.0)))
        if self.title_color_edit:
            self.title_color_edit.setText(data.get('title_color', '#111827'))
        if self.title_weight_combo:
            self.title_weight_combo.setCurrentText(data.get('title_weight', 'bold'))
        if self.title_pad_spin:
            self.title_pad_spin.setValue(float(data.get('title_pad', 20.0)))
        if self.legend_frame_on_check:
            self.legend_frame_on_check.setChecked(bool(data.get('legend_frame_on', True)))
        if self.legend_frame_alpha_spin:
            self.legend_frame_alpha_spin.setValue(float(data.get('legend_frame_alpha', 0.95)))
        if self.legend_frame_face_edit:
            self.legend_frame_face_edit.setText(data.get('legend_frame_facecolor', '#ffffff'))
        if self.legend_frame_edge_edit:
            self.legend_frame_edge_edit.setText(data.get('legend_frame_edgecolor', '#cbd5f5'))

        legend_loc = data.get('legend_location', 'outside_right')
        app_state.legend_location = legend_loc
        app_state.legend_position = legend_loc
        self._set_legend_position_button(legend_loc)

        self._on_style_change()

    def _delete_theme(self):
        """删除选中的主题"""
        if self.theme_load_combo is None:
            return
        name = self.theme_load_combo.currentText()
        if not name:
            return

        reply = QMessageBox.question(
            self,
            translate("Confirm"),
            translate("Delete theme '{name}'?").format(name=name),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        if hasattr(app_state, 'saved_themes') and name in app_state.saved_themes:
            del app_state.saved_themes[name]

        theme_file = CONFIG['temp_dir'] / 'user_themes.json'
        try:
            with open(theme_file, 'w', encoding='utf-8') as handle:
                json.dump(app_state.saved_themes, handle, indent=2)
            self.theme_load_combo.setCurrentIndex(-1)
            self._refresh_theme_list()
        except Exception as exc:
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Failed to delete theme: {error}").format(error=exc)
            )

    def _on_style_change(self, *_args):
        """处理样式变化"""
        def _safe_float(text, default):
            try:
                return float(text)
            except (TypeError, ValueError):
                return default

        previous_scheme = getattr(app_state, 'color_scheme', None)
        previous_fonts = (
            getattr(app_state, 'custom_primary_font', ''),
            getattr(app_state, 'custom_cjk_font', '')
        )
        previous_font_sizes = dict(getattr(app_state, 'plot_font_sizes', {}))
        previous_show_title = bool(getattr(app_state, 'show_plot_title', False))
        previous_title_pad = float(getattr(app_state, 'title_pad', 20.0))
        previous_line_widths = (
            getattr(app_state, 'model_curve_width', 1.2),
            getattr(app_state, 'paleoisochron_width', 0.9),
            getattr(app_state, 'model_age_line_width', 0.7),
            getattr(app_state, 'isochron_line_width', 1.5),
        )

        if self.grid_check:
            app_state.plot_style_grid = bool(self.grid_check.isChecked())
        new_scheme = self.color_combo.currentText() if self.color_combo else app_state.color_scheme
        app_state.color_scheme = new_scheme

        primary_font = self.primary_font_combo.currentText() if self.primary_font_combo else ''
        if primary_font == '<Default>':
            primary_font = ''
        app_state.custom_primary_font = primary_font

        cjk_font = self.cjk_font_combo.currentText() if self.cjk_font_combo else ''
        if cjk_font == '<Default>':
            cjk_font = ''
        app_state.custom_cjk_font = cjk_font

        app_state.plot_font_sizes = {k: v.value() for k, v in self.font_size_spins.items()}
        if self.marker_size_spin:
            app_state.plot_marker_size = self.marker_size_spin.value()
        if self.marker_alpha_spin:
            app_state.plot_marker_alpha = self.marker_alpha_spin.value()
        if self.show_title_check:
            app_state.show_plot_title = bool(self.show_title_check.isChecked())

        if self.figure_dpi_spin:
            app_state.plot_dpi = int(self.figure_dpi_spin.value())
        if self.figure_bg_edit:
            app_state.plot_facecolor = self.figure_bg_edit.text() or '#ffffff'
        if self.axes_bg_edit:
            app_state.axes_facecolor = self.axes_bg_edit.text() or '#ffffff'
        if self.grid_color_edit:
            app_state.grid_color = self.grid_color_edit.text() or '#e2e8f0'
        if self.grid_width_spin:
            app_state.grid_linewidth = float(self.grid_width_spin.value())
        if self.grid_alpha_spin:
            app_state.grid_alpha = float(self.grid_alpha_spin.value())
        if self.grid_style_combo:
            app_state.grid_linestyle = self.grid_style_combo.currentText() or '--'
        if self.tick_dir_combo:
            app_state.tick_direction = self.tick_dir_combo.currentText() or 'out'
        if self.tick_color_edit:
            app_state.tick_color = self.tick_color_edit.text() or '#1f2937'
        if self.tick_length_spin:
            app_state.tick_length = float(self.tick_length_spin.value())
        if self.tick_width_spin:
            app_state.tick_width = float(self.tick_width_spin.value())
        if self.minor_ticks_check:
            app_state.minor_ticks = bool(self.minor_ticks_check.isChecked())
        if self.minor_tick_length_spin:
            app_state.minor_tick_length = float(self.minor_tick_length_spin.value())
        if self.minor_tick_width_spin:
            app_state.minor_tick_width = float(self.minor_tick_width_spin.value())
        if self.axis_linewidth_spin:
            app_state.axis_linewidth = float(self.axis_linewidth_spin.value())
        if self.axis_line_color_edit:
            app_state.axis_line_color = self.axis_line_color_edit.text() or '#1f2937'
        if self.show_top_spine_check:
            app_state.show_top_spine = bool(self.show_top_spine_check.isChecked())
        if self.show_right_spine_check:
            app_state.show_right_spine = bool(self.show_right_spine_check.isChecked())
        if self.minor_grid_check:
            app_state.minor_grid = bool(self.minor_grid_check.isChecked())
        if self.minor_grid_color_edit:
            app_state.minor_grid_color = self.minor_grid_color_edit.text() or '#e2e8f0'
        if self.minor_grid_width_spin:
            app_state.minor_grid_linewidth = float(self.minor_grid_width_spin.value())
        if self.minor_grid_alpha_spin:
            app_state.minor_grid_alpha = float(self.minor_grid_alpha_spin.value())
        if self.minor_grid_style_combo:
            app_state.minor_grid_linestyle = self.minor_grid_style_combo.currentText() or ':'
        if self.scatter_edgecolor_edit:
            app_state.scatter_edgecolor = self.scatter_edgecolor_edit.text() or '#1e293b'
        if self.scatter_edgewidth_spin:
            app_state.scatter_edgewidth = float(self.scatter_edgewidth_spin.value())
        if self.model_curve_width_spin:
            app_state.model_curve_width = float(self.model_curve_width_spin.value())
        if self.paleoisochron_width_spin:
            app_state.paleoisochron_width = float(self.paleoisochron_width_spin.value())
        if self.model_age_width_spin:
            app_state.model_age_line_width = float(self.model_age_width_spin.value())
        if self.isochron_width_spin:
            app_state.isochron_line_width = float(self.isochron_width_spin.value())

        if hasattr(app_state, 'line_styles'):
            app_state.line_styles.setdefault('model_curve', {})['linewidth'] = app_state.model_curve_width
            app_state.line_styles.setdefault('paleoisochron', {})['linewidth'] = app_state.paleoisochron_width
            app_state.line_styles.setdefault('model_age_line', {})['linewidth'] = app_state.model_age_line_width
            app_state.line_styles.setdefault('isochron', {})['linewidth'] = app_state.isochron_line_width

        if self.label_color_edit:
            app_state.label_color = self.label_color_edit.text() or '#1f2937'
        if self.label_weight_combo:
            app_state.label_weight = self.label_weight_combo.currentText() or 'normal'
        if self.label_pad_spin:
            app_state.label_pad = float(self.label_pad_spin.value())
        if self.title_color_edit:
            app_state.title_color = self.title_color_edit.text() or '#111827'
        if self.title_weight_combo:
            app_state.title_weight = self.title_weight_combo.currentText() or 'bold'
        if self.title_pad_spin:
            app_state.title_pad = float(self.title_pad_spin.value())

        if self.legend_frame_on_check:
            app_state.legend_frame_on = bool(self.legend_frame_on_check.isChecked())
        if self.legend_frame_alpha_spin:
            app_state.legend_frame_alpha = float(self.legend_frame_alpha_spin.value())
        if self.legend_frame_face_edit:
            app_state.legend_frame_facecolor = self.legend_frame_face_edit.text() or '#ffffff'
        if self.legend_frame_edge_edit:
            app_state.legend_frame_edgecolor = self.legend_frame_edge_edit.text() or '#cbd5f5'

        if app_state.fig is not None:
            try:
                app_state.fig.set_dpi(app_state.plot_dpi)
                app_state.fig.patch.set_facecolor(app_state.plot_facecolor)
            except Exception:
                pass
        if app_state.ax is not None:
            try:
                app_state.ax.set_facecolor(app_state.axes_facecolor)
            except Exception:
                pass

        if new_scheme != previous_scheme and hasattr(app_state, 'current_palette'):
            app_state.current_palette = {}

        requires_replot = False
        if new_scheme != previous_scheme:
            requires_replot = True
        if (primary_font, cjk_font) != previous_fonts:
            requires_replot = True
        if app_state.plot_font_sizes != previous_font_sizes:
            requires_replot = True
        if app_state.show_plot_title != previous_show_title:
            requires_replot = True
        if app_state.title_pad != previous_title_pad:
            requires_replot = True
        if (
            app_state.model_curve_width,
            app_state.paleoisochron_width,
            app_state.model_age_line_width,
            app_state.isochron_line_width,
        ) != previous_line_widths:
            requires_replot = True

        if requires_replot:
            if self.callback:
                self.callback()
        else:
            try:
                from visualization import refresh_plot_style
                refresh_plot_style()
            except Exception:
                if self.callback:
                    self.callback()

    def _apply_auto_layout(self):
        """应用自动布局"""
        if app_state.fig is None:
            return
        try:
            app_state.fig.set_constrained_layout(True)
            app_state.fig.set_constrained_layout_pads(
                w_pad=0.02, h_pad=0.02, wspace=0.02, hspace=0.02
            )
            if app_state.fig.canvas:
                app_state.fig.canvas.draw_idle()
        except Exception:
            pass

    def _on_ui_theme_change(self, *_args):
        """UI 主题切换"""
        if self.ui_theme_combo is None:
            return
        self._apply_ui_theme(self.ui_theme_combo.currentText())

    def _apply_ui_theme(self, theme_name):
        """保存 UI 主题选择"""
        if not theme_name:
            theme_name = 'Modern Light'
        app_state.ui_theme = theme_name

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
                print(f"[INFO] Tooltip columns configured: {result}")
                self._on_change()
        except Exception as e:
            print(f"[ERROR] Failed to open tooltip configuration dialog: {e}")
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Failed to open tooltip configuration: {error}").format(error=str(e))
            )

    def _on_set_endmember(self):
        """设置端元"""
        group_name = self.mixing_group_name_edit.text().strip()
        if not group_name:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("Please enter a group name.")
            )
            return

        if not app_state.selected_indices:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("Please select data points first.")
            )
            return

        # 初始化混合组
        if not hasattr(app_state, 'mixing_endmembers'):
            app_state.mixing_endmembers = {}
        if not hasattr(app_state, 'mixing_mixtures'):
            app_state.mixing_mixtures = {}

        app_state.mixing_endmembers[group_name] = list(app_state.selected_indices)
        self._update_mixing_status()
        self._clear_selection_after_mixing()
        QMessageBox.information(
            self,
            translate("Success"),
            translate("Endmember '{name}' set with {count} samples.").format(
                name=group_name, count=len(app_state.selected_indices)
            )
        )

    def _on_set_mixture(self):
        """设置混合物"""
        group_name = self.mixing_group_name_edit.text().strip()
        if not group_name:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("Please enter a group name.")
            )
            return

        if not app_state.selected_indices:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("Please select data points first.")
            )
            return

        # 初始化混合组
        if not hasattr(app_state, 'mixing_endmembers'):
            app_state.mixing_endmembers = {}
        if not hasattr(app_state, 'mixing_mixtures'):
            app_state.mixing_mixtures = {}

        app_state.mixing_mixtures[group_name] = list(app_state.selected_indices)
        self._update_mixing_status()
        self._clear_selection_after_mixing()
        QMessageBox.information(
            self,
            translate("Success"),
            translate("Mixture '{name}' set with {count} samples.").format(
                name=group_name, count=len(app_state.selected_indices)
            )
        )

    def _clear_selection_after_mixing(self):
        """Clear selection and refresh overlays after mixing group changes."""
        if app_state.selected_indices:
            app_state.selected_indices.clear()
        try:
            from visualization.events import refresh_selection_overlay
            refresh_selection_overlay()
        except Exception:
            pass
        self.update_selection_controls()

    def _on_clear_mixing_groups(self):
        """清除混合组"""
        app_state.mixing_endmembers = {}
        app_state.mixing_mixtures = {}
        self._update_mixing_status()
        QMessageBox.information(
            self,
            translate("Info"),
            translate("All mixing groups cleared.")
        )

    def _on_compute_mixing(self):
        """计算混合"""
        if not hasattr(app_state, 'mixing_endmembers') or not app_state.mixing_endmembers:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("Please define at least one endmember.")
            )
            return

        if not hasattr(app_state, 'mixing_mixtures') or not app_state.mixing_mixtures:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("Please define at least one mixture.")
            )
            return

        try:
            from ui.dialogs.mixing_dialog import show_mixing_calculator
            show_mixing_calculator(self)
        except Exception as e:
            print(f"[ERROR] Failed to compute mixing: {e}")
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Failed to compute mixing: {error}").format(error=str(e))
            )

    def _update_mixing_status(self):
        """更新混合组状态"""
        endmembers = getattr(app_state, 'mixing_endmembers', {})
        mixtures = getattr(app_state, 'mixing_mixtures', {})

        if not endmembers and not mixtures:
            self.mixing_status_label.setText(translate("No mixing groups defined"))
        else:
            status_parts = []
            if endmembers:
                status_parts.append(translate("Endmembers: {count}").format(count=len(endmembers)))
            if mixtures:
                status_parts.append(translate("Mixtures: {count}").format(count=len(mixtures)))
            self.mixing_status_label.setText(", ".join(status_parts))

    def _on_confidence_change(self, level):
        """置信水平变化"""
        app_state.confidence_level = level
        print(f"[INFO] Confidence level changed to: {level}")
        self._on_change()

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
            print(f"[DEBUG] 2D Axes Changed: X={x_col}, Y={y_col}", flush=True)
            self._on_change()

    def _on_export_clicked(self):
        """导出按钮点击"""
        from PyQt5.QtWidgets import QFileDialog

        if not app_state.selected_indices:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("No data selected. Please select data points first.")
            )
            return

        # 选择保存文件
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            translate("Export Selected Data"),
            "",
            "CSV Files (*.csv);;Excel Files (*.xlsx);;All Files (*.*)"
        )

        if file_path:
            try:
                # 获取选中的数据
                selected_df = app_state.df_global.iloc[list(app_state.selected_indices)]

                # 根据文件扩展名保存
                if file_path.endswith('.xlsx'):
                    selected_df.to_excel(file_path, index=False)
                else:
                    selected_df.to_csv(file_path, index=False)

                QMessageBox.information(
                    self,
                    translate("Success"),
                    translate("Data exported successfully to {file}").format(file=file_path)
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    translate("Error"),
                    translate("Failed to export data: {error}").format(error=str(e))
                )

    def _show_2d_column_dialog(self):
        """显示 2D 列选择对话框"""
        from ui.dialogs.two_d_dialog import get_2d_column_selection

        result = get_2d_column_selection()
        if result:
            app_state.selected_2d_cols = result
            app_state.selected_2d_confirmed = True
            print(f"[INFO] Selected 2D columns: {result}", flush=True)
            self._on_change()

    def _show_3d_column_dialog(self):
        """显示 3D 列选择对话框"""
        from ui.dialogs.three_d_dialog import get_3d_column_selection

        result = get_3d_column_selection()
        if result:
            app_state.selected_3d_cols = result
            app_state.selected_3d_confirmed = True
            print(f"[INFO] Selected 3D columns: {result}", flush=True)
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
            print(f"[INFO] Selected ternary columns: {result['columns']}", flush=True)
            print(f"[INFO] Ternary stretch: {result['stretch']}, factors: {result['factors']}", flush=True)
            self._on_change()

    def _update_group_list(self):
        """更新分组列表 - 增强版：包含颜色和形状选择"""
        if not hasattr(self, 'group_list') or self.group_list is None:
            return
        self.group_list.clear()
        self.legend_checkboxes = {}

        if not app_state.last_group_col or app_state.df_global is None:
            return

        # 获取所有分组
        groups = app_state.df_global[app_state.last_group_col].unique()

        # 确保标记形状映射存在
        self._ensure_marker_shape_map()

        # 可见分组集合
        visible = set(app_state.visible_groups) if app_state.visible_groups is not None else set(groups)

        # 限制项目数量以防止UI冻结
        max_items = 100
        groups_to_show = list(groups)[:max_items]

        if len(groups) > max_items:
            print(f"[WARN] Showing first {max_items} groups only.", flush=True)

        for group in groups_to_show:
            # 创建自定义widget用于列表项
            item_widget = QWidget()
            item_layout = QHBoxLayout()
            item_layout.setContentsMargins(5, 2, 5, 2)
            item_layout.setSpacing(10)

            # 颜色选择块（可点击）
            color = app_state.current_palette.get(group, '#cccccc')
            color_btn = QPushButton()
            color_btn.setFixedSize(24, 24)
            self._update_marker_swatch(group, color_btn)
            color_btn.setCursor(QCursor(Qt.PointingHandCursor))
            color_btn.clicked.connect(lambda checked=False, g=group, btn=color_btn: self._pick_color(g, btn))
            item_layout.addWidget(color_btn)

            # 复选框
            checkbox = QCheckBox(str(group))
            is_visible = group in visible
            checkbox.setChecked(is_visible)
            checkbox.stateChanged.connect(lambda state, g=group: self._on_group_checkbox_change(g, state))
            item_layout.addWidget(checkbox, 1)
            self.legend_checkboxes[group] = checkbox

            # 形状选择下拉框
            shape_combo = QComboBox()
            shape_combo.setFixedWidth(120)
            for label in self._marker_shape_map.keys():
                shape_combo.addItem(label)
            current_marker = app_state.group_marker_map.get(group, getattr(app_state, 'plot_marker_shape', 'o'))
            current_label = self._marker_label_for_value(current_marker)
            shape_combo.setCurrentText(current_label)
            shape_combo.currentTextChanged.connect(lambda text, g=group, combo=shape_combo, btn=color_btn: self._apply_marker_shape(g, combo, btn))
            item_layout.addWidget(shape_combo)

            # Top 按钮
            top_btn = QPushButton(translate("Top"))
            top_btn.setFixedWidth(50)
            top_btn.clicked.connect(lambda checked=False, g=group: self._bring_to_front(g))
            item_layout.addWidget(top_btn)

            item_widget.setLayout(item_layout)

            # 创建 QListWidgetItem
            item = QListWidgetItem()
            item.setSizeHint(item_widget.sizeHint())
            self.group_list.addItem(item)
            self.group_list.setItemWidget(item, item_widget)

    def _on_group_checkbox_change(self, group, state):
        """分组复选框状态变化"""
        if not app_state.last_group_col or app_state.df_global is None:
            return

        groups = list(app_state.available_groups or app_state.df_global[app_state.last_group_col].unique())
        if app_state.visible_groups is None:
            current_visible = set(groups)
        else:
            current_visible = set(app_state.visible_groups)

        if state == Qt.Checked:
            current_visible.add(group)
        else:
            current_visible.discard(group)

        if len(current_visible) == len(groups):
            app_state.visible_groups = None
        else:
            app_state.visible_groups = sorted(current_visible)

        self._on_change()

    def _on_group_visibility_change(self, item):
        """分组可见性变化"""
        group_name = item.text()
        is_checked = item.checkState() == Qt.Checked
        state = Qt.Checked if is_checked else Qt.Unchecked
        self._on_group_checkbox_change(group_name, state)

    def _show_all_groups(self):
        """显示所有分组"""
        was_empty = app_state.visible_groups == []
        app_state.visible_groups = None
        self._update_group_list()
        self._on_change()
        if was_empty:
            QTimer.singleShot(0, self._autoscale_current_axes)

    def _hide_all_groups(self):
        """隐藏所有分组"""
        if app_state.last_group_col and app_state.df_global is not None:
            app_state.visible_groups = []
            self._update_group_list()
            self._on_change()

    def _autoscale_current_axes(self):
        """Autoscale current axes after legend visibility changes."""
        ax = getattr(app_state, 'ax', None)
        if ax is None:
            return
        try:
            ax.autoscale(enable=True, axis='both')
            ax.relim()
            ax.autoscale_view()
            if app_state.fig is not None and app_state.fig.canvas is not None:
                app_state.fig.canvas.draw_idle()
        except Exception:
            pass

    def sync_legend_ui(self):
        """Sync legend checkboxes with app_state.visible_groups."""
        if not hasattr(self, 'legend_checkboxes'):
            return
        if app_state.last_group_col and app_state.df_global is not None:
            groups = list(app_state.available_groups or app_state.df_global[app_state.last_group_col].unique())
        else:
            groups = []

        if app_state.visible_groups is None:
            visible = set(groups)
        else:
            visible = set(app_state.visible_groups)

        for group, checkbox in self.legend_checkboxes.items():
            checkbox.blockSignals(True)
            checkbox.setChecked(group in visible)
            checkbox.blockSignals(False)

    def _bring_to_front(self, group):
        """将分组的点置于顶层"""
        if hasattr(app_state, 'group_to_scatter') and group in app_state.group_to_scatter:
            sc = app_state.group_to_scatter[group]
            try:
                # 查找最大zorder
                max_z = 2  # 默认基础zorder
                if hasattr(app_state, 'scatter_collections'):
                    for c in app_state.scatter_collections:
                        max_z = max(max_z, c.get_zorder())

                sc.set_zorder(max_z + 1)
                if app_state.fig:
                    app_state.fig.canvas.draw_idle()
            except Exception as e:
                print(f"[WARN] Failed to bring {group} to front: {e}", flush=True)

    def _on_legend_position_change(self, position):
        """图例位置变化"""
        if position == 'outside right':
            position = 'outside_right'
        app_state.legend_position = position
        app_state.legend_location = position
        self._set_legend_position_button(position)
        self._on_change()

    def _on_legend_columns_change(self, columns):
        """图例列数变化"""
        app_state.legend_columns = columns
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

    def _on_equation_overlays_change(self, state):
        """方程叠加显示变化"""
        app_state.show_equation_overlays = (state == Qt.Checked)
        self._on_change()

    def _on_equation_overlay_toggle(self, overlay, state):
        """单个方程叠加的启用状态变化"""
        overlay['enabled'] = (state == Qt.Checked)
        self._on_change()

    def _refresh_equation_overlays(self):
        """刷新方程叠加列表"""
        if self.equation_overlays_layout is None:
            return

        while self.equation_overlays_layout.count():
            item = self.equation_overlays_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        overlays = getattr(app_state, 'equation_overlays', []) or []
        for overlay in overlays:
            self._add_equation_overlay_row(overlay)

    def _add_equation_overlay_row(self, overlay):
        """添加方程叠加项"""
        if self.equation_overlays_layout is None:
            return

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)

        label_text = overlay.get('label', 'Equation')
        eq_chk = QCheckBox(translate(label_text))
        eq_chk.setChecked(overlay.get('enabled', True))
        eq_chk.stateChanged.connect(lambda state, ov=overlay: self._on_equation_overlay_toggle(ov, state))
        row_layout.addWidget(eq_chk)

        swatch = QLabel()
        swatch.setFixedSize(16, 16)
        color_val = overlay.get('color', '#ef4444')
        swatch.setStyleSheet(f"background-color: {color_val}; border: 1px solid #111827;")
        swatch.mousePressEvent = lambda event, ov=overlay, sw=swatch: self._open_equation_style_dialog(ov, sw)
        row_layout.addWidget(swatch)
        row_layout.addStretch()

        self.equation_overlays_layout.addWidget(row)

    def _open_equation_style_dialog(self, overlay, swatch):
        """打开方程线样式对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle(translate("Edit Equation Style"))
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)

        color_row = QHBoxLayout()
        color_row.addWidget(QLabel(translate("Line Color")))
        color_swatch = QLabel()
        color_swatch.setFixedSize(20, 16)
        color_val = overlay.get('color', '#ef4444')
        color_swatch.setStyleSheet(f"background-color: {color_val}; border: 1px solid #111827;")
        color_row.addWidget(color_swatch)

        def _pick_color():
            from PyQt5.QtWidgets import QColorDialog
            chosen = QColorDialog.getColor(QColor(color_val), self, translate("Line Color"))
            if chosen.isValid():
                new_color = chosen.name()
                overlay['color'] = new_color
                color_swatch.setStyleSheet(f"background-color: {new_color}; border: 1px solid #111827;")

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
        width_spin.setValue(float(overlay.get('linewidth', 1.0)))
        width_row.addWidget(width_spin)
        width_row.addStretch()
        layout.addLayout(width_row)

        style_row = QHBoxLayout()
        style_row.addWidget(QLabel(translate("Line Style")))
        style_combo = QComboBox()
        style_combo.addItems(['-', '--', '-.', ':'])
        style_combo.setCurrentText(overlay.get('linestyle', '--'))
        style_row.addWidget(style_combo)
        style_row.addStretch()
        layout.addLayout(style_row)

        alpha_row = QHBoxLayout()
        alpha_row.addWidget(QLabel(translate("Opacity")))
        alpha_spin = QDoubleSpinBox()
        alpha_spin.setRange(0.1, 1.0)
        alpha_spin.setSingleStep(0.05)
        alpha_spin.setValue(float(overlay.get('alpha', 0.85)))
        alpha_row.addWidget(alpha_spin)
        alpha_row.addStretch()
        layout.addLayout(alpha_row)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton(translate("Cancel"))
        cancel_btn.clicked.connect(dialog.reject)
        btn_row.addWidget(cancel_btn)
        save_btn = QPushButton(translate("Save"))

        def _apply():
            overlay['linewidth'] = float(width_spin.value())
            overlay['linestyle'] = style_combo.currentText()
            overlay['alpha'] = float(alpha_spin.value())
            swatch.setStyleSheet(f"background-color: {overlay.get('color', '#ef4444')}; border: 1px solid #111827;")
            dialog.accept()
            self._on_change()

        save_btn.clicked.connect(_apply)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

        dialog.exec_()

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

    def _open_kde_style_dialog(self, target, swatch):
        """打开 KDE 样式对话框"""
        dialog = QDialog(self)
        title_key = "KDE Style" if target == 'kde' else "Marginal KDE Style"
        dialog.setWindowTitle(translate(title_key))
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)

        style_key = 'kde_style' if target == 'kde' else 'marginal_kde_style'
        style = getattr(app_state, style_key, {}) or {}

        alpha_row = QHBoxLayout()
        alpha_row.addWidget(QLabel(translate("Opacity")))
        alpha_spin = QDoubleSpinBox()
        alpha_spin.setRange(0.05, 1.0)
        alpha_spin.setSingleStep(0.05)
        alpha_spin.setValue(float(style.get('alpha', 0.6 if target == 'kde' else 0.25)))
        alpha_row.addWidget(alpha_spin)
        alpha_row.addStretch()
        layout.addLayout(alpha_row)

        width_row = QHBoxLayout()
        width_row.addWidget(QLabel(translate("Line Width")))
        width_spin = QDoubleSpinBox()
        width_spin.setRange(0.0, 4.0)
        width_spin.setSingleStep(0.1)
        width_spin.setValue(float(style.get('linewidth', 1.0)))
        width_row.addWidget(width_spin)
        width_row.addStretch()
        layout.addLayout(width_row)

        fill_row = QHBoxLayout()
        fill_row.addWidget(QLabel(translate("Fill")))
        fill_check = QCheckBox()
        fill_check.setChecked(bool(style.get('fill', True)))
        fill_row.addWidget(fill_check)
        fill_row.addStretch()
        layout.addLayout(fill_row)

        levels_spin = None
        if target == 'kde':
            levels_row = QHBoxLayout()
            levels_row.addWidget(QLabel(translate("KDE Levels")))
            levels_spin = QSpinBox()
            levels_spin.setRange(3, 30)
            levels_spin.setValue(int(style.get('levels', 10)))
            levels_row.addWidget(levels_spin)
            levels_row.addStretch()
            layout.addLayout(levels_row)

        top_size_spin = None
        right_size_spin = None
        if target == 'marginal_kde':
            top_row = QHBoxLayout()
            top_row.addWidget(QLabel(translate("Top KDE Height (%)")))
            top_size_spin = QDoubleSpinBox()
            top_size_spin.setRange(5.0, 40.0)
            top_size_spin.setSingleStep(1.0)
            top_size_spin.setValue(float(getattr(app_state, 'marginal_kde_top_size', 15.0)))
            top_row.addWidget(top_size_spin)
            top_row.addStretch()
            layout.addLayout(top_row)

            right_row = QHBoxLayout()
            right_row.addWidget(QLabel(translate("Right KDE Width (%)")))
            right_size_spin = QDoubleSpinBox()
            right_size_spin.setRange(5.0, 40.0)
            right_size_spin.setSingleStep(1.0)
            right_size_spin.setValue(float(getattr(app_state, 'marginal_kde_right_size', 15.0)))
            right_row.addWidget(right_size_spin)
            right_row.addStretch()
            layout.addLayout(right_row)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton(translate("Cancel"))
        cancel_btn.clicked.connect(dialog.reject)
        btn_row.addWidget(cancel_btn)
        save_btn = QPushButton(translate("Save"))

        def _apply():
            style_ref = getattr(app_state, style_key, {}) or {}
            style_ref['alpha'] = float(alpha_spin.value())
            style_ref['linewidth'] = float(width_spin.value())
            style_ref['fill'] = bool(fill_check.isChecked())
            if target == 'kde' and levels_spin is not None:
                style_ref['levels'] = int(levels_spin.value())
            if target == 'marginal_kde':
                if top_size_spin is not None:
                    app_state.marginal_kde_top_size = float(top_size_spin.value())
                if right_size_spin is not None:
                    app_state.marginal_kde_right_size = float(right_size_spin.value())
            setattr(app_state, style_key, style_ref)

            if swatch is not None:
                swatch.setStyleSheet("background-color: #e2e8f0; border: 1px solid #111827;")
            dialog.accept()
            self._on_change()

        save_btn.clicked.connect(_apply)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

        dialog.exec_()

    def _open_add_equation_dialog(self):
        """打开新增方程对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle(translate("Manage Equations"))
        dialog.setModal(True)
        dialog.resize(520, 640)

        layout = QVBoxLayout(dialog)

        info_label = QLabel(translate("Select equations to display."))
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        presets = [
            {
                'label': translate("y=x"),
                'latex': translate("y=x"),
                'expression': 'x'
            },
            {
                'label': translate("y=1.0049x+20.259"),
                'latex': translate("y=1.0049x+20.259"),
                'expression': '1.0049*x+20.259'
            }
        ]

        working_overlays = list(getattr(app_state, 'equation_overlays', []) or [])

        list_group = QGroupBox(translate("Equation Library"))
        list_layout = QVBoxLayout()

        list_container = QWidget()
        list_container_layout = QVBoxLayout(list_container)
        list_container_layout.setContentsMargins(0, 0, 0, 0)
        list_container_layout.setSpacing(6)

        entries = []

        def _clear_layout(target_layout):
            while target_layout.count():
                item = target_layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()

        def _find_overlay(expression):
            for overlay in working_overlays:
                if overlay.get('expression') == expression:
                    return overlay
            return None

        def _add_entry_row(label_text, overlay, checked=False, is_preset=False):
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)

            chk = QCheckBox(label_text)
            chk.setChecked(bool(checked))
            row_layout.addWidget(chk)

            swatch = QLabel()
            swatch.setFixedSize(16, 16)
            swatch_color = overlay.get('color', '#ef4444')
            swatch.setStyleSheet(f"background-color: {swatch_color}; border: 1px solid #111827;")
            swatch.setProperty("keepStyle", True)
            swatch.mousePressEvent = lambda event, ov=overlay, sw=swatch: self._open_equation_style_dialog(ov, sw)
            row_layout.addWidget(swatch)
            row_layout.addStretch()

            list_container_layout.addWidget(row)
            entries.append({
                'checkbox': chk,
                'overlay': overlay,
                'is_preset': is_preset
            })

        def _rebuild_list():
            entries.clear()
            _clear_layout(list_container_layout)

            existing_label = QLabel(translate("Existing Equations"))
            existing_label.setStyleSheet("font-weight: bold;")
            list_container_layout.addWidget(existing_label)

            if working_overlays:
                for overlay in working_overlays:
                    label_text = overlay.get('label', 'Equation')
                    _add_entry_row(translate(label_text), overlay, checked=overlay.get('enabled', False))
            else:
                empty_label = QLabel(translate("No equations yet."))
                list_container_layout.addWidget(empty_label)

            preset_label = QLabel(translate("Preset Equations"))
            preset_label.setStyleSheet("font-weight: bold; margin-top: 6px;")
            list_container_layout.addWidget(preset_label)

            for preset in presets:
                existing = _find_overlay(preset['expression'])
                if existing is not None:
                    continue
                preset_overlay = {
                    'label': preset['label'],
                    'latex': preset['latex'],
                    'expression': preset['expression'],
                    'enabled': False,
                    'color': '#ef4444',
                    'linewidth': 1.0,
                    'linestyle': '--',
                    'alpha': 0.85
                }
                _add_entry_row(preset['label'], preset_overlay, checked=False, is_preset=True)

            list_container_layout.addStretch()

        _rebuild_list()

        list_layout.addWidget(list_container)
        list_group.setLayout(list_layout)
        layout.addWidget(list_group)

        custom_group = QGroupBox(translate("Custom Equation"))
        custom_layout = QVBoxLayout()

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel(translate("Equation Name")))
        name_edit = QLineEdit()
        name_row.addWidget(name_edit)
        custom_layout.addLayout(name_row)

        latex_row = QHBoxLayout()
        latex_row.addWidget(QLabel(translate("Equation (LaTeX)")))
        latex_edit = QLineEdit()
        latex_row.addWidget(latex_edit)
        custom_layout.addLayout(latex_row)

        expr_row = QHBoxLayout()
        expr_row.addWidget(QLabel(translate("Expression (Python, x only)")))
        expr_edit = QLineEdit()
        expr_row.addWidget(expr_edit)
        custom_layout.addLayout(expr_row)

        add_custom_row = QHBoxLayout()
        add_custom_row.addStretch()
        add_custom_btn = QPushButton(translate("Add to List"))
        add_custom_row.addWidget(add_custom_btn)
        custom_layout.addLayout(add_custom_row)

        custom_group.setLayout(custom_layout)
        layout.addWidget(custom_group)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton(translate("Cancel"))
        cancel_btn.clicked.connect(dialog.reject)
        btn_row.addWidget(cancel_btn)

        def _validate_expression(expression):
            expression = expression.strip()
            if not expression:
                QMessageBox.warning(dialog, translate("Warning"), translate("Expression cannot be empty."))
                return None
            try:
                ast.parse(expression, mode='eval')
            except Exception:
                QMessageBox.warning(dialog, translate("Warning"), translate("Invalid expression."))
                return None
            return expression

        def _add_custom_to_list():
            expression = _validate_expression(expr_edit.text())
            if expression is None:
                return
            label_text = name_edit.text().strip() or 'Equation'
            latex_text = latex_edit.text().strip() or label_text
            overlay = {
                'id': f"eq_custom_{uuid.uuid4().hex[:8]}",
                'label': label_text,
                'latex': latex_text,
                'expression': expression,
                'enabled': False,
                'color': '#ef4444',
                'linewidth': 1.0,
                'linestyle': '--',
                'alpha': 0.85
            }
            working_overlays.append(overlay)
            name_edit.clear()
            latex_edit.clear()
            expr_edit.clear()
            _rebuild_list()

        def _apply_selection():
            new_overlays = []
            for entry in entries:
                overlay = entry['overlay']
                checked = bool(entry['checkbox'].isChecked())
                if entry['is_preset']:
                    if not checked:
                        continue
                    overlay = dict(overlay)
                    overlay['id'] = overlay.get('id') or f"eq_preset_{uuid.uuid4().hex[:8]}"
                    overlay['enabled'] = True
                    new_overlays.append(overlay)
                else:
                    overlay['enabled'] = checked
                    new_overlays.append(overlay)

            app_state.equation_overlays = new_overlays
            app_state.show_equation_overlays = any(ov.get('enabled', False) for ov in new_overlays)
            self._on_change()
            dialog.accept()

        add_custom_btn.clicked.connect(_add_custom_to_list)

        apply_btn = QPushButton(translate("Apply"))
        apply_btn.clicked.connect(_apply_selection)
        btn_row.addWidget(apply_btn)
        layout.addLayout(btn_row)

        dialog.exec_()

    def _on_calculate_isochron(self):
        """计算等时线年龄"""
        try:
            from visualization.events import toggle_selection_mode, calculate_selected_isochron, on_slider_change
        except Exception as e:
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Failed to start isochron selection: {error}").format(error=str(e))
            )
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

        previous_selection = set(getattr(app_state, 'selected_indices', set()) or set())
        toggle_selection_mode('isochron')

        if app_state.selection_tool == 'isochron' and previous_selection:
            app_state.selected_indices = set(previous_selection)
            calculate_selected_isochron()
            try:
                on_slider_change()
            except Exception as refresh_err:
                print(f"[WARN] Failed to refresh plot after isochron calculation: {refresh_err}", flush=True)

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

    def _combo_value(self, combo, value_or_index):
        """获取组合框的实际值"""
        if isinstance(value_or_index, int):
            data = combo.itemData(value_or_index)
            return data if data is not None else combo.itemText(value_or_index)
        return value_or_index

    def _set_combo_value(self, combo, value):
        """设置组合框的值"""
        if value is None:
            return
        index = combo.findData(value)
        if index == -1:
            index = combo.findText(str(value))
        if index >= 0 and combo.currentIndex() != index:
            combo.blockSignals(True)
            combo.setCurrentIndex(index)
            combo.blockSignals(False)

    def _sync_geochem_model_for_mode(self, mode):
        """根据模式同步地球化学模型"""
        if not hasattr(self, 'geo_model_combo'):
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

        available_models = [self.geo_model_combo.itemText(i) for i in range(self.geo_model_combo.count())]
        if target_model in available_models:
            self.geo_model_combo.setCurrentText(target_model)

    def _on_geo_model_change(self, model_name):
        """地球化学模型选择变化"""
        if not model_name:
            return

        try:
            from data.geochemistry import engine

            # 加载预设模型
            if engine.load_preset(model_name):
                # 获取当前参数
                current_params = engine.get_parameters()

                # 更新 UI 控件
                if 'T1' in self.geo_params:
                    self.geo_params['T1'].setValue(current_params['T1'] / 1e6)
                if 'T2' in self.geo_params:
                    self.geo_params['T2'].setValue(current_params['T2'] / 1e6)
                if 'Tsec' in self.geo_params:
                    self.geo_params['Tsec'].setValue(current_params['Tsec'] / 1e6)

                if 'lambda_238' in self.geo_params:
                    self.geo_params['lambda_238'].setValue(current_params['lambda_238'])
                if 'lambda_235' in self.geo_params:
                    self.geo_params['lambda_235'].setValue(current_params['lambda_235'])
                if 'lambda_232' in self.geo_params:
                    self.geo_params['lambda_232'].setValue(current_params['lambda_232'])

                if 'a0' in self.geo_params:
                    self.geo_params['a0'].setValue(current_params['a0'])
                if 'b0' in self.geo_params:
                    self.geo_params['b0'].setValue(current_params['b0'])
                if 'c0' in self.geo_params:
                    self.geo_params['c0'].setValue(current_params['c0'])

                if 'a1' in self.geo_params:
                    self.geo_params['a1'].setValue(current_params['a1'])
                if 'b1' in self.geo_params:
                    self.geo_params['b1'].setValue(current_params['b1'])
                if 'c1' in self.geo_params:
                    self.geo_params['c1'].setValue(current_params['c1'])

                if 'mu_M' in self.geo_params:
                    self.geo_params['mu_M'].setValue(current_params['mu_M'])
                if 'omega_M' in self.geo_params:
                    self.geo_params['omega_M'].setValue(current_params['omega_M'])
                if 'U_ratio' in self.geo_params:
                    self.geo_params['U_ratio'].setValue(current_params['U_ratio'])

                # 保存模型名称到状态
                app_state.geo_model_name = model_name

                print(f"[INFO] Loaded Geochemistry Model: {model_name}")

                # 如果当前是地球化学渲染模式，自动刷新
                if app_state.render_mode in ('V1V2', 'PB_EVOL_76', 'PB_EVOL_86', 'PB_MU_AGE', 'PB_KAPPA_AGE'):
                    self._on_change()

        except Exception as e:
            print(f"[ERROR] Failed to load geochemistry model: {e}")
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Failed to load geochemistry model: {error}").format(error=str(e))
            )

    def _on_apply_geo_params(self):
        """应用地球化学参数"""
        try:
            from data.geochemistry import engine

            # 收集参数
            params = {}

            # 时间参数（转换为年）
            if 'T1' in self.geo_params:
                params['T1'] = self.geo_params['T1'].value() * 1e6
            if 'T2' in self.geo_params:
                params['T2'] = self.geo_params['T2'].value() * 1e6
            if 'Tsec' in self.geo_params:
                params['Tsec'] = self.geo_params['Tsec'].value() * 1e6

            # 衰变常数
            if 'lambda_238' in self.geo_params:
                params['lambda_238'] = self.geo_params['lambda_238'].value()
            if 'lambda_235' in self.geo_params:
                params['lambda_235'] = self.geo_params['lambda_235'].value()
            if 'lambda_232' in self.geo_params:
                params['lambda_232'] = self.geo_params['lambda_232'].value()

            # 初始铅组成
            if 'a0' in self.geo_params:
                params['a0'] = self.geo_params['a0'].value()
            if 'b0' in self.geo_params:
                params['b0'] = self.geo_params['b0'].value()
            if 'c0' in self.geo_params:
                params['c0'] = self.geo_params['c0'].value()
            if 'a1' in self.geo_params:
                params['a1'] = self.geo_params['a1'].value()
            if 'b1' in self.geo_params:
                params['b1'] = self.geo_params['b1'].value()
            if 'c1' in self.geo_params:
                params['c1'] = self.geo_params['c1'].value()

            # 地幔参数
            if 'mu_M' in self.geo_params:
                params['mu_M'] = self.geo_params['mu_M'].value()
            if 'omega_M' in self.geo_params:
                params['omega_M'] = self.geo_params['omega_M'].value()
            if 'U_ratio' in self.geo_params:
                params['U_ratio'] = self.geo_params['U_ratio'].value()

            # 更新引擎参数
            engine.update_parameters(params)

            print(f"[INFO] Applied geochemistry parameters")

            # 如果当前是地球化学渲染模式，刷新绘图
            if app_state.render_mode in ('V1V2', 'PB_EVOL_76', 'PB_EVOL_86', 'PB_MU_AGE', 'PB_KAPPA_AGE'):
                self._on_change()

            QMessageBox.information(
                self,
                translate("Success"),
                translate("Geochemistry parameters applied successfully.")
            )

        except Exception as e:
            print(f"[ERROR] Failed to apply geochemistry parameters: {e}")
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Failed to apply parameters: {error}").format(error=str(e))
            )

    def _on_reset_geo_params(self):
        """重置地球化学参数为默认值"""
        try:
            from data.geochemistry import engine

            # 重新加载当前模型
            model_name = self.geo_model_combo.currentText()
            if engine.load_preset(model_name):
                # 触发模型变化事件来更新 UI
                self._on_geo_model_change(model_name)

                QMessageBox.information(
                    self,
                    translate("Success"),
                    translate("Parameters reset to defaults.")
                )

        except Exception as e:
            print(f"[ERROR] Failed to reset geochemistry parameters: {e}")
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Failed to reset parameters: {error}").format(error=str(e))
            )


def create_control_panel(callback):
    """创建控制面板工厂函数"""
    return Qt5ControlPanel(callback)


def create_section_dialog(section_key, callback, parent=None):
    """Create a dialog that hosts a single control section."""
    from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QApplication
    from core.localization import set_language

    section_key = (section_key or '').lower()

    section_map = {
        'data': ("Data", Qt5ControlPanel._build_data_section),
        'display': ("Display", Qt5ControlPanel._build_display_section),
        'analysis': ("Analysis", Qt5ControlPanel._build_analysis_section),
        'export': ("Export", Qt5ControlPanel._build_export_section),
        'legend': ("Legend", Qt5ControlPanel._build_legend_section),
        'geochemistry': ("Geochemistry", Qt5ControlPanel._build_geo_section),
    }

    if section_key not in section_map:
        return None

    title_key, builder = section_map[section_key]
    title = translate(title_key)

    dialog = QDialog(parent)
    dialog.setWindowTitle(title)

    root = QVBoxLayout(dialog)
    header = QHBoxLayout()
    title_label = QLabel(title)
    header.addWidget(title_label)
    header.addStretch()

    lang_label = QLabel(translate("Language"))
    header.addWidget(lang_label)

    lang_combo = QComboBox()
    lang_combo.setFixedWidth(140)
    lang_map = dict(available_languages())
    for code, label in lang_map.items():
        lang_combo.addItem(label, code)
    current_lang = getattr(app_state, 'language', None)
    if current_lang:
        idx = lang_combo.findData(current_lang)
        if idx >= 0:
            lang_combo.setCurrentIndex(idx)
    header.addWidget(lang_combo)
    root.addLayout(header)

    panel = Qt5ControlPanel(callback, parent=dialog, build_ui=False)
    panel._setup_styles()

    content_widget = builder(panel)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setWidget(content_widget)
    root.addWidget(scroll, 1)

    def _apply_adaptive_size():
        dialog.adjustSize()
        hint = dialog.sizeHint()
        screen = dialog.screen() or QApplication.primaryScreen()
        if screen is None:
            dialog.resize(hint)
            return
        bounds = screen.availableGeometry()
        max_w = int(bounds.width() * 0.9)
        max_h = int(bounds.height() * 0.85)
        min_w = 420
        min_h = 280
        target_w = min(max(hint.width(), min_w), max_w)
        target_h = min(max(hint.height(), min_h), max_h)
        dialog.resize(target_w, target_h)

    def _rebuild_section():
        panel._reset_ui_state()
        new_content = builder(panel)
        scroll.takeWidget()
        scroll.setWidget(new_content)
        QTimer.singleShot(0, _apply_adaptive_size)

    def _refresh_titles():
        new_title = translate(title_key)
        dialog.setWindowTitle(new_title)
        title_label.setText(new_title)
        lang_label.setText(translate("Language"))

    def _on_language_change(_index):
        code = lang_combo.currentData()
        if not code:
            return
        set_language(code)
        QTimer.singleShot(0, _refresh_titles)
        QTimer.singleShot(0, _rebuild_section)

    lang_combo.currentIndexChanged.connect(_on_language_change)

    def _on_show(_event):
        app_state.control_panel_ref = panel
        try:
            panel.update_selection_controls()
        except Exception:
            pass
        QTimer.singleShot(0, _apply_adaptive_size)

    def _on_language_refresh():
        current_lang = getattr(app_state, 'language', None)
        if current_lang:
            idx = lang_combo.findData(current_lang)
            if idx >= 0 and lang_combo.currentIndex() != idx:
                lang_combo.blockSignals(True)
                lang_combo.setCurrentIndex(idx)
                lang_combo.blockSignals(False)
        QTimer.singleShot(0, _refresh_titles)
        QTimer.singleShot(0, _rebuild_section)

    def _on_close(_event):
        if getattr(app_state, 'control_panel_ref', None) is panel:
            app_state.control_panel_ref = None
        listeners = getattr(app_state, 'language_listeners', [])
        if _on_language_refresh in listeners:
            listeners.remove(_on_language_refresh)

    dialog.showEvent = _on_show
    dialog.closeEvent = _on_close
    try:
        app_state.register_language_listener(_on_language_refresh)
    except Exception:
        pass

    return dialog
