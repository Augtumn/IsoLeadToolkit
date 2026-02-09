"""
Qt5 控制面板
提供算法参数调整和可视化设置
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                              QStackedWidget, QPushButton, QLabel,
                              QFrame, QScrollArea, QToolButton,
                              QComboBox, QCheckBox, QRadioButton,
                              QSlider, QProgressBar, QGroupBox,
                              QLineEdit, QSpinBox, QDoubleSpinBox,
                              QTabWidget, QGridLayout, QListWidget,
                              QListWidgetItem, QSizePolicy, QMessageBox)
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QTimer, pyqtSlot
from PyQt5.QtGui import QIcon, QFont, QPalette, QColor

from core import translate, app_state
from core.localization import available_languages


class Qt5ControlPanel(QWidget):
    """Qt5 控制面板"""

    # 信号定义
    parameter_changed = pyqtSignal(str, object)

    def __init__(self, callback=None, parent=None):
        super().__init__(parent)
        self.callback = callback
        self._translations = {}

        # 初始化变量
        self.sliders = {}
        self.labels = {}
        self.radio_vars = {}
        self.check_vars = {}
        self._slider_steps = {}
        self._slider_delay_ms = 350
        self._slider_timers = {}

        # 样式常量
        self.primary_bg = "#edf2f7"
        self.card_bg = "#ffffff"

        self._setup_ui()
        self._setup_styles()
        self._refresh_language()

        # 注册语言监听器
        app_state.register_language_listener(self._refresh_language)

    def _setup_ui(self):
        """设置 UI"""
        self.setWindowTitle(translate("Control Panel"))
        self.setMinimumWidth(520)
        self.resize(560, 860)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 标题栏
        self._create_header(layout)

        # 主内容区（侧边导航 + 内容）
        content_wrap = QHBoxLayout()
        content_wrap.setSpacing(10)

        # 侧边导航
        self.nav_frame = QFrame()
        self.nav_frame.setFixedWidth(120)
        self.nav_layout = QVBoxLayout(self.nav_frame)
        self.nav_layout.setContentsMargins(0, 0, 0, 0)
        self.nav_layout.setSpacing(2)

        self.section_buttons = {}
        self._create_navigation()

        # 内容区域
        self.content_stack = QStackedWidget()
        self._create_content()

        content_wrap.addWidget(self.nav_frame)
        content_wrap.addWidget(self.content_stack, 1)

        layout.addLayout(content_wrap, 1)

        # 底部按钮
        self._create_footer(layout)

    def _create_header(self, layout):
        """创建标题栏"""
        header = QHBoxLayout()

        title = QLabel(translate("Visualization Controls"))
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        header.addWidget(title)

        self.data_count_label = QLabel()
        header.addWidget(self.data_count_label, alignment=Qt.AlignRight)

        layout.addLayout(header)

        # 更新数据计数
        self._update_data_count_label()

    def _create_navigation(self):
        """创建侧边导航"""
        sections = [
            ("Modeling", self._build_modeling_section),
            ("Display", self._build_display_section),
            ("Legend", self._build_legend_section),
            ("Tools", self._build_tools_section),
            ("Geochemistry", self._build_geo_section),
        ]

        for name, builder in sections:
            btn = QPushButton(translate(name))
            btn.setCheckable(True)
            btn.setChecked(len(self.section_buttons) == 0)
            btn.clicked.connect(lambda checked, n=name: self._show_section(n))
            self.nav_layout.addWidget(btn)
            self.section_buttons[name] = btn

        self.nav_layout.addStretch()

    def _create_content(self):
        """创建内容区域"""
        sections = [
            ("Modeling", self._build_modeling_section),
            ("Display", self._build_display_section),
            ("Legend", self._build_legend_section),
            ("Tools", self._build_tools_section),
            ("Geochemistry", self._build_geo_section),
        ]

        for name, builder in sections:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.NoFrame)

            content = builder()
            scroll.setWidget(content)

            self.content_stack.addWidget(scroll)

    def _show_section(self, name):
        """显示指定部分"""
        for n, btn in self.section_buttons.items():
            btn.setChecked(n == name)
        index = list(self.section_buttons.keys()).index(name)
        self.content_stack.setCurrentIndex(index)

    def _create_footer(self, layout):
        """创建底部按钮"""
        footer = QHBoxLayout()

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        footer.addWidget(spacer)

        close_btn = QPushButton(translate("Close Panel"))
        close_btn.clicked.connect(self.hide)
        footer.addWidget(close_btn)

        layout.addLayout(footer)

    def _setup_styles(self):
        """设置样式"""
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {self.primary_bg};
            }}
            QPushButton {{
                background-color: white;
                border: 1px solid #cbd5e0;
                border-radius: 4px;
                padding: 8px 12px;
                min-width: 80px;
            }}
            QPushButton:checked {{
                background-color: #2563eb;
                color: white;
                border-color: #2563eb;
            }}
            QPushButton:hover {{
                background-color: #f7fafc;
            }}
            QPushButton:checked:hover {{
                background-color: #1d4ed8;
            }}
            QGroupBox {{
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
        """)

    def _refresh_language(self):
        """刷新语言"""
        current_lang = app_state.language
        # TODO: 实现翻译刷新逻辑
        self._update_data_count_label()

    def _update_data_count_label(self):
        """更新数据计数标签"""
        if app_state.df_global is not None:
            count = len(app_state.df_global)
            text = translate("Loaded Data: {count} rows", count=count)
            self.data_count_label.setText(text)
        else:
            self.data_count_label.setText("")

    def _on_change(self):
        """参数变化回调"""
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

        # 渲染模式选择
        render_group = QGroupBox(translate("Render Mode"))
        render_layout = QVBoxLayout()

        self.render_combo = QComboBox()
        self.render_combo.addItems(["UMAP", "t-SNE", "PCA", "RobustPCA", "2D", "3D", "Ternary", "PB_EVOL_76", "PB_EVOL_86"])
        self.render_combo.setCurrentText(app_state.render_mode)
        self.render_combo.currentTextChanged.connect(self._on_render_mode_change)
        render_layout.addWidget(self.render_combo)

        render_group.setLayout(render_layout)
        layout.addWidget(render_group)

        # 算法选择（用于 UMAP/t-SNE/PCA）
        algo_group = QGroupBox(translate("Algorithm"))
        algo_layout = QVBoxLayout()

        self.algo_combo = QComboBox()
        self.algo_combo.addItems(["UMAP", "t-SNE", "PCA", "RobustPCA"])
        self.algo_combo.setCurrentText(app_state.algorithm)
        self.algo_combo.currentTextChanged.connect(self._on_algorithm_change)
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
        n_slider.setMaximum(200)
        n_slider.setValue(app_state.umap_params['n_neighbors'])
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
        perp_slider.setMaximum(50)
        perp_slider.setValue(int(app_state.tsne_params['perplexity']))
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

        # 根据当前算法显示/隐藏参数组
        self._update_algorithm_visibility()

        layout.addStretch()
        return widget

    def _build_display_section(self):
        """构建显示部分"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)

        # 点大小
        size_group = QGroupBox(translate("Point Size"))
        size_layout = QVBoxLayout()

        size_label = QLabel(translate("Size: {value}").format(value=app_state.point_size))
        size_layout.addWidget(size_label)

        size_slider = QSlider(Qt.Horizontal)
        size_slider.setMinimum(10)
        size_slider.setMaximum(200)
        size_slider.setValue(app_state.point_size)
        size_slider.valueChanged.connect(lambda v: self._on_point_size_change(v, size_label))
        size_layout.addWidget(size_slider)

        self.sliders['point_size'] = size_slider
        self.labels['point_size'] = size_label

        size_group.setLayout(size_layout)
        layout.addWidget(size_group)

        # 样式选项
        style_group = QGroupBox(translate("Plot Style"))
        style_layout = QVBoxLayout()

        # 网格显示
        self.grid_check = QCheckBox(translate("Show grid"))
        self.grid_check.setChecked(app_state.plot_style_grid)
        self.grid_check.stateChanged.connect(self._on_grid_change)
        style_layout.addWidget(self.grid_check)

        # KDE 显示
        self.kde_check = QCheckBox(translate("Show KDE"))
        self.kde_check.setChecked(app_state.show_kde)
        self.kde_check.stateChanged.connect(self._on_kde_change)
        style_layout.addWidget(self.kde_check)

        # 边际 KDE
        self.marginal_kde_check = QCheckBox(translate("Show marginal KDE"))
        self.marginal_kde_check.setChecked(app_state.show_marginal_kde)
        self.marginal_kde_check.stateChanged.connect(self._on_marginal_kde_change)
        style_layout.addWidget(self.marginal_kde_check)

        # 椭圆显示
        self.ellipse_check = QCheckBox(translate("Show ellipses"))
        self.ellipse_check.setChecked(app_state.show_ellipses)
        self.ellipse_check.stateChanged.connect(self._on_ellipse_change)
        style_layout.addWidget(self.ellipse_check)

        style_group.setLayout(style_layout)
        layout.addWidget(style_group)

        # 颜色方案
        color_group = QGroupBox(translate("Color Scheme"))
        color_layout = QVBoxLayout()

        self.color_combo = QComboBox()
        self.color_combo.addItems(['vibrant', 'pastel', 'deep', 'muted', 'bright', 'dark'])
        self.color_combo.setCurrentText(app_state.color_scheme)
        self.color_combo.currentTextChanged.connect(self._on_color_scheme_change)
        color_layout.addWidget(self.color_combo)

        color_group.setLayout(color_layout)
        layout.addWidget(color_group)

        layout.addStretch()
        return widget

    def _build_legend_section(self):
        """构建图例部分"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)

        # 分组可见性
        group_visibility_group = QGroupBox(translate("Group Visibility"))
        group_layout = QVBoxLayout()

        # 分组列表
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

        self.legend_position_combo = QComboBox()
        self.legend_position_combo.addItems([
            'best', 'upper right', 'upper left', 'lower left', 'lower right',
            'right', 'center left', 'center right', 'lower center', 'upper center', 'center'
        ])
        self.legend_position_combo.setCurrentText(app_state.legend_position)
        self.legend_position_combo.currentTextChanged.connect(self._on_legend_position_change)
        position_layout.addWidget(self.legend_position_combo)

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

    def _build_tools_section(self):
        """构建工具部分"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)

        # 导出按钮
        export_btn = QPushButton(translate("Export Selected"))
        export_btn.clicked.connect(self._on_export_clicked)
        layout.addWidget(export_btn)

        layout.addStretch()
        return widget

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

        apply_btn = QPushButton(translate("Apply Changes"))
        apply_btn.clicked.connect(self._on_apply_geo_params)
        button_layout.addWidget(apply_btn)

        reset_btn = QPushButton(translate("Reset Defaults"))
        reset_btn.clicked.connect(self._on_reset_geo_params)
        button_layout.addWidget(reset_btn)

        layout.addLayout(button_layout)

        # 显示选项
        display_group = QGroupBox(translate("Display Options"))
        display_layout = QVBoxLayout()

        self.show_model_check = QCheckBox(translate("Show model curves"))
        self.show_model_check.setChecked(app_state.show_model_curves)
        self.show_model_check.stateChanged.connect(self._on_model_curves_change)
        display_layout.addWidget(self.show_model_check)

        self.show_paleoisochron_check = QCheckBox(translate("Show paleoisochrons"))
        self.show_paleoisochron_check.setChecked(app_state.show_paleoisochrons)
        self.show_paleoisochron_check.stateChanged.connect(self._on_paleoisochron_change)
        display_layout.addWidget(self.show_paleoisochron_check)

        self.show_model_age_check = QCheckBox(translate("Show model age lines"))
        self.show_model_age_check.setChecked(app_state.show_model_age_lines)
        self.show_model_age_check.stateChanged.connect(self._on_model_age_change)
        display_layout.addWidget(self.show_model_age_check)

        self.show_isochron_check = QCheckBox(translate("Show isochron"))
        self.show_isochron_check.setChecked(app_state.show_isochrons)
        self.show_isochron_check.stateChanged.connect(self._on_isochron_change)
        display_layout.addWidget(self.show_isochron_check)

        # 计算等时线年龄按钮
        calc_isochron_btn = QPushButton(translate("Calculate Isochron Age"))
        calc_isochron_btn.clicked.connect(self._on_calculate_isochron)
        display_layout.addWidget(calc_isochron_btn)

        display_group.setLayout(display_layout)
        layout.addWidget(display_group)

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
        app_state.render_mode = mode

        # 如果是算法模式，同步算法选择
        if mode in ['UMAP', 't-SNE', 'PCA', 'RobustPCA']:
            app_state.algorithm = mode
            self.algo_combo.setCurrentText(mode)
            self._update_algorithm_visibility()

        # 如果是 2D/3D/Ternary，可能需要弹出列选择对话框
        if mode == '2D' and not app_state.selected_2d_confirmed:
            self._show_2d_column_dialog()
        elif mode == '3D' and not app_state.selected_3d_confirmed:
            self._show_3d_column_dialog()
        elif mode == 'Ternary' and not app_state.selected_ternary_confirmed:
            self._show_ternary_column_dialog()

        self._on_change()

    def _on_algorithm_change(self, algorithm):
        """算法变化处理"""
        app_state.algorithm = algorithm
        app_state.render_mode = algorithm
        self.render_combo.setCurrentText(algorithm)
        self._update_algorithm_visibility()
        self._on_change()

    def _update_algorithm_visibility(self):
        """根据当前算法更新参数组可见性"""
        algorithm = app_state.algorithm

        # 显示/隐藏算法组
        self.algo_group.setVisible(app_state.render_mode in ['UMAP', 't-SNE', 'PCA', 'RobustPCA'])

        # 显示/隐藏参数组
        self.umap_group.setVisible(algorithm == 'UMAP')
        self.tsne_group.setVisible(algorithm == 't-SNE')
        self.pca_group.setVisible(algorithm == 'PCA')
        self.robust_pca_group.setVisible(algorithm == 'RobustPCA')

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

    def _on_pca_param_change(self, param, value):
        """PCA 参数变化"""
        app_state.pca_params[param] = value
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
        self._on_change()

    def _on_marginal_kde_change(self, state):
        """边际 KDE 显示变化"""
        app_state.show_marginal_kde = (state == Qt.Checked)
        self._on_change()

    def _on_ellipse_change(self, state):
        """椭圆显示变化"""
        app_state.show_ellipses = (state == Qt.Checked)
        self._on_change()

    def _on_color_scheme_change(self, scheme):
        """颜色方案变化"""
        app_state.color_scheme = scheme
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
        from ui.qt5_dialogs.two_d_dialog import get_2d_column_selection

        result = get_2d_column_selection()
        if result:
            app_state.selected_2d_cols = result
            app_state.selected_2d_confirmed = True
            print(f"[INFO] Selected 2D columns: {result}", flush=True)
            self._on_change()

    def _show_3d_column_dialog(self):
        """显示 3D 列选择对话框"""
        from ui.qt5_dialogs.three_d_dialog import get_3d_column_selection

        result = get_3d_column_selection()
        if result:
            app_state.selected_3d_cols = result
            app_state.selected_3d_confirmed = True
            print(f"[INFO] Selected 3D columns: {result}", flush=True)
            self._on_change()

    def _show_ternary_column_dialog(self):
        """显示三元图列选择对话框"""
        from ui.qt5_dialogs.ternary_dialog import get_ternary_column_selection

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
        """更新分组列表"""
        self.group_list.clear()

        if not app_state.last_group_col or app_state.df_global is None:
            return

        # 获取所有分组
        groups = app_state.df_global[app_state.last_group_col].unique()

        for group in groups:
            item = QListWidgetItem(str(group))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            # 检查分组是否可见
            is_visible = group not in app_state.hidden_groups
            item.setCheckState(Qt.Checked if is_visible else Qt.Unchecked)
            self.group_list.addItem(item)

    def _on_group_visibility_change(self, item):
        """分组可见性变化"""
        group_name = item.text()
        is_checked = item.checkState() == Qt.Checked

        if is_checked:
            # 显示分组
            if group_name in app_state.hidden_groups:
                app_state.hidden_groups.remove(group_name)
        else:
            # 隐藏分组
            if group_name not in app_state.hidden_groups:
                app_state.hidden_groups.add(group_name)

        self._on_change()

    def _show_all_groups(self):
        """显示所有分组"""
        app_state.hidden_groups.clear()
        self._update_group_list()
        self._on_change()

    def _hide_all_groups(self):
        """隐藏所有分组"""
        if app_state.last_group_col and app_state.df_global is not None:
            groups = app_state.df_global[app_state.last_group_col].unique()
            app_state.hidden_groups = set(groups)
            self._update_group_list()
            self._on_change()

    def _on_legend_position_change(self, position):
        """图例位置变化"""
        app_state.legend_position = position
        self._on_change()

    def _on_legend_columns_change(self, columns):
        """图例列数变化"""
        app_state.legend_columns = columns
        self._on_change()

    def _on_model_curves_change(self, state):
        """模型曲线显示变化"""
        app_state.show_model_curves = (state == Qt.Checked)
        self._on_change()

    def _on_paleoisochron_change(self, state):
        """古等时线显示变化"""
        app_state.show_paleoisochrons = (state == Qt.Checked)
        self._on_change()

    def _on_model_age_change(self, state):
        """模型年龄线显示变化"""
        app_state.show_model_age_lines = (state == Qt.Checked)
        self._on_change()

    def _on_isochron_change(self, state):
        """等时线显示变化"""
        app_state.show_isochrons = (state == Qt.Checked)
        self._on_change()

    def _on_calculate_isochron(self):
        """计算等时线年龄"""
        # TODO: 实现等时线年龄计算
        QMessageBox.information(
            self,
            translate("Info"),
            translate("Isochron age calculation will be implemented.")
        )

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
