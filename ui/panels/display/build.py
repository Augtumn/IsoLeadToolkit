"""Display panel UI construction and control helpers."""
from __future__ import annotations

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


from .build_pages import DisplayBuildPagesMixin
from .build_pages_axes import DisplayBuildAxesMixin


class DisplayBuildMixin(DisplayBuildPagesMixin, DisplayBuildAxesMixin):
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
        self.label_color_edit = None
        self.label_weight_combo = None
        self.label_pad_spin = None
        self.title_color_edit = None
        self.title_weight_combo = None
        self.title_pad_spin = None
        self.adjust_force_text_x_spin = None
        self.adjust_force_text_y_spin = None
        self.adjust_force_static_x_spin = None
        self.adjust_force_static_y_spin = None
        self.adjust_expand_x_spin = None
        self.adjust_expand_y_spin = None
        self.adjust_iter_lim_spin = None
        self.adjust_time_lim_spin = None
        self._section_toolbox = None
        self._search_edit = None
        self._search_match_label = None

    def _collect_widget_text(self, widget) -> str:
        """Recursively collect display text from QLabel and QGroupBox widgets."""
        texts = []
        if isinstance(widget, QLabel):
            t = widget.text()
            if t:
                texts.append(t)
        elif isinstance(widget, QGroupBox):
            t = widget.title()
            if t:
                texts.append(t)
        for label in widget.findChildren(QLabel):
            t = label.text()
            if t:
                texts.append(t)
        for group in widget.findChildren(QGroupBox):
            t = group.title()
            if t:
                texts.append(t)
        return ' '.join(texts)

    def _on_search_changed(self, text: str):
        """Filter toolbox pages by search text."""
        toolbox = self._section_toolbox
        if toolbox is None:
            return
        text = text.strip()
        if not text:
            for i in range(toolbox.count()):
                toolbox.setItemEnabled(i, True)
            self._search_match_label.setText('')
            return

        match_count = 0
        text_lower = text.lower()
        for i in range(toolbox.count()):
            page = toolbox.widget(i)
            page_text = self._collect_widget_text(page).lower()
            if text_lower in page_text:
                toolbox.setItemEnabled(i, True)
                match_count += 1
            else:
                toolbox.setItemEnabled(i, False)

        if match_count == 0:
            self._search_match_label.setText(translate("No matches"))
        else:
            self._search_match_label.setText(
                translate("{n} matches").format(n=match_count)
            )

    def _clear_search(self):
        """Clear search text and reset filter."""
        if self._search_edit:
            self._search_edit.clear()
            self._search_edit.setFocus()

    def build(self) -> QWidget:
        widget = self._build_display_section()
        self._is_initialized = True
        return widget

    def _build_display_section(self):
        """构建显示部分"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Search/filter bar
        search_layout = QHBoxLayout()
        search_layout.setSpacing(4)
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText(translate("Search settings..."))
        self._search_edit.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(self._search_edit, 1)

        self._search_clear_btn = QPushButton("×")
        self._search_clear_btn.setFixedWidth(28)
        self._search_clear_btn.clicked.connect(self._clear_search)
        search_layout.addWidget(self._search_clear_btn)

        self._search_match_label = QLabel("")
        search_layout.addWidget(self._search_match_label)
        layout.addLayout(search_layout)

        section_toolbox = QToolBox()
        section_toolbox.setObjectName('display_section_toolbox')
        # Language refresh: BasePanel._update_translations re-labels the tabs.
        section_toolbox.setProperty('toolbox_tab_keys', '["Presets & Themes", "Text & Markers", "Axes, Grid & Canvas"]')
        self._section_toolbox = section_toolbox

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

        self._build_theme_page(presets_layout)
        self._build_saved_settings_page(presets_layout)
        self._build_font_page(style_layout)
        self._build_marker_page(style_layout)
        self._build_axes_page(axes_page_layout)
        section_toolbox.addItem(presets_page, translate("Presets & Themes"))
        section_toolbox.addItem(style_page, translate("Text & Markers"))
        section_toolbox.addItem(axes_page, translate("Axes, Grid & Canvas"))
        self._restore_toolbox_state(section_toolbox, 'display')
        layout.addWidget(section_toolbox)

        self._sync_color_controls_from_state()

        layout.addStretch()
        return widget
