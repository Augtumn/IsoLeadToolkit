"""显示面板 - UI 与绘图样式设置"""
import json
import logging

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QComboBox, QCheckBox, QSpinBox, QDoubleSpinBox,
    QLineEdit, QMessageBox, QGridLayout, QToolBox,
)

from core import translate, app_state, CONFIG
from .base_panel import BasePanel

logger = logging.getLogger(__name__)


class DisplayPanel(BasePanel):
    """显示标签页"""

    def __init__(self, callback=None, parent=None):
        super().__init__(callback, parent)
        self.legend_panel = None

    def reset_state(self):
        super().reset_state()
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
        self.legend_frame_on_check = None
        self.legend_frame_alpha_spin = None
        self.legend_frame_face_edit = None
        self.legend_frame_edge_edit = None

    def build(self) -> QWidget:
        widget = self._build_display_section()
        self._is_initialized = True
        return widget

    def _set_legend_position_button(self, inside_location, outside_location=None):
        panel = getattr(self, 'legend_panel', None)
        if panel is None:
            return
        if hasattr(panel, '_set_legend_inside_position_button'):
            panel._set_legend_inside_position_button(inside_location)
        if hasattr(panel, '_set_legend_outside_position_button'):
            panel._set_legend_outside_position_button(outside_location)



    def _build_display_section(self):
        """构建显示部分"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        section_toolbox = QToolBox()
        section_toolbox.setObjectName('display_section_toolbox')

        presets_page = QWidget()
        presets_layout = QVBoxLayout(presets_page)
        presets_layout.setContentsMargins(6, 6, 6, 6)
        presets_layout.setSpacing(8)

        style_page = QWidget()
        style_layout = QVBoxLayout(style_page)
        style_layout.setContentsMargins(6, 6, 6, 6)
        style_layout.setSpacing(8)

        axes_page = QWidget()
        axes_page_layout = QVBoxLayout(axes_page)
        axes_page_layout.setContentsMargins(6, 6, 6, 6)
        axes_page_layout.setSpacing(8)

        # Interface Theme
        theme_group = QGroupBox(translate("Interface Theme"))
        theme_group.setProperty('translate_key', 'Interface Theme')
        theme_layout = QVBoxLayout()
        theme_row = QHBoxLayout()
        ui_theme_label = QLabel(translate("UI Theme:"))
        ui_theme_label.setProperty('translate_key', 'UI Theme:')
        theme_row.addWidget(ui_theme_label)
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
        presets_layout.addWidget(theme_group)

        # Saved Plot Settings
        saved_group = QGroupBox(translate("Saved Plot Settings"))
        saved_group.setProperty('translate_key', 'Saved Plot Settings')
        saved_layout = QVBoxLayout()
        name_row = QHBoxLayout()
        theme_name_label = QLabel(translate("Theme Name:"))
        theme_name_label.setProperty('translate_key', 'Theme Name:')
        name_row.addWidget(theme_name_label)
        self.theme_name_edit = QLineEdit()
        name_row.addWidget(self.theme_name_edit)
        save_btn = QPushButton(translate("Save"))
        save_btn.setProperty('translate_key', 'Save')
        save_btn.clicked.connect(self._save_theme)
        name_row.addWidget(save_btn)
        saved_layout.addLayout(name_row)

        load_row = QHBoxLayout()
        load_theme_label = QLabel(translate("Load Theme:"))
        load_theme_label.setProperty('translate_key', 'Load Theme:')
        load_row.addWidget(load_theme_label)
        self.theme_load_combo = QComboBox()
        self.theme_load_combo.currentTextChanged.connect(self._load_theme)
        load_row.addWidget(self.theme_load_combo)
        delete_btn = QPushButton(translate("Delete"))
        delete_btn.setProperty('translate_key', 'Delete')
        delete_btn.clicked.connect(self._delete_theme)
        load_row.addWidget(delete_btn)
        saved_layout.addLayout(load_row)
        saved_group.setLayout(saved_layout)
        presets_layout.addWidget(saved_group)
        self._refresh_theme_list()

        # Font Settings
        font_group = QGroupBox(translate("Font Settings"))
        font_group.setProperty('translate_key', 'Font Settings')
        font_layout = QVBoxLayout()
        try:
            from visualization.style_manager import style_manager_instance
            all_fonts = ['<Default>'] + sorted(style_manager_instance.get_available_fonts())
        except Exception:
            all_fonts = ['<Default>']

        primary_row = QHBoxLayout()
        primary_font_label = QLabel(translate("Primary Font (English)"))
        primary_font_label.setProperty('translate_key', 'Primary Font (English)')
        primary_row.addWidget(primary_font_label)
        self.primary_font_combo = QComboBox()
        self.primary_font_combo.addItems(all_fonts)
        current_primary = getattr(app_state, 'custom_primary_font', '') or '<Default>'
        self.primary_font_combo.setCurrentText(current_primary)
        self.primary_font_combo.currentTextChanged.connect(self._on_style_change)
        primary_row.addWidget(self.primary_font_combo)
        font_layout.addLayout(primary_row)

        cjk_row = QHBoxLayout()
        cjk_font_label = QLabel(translate("CJK Font (Chinese)"))
        cjk_font_label.setProperty('translate_key', 'CJK Font (Chinese)')
        cjk_row.addWidget(cjk_font_label)
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
        self.show_title_check.setProperty('translate_key', 'Show Plot Title')
        self.show_title_check.setChecked(getattr(app_state, 'show_plot_title', False))
        self.show_title_check.stateChanged.connect(self._on_style_change)
        font_layout.addWidget(self.show_title_check)

        font_group.setLayout(font_layout)
        style_layout.addWidget(font_group)

        # Marker Settings
        marker_group = QGroupBox(translate("Marker Settings"))
        marker_group.setProperty('translate_key', 'Marker Settings')
        marker_layout = QVBoxLayout()
        marker_size_row = QHBoxLayout()
        marker_size_label = QLabel(translate("Size"))
        marker_size_label.setProperty('translate_key', 'Size')
        marker_size_row.addWidget(marker_size_label)
        self.marker_size_spin = QSpinBox()
        self.marker_size_spin.setRange(10, 500)
        self.marker_size_spin.setValue(int(getattr(app_state, 'plot_marker_size', 60)))
        self.marker_size_spin.valueChanged.connect(self._on_style_change)
        marker_size_row.addWidget(self.marker_size_spin)
        marker_layout.addLayout(marker_size_row)

        marker_alpha_row = QHBoxLayout()
        marker_alpha_label = QLabel(translate("Opacity"))
        marker_alpha_label.setProperty('translate_key', 'Opacity')
        marker_alpha_row.addWidget(marker_alpha_label)
        self.marker_alpha_spin = QDoubleSpinBox()
        self.marker_alpha_spin.setRange(0.1, 1.0)
        self.marker_alpha_spin.setSingleStep(0.05)
        self.marker_alpha_spin.setValue(float(getattr(app_state, 'plot_marker_alpha', 0.8)))
        self.marker_alpha_spin.valueChanged.connect(self._on_style_change)
        marker_alpha_row.addWidget(self.marker_alpha_spin)
        marker_layout.addLayout(marker_alpha_row)
        marker_group.setLayout(marker_layout)
        style_layout.addWidget(marker_group)

        # Axes & Lines
        axes_group = QGroupBox(translate("Axes & Lines"))
        axes_group.setProperty('translate_key', 'Axes & Lines')
        axes_layout = QVBoxLayout()
        auto_layout_btn = QPushButton(translate("Auto Layout"))
        auto_layout_btn.setProperty('translate_key', 'Auto Layout')
        auto_layout_btn.clicked.connect(self._apply_auto_layout)
        axes_layout.addWidget(auto_layout_btn)

        advanced_grid = QGridLayout()
        advanced_grid.setHorizontalSpacing(10)
        advanced_grid.setVerticalSpacing(8)
        advanced_grid.setColumnStretch(0, 1)
        advanced_grid.setColumnStretch(1, 1)
        section_index = {'value': 0}

        def add_row(grid, label_key, widget, row_idx):
            grid.addWidget(QLabel(translate(label_key)), row_idx, 0)
            grid.addWidget(widget, row_idx, 1)
            return row_idx + 1

        def make_group(title_key):
            group = QGroupBox(translate(title_key))
            group.setProperty('translate_key', title_key)
            grid = QGridLayout()
            grid.setColumnStretch(0, 1)
            grid.setColumnStretch(1, 2)
            group.setLayout(grid)
            index = section_index['value']
            row = index // 2
            col = index % 2
            advanced_grid.addWidget(group, row, col)
            section_index['value'] += 1
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
        self.grid_check.setProperty('translate_key', 'Show Grid')
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

        axes_layout.addLayout(advanced_grid)

        axes_group.setLayout(axes_layout)
        axes_page_layout.addWidget(axes_group)

        section_toolbox.addItem(presets_page, translate("Presets & Themes"))
        section_toolbox.addItem(style_page, translate("Text & Markers"))
        section_toolbox.addItem(axes_page, translate("Axes, Grid & Canvas"))
        layout.addWidget(section_toolbox)

        layout.addStretch()
        return widget

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
                logger.warning("Failed to load themes: %s", exc)
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
            'color_scheme': self.color_combo.currentText() if self.color_combo else getattr(app_state, 'color_scheme', 'vibrant'),
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
            'legend_position': getattr(app_state, 'legend_position', None),
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
        else:
            app_state.color_scheme = data.get('color_scheme', getattr(app_state, 'color_scheme', 'vibrant'))

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

        legend_outside = data.get('legend_location', None)
        legend_inside = data.get('legend_position', None)

        if legend_outside not in {'outside_left', 'outside_right'}:
            legend_outside = None

        app_state.legend_location = legend_outside
        app_state.legend_position = legend_inside
        self._set_legend_position_button(legend_inside, legend_outside)

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
