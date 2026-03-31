"""Display panel UI construction and control helpers."""

from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QToolBox,
    QVBoxLayout,
    QWidget,
)

from core import app_state, translate
from ui.icons import apply_color_swatch, normalize_color_hex


class DisplayBuildMixin:
    """Build and widget helpers for display panel."""

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
        self.scatter_edge_check = None
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
        self.adjust_force_text_x_spin = None
        self.adjust_force_text_y_spin = None
        self.adjust_force_static_x_spin = None
        self.adjust_force_static_y_spin = None
        self.adjust_expand_x_spin = None
        self.adjust_expand_y_spin = None
        self.adjust_iter_lim_spin = None
        self.adjust_time_lim_spin = None

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

    def _normalize_color_value(self, value: str, fallback: str) -> str:
        """Normalize a color string to a valid hex representation."""
        return normalize_color_hex(value, fallback)

    def _set_color_button(self, button: QPushButton, color_value: str) -> None:
        normalized = apply_color_swatch(button, color_value, fallback='#e2e8f0', marker='s', icon_size=16)
        button.setToolTip(f"{translate('Choose Color')}: {normalized}")

    def _set_color_control_value(
        self,
        control: QWidget | None,
        value: str,
        fallback: str,
        trigger_refresh: bool = False,
    ) -> None:
        """Sync a color control value and trigger refresh when requested."""
        if control is None:
            return
        normalized = self._normalize_color_value(value, fallback)
        if isinstance(control, QPushButton):
            self._set_color_button(control, normalized)
        elif isinstance(control, QLineEdit):
            control.setText(normalized)
        if trigger_refresh:
            self._on_style_change()

    def _get_color_control_value(self, control: QWidget | None, fallback: str) -> str:
        """Return the normalized color represented by a display control."""
        if control is None:
            return fallback
        if isinstance(control, QPushButton):
            return self._normalize_color_value(control.property('color_value') or '', fallback)
        if isinstance(control, QLineEdit):
            return self._normalize_color_value(control.text(), fallback)
        return fallback

    def _sync_color_controls_from_state(self) -> None:
        """Initialize all display color controls from current app_state values."""
        color_bindings = [
            ('figure_bg_edit', 'plot_facecolor', '#ffffff'),
            ('axes_bg_edit', 'axes_facecolor', '#ffffff'),
            ('grid_color_edit', 'grid_color', '#e2e8f0'),
            ('minor_grid_color_edit', 'minor_grid_color', '#e2e8f0'),
            ('tick_color_edit', 'tick_color', '#1f2937'),
            ('axis_line_color_edit', 'axis_line_color', '#1f2937'),
            ('label_color_edit', 'label_color', '#1f2937'),
            ('title_color_edit', 'title_color', '#111827'),
        ]
        for control_attr, state_attr, fallback in color_bindings:
            control = getattr(self, control_attr, None)
            if control is None:
                continue
            value = getattr(app_state, state_attr, fallback)
            self._set_color_control_value(control, value, fallback, trigger_refresh=False)

    def _create_color_picker(self, initial_color: str) -> tuple[QWidget, QPushButton]:
        """Create a curve-style color picker: button opens dialog and shows current color."""
        normalized = self._normalize_color_value(initial_color, '#e2e8f0')

        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        color_button = QPushButton()
        color_button.setFixedSize(20, 16)
        self._set_color_button(color_button, normalized)
        row.addWidget(color_button)
        row.addStretch()

        def _pick_color() -> None:
            current_color = self._get_color_control_value(color_button, normalized)
            chosen = QColorDialog.getColor(QColor(current_color), self, translate("Choose Color"))
            if chosen.isValid():
                self._set_color_control_value(color_button, chosen.name(), normalized, trigger_refresh=True)

        color_button.clicked.connect(_pick_color)

        return container, color_button

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
        self.marker_size_spin.setRange(1, 500)
        self.marker_size_spin.setValue(int(getattr(app_state, 'plot_marker_size', 60)))
        self.marker_size_spin.valueChanged.connect(self._on_style_change)
        marker_size_row.addWidget(self.marker_size_spin)
        marker_layout.addLayout(marker_size_row)

        marker_alpha_row = QHBoxLayout()
        marker_alpha_label = QLabel(translate("Opacity"))
        marker_alpha_label.setProperty('translate_key', 'Opacity')
        marker_alpha_row.addWidget(marker_alpha_label)
        self.marker_alpha_spin = QDoubleSpinBox()
        self.marker_alpha_spin.setRange(0.02, 1.0)
        self.marker_alpha_spin.setSingleStep(0.02)
        self.marker_alpha_spin.setDecimals(2)
        self.marker_alpha_spin.setValue(float(getattr(app_state, 'plot_marker_alpha', 0.8)))
        self.marker_alpha_spin.valueChanged.connect(self._on_style_change)
        marker_alpha_row.addWidget(self.marker_alpha_spin)
        marker_layout.addLayout(marker_alpha_row)

        marker_edge_row = QHBoxLayout()
        self.scatter_edge_check = QCheckBox(translate("Show Marker Edge"))
        self.scatter_edge_check.setProperty('translate_key', 'Show Marker Edge')
        self.scatter_edge_check.setChecked(bool(getattr(app_state, 'scatter_show_edge', True)))
        self.scatter_edge_check.stateChanged.connect(self._on_style_change)
        marker_edge_row.addWidget(self.scatter_edge_check)
        marker_edge_row.addStretch()
        marker_layout.addLayout(marker_edge_row)

        marker_edge_color_row = QHBoxLayout()
        marker_edge_color_row.addWidget(QLabel(translate("Scatter Edge Color")))
        marker_edge_editor, self.scatter_edgecolor_edit = self._create_color_picker(
            getattr(app_state, 'scatter_edgecolor', '#1e293b')
        )
        marker_edge_color_row.addWidget(marker_edge_editor, 1)
        marker_layout.addLayout(marker_edge_color_row)

        marker_edge_width_row = QHBoxLayout()
        marker_edge_width_row.addWidget(QLabel(translate("Scatter Edge Width")))
        self.scatter_edgewidth_spin = QDoubleSpinBox()
        self.scatter_edgewidth_spin.setRange(0.0, 3.0)
        self.scatter_edgewidth_spin.setSingleStep(0.1)
        self.scatter_edgewidth_spin.setValue(float(getattr(app_state, 'scatter_edgewidth', 0.4)))
        self.scatter_edgewidth_spin.valueChanged.connect(self._on_style_change)
        marker_edge_width_row.addWidget(self.scatter_edgewidth_spin)
        marker_layout.addLayout(marker_edge_width_row)
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
            axes_layout.addWidget(group)
            return grid

        figure_grid = make_group("Figure")
        row = 0
        self.figure_dpi_spin = QSpinBox()
        self.figure_dpi_spin.setRange(50, 600)
        self.figure_dpi_spin.setValue(int(getattr(app_state, 'plot_dpi', 130)))
        self.figure_dpi_spin.valueChanged.connect(self._on_style_change)
        row = add_row(figure_grid, "Figure DPI", self.figure_dpi_spin, row)

        figure_bg_editor, self.figure_bg_edit = self._create_color_picker(
            getattr(app_state, 'plot_facecolor', '#ffffff')
        )
        row = add_row(figure_grid, "Figure Background", figure_bg_editor, row)

        axes_bg_editor, self.axes_bg_edit = self._create_color_picker(
            getattr(app_state, 'axes_facecolor', '#ffffff')
        )
        row = add_row(figure_grid, "Axes Background", axes_bg_editor, row)

        grid_grid = make_group("Grid")
        row = 0
        self.grid_check = QCheckBox(translate("Show Grid"))
        self.grid_check.setProperty('translate_key', 'Show Grid')
        self.grid_check.setChecked(getattr(app_state, 'plot_style_grid', False))
        self.grid_check.stateChanged.connect(self._on_style_change)
        row = add_row(grid_grid, "Show Grid", self.grid_check, row)

        grid_color_editor, self.grid_color_edit = self._create_color_picker(
            getattr(app_state, 'grid_color', '#e2e8f0')
        )
        row = add_row(grid_grid, "Grid Color", grid_color_editor, row)

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

        minor_grid_editor, self.minor_grid_color_edit = self._create_color_picker(
            getattr(app_state, 'minor_grid_color', '#e2e8f0')
        )
        row = add_row(grid_grid, "Minor Grid Color", minor_grid_editor, row)

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

        tick_color_editor, self.tick_color_edit = self._create_color_picker(
            getattr(app_state, 'tick_color', '#1f2937')
        )
        row = add_row(tick_grid, "Tick Color", tick_color_editor, row)

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

        axis_color_editor, self.axis_line_color_edit = self._create_color_picker(
            getattr(app_state, 'axis_line_color', '#1f2937')
        )
        row = add_row(spine_grid, "Axis Line Color", axis_color_editor, row)

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
        label_color_editor, self.label_color_edit = self._create_color_picker(
            getattr(app_state, 'label_color', '#1f2937')
        )
        row = add_row(text_grid, "Label Color", label_color_editor, row)

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

        title_color_editor, self.title_color_edit = self._create_color_picker(
            getattr(app_state, 'title_color', '#111827')
        )
        row = add_row(text_grid, "Title Color", title_color_editor, row)

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

        label_layout_grid = make_group("Label Layout (adjustText)")
        row = 0
        force_text = getattr(app_state, 'adjust_text_force_text', (0.8, 1.0))
        force_static = getattr(app_state, 'adjust_text_force_static', (0.4, 0.6))
        expand = getattr(app_state, 'adjust_text_expand', (1.08, 1.20))

        self.adjust_force_text_x_spin = QDoubleSpinBox()
        self.adjust_force_text_x_spin.setRange(0.0, 3.0)
        self.adjust_force_text_x_spin.setSingleStep(0.05)
        self.adjust_force_text_x_spin.setDecimals(2)
        self.adjust_force_text_x_spin.setValue(float(force_text[0]))
        self.adjust_force_text_x_spin.valueChanged.connect(self._on_style_change)
        row = add_row(label_layout_grid, "Adjust Force Text X", self.adjust_force_text_x_spin, row)

        self.adjust_force_text_y_spin = QDoubleSpinBox()
        self.adjust_force_text_y_spin.setRange(0.0, 3.0)
        self.adjust_force_text_y_spin.setSingleStep(0.05)
        self.adjust_force_text_y_spin.setDecimals(2)
        self.adjust_force_text_y_spin.setValue(float(force_text[1]))
        self.adjust_force_text_y_spin.valueChanged.connect(self._on_style_change)
        row = add_row(label_layout_grid, "Adjust Force Text Y", self.adjust_force_text_y_spin, row)

        self.adjust_force_static_x_spin = QDoubleSpinBox()
        self.adjust_force_static_x_spin.setRange(0.0, 3.0)
        self.adjust_force_static_x_spin.setSingleStep(0.05)
        self.adjust_force_static_x_spin.setDecimals(2)
        self.adjust_force_static_x_spin.setValue(float(force_static[0]))
        self.adjust_force_static_x_spin.valueChanged.connect(self._on_style_change)
        row = add_row(label_layout_grid, "Adjust Force Static X", self.adjust_force_static_x_spin, row)

        self.adjust_force_static_y_spin = QDoubleSpinBox()
        self.adjust_force_static_y_spin.setRange(0.0, 3.0)
        self.adjust_force_static_y_spin.setSingleStep(0.05)
        self.adjust_force_static_y_spin.setDecimals(2)
        self.adjust_force_static_y_spin.setValue(float(force_static[1]))
        self.adjust_force_static_y_spin.valueChanged.connect(self._on_style_change)
        row = add_row(label_layout_grid, "Adjust Force Static Y", self.adjust_force_static_y_spin, row)

        self.adjust_expand_x_spin = QDoubleSpinBox()
        self.adjust_expand_x_spin.setRange(1.0, 2.5)
        self.adjust_expand_x_spin.setSingleStep(0.02)
        self.adjust_expand_x_spin.setDecimals(2)
        self.adjust_expand_x_spin.setValue(float(expand[0]))
        self.adjust_expand_x_spin.valueChanged.connect(self._on_style_change)
        row = add_row(label_layout_grid, "Adjust Expand X", self.adjust_expand_x_spin, row)

        self.adjust_expand_y_spin = QDoubleSpinBox()
        self.adjust_expand_y_spin.setRange(1.0, 2.5)
        self.adjust_expand_y_spin.setSingleStep(0.02)
        self.adjust_expand_y_spin.setDecimals(2)
        self.adjust_expand_y_spin.setValue(float(expand[1]))
        self.adjust_expand_y_spin.valueChanged.connect(self._on_style_change)
        row = add_row(label_layout_grid, "Adjust Expand Y", self.adjust_expand_y_spin, row)

        self.adjust_iter_lim_spin = QSpinBox()
        self.adjust_iter_lim_spin.setRange(10, 1000)
        self.adjust_iter_lim_spin.setValue(int(getattr(app_state, 'adjust_text_iter_lim', 120)))
        self.adjust_iter_lim_spin.valueChanged.connect(self._on_style_change)
        row = add_row(label_layout_grid, "Adjust Iteration Limit", self.adjust_iter_lim_spin, row)

        self.adjust_time_lim_spin = QDoubleSpinBox()
        self.adjust_time_lim_spin.setRange(0.05, 2.0)
        self.adjust_time_lim_spin.setSingleStep(0.05)
        self.adjust_time_lim_spin.setDecimals(2)
        self.adjust_time_lim_spin.setValue(float(getattr(app_state, 'adjust_text_time_lim', 0.25)))
        self.adjust_time_lim_spin.valueChanged.connect(self._on_style_change)
        row = add_row(label_layout_grid, "Adjust Time Limit (s)", self.adjust_time_lim_spin, row)

        axes_group.setLayout(axes_layout)
        axes_page_layout.addWidget(axes_group)

        section_toolbox.addItem(presets_page, translate("Presets & Themes"))
        section_toolbox.addItem(style_page, translate("Text & Markers"))
        section_toolbox.addItem(axes_page, translate("Axes, Grid & Canvas"))
        layout.addWidget(section_toolbox)

        self._sync_color_controls_from_state()

        layout.addStretch()
        return widget
