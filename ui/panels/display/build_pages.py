from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
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


class DisplayBuildPagesMixin:
    """Presets, theme, font and marker page builders for the display panel."""

    def _build_theme_page(self, presets_layout):
            """Build the interface theme controls."""
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
            current_theme = app_state.ui_theme
            if current_theme in theme_names:
                self.ui_theme_combo.setCurrentText(current_theme)
            self.ui_theme_combo.currentTextChanged.connect(self._on_ui_theme_change)
            theme_row.addWidget(self.ui_theme_combo)
            theme_layout.addLayout(theme_row)
            theme_group.setLayout(theme_layout)
            presets_layout.addWidget(theme_group)


    def _build_saved_settings_page(self, presets_layout):
            """Build the saved plot settings controls."""
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


    def _build_font_page(self, style_layout):
            """Build the fonts controls."""
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
            current_primary = app_state.custom_primary_font or '<Default>'
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
            current_cjk = app_state.custom_cjk_font or '<Default>'
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
                size_label = QLabel(translate(label_key))
                size_label.setProperty('translate_key', label_key)
                size_grid.addWidget(size_label, row, 0)
                spin = QSpinBox()
                spin.setRange(6, 36)
                spin.setValue(app_state.plot_font_sizes.get(key, default))
                spin.valueChanged.connect(self._on_style_change)
                size_grid.addWidget(spin, row, 1)
                self.font_size_spins[key] = spin
            font_layout.addLayout(size_grid)

            self.show_title_check = QCheckBox(translate("Show Plot Title"))
            self.show_title_check.setProperty('translate_key', 'Show Plot Title')
            self.show_title_check.setChecked(app_state.show_plot_title)
            self.show_title_check.stateChanged.connect(self._on_style_change)
            font_layout.addWidget(self.show_title_check)

            font_group.setLayout(font_layout)
            style_layout.addWidget(font_group)


    def _build_marker_page(self, style_layout):
            """Build the markers controls."""
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
            self.marker_size_spin.setValue(int(app_state.plot_marker_size))
            self.marker_size_spin.setToolTip(translate("Marker size (1-2000)"))
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
            self.marker_alpha_spin.setValue(float(app_state.plot_marker_alpha))
            self.marker_alpha_spin.setToolTip(translate("Point transparency (0-1)"))
            self.marker_alpha_spin.valueChanged.connect(self._on_style_change)
            marker_alpha_row.addWidget(self.marker_alpha_spin)
            marker_layout.addLayout(marker_alpha_row)

            marker_edge_row = QHBoxLayout()
            self.scatter_edge_check = QCheckBox(translate("Show Marker Edge"))
            self.scatter_edge_check.setProperty('translate_key', 'Show Marker Edge')
            self.scatter_edge_check.setChecked(bool(app_state.scatter_show_edge))
            self.scatter_edge_check.stateChanged.connect(self._on_style_change)
            marker_edge_row.addWidget(self.scatter_edge_check)
            marker_edge_row.addStretch()
            marker_layout.addLayout(marker_edge_row)

            marker_edge_color_row = QHBoxLayout()
            marker_edge_color_label = QLabel(translate("Scatter Edge Color"))
            marker_edge_color_label.setProperty('translate_key', 'Scatter Edge Color')
            marker_edge_color_row.addWidget(marker_edge_color_label)
            marker_edge_editor, self.scatter_edgecolor_edit = self._create_color_picker(
                app_state.scatter_edgecolor
            )
            marker_edge_color_row.addWidget(marker_edge_editor, 1)
            marker_layout.addLayout(marker_edge_color_row)

            marker_edge_width_row = QHBoxLayout()
            marker_edge_width_label = QLabel(translate("Scatter Edge Width"))
            marker_edge_width_label.setProperty('translate_key', 'Scatter Edge Width')
            marker_edge_width_row.addWidget(marker_edge_width_label)
            self.scatter_edgewidth_spin = QDoubleSpinBox()
            self.scatter_edgewidth_spin.setRange(0.0, 3.0)
            self.scatter_edgewidth_spin.setSingleStep(0.1)
            self.scatter_edgewidth_spin.setValue(float(app_state.scatter_edgewidth))
            self.scatter_edgewidth_spin.valueChanged.connect(self._on_style_change)
            marker_edge_width_row.addWidget(self.scatter_edgewidth_spin)
            marker_layout.addLayout(marker_edge_width_row)
            marker_group.setLayout(marker_layout)
            style_layout.addWidget(marker_group)
