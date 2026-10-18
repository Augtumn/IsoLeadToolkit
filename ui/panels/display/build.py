"""Display panel UI construction and control helpers."""
from __future__ import annotations

from ui.panels.widget_state import reset_widget_state

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
    QRadioButton,
    QSpinBox,
    QToolBox,
    QVBoxLayout,
    QWidget,
)

from core import app_state, translate


from .build_pages import DisplayBuildPagesMixin
from .build_pages_axes import DisplayBuildAxesMixin

#: Methods this class expects from the classes it is composed with
#: (explicit interface, UI review item I).
REQUIRES_DisplayBuildMixin = (
    "_apply_ui_theme",
    "_build_axes_page",
    "_build_font_page",
    "_build_kde_page",
    "_build_marker_page",
    "_build_saved_settings_page",
    "_build_theme_page",
    "_restore_toolbox_state",
    "_sync_color_controls_from_state",
)


#: Every widget this panel builds, with its fallback. One table instead of one assignment per line:
#: the set is visible in one place and a reset cannot forget a member.
_WIDGET_DEFAULTS: dict[str, object] = {
    'ui_theme_combo': None,
    'theme_name_edit': None,
    'theme_load_combo': None,
    'grid_check': None,
    'primary_font_combo': None,
    'cjk_font_combo': None,
    'font_size_spins': dict,
    'show_title_check': None,
    'marker_size_spin': None,
    'marker_alpha_spin': None,
    'scatter_edge_check': None,
    'figure_dpi_spin': None,
    'figure_bg_edit': None,
    'axes_bg_edit': None,
    'grid_color_edit': None,
    'grid_width_spin': None,
    'grid_alpha_spin': None,
    'grid_style_combo': None,
    'tick_dir_combo': None,
    'tick_color_edit': None,
    'tick_length_spin': None,
    'tick_width_spin': None,
    'minor_ticks_check': None,
    'minor_tick_length_spin': None,
    'minor_tick_width_spin': None,
    'axis_linewidth_spin': None,
    'axis_line_color_edit': None,
    'show_top_spine_check': None,
    'show_right_spine_check': None,
    'minor_grid_check': None,
    'minor_grid_color_edit': None,
    'minor_grid_width_spin': None,
    'minor_grid_alpha_spin': None,
    'minor_grid_style_combo': None,
    'scatter_edgecolor_edit': None,
    'scatter_edgewidth_spin': None,
    'label_color_edit': None,
    'label_weight_combo': None,
    'label_pad_spin': None,
    'title_color_edit': None,
    'title_weight_combo': None,
    'title_pad_spin': None,
    'adjust_force_text_x_spin': None,
    'adjust_force_text_y_spin': None,
    'adjust_force_static_x_spin': None,
    'adjust_force_static_y_spin': None,
    'adjust_expand_x_spin': None,
    'adjust_expand_y_spin': None,
    'adjust_iter_lim_spin': None,
    'adjust_time_lim_spin': None,
    '_section_toolbox': None,
    '_search_edit': None,
    '_search_match_label': None,
    '_search_hidden_pages': list,
}


