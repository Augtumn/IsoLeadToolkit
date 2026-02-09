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
        self.render_combo.addItems(["UMAP", "t-SNE", "PCA", "2D", "3D", "Ternary"])
        self.render_combo.setCurrentText(app_state.render_mode)
        self.render_combo.currentTextChanged.connect(self._on_render_mode_change)
        render_layout.addWidget(self.render_combo)

        render_group.setLayout(render_layout)
        layout.addWidget(render_group)

        # 算法选择（用于 UMAP/t-SNE/PCA）
        algo_group = QGroupBox(translate("Algorithm"))
        algo_layout = QVBoxLayout()

        self.algo_combo = QComboBox()
        self.algo_combo.addItems(["UMAP", "t-SNE", "PCA"])
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

        self.pca_group.setLayout(pca_layout)
        layout.addWidget(self.pca_group)

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

        # 模型曲线
        model_group = QGroupBox(translate("Model Curves"))
        model_layout = QVBoxLayout()

        self.show_model_check = QCheckBox(translate("Show model curves"))
        self.show_model_check.setChecked(app_state.show_model_curves)
        self.show_model_check.stateChanged.connect(self._on_model_curves_change)
        model_layout.addWidget(self.show_model_check)

        model_group.setLayout(model_layout)
        layout.addWidget(model_group)

        # 等时线
        isochron_group = QGroupBox(translate("Isochron"))
        isochron_layout = QVBoxLayout()

        self.show_isochron_check = QCheckBox(translate("Show isochron"))
        self.show_isochron_check.setChecked(app_state.show_isochrons)
        self.show_isochron_check.stateChanged.connect(self._on_isochron_change)
        isochron_layout.addWidget(self.show_isochron_check)

        # 计算等时线年龄按钮
        calc_isochron_btn = QPushButton(translate("Calculate Isochron Age"))
        calc_isochron_btn.clicked.connect(self._on_calculate_isochron)
        isochron_layout.addWidget(calc_isochron_btn)

        isochron_group.setLayout(isochron_layout)
        layout.addWidget(isochron_group)

        # V1V2 参数
        v1v2_group = QGroupBox(translate("V1V2 Parameters"))
        v1v2_layout = QVBoxLayout()

        # V1 输入
        v1_label = QLabel(translate("V1:"))
        v1v2_layout.addWidget(v1_label)

        self.v1_spin = QDoubleSpinBox()
        self.v1_spin.setRange(-1000.0, 1000.0)
        self.v1_spin.setSingleStep(0.1)
        self.v1_spin.setValue(app_state.v1_value)
        self.v1_spin.valueChanged.connect(self._on_v1_change)
        v1v2_layout.addWidget(self.v1_spin)

        # V2 输入
        v2_label = QLabel(translate("V2:"))
        v1v2_layout.addWidget(v2_label)

        self.v2_spin = QDoubleSpinBox()
        self.v2_spin.setRange(-1000.0, 1000.0)
        self.v2_spin.setSingleStep(0.1)
        self.v2_spin.setValue(app_state.v2_value)
        self.v2_spin.valueChanged.connect(self._on_v2_change)
        v1v2_layout.addWidget(self.v2_spin)

        v1v2_group.setLayout(v1v2_layout)
        layout.addWidget(v1v2_group)

        layout.addStretch()
        return widget

    # ========== 事件处理 ==========

    def _on_render_mode_change(self, mode):
        """渲染模式变化处理"""
        app_state.render_mode = mode

        # 如果是算法模式，同步算法选择
        if mode in ['UMAP', 't-SNE', 'PCA']:
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
        self.algo_group.setVisible(app_state.render_mode in ['UMAP', 't-SNE', 'PCA'])

        # 显示/隐藏参数组
        self.umap_group.setVisible(algorithm == 'UMAP')
        self.tsne_group.setVisible(algorithm == 't-SNE')
        self.pca_group.setVisible(algorithm == 'PCA')

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

    def _on_standardize_change(self, state):
        """标准化选项变化"""
        app_state.standardize_data = (state == Qt.Checked)
        self._on_change()

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

        if not app_state.group_col or app_state.df_global is None:
            return

        # 获取所有分组
        groups = app_state.df_global[app_state.group_col].unique()

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
        if app_state.group_col and app_state.df_global is not None:
            groups = app_state.df_global[app_state.group_col].unique()
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

    def _on_v1_change(self, value):
        """V1 参数变化"""
        app_state.v1_value = value
        self._on_change()

    def _on_v2_change(self, value):
        """V2 参数变化"""
        app_state.v2_value = value
        self._on_change()


def create_control_panel(callback):
    """创建控制面板工厂函数"""
    return Qt5ControlPanel(callback)
