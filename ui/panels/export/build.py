"""Build/reset logic for export panel."""
from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QToolBox,
    QVBoxLayout,
    QWidget,
)

from core import state_gateway, translate


class ExportPanelBuildMixin:
    """Build/reset behavior for ExportPanel."""

    def reset_state(self):
        super().reset_state()
        self.export_csv_button = None
        self.export_excel_button = None
        self.export_append_button = None
        self.image_preset_combo = None
        self.image_format_combo = None
        self.image_point_size_spin = None
        self.image_legend_size_spin = None
        self.image_dpi_spin = None
        self.image_tight_bbox_check = None
        self.image_transparent_check = None
        self.image_pad_inches_spin = None
        self.image_style_source_label = None
        self.export_image_button = None
        self.preview_image_button = None
        self.image_label_size_spin = None
        self.image_title_size_spin = None
        self.image_tick_size_spin = None
        self.export_origin_button = None
        self._scienceplots_available = None

    def build(self) -> QWidget:
        export_options = state_gateway.get_export_image_options()

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        section_toolbox = QToolBox()
        section_toolbox.setObjectName('export_section_toolbox')

        data_export_group = QGroupBox(translate("Data Export"))
        data_export_group.setProperty('translate_key', 'Data Export')
        export_layout = QVBoxLayout()

        self.export_csv_button = QPushButton(translate("Export CSV"))
        self.export_csv_button.setProperty('translate_key', 'Export CSV')
        self.export_csv_button.setFixedWidth(200)
        self.export_csv_button.clicked.connect(self._on_export_csv)
        export_layout.addWidget(self.export_csv_button, 0, Qt.AlignHCenter)

        self.export_excel_button = QPushButton(translate("Export Excel"))
        self.export_excel_button.setProperty('translate_key', 'Export Excel')
        self.export_excel_button.setFixedWidth(200)
        self.export_excel_button.clicked.connect(self._on_export_excel)
        export_layout.addWidget(self.export_excel_button, 0, Qt.AlignHCenter)

        self.export_append_button = QPushButton(translate("Append to Excel"))
        self.export_append_button.setProperty('translate_key', 'Append to Excel')
        self.export_append_button.setFixedWidth(200)
        self.export_append_button.clicked.connect(self._on_export_append_excel)
        export_layout.addWidget(self.export_append_button, 0, Qt.AlignHCenter)

        data_export_group.setLayout(export_layout)

        export_page = QWidget()
        export_page_layout = QVBoxLayout(export_page)
        export_page_layout.setContentsMargins(6, 6, 6, 6)
        export_page_layout.setSpacing(8)
        export_page_layout.addWidget(data_export_group)
        export_page_layout.addStretch()
        section_toolbox.addItem(export_page, translate("Data Export"))

        image_group = QGroupBox(translate("Image Export"))
        image_group.setProperty('translate_key', 'Image Export')
        image_layout = QVBoxLayout()

        preset_row = QHBoxLayout()
        preset_label = QLabel(translate("Journal Preset"))
        preset_label.setProperty('translate_key', 'Journal Preset')
        preset_row.addWidget(preset_label)
        self.image_preset_combo = QComboBox()
        self.image_preset_combo.addItem(translate("Science Single Column"), 'science_single')
        self.image_preset_combo.addItem(translate("IEEE Single Column"), 'ieee_single')
        self.image_preset_combo.addItem(translate("Nature Double Column"), 'nature_double')
        self.image_preset_combo.addItem(translate("Presentation"), 'presentation')
        preset_key = str(export_options.get('preset_key') or 'science_single')
        preset_index = self.image_preset_combo.findData(preset_key)
        if preset_index >= 0:
            self.image_preset_combo.setCurrentIndex(preset_index)
        self.image_preset_combo.currentIndexChanged.connect(self._on_image_preset_changed)
        preset_row.addWidget(self.image_preset_combo)
        image_layout.addLayout(preset_row)

        style_source_row = QHBoxLayout()
        style_source_label = QLabel(translate("Template Source"))
        style_source_label.setProperty('translate_key', 'Template Source')
        style_source_row.addWidget(style_source_label)
        self.image_style_source_label = QLabel()
        style_source_row.addWidget(self.image_style_source_label)
        image_layout.addLayout(style_source_row)

        button_row = QHBoxLayout()
        self.preview_image_button = QPushButton(translate("Preview Export"))
        self.preview_image_button.setProperty('translate_key', 'Preview Export')
        self.preview_image_button.setFixedWidth(160)
        self.preview_image_button.clicked.connect(self._on_preview_image_clicked)
        button_row.addWidget(self.preview_image_button, 0, Qt.AlignHCenter)

        self.export_image_button = QPushButton(translate("Export Image"))
        self.export_image_button.setProperty('translate_key', 'Export Image')
        self.export_image_button.setFixedWidth(160)
        self.export_image_button.clicked.connect(self._on_export_image_clicked)
        button_row.addWidget(self.export_image_button, 0, Qt.AlignHCenter)
        image_layout.addLayout(button_row)

        origin_row = QHBoxLayout()
        self.export_origin_button = QPushButton(translate("Export to Origin"))
        self.export_origin_button.setProperty('translate_key', 'Export to Origin')
        self.export_origin_button.setFixedWidth(160)
        self.export_origin_button.clicked.connect(self._on_export_origin_clicked)
        origin_row.addWidget(self.export_origin_button, 0, Qt.AlignHCenter)
        image_layout.addLayout(origin_row)

        image_group.setLayout(image_layout)

        image_page = QWidget()
        image_page_layout = QVBoxLayout(image_page)
        image_page_layout.setContentsMargins(6, 6, 6, 6)
        image_page_layout.setSpacing(8)
        image_page_layout.addWidget(image_group)
        image_page_layout.addStretch()
        section_toolbox.addItem(image_page, translate("Image Export"))

        self._restore_toolbox_state(section_toolbox, 'export')
        layout.addWidget(section_toolbox)

        self._on_image_preset_changed()
        layout.addStretch()
        return widget
