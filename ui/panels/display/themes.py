"""Display panel theme persistence and application logic."""

import json
import logging

from PyQt5.QtWidgets import QMessageBox

from core import CONFIG, app_state, state_gateway, translate
from visualization.plotting.style import configure_constrained_layout

logger = logging.getLogger(__name__)


class DisplayThemeMixin:
    """Theme management methods for display panel."""

    def _refresh_theme_list(self):
        """从磁盘加载主题并刷新下拉列表"""
        if not hasattr(app_state, 'saved_themes'):
            state_gateway.set_saved_themes({})

        theme_file = CONFIG['temp_dir'] / 'user_themes.json'
        if theme_file.exists():
            try:
                with open(theme_file, 'r', encoding='utf-8') as handle:
                    state_gateway.set_saved_themes(json.load(handle))
            except Exception as exc:
                logger.warning("Failed to load themes: %s", exc)
                state_gateway.set_saved_themes({})

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
            state_gateway.set_saved_themes({})

        theme_data = {
            'grid': bool(self.grid_check.isChecked()) if self.grid_check else False,
            'color_scheme': self.color_combo.currentText() if self.color_combo else getattr(app_state, 'color_scheme', 'vibrant'),
            'primary_font': self.primary_font_combo.currentText() if self.primary_font_combo else '',
            'cjk_font': self.cjk_font_combo.currentText() if self.cjk_font_combo else '',
            'font_sizes': {k: v.value() for k, v in self.font_size_spins.items()},
            'marker_size': self.marker_size_spin.value() if self.marker_size_spin else 60,
            'marker_alpha': self.marker_alpha_spin.value() if self.marker_alpha_spin else 0.8,
            'figure_dpi': self.figure_dpi_spin.value() if self.figure_dpi_spin else 130,
            'figure_bg': self._get_color_control_value(self.figure_bg_edit, '#ffffff'),
            'axes_bg': self._get_color_control_value(self.axes_bg_edit, '#ffffff'),
            'grid_color': self._get_color_control_value(self.grid_color_edit, '#e2e8f0'),
            'grid_linewidth': self.grid_width_spin.value() if self.grid_width_spin else 0.6,
            'grid_alpha': self.grid_alpha_spin.value() if self.grid_alpha_spin else 0.7,
            'grid_linestyle': self.grid_style_combo.currentText() if self.grid_style_combo else '--',
            'tick_direction': self.tick_dir_combo.currentText() if self.tick_dir_combo else 'out',
            'tick_color': self._get_color_control_value(self.tick_color_edit, '#1f2937'),
            'tick_length': self.tick_length_spin.value() if self.tick_length_spin else 4.0,
            'tick_width': self.tick_width_spin.value() if self.tick_width_spin else 0.8,
            'minor_ticks': bool(self.minor_ticks_check.isChecked()) if self.minor_ticks_check else False,
            'minor_tick_length': self.minor_tick_length_spin.value() if self.minor_tick_length_spin else 2.5,
            'minor_tick_width': self.minor_tick_width_spin.value() if self.minor_tick_width_spin else 0.6,
            'axis_linewidth': self.axis_linewidth_spin.value() if self.axis_linewidth_spin else 1.0,
            'axis_line_color': self._get_color_control_value(self.axis_line_color_edit, '#1f2937'),
            'show_top_spine': bool(self.show_top_spine_check.isChecked()) if self.show_top_spine_check else True,
            'show_right_spine': bool(self.show_right_spine_check.isChecked()) if self.show_right_spine_check else True,
            'minor_grid': bool(self.minor_grid_check.isChecked()) if self.minor_grid_check else False,
            'minor_grid_color': self._get_color_control_value(self.minor_grid_color_edit, '#e2e8f0'),
            'minor_grid_linewidth': self.minor_grid_width_spin.value() if self.minor_grid_width_spin else 0.4,
            'minor_grid_alpha': self.minor_grid_alpha_spin.value() if self.minor_grid_alpha_spin else 0.4,
            'minor_grid_linestyle': self.minor_grid_style_combo.currentText() if self.minor_grid_style_combo else ':',
            'scatter_show_edge': bool(self.scatter_edge_check.isChecked()) if self.scatter_edge_check else True,
            'scatter_edgecolor': self._get_color_control_value(self.scatter_edgecolor_edit, '#1e293b'),
            'scatter_edgewidth': self.scatter_edgewidth_spin.value() if self.scatter_edgewidth_spin else 0.4,
            'model_curve_width': self.model_curve_width_spin.value() if self.model_curve_width_spin else 1.2,
            'paleoisochron_width': self.paleoisochron_width_spin.value() if self.paleoisochron_width_spin else 0.9,
            'model_age_line_width': self.model_age_width_spin.value() if self.model_age_width_spin else 0.7,
            'isochron_line_width': self.isochron_width_spin.value() if self.isochron_width_spin else 1.5,
            'line_styles': getattr(app_state, 'line_styles', {}),
            'label_color': self._get_color_control_value(self.label_color_edit, '#1f2937'),
            'label_weight': self.label_weight_combo.currentText() if self.label_weight_combo else 'normal',
            'label_pad': self.label_pad_spin.value() if self.label_pad_spin else 6.0,
            'title_color': self._get_color_control_value(self.title_color_edit, '#111827'),
            'title_weight': self.title_weight_combo.currentText() if self.title_weight_combo else 'bold',
            'title_pad': self.title_pad_spin.value() if self.title_pad_spin else 20.0,
            'legend_location': getattr(app_state, 'legend_location', 'outside_right'),
            'legend_position': getattr(app_state, 'legend_position', None),
            'legend_frame_on': bool(self.legend_frame_on_check.isChecked()) if self.legend_frame_on_check else True,
            'legend_frame_alpha': self.legend_frame_alpha_spin.value() if self.legend_frame_alpha_spin else 0.95,
            'legend_frame_facecolor': self.legend_frame_face_edit.text() if self.legend_frame_face_edit else '#ffffff',
            'legend_frame_edgecolor': self.legend_frame_edge_edit.text() if self.legend_frame_edge_edit else '#cbd5f5',
            'adjust_text_force_text': [
                self.adjust_force_text_x_spin.value() if self.adjust_force_text_x_spin else 0.8,
                self.adjust_force_text_y_spin.value() if self.adjust_force_text_y_spin else 1.0,
            ],
            'adjust_text_force_static': [
                self.adjust_force_static_x_spin.value() if self.adjust_force_static_x_spin else 0.4,
                self.adjust_force_static_y_spin.value() if self.adjust_force_static_y_spin else 0.6,
            ],
            'adjust_text_expand': [
                self.adjust_expand_x_spin.value() if self.adjust_expand_x_spin else 1.08,
                self.adjust_expand_y_spin.value() if self.adjust_expand_y_spin else 1.20,
            ],
            'adjust_text_iter_lim': self.adjust_iter_lim_spin.value() if self.adjust_iter_lim_spin else 120,
            'adjust_text_time_lim': self.adjust_time_lim_spin.value() if self.adjust_time_lim_spin else 0.25,
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
            state_gateway.set_color_scheme(data.get('color_scheme', getattr(app_state, 'color_scheme', 'vibrant')))

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
            self._set_color_control_value(self.figure_bg_edit, data.get('figure_bg', '#ffffff'), '#ffffff')
        if self.axes_bg_edit:
            self._set_color_control_value(self.axes_bg_edit, data.get('axes_bg', '#ffffff'), '#ffffff')
        if self.grid_color_edit:
            self._set_color_control_value(self.grid_color_edit, data.get('grid_color', '#e2e8f0'), '#e2e8f0')
        if self.grid_width_spin:
            self.grid_width_spin.setValue(float(data.get('grid_linewidth', 0.6)))
        if self.grid_alpha_spin:
            self.grid_alpha_spin.setValue(float(data.get('grid_alpha', 0.7)))
        if self.grid_style_combo:
            self.grid_style_combo.setCurrentText(data.get('grid_linestyle', '--'))
        if self.tick_dir_combo:
            self.tick_dir_combo.setCurrentText(data.get('tick_direction', 'out'))
        if self.tick_color_edit:
            self._set_color_control_value(self.tick_color_edit, data.get('tick_color', '#1f2937'), '#1f2937')
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
            self._set_color_control_value(self.axis_line_color_edit, data.get('axis_line_color', '#1f2937'), '#1f2937')
        if self.show_top_spine_check:
            self.show_top_spine_check.setChecked(bool(data.get('show_top_spine', True)))
        if self.show_right_spine_check:
            self.show_right_spine_check.setChecked(bool(data.get('show_right_spine', True)))
        if self.minor_grid_check:
            self.minor_grid_check.setChecked(bool(data.get('minor_grid', False)))
        if self.minor_grid_color_edit:
            self._set_color_control_value(self.minor_grid_color_edit, data.get('minor_grid_color', '#e2e8f0'), '#e2e8f0')
        if self.minor_grid_width_spin:
            self.minor_grid_width_spin.setValue(float(data.get('minor_grid_linewidth', 0.4)))
        if self.minor_grid_alpha_spin:
            self.minor_grid_alpha_spin.setValue(float(data.get('minor_grid_alpha', 0.4)))
        if self.minor_grid_style_combo:
            self.minor_grid_style_combo.setCurrentText(data.get('minor_grid_linestyle', ':'))
        if self.scatter_edge_check:
            self.scatter_edge_check.setChecked(bool(data.get('scatter_show_edge', True)))
        if self.scatter_edgecolor_edit:
            self._set_color_control_value(self.scatter_edgecolor_edit, data.get('scatter_edgecolor', '#1e293b'), '#1e293b')
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
            state_gateway.set_line_styles(data.get('line_styles', {}))
        if self.label_color_edit:
            self._set_color_control_value(self.label_color_edit, data.get('label_color', '#1f2937'), '#1f2937')
        if self.label_weight_combo:
            self.label_weight_combo.setCurrentText(data.get('label_weight', 'normal'))
        if self.label_pad_spin:
            self.label_pad_spin.setValue(float(data.get('label_pad', 6.0)))
        if self.title_color_edit:
            self._set_color_control_value(self.title_color_edit, data.get('title_color', '#111827'), '#111827')
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

        def _pair(value, fallback):
            if isinstance(value, (list, tuple)) and len(value) >= 2:
                try:
                    return float(value[0]), float(value[1])
                except Exception:
                    return fallback
            if isinstance(value, (int, float)):
                scalar = float(value)
                return scalar, scalar
            return fallback

        adjust_force_text = _pair(
            data.get('adjust_text_force_text', getattr(app_state, 'adjust_text_force_text', (0.8, 1.0))),
            (0.8, 1.0),
        )
        adjust_force_static = _pair(
            data.get('adjust_text_force_static', getattr(app_state, 'adjust_text_force_static', (0.4, 0.6))),
            (0.4, 0.6),
        )
        adjust_expand = _pair(
            data.get('adjust_text_expand', getattr(app_state, 'adjust_text_expand', (1.08, 1.20))),
            (1.08, 1.20),
        )
        if self.adjust_force_text_x_spin:
            self.adjust_force_text_x_spin.setValue(float(adjust_force_text[0]))
        if self.adjust_force_text_y_spin:
            self.adjust_force_text_y_spin.setValue(float(adjust_force_text[1]))
        if self.adjust_force_static_x_spin:
            self.adjust_force_static_x_spin.setValue(float(adjust_force_static[0]))
        if self.adjust_force_static_y_spin:
            self.adjust_force_static_y_spin.setValue(float(adjust_force_static[1]))
        if self.adjust_expand_x_spin:
            self.adjust_expand_x_spin.setValue(float(adjust_expand[0]))
        if self.adjust_expand_y_spin:
            self.adjust_expand_y_spin.setValue(float(adjust_expand[1]))
        if self.adjust_iter_lim_spin:
            self.adjust_iter_lim_spin.setValue(int(data.get('adjust_text_iter_lim', getattr(app_state, 'adjust_text_iter_lim', 120))))
        if self.adjust_time_lim_spin:
            self.adjust_time_lim_spin.setValue(float(data.get('adjust_text_time_lim', getattr(app_state, 'adjust_text_time_lim', 0.25))))

        legend_outside = data.get('legend_location', None)
        legend_inside = data.get('legend_position', None)

        if legend_outside not in {'outside_left', 'outside_right'}:
            legend_outside = None

        state_gateway.set_legend_location(legend_outside)
        state_gateway.set_legend_position(legend_inside)
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
            configure_constrained_layout(app_state.fig)
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
        state_gateway.set_ui_theme(theme_name)
