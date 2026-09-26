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

#: Methods this class expects from the classes it is composed with
#: (explicit interface, UI review item I).
REQUIRES_DisplayBuildAxesMixin = (
    "_create_color_picker",
)


class DisplayBuildAxesMixin:
    """Axes, grid and canvas page builder for the display panel."""

    def _build_axes_page(self, axes_page_layout):
            """Build the axes, grid and canvas controls."""
            # Axes & Lines
            axes_group = QGroupBox(translate("Axes & Lines"))
            axes_group.setProperty('translate_key', 'Axes & Lines')
            axes_layout = QVBoxLayout()
            auto_layout_btn = QPushButton(translate("Auto Layout"))
            auto_layout_btn.setProperty('translate_key', 'Auto Layout')
            auto_layout_btn.clicked.connect(self._apply_auto_layout)
            axes_layout.addWidget(auto_layout_btn)

            def add_row(grid, label_key, widget, row_idx):
                label = QLabel(translate(label_key))
                label.setProperty('translate_key', label_key)
                label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                grid.addWidget(label, row_idx, 0)
                grid.addWidget(widget, row_idx, 1)
                return row_idx + 1

            def make_group(title_key):
                group = QGroupBox(translate(title_key))
                group.setProperty('translate_key', title_key)
                grid = QGridLayout()
                # Keep labels from squeezing the value widgets: labels size to
                # their text, values get the remaining width.
                grid.setColumnStretch(0, 0)
                grid.setColumnStretch(1, 1)
                grid.setHorizontalSpacing(10)
                grid.setVerticalSpacing(6)
                group.setLayout(grid)
                axes_layout.addWidget(group)
                return grid

            figure_grid = make_group("Figure")
            row = 0
            self.figure_dpi_spin = QSpinBox()
            self.figure_dpi_spin.setRange(50, 600)
            self.figure_dpi_spin.setSingleStep(1)
            self.figure_dpi_spin.setValue(int(app_state.plot_dpi))
            self.figure_dpi_spin.valueChanged.connect(self._on_style_change)
            self.figure_dpi_spin.setToolTip(translate("Figure resolution (DPI)"))
            row = add_row(figure_grid, "Figure DPI", self.figure_dpi_spin, row)

            figure_bg_editor, self.figure_bg_edit = self._create_color_picker(
                app_state.plot_facecolor
            )
            row = add_row(figure_grid, "Figure Background", figure_bg_editor, row)

            axes_bg_editor, self.axes_bg_edit = self._create_color_picker(
                app_state.axes_facecolor
            )
            row = add_row(figure_grid, "Axes Background", axes_bg_editor, row)

            grid_grid = make_group("Grid")
            row = 0
            self.grid_check = QCheckBox(translate("Show Grid"))
            self.grid_check.setProperty('translate_key', 'Show Grid')
            self.grid_check.setChecked(app_state.plot_style_grid)
            self.grid_check.stateChanged.connect(self._on_style_change)
            row = add_row(grid_grid, "Show Grid", self.grid_check, row)

            grid_color_editor, self.grid_color_edit = self._create_color_picker(
                app_state.grid_color
            )
            row = add_row(grid_grid, "Grid Color", grid_color_editor, row)

            self.grid_width_spin = QDoubleSpinBox()
            self.grid_width_spin.setRange(0.1, 3.0)
            self.grid_width_spin.setSingleStep(0.1)
            self.grid_width_spin.setDecimals(2)
            self.grid_width_spin.setValue(float(app_state.grid_linewidth))
            self.grid_width_spin.valueChanged.connect(self._on_style_change)
            row = add_row(grid_grid, "Grid Linewidth", self.grid_width_spin, row)

            self.grid_alpha_spin = QDoubleSpinBox()
            self.grid_alpha_spin.setRange(0.0, 1.0)
            self.grid_alpha_spin.setSingleStep(0.05)
            self.grid_alpha_spin.setDecimals(2)
            self.grid_alpha_spin.setValue(float(app_state.grid_alpha))
            self.grid_alpha_spin.valueChanged.connect(self._on_style_change)
            self.grid_alpha_spin.setToolTip(translate("Grid line transparency (0-1)"))
            row = add_row(grid_grid, "Grid Alpha", self.grid_alpha_spin, row)

            grid_style_items = ['-', '--', '-.', ':']
            grid_style_default = app_state.grid_linestyle
            self.grid_style_combo = QComboBox()
            self.grid_style_combo.addItems(grid_style_items)
            self.grid_style_combo.setCurrentIndex(max(0, grid_style_items.index(grid_style_default)))
            self.grid_style_combo.currentTextChanged.connect(self._on_style_change)
            self.grid_style_combo.setToolTip(translate("Grid line style"))
            row = add_row(grid_grid, "Grid Style", self.grid_style_combo, row)

            self.minor_grid_check = QCheckBox()
            self.minor_grid_check.setChecked(app_state.minor_grid)
            self.minor_grid_check.setToolTip(translate("Show minor grid lines"))
            self.minor_grid_check.stateChanged.connect(self._on_style_change)
            row = add_row(grid_grid, "Minor Grid", self.minor_grid_check, row)

            minor_grid_editor, self.minor_grid_color_edit = self._create_color_picker(
                app_state.minor_grid_color
            )
            row = add_row(grid_grid, "Minor Grid Color", minor_grid_editor, row)

            self.minor_grid_width_spin = QDoubleSpinBox()
            self.minor_grid_width_spin.setRange(0.1, 2.0)
            self.minor_grid_width_spin.setSingleStep(0.1)
            self.minor_grid_width_spin.setDecimals(2)
            self.minor_grid_width_spin.setValue(float(app_state.minor_grid_linewidth))
            self.minor_grid_width_spin.valueChanged.connect(self._on_style_change)
            row = add_row(grid_grid, "Minor Grid Linewidth", self.minor_grid_width_spin, row)

            self.minor_grid_alpha_spin = QDoubleSpinBox()
            self.minor_grid_alpha_spin.setRange(0.0, 1.0)
            self.minor_grid_alpha_spin.setSingleStep(0.05)
            self.minor_grid_alpha_spin.setDecimals(2)
            self.minor_grid_alpha_spin.setValue(float(app_state.minor_grid_alpha))
            self.minor_grid_alpha_spin.valueChanged.connect(self._on_style_change)
            row = add_row(grid_grid, "Minor Grid Alpha", self.minor_grid_alpha_spin, row)

            minor_grid_style_items = ['-', '--', '-.', ':']
            minor_grid_style_default = app_state.minor_grid_linestyle
            self.minor_grid_style_combo = QComboBox()
            self.minor_grid_style_combo.addItems(minor_grid_style_items)
            self.minor_grid_style_combo.setCurrentIndex(max(0, minor_grid_style_items.index(minor_grid_style_default)))
            self.minor_grid_style_combo.currentTextChanged.connect(self._on_style_change)
            row = add_row(grid_grid, "Minor Grid Style", self.minor_grid_style_combo, row)

            tick_grid = make_group("Ticks")
            row = 0
            tick_dir_items = ['out', 'in', 'inout']
            tick_dir_default = app_state.tick_direction
            self.tick_dir_combo = QComboBox()
            self.tick_dir_combo.addItems(tick_dir_items)
            self.tick_dir_combo.setCurrentIndex(max(0, tick_dir_items.index(tick_dir_default)))
            self.tick_dir_combo.currentTextChanged.connect(self._on_style_change)
            row = add_row(tick_grid, "Tick Direction", self.tick_dir_combo, row)

            tick_color_editor, self.tick_color_edit = self._create_color_picker(
                app_state.tick_color
            )
            row = add_row(tick_grid, "Tick Color", tick_color_editor, row)

            self.tick_length_spin = QDoubleSpinBox()
            self.tick_length_spin.setRange(0.0, 12.0)
            self.tick_length_spin.setSingleStep(0.5)
            self.tick_length_spin.setDecimals(2)
            self.tick_length_spin.setValue(float(app_state.tick_length))
            self.tick_length_spin.valueChanged.connect(self._on_style_change)
            row = add_row(tick_grid, "Tick Length", self.tick_length_spin, row)

            self.tick_width_spin = QDoubleSpinBox()
            self.tick_width_spin.setRange(0.2, 3.0)
            self.tick_width_spin.setSingleStep(0.1)
            self.tick_width_spin.setDecimals(2)
            self.tick_width_spin.setValue(float(app_state.tick_width))
            self.tick_width_spin.valueChanged.connect(self._on_style_change)
            row = add_row(tick_grid, "Tick Width", self.tick_width_spin, row)

            self.minor_ticks_check = QCheckBox()
            self.minor_ticks_check.setChecked(app_state.minor_ticks)
            self.minor_ticks_check.stateChanged.connect(self._on_style_change)
            row = add_row(tick_grid, "Minor Ticks", self.minor_ticks_check, row)

            self.minor_tick_length_spin = QDoubleSpinBox()
            self.minor_tick_length_spin.setRange(0.0, 8.0)
            self.minor_tick_length_spin.setSingleStep(0.5)
            self.minor_tick_length_spin.setDecimals(2)
            self.minor_tick_length_spin.setValue(float(app_state.minor_tick_length))
            self.minor_tick_length_spin.valueChanged.connect(self._on_style_change)
            row = add_row(tick_grid, "Minor Tick Length", self.minor_tick_length_spin, row)

            self.minor_tick_width_spin = QDoubleSpinBox()
            self.minor_tick_width_spin.setRange(0.2, 2.0)
            self.minor_tick_width_spin.setSingleStep(0.1)
            self.minor_tick_width_spin.setDecimals(2)
            self.minor_tick_width_spin.setValue(float(app_state.minor_tick_width))
            self.minor_tick_width_spin.valueChanged.connect(self._on_style_change)
            row = add_row(tick_grid, "Minor Tick Width", self.minor_tick_width_spin, row)

            spine_grid = make_group("Spines")
            row = 0
            self.axis_linewidth_spin = QDoubleSpinBox()
            self.axis_linewidth_spin.setRange(0.2, 3.0)
            self.axis_linewidth_spin.setSingleStep(0.1)
            self.axis_linewidth_spin.setDecimals(2)
            self.axis_linewidth_spin.setValue(float(app_state.axis_linewidth))
            self.axis_linewidth_spin.valueChanged.connect(self._on_style_change)
            row = add_row(spine_grid, "Axis Line Width", self.axis_linewidth_spin, row)

            axis_color_editor, self.axis_line_color_edit = self._create_color_picker(
                app_state.axis_line_color
            )
            row = add_row(spine_grid, "Axis Line Color", axis_color_editor, row)

            self.show_top_spine_check = QCheckBox()
            self.show_top_spine_check.setChecked(app_state.show_top_spine)
            self.show_top_spine_check.stateChanged.connect(self._on_style_change)
            row = add_row(spine_grid, "Show Top Spine", self.show_top_spine_check, row)

            self.show_right_spine_check = QCheckBox()
            self.show_right_spine_check.setChecked(app_state.show_right_spine)
            self.show_right_spine_check.stateChanged.connect(self._on_style_change)
            row = add_row(spine_grid, "Show Right Spine", self.show_right_spine_check, row)

            text_grid = make_group("Text")
            row = 0
            label_color_editor, self.label_color_edit = self._create_color_picker(
                app_state.label_color
            )
            row = add_row(text_grid, "Label Color", label_color_editor, row)

            weight_items = ['normal', 'bold']
            label_weight_default = app_state.label_weight
            self.label_weight_combo = QComboBox()
            self.label_weight_combo.addItems(weight_items)
            self.label_weight_combo.setCurrentIndex(max(0, weight_items.index(label_weight_default)))
            self.label_weight_combo.currentTextChanged.connect(self._on_style_change)
            row = add_row(text_grid, "Label Weight", self.label_weight_combo, row)

            self.label_pad_spin = QDoubleSpinBox()
            self.label_pad_spin.setRange(0.0, 30.0)
            self.label_pad_spin.setSingleStep(1.0)
            self.label_pad_spin.setDecimals(2)
            self.label_pad_spin.setValue(float(app_state.label_pad))
            self.label_pad_spin.valueChanged.connect(self._on_style_change)
            row = add_row(text_grid, "Label Pad", self.label_pad_spin, row)

            title_color_editor, self.title_color_edit = self._create_color_picker(
                app_state.title_color
            )
            row = add_row(text_grid, "Title Color", title_color_editor, row)

            weight_items2 = ['normal', 'bold']
            title_weight_default = app_state.title_weight
            self.title_weight_combo = QComboBox()
            self.title_weight_combo.addItems(weight_items2)
            self.title_weight_combo.setCurrentIndex(max(0, weight_items2.index(title_weight_default)))
            self.title_weight_combo.currentTextChanged.connect(self._on_style_change)
            row = add_row(text_grid, "Title Weight", self.title_weight_combo, row)

            self.title_pad_spin = QDoubleSpinBox()
            self.title_pad_spin.setRange(0.0, 40.0)
            self.title_pad_spin.setSingleStep(1.0)
            self.title_pad_spin.setDecimals(2)
            self.title_pad_spin.setValue(float(app_state.title_pad))
            self.title_pad_spin.valueChanged.connect(self._on_style_change)
            row = add_row(text_grid, "Title Pad", self.title_pad_spin, row)

            label_layout_grid = make_group("Label Layout (adjustText)")
            row = 0
            force_text = app_state.adjust_text_force_text
            force_static = app_state.adjust_text_force_static
            expand = app_state.adjust_text_expand

            self.adjust_force_text_x_spin = QDoubleSpinBox()
            self.adjust_force_text_x_spin.setRange(0.0, 3.0)
            self.adjust_force_text_x_spin.setSingleStep(0.05)
            self.adjust_force_text_x_spin.setDecimals(2)
            self.adjust_force_text_x_spin.setValue(float(force_text[0]))
            self.adjust_force_text_x_spin.valueChanged.connect(self._on_style_change)
            self.adjust_force_text_x_spin.setToolTip(translate("Label repulsion strength"))
            row = add_row(label_layout_grid, "Adjust Force Text X", self.adjust_force_text_x_spin, row)

            self.adjust_force_text_y_spin = QDoubleSpinBox()
            self.adjust_force_text_y_spin.setRange(0.0, 3.0)
            self.adjust_force_text_y_spin.setSingleStep(0.05)
            self.adjust_force_text_y_spin.setDecimals(2)
            self.adjust_force_text_y_spin.setValue(float(force_text[1]))
            self.adjust_force_text_y_spin.valueChanged.connect(self._on_style_change)
            self.adjust_force_text_y_spin.setToolTip(translate("Label repulsion strength"))
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
            self.adjust_iter_lim_spin.setSingleStep(1)
            self.adjust_iter_lim_spin.setValue(int(app_state.adjust_text_iter_lim))
            self.adjust_iter_lim_spin.valueChanged.connect(self._on_style_change)
            row = add_row(label_layout_grid, "Adjust Iteration Limit", self.adjust_iter_lim_spin, row)

            self.adjust_time_lim_spin = QDoubleSpinBox()
            self.adjust_time_lim_spin.setRange(0.05, 2.0)
            self.adjust_time_lim_spin.setSingleStep(0.05)
            self.adjust_time_lim_spin.setDecimals(2)
            self.adjust_time_lim_spin.setValue(float(app_state.adjust_text_time_lim))
            self.adjust_time_lim_spin.valueChanged.connect(self._on_style_change)
            row = add_row(label_layout_grid, "Adjust Time Limit (s)", self.adjust_time_lim_spin, row)

            axes_group.setLayout(axes_layout)
            axes_page_layout.addWidget(axes_group)
