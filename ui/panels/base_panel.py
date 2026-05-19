"""面板基类 - 提供共享工具方法"""
from __future__ import annotations

import logging
from typing import Callable

from PyQt5.QtWidgets import QWidget, QGroupBox, QLabel, QPushButton, QCheckBox, QRadioButton
from PyQt5.QtCore import QSettings, QTimer

from core import app_state, state_gateway, translate

logger = logging.getLogger(__name__)


def _safe_float(text, default):
    """安全转换为 float，失败时返回默认值。"""
    try:
        return float(text)
    except (TypeError, ValueError):
        return default


def _safe_color(widget, default):
    """从 widget 安全提取颜色值。

    优先读取 ``property('color_value')``，其次读取 ``text()``，
    均失败时返回 *default*。
    """
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


# ---------------------------------------------------------------------------
# 样式 Widget → 状态 映射表
# 每项: (widget_attr_name, state_key, extractor_id, *extractor_args)
# extractor_id: 'bool' | 'int' | 'float' | 'text' | 'text_or' | 'color'
# ---------------------------------------------------------------------------
_STYLE_WIDGET_MAP: list[tuple] = [
    # --- basic controls ---
    ('grid_check', 'plot_style_grid', 'bool'),
    ('marker_size_spin', 'plot_marker_size', 'int'),
    ('marker_alpha_spin', 'plot_marker_alpha', 'float'),
    ('show_title_check', 'show_plot_title', 'bool'),
    ('figure_dpi_spin', 'plot_dpi', 'int'),
    # --- color edits ---
    ('figure_bg_edit', 'plot_facecolor', 'color', '#ffffff'),
    ('axes_bg_edit', 'axes_facecolor', 'color', '#ffffff'),
    ('grid_color_edit', 'grid_color', 'color', '#e2e8f0'),
    ('tick_color_edit', 'tick_color', 'color', '#1f2937'),
    ('axis_line_color_edit', 'axis_line_color', 'color', '#1f2937'),
    ('minor_grid_color_edit', 'minor_grid_color', 'color', '#e2e8f0'),
    ('scatter_edgecolor_edit', 'scatter_edgecolor', 'color', '#1e293b'),
    ('label_color_edit', 'label_color', 'color', '#1f2937'),
    ('title_color_edit', 'title_color', 'color', '#111827'),
    # --- misc ---
    ('grid_width_spin', 'grid_linewidth', 'float'),
    ('grid_alpha_spin', 'grid_alpha', 'float'),
    ('grid_style_combo', 'grid_linestyle', 'text_or', '--'),
    ('tick_dir_combo', 'tick_direction', 'text_or', 'out'),
    ('tick_length_spin', 'tick_length', 'float'),
    ('tick_width_spin', 'tick_width', 'float'),
    ('minor_ticks_check', 'minor_ticks', 'bool'),
    ('minor_tick_length_spin', 'minor_tick_length', 'float'),
    ('minor_tick_width_spin', 'minor_tick_width', 'float'),
    ('axis_linewidth_spin', 'axis_linewidth', 'float'),
    ('show_top_spine_check', 'show_top_spine', 'bool'),
    ('show_right_spine_check', 'show_right_spine', 'bool'),
    ('minor_grid_check', 'minor_grid', 'bool'),
    ('minor_grid_width_spin', 'minor_grid_linewidth', 'float'),
    ('minor_grid_alpha_spin', 'minor_grid_alpha', 'float'),
    ('minor_grid_style_combo', 'minor_grid_linestyle', 'text_or', ':'),
    ('scatter_edge_check', 'scatter_show_edge', 'bool'),
    ('scatter_edgewidth_spin', 'scatter_edgewidth', 'float'),
    # --- line widths ---
    ('model_curve_width_spin', 'model_curve_width', 'float'),
    ('paleoisochron_width_spin', 'paleoisochron_width', 'float'),
    ('model_age_width_spin', 'model_age_line_width', 'float'),
    ('isochron_width_spin', 'isochron_line_width', 'float'),
    # --- labels ---
    ('label_weight_combo', 'label_weight', 'text_or', 'normal'),
    ('label_pad_spin', 'label_pad', 'float'),
    ('title_weight_combo', 'title_weight', 'text_or', 'bold'),
    ('title_pad_spin', 'title_pad', 'float'),
    # --- legend frame ---
    ('legend_frame_on_check', 'legend_frame_on', 'bool'),
    ('legend_frame_alpha_spin', 'legend_frame_alpha', 'float'),
    # --- adjust text scalars ---
    ('adjust_iter_lim_spin', 'adjust_text_iter_lim', 'int'),
    ('adjust_time_lim_spin', 'adjust_text_time_lim', 'float'),
]


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
        self._style_snapshot: dict[str, object] = {}

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
        self._style_snapshot = {}
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
            translated_str = translate(key)
            if isinstance(child, QGroupBox):
                child.setTitle(translated_str)
            elif isinstance(child, (QLabel, QPushButton, QCheckBox, QRadioButton)):
                child.setText(translated_str)

    def _on_change(self):
        """参数变化回调"""
        for key, timer in list(self._slider_timers.items()):
            try:
                timer.stop()
            except Exception:
                pass
        self._slider_timers.clear()

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

    # ------------------------------------------------------------------
    # 数据驱动的样式收集
    # ------------------------------------------------------------------

    def _collect_style_updates(self) -> dict[str, object]:
        """遍历 ``_STYLE_WIDGET_MAP``，从已注册的 widget 提取样式更新。

        Returns:
            以 *state_key* 为键的样式更新字典。
        """
        updates: dict[str, object] = {}
        for attr, key, extractor, *args in _STYLE_WIDGET_MAP:
            widget = getattr(self, attr, None)
            if widget is None:
                continue
            if extractor == 'bool':
                updates[key] = bool(widget.isChecked())
            elif extractor == 'int':
                updates[key] = int(widget.value())
            elif extractor == 'float':
                updates[key] = float(widget.value())
            elif extractor == 'text':
                updates[key] = widget.currentText()
            elif extractor == 'text_or':
                updates[key] = widget.currentText() or (args[0] if args else '')
            elif extractor == 'color':
                updates[key] = _safe_color(widget, args[0] if args else '#000000')
        return updates

    # ------------------------------------------------------------------
    # 样式变化处理
    # ------------------------------------------------------------------

    def _on_style_change(self, *_args):
        """处理样式变化"""
        if not getattr(self, "_is_initialized", False):
            return

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

        # ---- 数据驱动: 从 _STYLE_WIDGET_MAP 批量提取样式更新 ----
        style_updates: dict[str, object] = {}
        style_updates = self._collect_style_updates()

        # ---- 特殊处理: 需额外逻辑的控件 ----

        # 配色方案 (用于后续 replot 检测)
        color_combo = getattr(self, 'color_combo', None)
        new_scheme = color_combo.currentText() if color_combo is not None else app_state.color_scheme
        style_updates['color_scheme'] = new_scheme

        # 字体选择器 (<Default> 哨兵值处理)
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

        # 字号字典
        font_size_spins = getattr(self, 'font_size_spins', {})
        if font_size_spins:
            style_updates['plot_font_sizes'] = {k: v.value() for k, v in font_size_spins.items()}

        # adjust_text 成对 spinners → 元组
        for base, key in [('adjust_force_text', 'adjust_text_force_text'),
                          ('adjust_force_static', 'adjust_text_force_static'),
                          ('adjust_expand', 'adjust_text_expand')]:
            x = getattr(self, f'{base}_x_spin', None)
            y = getattr(self, f'{base}_y_spin', None)
            if x is not None and y is not None:
                style_updates[key] = (float(x.value()), float(y.value()))

        # 图例框架背景 / 边框 (纯文本，不使用 _safe_color)
        legend_frame_face_edit = getattr(self, 'legend_frame_face_edit', None)
        if legend_frame_face_edit is not None:
            style_updates['legend_frame_facecolor'] = legend_frame_face_edit.text() or '#ffffff'
        legend_frame_edge_edit = getattr(self, 'legend_frame_edge_edit', None)
        if legend_frame_edge_edit is not None:
            style_updates['legend_frame_edgecolor'] = legend_frame_edge_edit.text() or '#cbd5f5'

        # ---- line_styles 同步 ----
        if hasattr(app_state, 'line_styles'):
            app_state.line_styles.setdefault('model_curve', {})['linewidth'] = float(
                style_updates.get('model_curve_width', app_state.model_curve_width)
            )
            app_state.line_styles.setdefault('paleoisochron', {})['linewidth'] = float(
                style_updates.get('paleoisochron_width', app_state.paleoisochron_width)
            )
            app_state.line_styles.setdefault('model_age_line', {})['linewidth'] = float(
                style_updates.get('model_age_line_width', app_state.model_age_line_width)
            )
            app_state.line_styles.setdefault('isochron', {})['linewidth'] = float(
                style_updates.get('isochron_line_width', app_state.isochron_line_width)
            )

        # ---- 保存快照（撤销用） ----
        self._style_snapshot = {
            key: getattr(app_state, key, None)
            for key in style_updates
            if hasattr(app_state, key)
        }

        # ---- 提交到状态网关 ----
        if style_updates:
            state_gateway.set_panel_style_updates(style_updates)

        # ---- fig / ax 直接样式更新 ----
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

        # ---- 判定是否需要完整重绘 ----
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

    # ------------------------------------------------------------------
    # 样式撤销
    # ------------------------------------------------------------------

    def _undo_style(self) -> None:
        """Revert the last style change from snapshot, one level only."""
        if not self._style_snapshot:
            logger.info("No style change to undo.")
            return
        try:
            state_gateway.set_panel_style_updates(self._style_snapshot)
            self._style_snapshot = {}
            logger.info("Style change undone")
            if self.callback:
                self.callback()
        except Exception:
            logger.exception("Failed to undo style change")

    # ------------------------------------------------------------------
    # QToolBox 状态持久化
    # ------------------------------------------------------------------

    def _save_toolbox_state(self, toolbox, section_key):
        """保存 QToolBox 当前展开的 section 索引到 QSettings。

        Args:
            toolbox: QToolBox 实例。
            section_key: 唯一标识该工具箱的字符串键（如 ``'data'``、``'display'``）。
        """
        settings = QSettings("IsotopesAnalyse", "ToolBox")
        settings.setValue(f"{section_key}/currentIndex", toolbox.currentIndex())

    def _restore_toolbox_state(self, toolbox, section_key):
        """从 QSettings 恢复 QToolBox 的 section 索引并连接保存信号。

        在 ``build()`` 中完成所有 ``addItem()`` 调用后调用此方法。
        它会将当前 section 恢复为上次保存的值，并自动连接
        ``currentChanged`` 信号，以便后续切换时自动持久化。

        Args:
            toolbox: QToolBox 实例。
            section_key: 唯一标识该工具箱的字符串键。
        """
        settings = QSettings("IsotopesAnalyse", "ToolBox")
        saved_index = settings.value(f"{section_key}/currentIndex", 0, type=int)
        if 0 <= saved_index < toolbox.count():
            toolbox.setCurrentIndex(saved_index)
        toolbox.currentChanged.connect(
            lambda idx, tb=toolbox, sk=section_key: self._save_toolbox_state(tb, sk)
        )
