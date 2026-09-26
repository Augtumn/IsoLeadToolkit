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

from .panel_style import PanelStyleMixin


class BasePanel(PanelStyleMixin, QWidget):
    """所有面板的基类，提供共享工具方法"""

    @staticmethod
    def _normalize_render_mode(mode) -> str:
        """Normalize render mode aliases."""
        if not mode:
            return "UMAP"
        value = str(mode)
        if value in ("t-SNE", "TSNE", "tSNE"):
            return "tSNE"
        if value in ("PB_MODELS_76", "PB_MODELS_86"):
            return "PB_EVOL_76" if value.endswith("_76") else "PB_EVOL_86"
        return value

    def _connect_spinbox_deferred(self, spinbox, callback, *, pass_value: bool = True) -> None:
            """Apply spinbox changes only when editing is finished."""
            try:
                spinbox.setKeyboardTracking(False)
            except Exception as err:
                logger.warning("_connect_spinbox_deferred failed: %s", err)

            if pass_value:
                spinbox.editingFinished.connect(lambda s=spinbox: callback(s.value()))
            else:
                spinbox.editingFinished.connect(callback)


    def _sync_toggle_widgets(self, checked, *widgets):
        """Sync toggle widgets to the same checked state."""
        for widget in widgets:
            if widget is None:
                continue
            if widget.isChecked() != checked:
                widget.blockSignals(True)
                widget.setChecked(checked)
                widget.blockSignals(False)

    def _open_line_style_dialog(self, style_key, swatch):
        """Open the line style dialog for *style_key*, refreshing on apply."""
        from ui.panels.display.dialogs.line_style_dialog import open_line_style_dialog

        open_line_style_dialog(self, style_key, swatch=swatch, on_applied=self._on_change)

    @staticmethod
    def add_group_page(section_toolbox, group_widget, title_key) -> None:
        """Add a QGroupBox as a labelled toolbox page (shared by all panels)."""
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(6, 6, 6, 6)
        page_layout.setSpacing(8)
        page_layout.addWidget(group_widget)
        page_layout.addStretch()
        section_toolbox.addItem(page, translate(title_key))
        # Record the English key so _update_translations can re-label the tab
        # on language switches (appends to any keys set by the caller).
        existing = section_toolbox.property('toolbox_tab_keys')
        try:
            keys = json.loads(existing) if existing else []
        except Exception:
            keys = []
        keys.append(title_key)
        section_toolbox.setProperty('toolbox_tab_keys', json.dumps(keys))

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

        支持的控件类型: QGroupBox (setTitle), QLabel/QPushButton/QCheckBox/
        QRadioButton/QToolButton (setText), QToolBox (``toolbox_tab_keys``
        JSON 属性), QComboBox (``combo_item_keys`` JSON 属性，与 addItem
        顺序一致)。
        """
        import json as _json

        if root is None:
            root = self
        for child in root.findChildren(QWidget):
            key = child.property('translate_key')
            if key:
                translated_str = translate(key)
                if isinstance(child, QGroupBox):
                    child.setTitle(translated_str)
                elif isinstance(child, (QLabel, QPushButton, QCheckBox, QRadioButton, QToolButton)):
                    child.setText(translated_str)

            if isinstance(child, QToolBox):
                tab_keys = child.property('toolbox_tab_keys')
                if isinstance(tab_keys, str) and tab_keys:
                    try:
                        keys = _json.loads(tab_keys)
                        for idx, tab_key in enumerate(keys):
                            if idx < child.count():
                                child.setItemText(idx, translate(tab_key))
                    except Exception as err:
                        logger.warning("_update_translations failed: %s", err)
            elif isinstance(child, QComboBox):
                item_keys = child.property('combo_item_keys')
                if isinstance(item_keys, str) and item_keys:
                    try:
                        keys = _json.loads(item_keys)
                        for idx, item_key in enumerate(keys):
                            if idx < child.count():
                                child.setItemText(idx, translate(item_key))
                    except Exception as err:
                        logger.warning("_update_translations failed: %s", err)

    def _on_change(self):
        """参数变化回调"""
        for key, timer in list(self._slider_timers.items()):
            try:
                timer.stop()
            except Exception as err:
                logger.warning("_on_change failed: %s", err)
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

    # ------------------------------------------------------------------
    # 样式变化处理
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 样式撤销
    # ------------------------------------------------------------------

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
