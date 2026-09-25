"""面板基类 - 提供共享工具方法"""
from __future__ import annotations

import json
import logging
from typing import Callable

from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QLabel,
    QPushButton,
    QRadioButton,
    QToolBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from PyQt5.QtCore import QSettings, QTimer

from core import app_state, state_gateway, translate

logger = logging.getLogger(__name__)

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

class PanelStyleMixin:
    """Style updates collected from panel widgets, plus undo snapshots."""

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

    def _on_style_change(self, *_args):
        """处理样式变化"""
        if not getattr(self, "_is_initialized", False):
            return

        previous_scheme = app_state.color_scheme
        previous_fonts = (
            app_state.custom_primary_font,
            app_state.custom_cjk_font
        )
        previous_font_sizes = dict(app_state.plot_font_sizes)
        previous_show_title = bool(app_state.show_plot_title)
        previous_title_pad = float(app_state.title_pad)
        previous_line_widths = (
            app_state.model_curve_width,
            app_state.paleoisochron_width,
            app_state.model_age_line_width,
            app_state.isochron_line_width,
        )

        # ---- 数据驱动: 从 _STYLE_WIDGET_MAP 批量提取样式更新 ----
        style_updates: dict[str, object] = self._collect_style_updates()

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

        # ---- line_styles 同步（拷贝后经 gateway 提交，避免被 store 回滚） ----
        line_styles = dict(app_state.line_styles or {})
        line_width_updates = {
            'model_curve': float(style_updates.get('model_curve_width', app_state.model_curve_width)),
            'paleoisochron': float(style_updates.get('paleoisochron_width', app_state.paleoisochron_width)),
            'model_age_line': float(style_updates.get('model_age_line_width', app_state.model_age_line_width)),
            'isochron': float(style_updates.get('isochron_line_width', app_state.isochron_line_width)),
        }
        changed = False
        for key, width in line_width_updates.items():
            entry = dict(line_styles.get(key, {}) or {})
            if entry.get('linewidth') != width:
                entry['linewidth'] = width
                line_styles[key] = entry
                changed = True
        if changed:
            state_gateway.set_line_styles(line_styles)

        # ---- 保存快照（撤销用） ----
        self._style_snapshot = {key: getattr(app_state, key, None) for key in style_updates}

        # ---- 提交到状态网关 ----
        if style_updates:
            state_gateway.set_panel_style_updates(style_updates)

        # ---- 状态栏短暂消息 ----
        if style_updates:
            try:
                from PyQt5.QtWidgets import QApplication
                for widget in QApplication.topLevelWidgets():
                    if hasattr(widget, 'statusBar'):
                        widget.statusBar().showMessage(translate("Settings applied"), 1500)
                        break
            except Exception:
                pass

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
