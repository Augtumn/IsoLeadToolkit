"""面板基类 - 提供共享工具方法"""
from __future__ import annotations

import logging
from typing import Callable

from PyQt5.QtWidgets import QWidget, QGroupBox, QLabel, QPushButton, QCheckBox, QRadioButton
from PyQt5.QtCore import QTimer

from core import app_state, state_gateway, translate

logger = logging.getLogger(__name__)


class BasePanel(QWidget):
    """所有面板的基类，提供共享工具方法"""

    def __init__(self, callback=None, parent=None):
        super().__init__(parent)
        self.callback = callback
        self.sliders = {}
        self.labels = {}
        self.radio_vars = {}
        self.check_vars = {}
        self._slider_steps = {}
        self._slider_timers = {}
        self._debounce_timers: dict[str, QTimer] = {}
        self._slider_delay_ms = 350
        self._is_initialized = False

    def build(self) -> QWidget:
        """构建面板内容，子类必须实现"""
        raise NotImplementedError

    def reset_state(self):
        """重置面板 widget 引用，子类必须实现"""
        self.sliders = {}
        self.labels = {}
        self.radio_vars = {}
        self.check_vars = {}
        self._slider_steps = {}
        self._slider_timers = {}
        self._debounce_timers = {}
        self._is_initialized = False

    def _update_translations(self, root: QWidget | None = None) -> None:
        """遍历控件树，根据 ``translate_key`` 属性更新文本。

        在控件构建时通过 ``widget.setProperty('translate_key', 'English Key')``
        标记需要翻译的控件，语言切换时调用此方法即可就地刷新文本，
        无需销毁重建整个 UI。

        支持的控件类型: QGroupBox (setTitle), QLabel/QPushButton/QCheckBox/QRadioButton (setText)。
        """
        if root is None:
            root = self
        for child in root.findChildren(QWidget):
            key = child.property('translate_key')
            if not key:
                continue
            translated = translate(key)
            if isinstance(child, QGroupBox):
                child.setTitle(translated)
            elif isinstance(child, (QLabel, QPushButton, QCheckBox, QRadioButton)):
                child.setText(translated)

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

    def _debounce(self, key: str, func: Callable, delay_ms: int | None = None) -> None:
        """通用防抖：在 *delay_ms* 毫秒内仅执行最后一次调用。

        Args:
            key: 唯一标识符，同一 key 的连续调用会取消前一次。
            func: 延迟后执行的无参回调。
            delay_ms: 延迟毫秒数，默认使用 ``_slider_delay_ms``。
        """
        if delay_ms is None:
            delay_ms = self._slider_delay_ms

        existing = self._debounce_timers.get(key)
        if existing is not None:
            existing.stop()

        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self._fire_debounced(key, func))
        timer.start(delay_ms)
        self._debounce_timers[key] = timer

    def _fire_debounced(self, key: str, func: Callable) -> None:
        """执行防抖回调并清理 timer。"""
        if key in self._debounce_timers:
            self._debounce_timers[key].stop()
            del self._debounce_timers[key]
        try:
            func()
        except Exception:
            logger.exception("Debounced callback %s failed", key)

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

    def _on_style_change(self, *_args):
        """处理样式变化"""
        if not getattr(self, "_is_initialized", False):
            return

        def _safe_float(text, default):
            try:
                return float(text)
            except (TypeError, ValueError):
                return default

        def _safe_color(widget, default):
            if widget is None:
                return default
            try:
                color_value = widget.property('color_value')
                if isinstance(color_value, str) and color_value.strip():
                    return color_value.strip()
            except Exception:
                pass
            if hasattr(widget, 'text') and callable(widget.text):
                try:
                    text_value = widget.text()
                    if isinstance(text_value, str) and text_value.strip():
                        return text_value.strip()
                except Exception:
                    pass
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

        style_updates: dict[str, object] = {}

        grid_check = getattr(self, 'grid_check', None)
        if grid_check is not None:
            style_updates['plot_style_grid'] = bool(grid_check.isChecked())
        color_combo = getattr(self, 'color_combo', None)
        new_scheme = color_combo.currentText() if color_combo is not None else app_state.color_scheme
        style_updates['color_scheme'] = new_scheme

        primary_combo = getattr(self, 'primary_font_combo', None)
        primary_font = primary_combo.currentText() if primary_combo is not None else ''
        if primary_font == '<Default>':
            primary_font = ''
        style_updates['custom_primary_font'] = primary_font

        cjk_combo = getattr(self, 'cjk_font_combo', None)
        cjk_font = cjk_combo.currentText() if cjk_combo is not None else ''
        if cjk_font == '<Default>':
            cjk_font = ''
        style_updates['custom_cjk_font'] = cjk_font

        font_size_spins = getattr(self, 'font_size_spins', {})
        if font_size_spins:
            style_updates['plot_font_sizes'] = {k: v.value() for k, v in font_size_spins.items()}
        marker_size_spin = getattr(self, 'marker_size_spin', None)
        if marker_size_spin is not None:
            style_updates['plot_marker_size'] = marker_size_spin.value()
        marker_alpha_spin = getattr(self, 'marker_alpha_spin', None)
        if marker_alpha_spin is not None:
            style_updates['plot_marker_alpha'] = marker_alpha_spin.value()
        show_title_check = getattr(self, 'show_title_check', None)
        if show_title_check is not None:
            style_updates['show_plot_title'] = bool(show_title_check.isChecked())

        figure_dpi_spin = getattr(self, 'figure_dpi_spin', None)
        if figure_dpi_spin is not None:
            style_updates['plot_dpi'] = int(figure_dpi_spin.value())
        figure_bg_edit = getattr(self, 'figure_bg_edit', None)
        if figure_bg_edit is not None:
            style_updates['plot_facecolor'] = _safe_color(figure_bg_edit, '#ffffff')
        axes_bg_edit = getattr(self, 'axes_bg_edit', None)
        if axes_bg_edit is not None:
            style_updates['axes_facecolor'] = _safe_color(axes_bg_edit, '#ffffff')
        grid_color_edit = getattr(self, 'grid_color_edit', None)
        if grid_color_edit is not None:
            style_updates['grid_color'] = _safe_color(grid_color_edit, '#e2e8f0')
        grid_width_spin = getattr(self, 'grid_width_spin', None)
        if grid_width_spin is not None:
            style_updates['grid_linewidth'] = float(grid_width_spin.value())
        grid_alpha_spin = getattr(self, 'grid_alpha_spin', None)
        if grid_alpha_spin is not None:
            style_updates['grid_alpha'] = float(grid_alpha_spin.value())
        grid_style_combo = getattr(self, 'grid_style_combo', None)
        if grid_style_combo is not None:
            style_updates['grid_linestyle'] = grid_style_combo.currentText() or '--'
        tick_dir_combo = getattr(self, 'tick_dir_combo', None)
        if tick_dir_combo is not None:
            style_updates['tick_direction'] = tick_dir_combo.currentText() or 'out'
        tick_color_edit = getattr(self, 'tick_color_edit', None)
        if tick_color_edit is not None:
            style_updates['tick_color'] = _safe_color(tick_color_edit, '#1f2937')
        tick_length_spin = getattr(self, 'tick_length_spin', None)
        if tick_length_spin is not None:
            style_updates['tick_length'] = float(tick_length_spin.value())
        tick_width_spin = getattr(self, 'tick_width_spin', None)
        if tick_width_spin is not None:
            style_updates['tick_width'] = float(tick_width_spin.value())
        minor_ticks_check = getattr(self, 'minor_ticks_check', None)
        if minor_ticks_check is not None:
            style_updates['minor_ticks'] = bool(minor_ticks_check.isChecked())
        minor_tick_length_spin = getattr(self, 'minor_tick_length_spin', None)
        if minor_tick_length_spin is not None:
            style_updates['minor_tick_length'] = float(minor_tick_length_spin.value())
        minor_tick_width_spin = getattr(self, 'minor_tick_width_spin', None)
        if minor_tick_width_spin is not None:
            style_updates['minor_tick_width'] = float(minor_tick_width_spin.value())
        axis_linewidth_spin = getattr(self, 'axis_linewidth_spin', None)
        if axis_linewidth_spin is not None:
            style_updates['axis_linewidth'] = float(axis_linewidth_spin.value())
        axis_line_color_edit = getattr(self, 'axis_line_color_edit', None)
        if axis_line_color_edit is not None:
            style_updates['axis_line_color'] = _safe_color(axis_line_color_edit, '#1f2937')
        show_top_spine_check = getattr(self, 'show_top_spine_check', None)
        if show_top_spine_check is not None:
            style_updates['show_top_spine'] = bool(show_top_spine_check.isChecked())
        show_right_spine_check = getattr(self, 'show_right_spine_check', None)
        if show_right_spine_check is not None:
            style_updates['show_right_spine'] = bool(show_right_spine_check.isChecked())
        minor_grid_check = getattr(self, 'minor_grid_check', None)
        if minor_grid_check is not None:
            style_updates['minor_grid'] = bool(minor_grid_check.isChecked())
        minor_grid_color_edit = getattr(self, 'minor_grid_color_edit', None)
        if minor_grid_color_edit is not None:
            style_updates['minor_grid_color'] = _safe_color(minor_grid_color_edit, '#e2e8f0')
        minor_grid_width_spin = getattr(self, 'minor_grid_width_spin', None)
        if minor_grid_width_spin is not None:
            style_updates['minor_grid_linewidth'] = float(minor_grid_width_spin.value())
        minor_grid_alpha_spin = getattr(self, 'minor_grid_alpha_spin', None)
        if minor_grid_alpha_spin is not None:
            style_updates['minor_grid_alpha'] = float(minor_grid_alpha_spin.value())
        minor_grid_style_combo = getattr(self, 'minor_grid_style_combo', None)
        if minor_grid_style_combo is not None:
            style_updates['minor_grid_linestyle'] = minor_grid_style_combo.currentText() or ':'
        scatter_edgecolor_edit = getattr(self, 'scatter_edgecolor_edit', None)
        scatter_edge_check = getattr(self, 'scatter_edge_check', None)
        if scatter_edge_check is not None:
            style_updates['scatter_show_edge'] = bool(scatter_edge_check.isChecked())
        if scatter_edgecolor_edit is not None:
            style_updates['scatter_edgecolor'] = _safe_color(scatter_edgecolor_edit, '#1e293b')
        scatter_edgewidth_spin = getattr(self, 'scatter_edgewidth_spin', None)
        if scatter_edgewidth_spin is not None:
            style_updates['scatter_edgewidth'] = float(scatter_edgewidth_spin.value())
        model_curve_width_spin = getattr(self, 'model_curve_width_spin', None)
        if model_curve_width_spin is not None:
            style_updates['model_curve_width'] = float(model_curve_width_spin.value())
        paleoisochron_width_spin = getattr(self, 'paleoisochron_width_spin', None)
        if paleoisochron_width_spin is not None:
            style_updates['paleoisochron_width'] = float(paleoisochron_width_spin.value())
        model_age_width_spin = getattr(self, 'model_age_width_spin', None)
        if model_age_width_spin is not None:
            style_updates['model_age_line_width'] = float(model_age_width_spin.value())
        isochron_width_spin = getattr(self, 'isochron_width_spin', None)
        if isochron_width_spin is not None:
            style_updates['isochron_line_width'] = float(isochron_width_spin.value())

        if hasattr(app_state, 'line_styles'):
            app_state.line_styles.setdefault('model_curve', {})['linewidth'] = app_state.model_curve_width
            app_state.line_styles.setdefault('paleoisochron', {})['linewidth'] = app_state.paleoisochron_width
            app_state.line_styles.setdefault('model_age_line', {})['linewidth'] = app_state.model_age_line_width
            app_state.line_styles.setdefault('isochron', {})['linewidth'] = app_state.isochron_line_width

        label_color_edit = getattr(self, 'label_color_edit', None)
        if label_color_edit is not None:
            style_updates['label_color'] = _safe_color(label_color_edit, '#1f2937')
        label_weight_combo = getattr(self, 'label_weight_combo', None)
        if label_weight_combo is not None:
            style_updates['label_weight'] = label_weight_combo.currentText() or 'normal'
        label_pad_spin = getattr(self, 'label_pad_spin', None)
        if label_pad_spin is not None:
            style_updates['label_pad'] = float(label_pad_spin.value())
        title_color_edit = getattr(self, 'title_color_edit', None)
        if title_color_edit is not None:
            style_updates['title_color'] = _safe_color(title_color_edit, '#111827')
        title_weight_combo = getattr(self, 'title_weight_combo', None)
        if title_weight_combo is not None:
            style_updates['title_weight'] = title_weight_combo.currentText() or 'bold'
        title_pad_spin = getattr(self, 'title_pad_spin', None)
        if title_pad_spin is not None:
            style_updates['title_pad'] = float(title_pad_spin.value())

        adjust_force_text_x_spin = getattr(self, 'adjust_force_text_x_spin', None)
        adjust_force_text_y_spin = getattr(self, 'adjust_force_text_y_spin', None)
        if adjust_force_text_x_spin is not None and adjust_force_text_y_spin is not None:
            style_updates['adjust_text_force_text'] = (
                float(adjust_force_text_x_spin.value()),
                float(adjust_force_text_y_spin.value()),
            )
        adjust_force_static_x_spin = getattr(self, 'adjust_force_static_x_spin', None)
        adjust_force_static_y_spin = getattr(self, 'adjust_force_static_y_spin', None)
        if adjust_force_static_x_spin is not None and adjust_force_static_y_spin is not None:
            style_updates['adjust_text_force_static'] = (
                float(adjust_force_static_x_spin.value()),
                float(adjust_force_static_y_spin.value()),
            )
        adjust_expand_x_spin = getattr(self, 'adjust_expand_x_spin', None)
        adjust_expand_y_spin = getattr(self, 'adjust_expand_y_spin', None)
        if adjust_expand_x_spin is not None and adjust_expand_y_spin is not None:
            style_updates['adjust_text_expand'] = (
                float(adjust_expand_x_spin.value()),
                float(adjust_expand_y_spin.value()),
            )
        adjust_iter_lim_spin = getattr(self, 'adjust_iter_lim_spin', None)
        if adjust_iter_lim_spin is not None:
            style_updates['adjust_text_iter_lim'] = int(adjust_iter_lim_spin.value())
        adjust_time_lim_spin = getattr(self, 'adjust_time_lim_spin', None)
        if adjust_time_lim_spin is not None:
            style_updates['adjust_text_time_lim'] = float(adjust_time_lim_spin.value())

        legend_frame_on_check = getattr(self, 'legend_frame_on_check', None)
        if legend_frame_on_check is not None:
            style_updates['legend_frame_on'] = bool(legend_frame_on_check.isChecked())
        legend_frame_alpha_spin = getattr(self, 'legend_frame_alpha_spin', None)
        if legend_frame_alpha_spin is not None:
            style_updates['legend_frame_alpha'] = float(legend_frame_alpha_spin.value())
        legend_frame_face_edit = getattr(self, 'legend_frame_face_edit', None)
        if legend_frame_face_edit is not None:
            style_updates['legend_frame_facecolor'] = legend_frame_face_edit.text() or '#ffffff'
        legend_frame_edge_edit = getattr(self, 'legend_frame_edge_edit', None)
        if legend_frame_edge_edit is not None:
            style_updates['legend_frame_edgecolor'] = legend_frame_edge_edit.text() or '#cbd5f5'

        if style_updates:
            state_gateway.set_panel_style_updates(style_updates)

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

        requires_replot = False
        if new_scheme != previous_scheme:
            requires_replot = True
        if (primary_font, cjk_font) != previous_fonts:
            requires_replot = True
        if app_state.plot_font_sizes != previous_font_sizes:
            requires_replot = True
        _title_visual_changed = (
            app_state.show_plot_title != previous_show_title
            or app_state.title_pad != previous_title_pad
        )

        # Overlay line width changes → lightweight refresh
        overlay_widths_changed = (
            app_state.model_curve_width,
            app_state.paleoisochron_width,
            app_state.model_age_line_width,
            app_state.isochron_line_width,
        ) != previous_line_widths

        if requires_replot:
            if self.callback:
                self.callback()
        elif _title_visual_changed:
            try:
                from visualization import refresh_plot_style
                refresh_plot_style()
            except Exception:
                if self.callback:
                    self.callback()
        elif overlay_widths_changed:
            try:
                from visualization.plotting.style import refresh_overlay_styles
                refresh_overlay_styles()
            except Exception:
                if self.callback:
                    self.callback()
        else:
            try:
                from visualization import refresh_plot_style
                refresh_plot_style()
            except Exception:
                if self.callback:
                    self.callback()
