"""Build mixin for data import dialog."""

import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QBoxLayout,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)

from core import app_state, available_languages, set_language, state_gateway, translate


class DataImportBuildMixin:
    """Construct and translate data import dialog UI."""

    PREVIEW_ROWS = 10

    def __init__(
        self,
        default_file=None,
        default_sheet=None,
        default_group_cols=None,
        default_data_cols=None,
        default_render_mode=None,
        parent=None,
    ):
        super().__init__(parent)
        self.result = None
        self.selected_file = default_file
        self.selected_sheet = default_sheet
        self.default_render_mode = default_render_mode or '2D'
        self._language_labels = dict(available_languages())
        self.default_group_cols = set(default_group_cols or [])
        self.default_data_cols = set(default_data_cols or [])
        self.df = None
        self.all_columns = []

        self._setup_ui()
        self._refresh_from_defaults()

    def _setup_ui(self):
        self.setWindowTitle(translate("Data Import Wizard"))
        self.resize(980, 720)
        self.setMinimumSize(900, 640)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        title = QLabel(translate("Data Import Wizard"))
        title_font = QFont(title.font())
        title_font.setPointSize(title_font.pointSize() + 2)
        title_font.setBold(True)
        title.setFont(title_font)
        self.title_label = title
        header_row.addWidget(title)

        header_row.addStretch()

        self.lang_label = QLabel()
        header_row.addWidget(self.lang_label)

        self.lang_combo = QComboBox()
        self.lang_combo.setMinimumWidth(140)
        self.lang_combo.currentIndexChanged.connect(self._on_language_change)
        header_row.addWidget(self.lang_combo)

        layout.addLayout(header_row)

        subtitle = QLabel(translate("Select file, worksheet, columns, and initial render mode in one workflow."))
        subtitle.setWordWrap(True)
        self.subtitle_label = subtitle
        layout.addWidget(subtitle)

        top_container = QWidget()
        top_layout = QHBoxLayout(top_container)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(12)

        self.file_group = self._build_file_section()
        self.file_group.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        self.file_group.setMinimumWidth(260)

        self.sheet_group = self._build_sheet_section()
        self.sheet_group.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        self.sheet_group.setMinimumWidth(220)

        self.columns_group = self._build_columns_section()

        top_layout.addWidget(self.file_group)
        top_layout.addWidget(self.sheet_group)
        top_layout.addWidget(self.columns_group, 1)

        layout.addWidget(top_container, 1)
        layout.addWidget(self._build_render_section())
        layout.addWidget(self._build_preview_section())

        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(8)
        footer_layout.addStretch()

        cancel_button = QPushButton(translate("Cancel"))
        cancel_button.clicked.connect(self.reject)
        self.cancel_btn = cancel_button
        footer_layout.addWidget(cancel_button)

        apply_button = QPushButton(translate("Apply"))
        apply_button.clicked.connect(self._ok_clicked)
        self.apply_btn = apply_button
        footer_layout.addWidget(apply_button)

        layout.addLayout(footer_layout)

        self._refresh_language()
        self._apply_translations()

    def _build_file_section(self):
        group = QGroupBox(translate("File"))
        self.file_group = group
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(12, 10, 12, 12)
        group_layout.setSpacing(8)

        self.file_label = QLabel(translate("No file selected"))
        self.file_label.setWordWrap(True)
        group_layout.addWidget(self.file_label)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)

        browse_button = QPushButton(translate("Browse..."))
        browse_button.clicked.connect(self._browse_file)
        self.browse_btn = browse_button
        button_row.addWidget(browse_button)

        clear_button = QPushButton(translate("Clear Selection"))
        clear_button.clicked.connect(self._clear_file)
        self.clear_btn = clear_button
        button_row.addWidget(clear_button)

        button_row.addStretch()
        group_layout.addLayout(button_row)

        recent_label = QLabel(translate("Recent Files"))
        recent_label.setStyleSheet("font-weight: bold;")
        self.recent_label = recent_label
        group_layout.addWidget(recent_label)

        self.recent_list = QListWidget()
        self.recent_list.setSelectionMode(QListWidget.SingleSelection)
        self.recent_list.itemDoubleClicked.connect(self._on_recent_file_selected)
        group_layout.addWidget(self.recent_list, 1)

        return group

    def _build_sheet_section(self):
        group = QGroupBox(translate("Sheet"))
        self.sheet_group = group
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(12, 10, 12, 12)
        group_layout.setSpacing(8)

        self.sheet_list = QListWidget()
        self.sheet_list.setSelectionMode(QListWidget.SingleSelection)
        self.sheet_list.itemSelectionChanged.connect(self._on_sheet_selected)
        group_layout.addWidget(self.sheet_list, 1)

        return group

    def _build_columns_section(self):
        self.columns_container = QWidget()
        self.columns_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.columns_layout = QBoxLayout(QBoxLayout.LeftToRight, self.columns_container)
        self.columns_layout.setContentsMargins(0, 0, 0, 0)
        self.columns_layout.setSpacing(12)

        self.group_card = self._build_column_section(
            translate("Grouping Columns"),
            translate("Pick one or more categorical columns to color and organize the scatter plot."),
            'group',
        )
        self.data_card = self._build_column_section(
            translate("Data Columns"),
            translate("Choose numeric measurement columns for 2D/3D, dimensionality reduction, and geochemistry views."),
            'data',
        )

        self.columns_layout.addWidget(self.group_card)
        self.columns_layout.addWidget(self.data_card)
        self._update_columns_layout()
        return self.columns_container

    def _build_preview_section(self):
        group = QGroupBox(translate("Data Preview"))
        self.preview_group = group
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(12, 10, 12, 12)
        group_layout.setSpacing(6)

        self.preview_label = QLabel(
            translate("Showing first {rows} rows across all columns (scroll horizontally to view more).")
            .format(rows=self.PREVIEW_ROWS)
        )
        self.preview_label.setWordWrap(True)
        group_layout.addWidget(self.preview_label)

        self.preview_table = QTableWidget()
        self.preview_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.preview_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.preview_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.preview_table.horizontalHeader().setStretchLastSection(False)
        self.preview_table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.setWordWrap(False)
        self.preview_table.verticalHeader().setVisible(False)
        group_layout.addWidget(self.preview_table)

        return group

    def _build_render_section(self):
        group = QGroupBox(translate("Initial Render Mode"))
        self.render_group = group
        group_layout = QHBoxLayout(group)
        group_layout.setContentsMargins(12, 10, 12, 12)
        group_layout.setSpacing(8)

        self.render_label = QLabel(
            translate("Tip: choose a fast mode (for example 2D Scatter) for first render on large datasets.")
        )
        self.render_label.setWordWrap(True)
        group_layout.addWidget(self.render_label, 1)

        self.render_mode_combo = QComboBox()
        self.render_mode_combo.setMinimumWidth(220)
        self._populate_render_modes()
        group_layout.addWidget(self.render_mode_combo)

        return group

    def _populate_render_modes(self):
        if not hasattr(self, 'render_mode_combo') or self.render_mode_combo is None:
            return

        current_value = self.render_mode_combo.currentData()

        options = [
            (translate("2D Scatter (Fast)"), '2D'),
            (translate("3D Scatter"), '3D'),
            (translate("Ternary"), 'Ternary'),
            (translate("V1-V2 Diagram"), 'V1V2'),
            (translate("Pb Evolution 206-207"), 'PB_EVOL_76'),
            (translate("Pb Evolution 206-208"), 'PB_EVOL_86'),
            (translate("Mu vs Age"), 'PB_MU_AGE'),
            (translate("Kappa vs Age"), 'PB_KAPPA_AGE'),
            (translate("Plumbotectonics 206-207"), 'PLUMBOTECTONICS_76'),
            (translate("Plumbotectonics 206-208"), 'PLUMBOTECTONICS_86'),
            (translate("UMAP"), 'UMAP'),
            (translate("t-SNE"), 'tSNE'),
            (translate("PCA"), 'PCA'),
            (translate("Robust PCA"), 'RobustPCA'),
        ]
        self.render_mode_combo.blockSignals(True)
        self.render_mode_combo.clear()
        for label, value in options:
            self.render_mode_combo.addItem(label, value)
        preferred_value = current_value if current_value is not None else self.default_render_mode
        index = self.render_mode_combo.findData(preferred_value)
        if index < 0:
            index = self.render_mode_combo.findData('2D')
        if index >= 0:
            self.render_mode_combo.setCurrentIndex(index)
        self.render_mode_combo.blockSignals(False)

    def _refresh_language(self):
        current_lang = getattr(app_state, 'language', None) or 'en'
        self.lang_combo.blockSignals(True)
        self.lang_combo.clear()
        for code, name in self._language_labels.items():
            self.lang_combo.addItem(name, code)
        index = self.lang_combo.findData(current_lang)
        if index >= 0:
            self.lang_combo.setCurrentIndex(index)
        self.lang_combo.blockSignals(False)
        self._update_language_label(current_lang)

    def _apply_translations(self):
        self.setWindowTitle(translate("Data Import Wizard"))
        if self.title_label is not None:
            self.title_label.setText(translate("Data Import Wizard"))
        if self.subtitle_label is not None:
            self.subtitle_label.setText(
                translate("Select file, worksheet, columns, and initial render mode in one workflow.")
            )
        if self.file_group is not None:
            self.file_group.setTitle(translate("File"))
        if self.sheet_group is not None:
            self.sheet_group.setTitle(translate("Sheet"))
        if self.preview_group is not None:
            self.preview_group.setTitle(translate("Data Preview"))
        if getattr(self, 'render_group', None) is not None:
            self.render_group.setTitle(translate("Initial Render Mode"))
        if getattr(self, 'render_label', None) is not None:
            self.render_label.setText(
                translate("Tip: choose a fast mode (for example 2D Scatter) for first render on large datasets.")
            )
        self._populate_render_modes()
        if self.recent_label is not None:
            self.recent_label.setText(translate("Recent Files"))
        if self.browse_btn is not None:
            self.browse_btn.setText(translate("Browse..."))
        if self.clear_btn is not None:
            self.clear_btn.setText(translate("Clear Selection"))
        if self.cancel_btn is not None:
            self.cancel_btn.setText(translate("Cancel"))
        if self.apply_btn is not None:
            self.apply_btn.setText(translate("Apply"))
        if self.group_card is not None:
            self.group_card.setTitle(translate("Grouping Columns"))
        if self.data_card is not None:
            self.data_card.setTitle(translate("Data Columns"))
        if self.group_desc_label is not None:
            self.group_desc_label.setText(
                translate("Pick one or more categorical columns to color and organize the scatter plot.")
            )
        if self.data_desc_label is not None:
            self.data_desc_label.setText(
                translate("Choose numeric measurement columns for 2D/3D, dimensionality reduction, and geochemistry views.")
            )
        if self.group_select_all_btn is not None:
            self.group_select_all_btn.setText(translate("Select all"))
        if self.group_clear_btn is not None:
            self.group_clear_btn.setText(translate("Clear"))
        if self.data_select_all_btn is not None:
            self.data_select_all_btn.setText(translate("Select all"))
        if self.data_clear_btn is not None:
            self.data_clear_btn.setText(translate("Clear"))
        if self.preview_label is not None:
            self.preview_label.setText(
                translate("Showing first {rows} rows across all columns (scroll horizontally to view more).")
                .format(rows=self.PREVIEW_ROWS)
            )
        if self.file_label is not None and not self.selected_file:
            self.file_label.setText(translate("No file selected"))
        if self.sheet_list is not None and not self.sheet_list.isEnabled() and self.sheet_list.count() == 1:
            item = self.sheet_list.item(0)
            if item is not None:
                item.setText(translate("No sheet"))

    def _update_language_label(self, current_lang):
        if current_lang == 'zh':
            self.lang_label.setText("语言:")
        else:
            self.lang_label.setText("Language:")

    def _on_language_change(self, _index):
        code = self.lang_combo.currentData()
        if not code:
            return
        if set_language(code):
            state_gateway.set_language_code(code)
            self._update_language_label(code)
            self._apply_translations()

    def _build_column_section(self, title, description, selection_type):
        card = QGroupBox(title)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 12)
        card_layout.setSpacing(8)

        description_label = QLabel(description)
        description_label.setWordWrap(True)
        card_layout.addWidget(description_label)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        select_all_button = QPushButton(translate("Select all"))
        select_all_button.clicked.connect(lambda: self._select_all(selection_type))
        toolbar.addWidget(select_all_button)

        clear_button = QPushButton(translate("Clear"))
        clear_button.clicked.connect(lambda: self._clear_selection(selection_type))
        toolbar.addWidget(clear_button)

        toolbar.addStretch()
        card_layout.addLayout(toolbar)

        list_widget = QListWidget()
        list_widget.setSelectionMode(QListWidget.MultiSelection)
        list_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        list_widget.itemSelectionChanged.connect(
            lambda: self._on_selection_changed(list_widget, selection_type)
        )

        card_layout.addWidget(list_widget, 1)

        if selection_type == 'group':
            self.group_list = list_widget
            self.group_desc_label = description_label
            self.group_select_all_btn = select_all_button
            self.group_clear_btn = clear_button
        else:
            self.data_list = list_widget
            self.data_desc_label = description_label
            self.data_select_all_btn = select_all_button
            self.data_clear_btn = clear_button

        return card

    def _update_columns_layout(self):
        if not hasattr(self, 'columns_layout'):
            return
        direction = QBoxLayout.LeftToRight if self.width() >= 900 else QBoxLayout.TopToBottom
        if self.columns_layout.direction() == direction:
            return
        self.columns_layout.setDirection(direction)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_columns_layout()

    def _update_file_display(self, file_path):
        if not file_path:
            self.file_label.setText(translate("No file selected"))
            return
        display_path = os.path.basename(file_path)
        directory = os.path.dirname(file_path)
        self.file_label.setText(f"{display_path}\\n{directory}")