class DisplayBuildMixin(DisplayBuildPagesMixin, DisplayBuildAxesMixin):
    """Build and widget helpers for display panel."""

    def __init__(self, callback=None, parent=None):
        super().__init__(callback, parent)

    def reset_state(self):
        """Widgets are rebuilt with the panel."""
        super().reset_state()
        reset_widget_state(self, _WIDGET_DEFAULTS)


    def _collect_widget_text(self, widget) -> str:
        """Recursively collect display text from a page's widgets.

        Indexes every user-visible label, not only QLabel/QGroupBox: checkbox,
        button and radio texts, combo item texts and toolbox tab texts are all
        things a user types into the search box.
        """
        texts = []
        if isinstance(widget, QLabel):
            t = widget.text()
            if t:
                texts.append(t)
        elif isinstance(widget, QGroupBox):
            t = widget.title()
            if t:
                texts.append(t)
        elif isinstance(widget, (QCheckBox, QPushButton, QRadioButton)):
            t = widget.text()
            if t:
                texts.append(t)
        elif isinstance(widget, QComboBox):
            texts.extend(widget.itemText(index) for index in range(widget.count()))
        elif isinstance(widget, QToolBox):
            texts.extend(widget.itemText(index) for index in range(widget.count()))
        for label in widget.findChildren(QLabel):
            t = label.text()
            if t:
                texts.append(t)
        for group in widget.findChildren(QGroupBox):
            t = group.title()
            if t:
                texts.append(t)
        for toggle in widget.findChildren((QCheckBox, QRadioButton)):
            t = toggle.text()
            if t:
                texts.append(t)
        for button in widget.findChildren(QPushButton):
            t = button.text()
            if t:
                texts.append(t)
        for combo in widget.findChildren(QComboBox):
            texts.extend(combo.itemText(index) for index in range(combo.count()))
        return ' '.join(texts)

    def _hide_toolbox_items(self, toolbox, keep_indices) -> None:
        """Remove every page outside *keep_indices* and remember it for restore.

        QToolBox.setItemVisible() is not used: it aborts the process in this build
        (verified on a bare QToolBox, offscreen and shown), so the pages are taken out
        of the toolbox and put back with their original text and position.
        """
        hidden = []
        for index in range(toolbox.count() - 1, -1, -1):
            if index in keep_indices:
                continue
            hidden.append({
                'index': index,
                'widget': toolbox.widget(index),
                'text': toolbox.itemText(index),
            })
            toolbox.removeItem(index)
        self._search_hidden_pages = hidden

    def _restore_hidden_toolbox_items(self, toolbox) -> None:
        """Put back every page removed by :meth:`_hide_toolbox_items`."""
        hidden = list(self._search_hidden_pages or [])
        self._search_hidden_pages = []
        if not hidden:
            return
        for entry in sorted(hidden, key=lambda item: item['index']):
            widget = entry.get('widget')
            if widget is None:
                continue
            toolbox.insertItem(entry['index'], widget, entry['text'])

    def _on_search_changed(self, text: str):
        """Filter toolbox pages by search text."""
        toolbox = self._section_toolbox
        if toolbox is None:
            return
        self._restore_hidden_toolbox_items(toolbox)
        text = text.strip()
        if not text:
            for i in range(toolbox.count()):
                toolbox.setItemEnabled(i, True)
            self._search_match_label.setText('')
            return

        matches = []
        text_lower = text.lower()
        for i in range(toolbox.count()):
            page = toolbox.widget(i)
            page_text = self._collect_widget_text(page).lower()
            if text_lower in page_text:
                toolbox.setItemEnabled(i, True)
                matches.append(i)
            else:
                toolbox.setItemEnabled(i, False)

        # Hiding matters as much as disabling: a disabled current page stays
        # visible, so "No matches" sat next to an un-filtered page.
        self._hide_toolbox_items(toolbox, set(matches))

        if not matches:
            self._search_match_label.setText(translate("No matches"))
        else:
            self._search_match_label.setText(
                translate("{n} matches").format(n=len(matches))
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
        self._search_edit.setPlaceholderText(translate("Search settings…"))
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
        # Language refresh: BasePanel._update_translations re-labels the tabs. The pages
        # added through add_group_page() append their own key, so only the three
        # hand-built pages are listed here - listing the KDE page too duplicated the key.
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
        self._build_kde_page(section_toolbox)
        self._restore_toolbox_state(section_toolbox, 'display')
        layout.addWidget(section_toolbox)

        self._sync_color_controls_from_state()

        # The restored ui_theme reached the combo but was never applied: setStyleSheet /
        # plt.style.use were only reachable from currentTextChanged, so a restarted
        # session showed the saved theme name over the default palette.
        self._apply_ui_theme(app_state.ui_theme, refresh=False, apply_mpl=False)

        layout.addStretch()
        return widget
