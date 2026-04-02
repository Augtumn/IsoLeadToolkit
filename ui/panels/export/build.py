"""Build/reset logic for export panel."""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QToolBox,
    QVBoxLayout,
    QWidget,
)

from core import CONFIG, app_state, state_gateway, translate


class ExportPanelBuildMixin:
    """Build/reset behavior for ExportPanel."""

    def reset_state(self):
        super().reset_state()
        self.export_csv_button = None
        self.export_excel_button = None
        self.export_append_button = None
        self.export_selected_button = None
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

        self.export_selected_button = QPushButton(translate("Export Selected"))
        self.export_selected_button.setProperty('translate_key', 'Export Selected')
        self.export_selected_button.setFixedWidth(200)
        self.export_selected_button.clicked.connect(self._on_export_clicked)
        export_layout.addWidget(self.export_selected_button, 0, Qt.AlignHCenter)

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

        format_row = QHBoxLayout()
        format_label = QLabel(translate("Image Format"))
        format_label.setProperty('translate_key', 'Image Format')
        format_row.addWidget(format_label)
        self.image_format_combo = QComboBox()
        self.image_format_combo.addItem("PNG", "png")
        self.image_format_combo.addItem("TIFF", "tiff")
        self.image_format_combo.addItem("PDF", "pdf")
        self.image_format_combo.addItem("SVG", "svg")
        self.image_format_combo.addItem("EPS", "eps")
        image_ext = str(export_options.get('image_ext') or 'png')
        format_index = self.image_format_combo.findData(image_ext)
        if format_index >= 0:
            self.image_format_combo.setCurrentIndex(format_index)
        format_row.addWidget(self.image_format_combo)
        image_layout.addLayout(format_row)

        style_source_row = QHBoxLayout()
        style_source_label = QLabel(translate("Template Source"))
        style_source_label.setProperty('translate_key', 'Template Source')
        style_source_row.addWidget(style_source_label)
        self.image_style_source_label = QLabel()
        style_source_row.addWidget(self.image_style_source_label)
        image_layout.addLayout(style_source_row)

        dpi_row = QHBoxLayout()
        dpi_label = QLabel(translate("Export DPI"))
        dpi_label.setProperty('translate_key', 'Export DPI')
        dpi_row.addWidget(dpi_label)
        self.image_dpi_spin = QSpinBox()
        self.image_dpi_spin.setRange(72, 1200)
        self.image_dpi_spin.setSingleStep(25)
        self.image_dpi_spin.setValue(int(export_options.get('dpi', CONFIG.get('savefig_dpi', 400))))
        dpi_row.addWidget(self.image_dpi_spin)
        image_layout.addLayout(dpi_row)

        point_size_row = QHBoxLayout()
        point_size_label = QLabel(translate("Point Size"))
        point_size_label.setProperty('translate_key', 'Point Size')
        point_size_row.addWidget(point_size_label)
        self.image_point_size_spin = QSpinBox()
        self.image_point_size_spin.setRange(1, 50)
        self.image_point_size_spin.setSingleStep(1)
        self.image_point_size_spin.setValue(int(getattr(app_state, 'point_size', 60)))
        point_size_row.addWidget(self.image_point_size_spin)
        image_layout.addLayout(point_size_row)

        legend_size_row = QHBoxLayout()
        legend_size_label = QLabel(translate("Legend Size"))
        legend_size_label.setProperty('translate_key', 'Legend Size')
        legend_size_row.addWidget(legend_size_label)
        self.image_legend_size_spin = QSpinBox()
        self.image_legend_size_spin.setRange(1, 15)
        self.image_legend_size_spin.setSingleStep(1)
        legend_size = export_options.get('legend_size')
        self.image_legend_size_spin.setValue(int(legend_size) if legend_size is not None else 8)
        legend_size_row.addWidget(self.image_legend_size_spin)
        image_layout.addLayout(legend_size_row)

        bbox_row = QHBoxLayout()
        self.image_tight_bbox_check = QCheckBox(translate("Tight Bounding Box"))
        self.image_tight_bbox_check.setProperty('translate_key', 'Tight Bounding Box')
        self.image_tight_bbox_check.setChecked(bool(export_options.get('bbox_tight', True)))
        self.image_transparent_check = QCheckBox(translate("Transparent Background"))
        self.image_transparent_check.setProperty('translate_key', 'Transparent Background')
        self.image_transparent_check.setChecked(bool(export_options.get('transparent', False)))
        bbox_row.addWidget(self.image_tight_bbox_check)
        bbox_row.addWidget(self.image_transparent_check)
        image_layout.addLayout(bbox_row)

        pad_row = QHBoxLayout()
        pad_label = QLabel(translate("Padding (inch)"))
        pad_label.setProperty('translate_key', 'Padding (inch)')
        pad_row.addWidget(pad_label)
        self.image_pad_inches_spin = QDoubleSpinBox()
        self.image_pad_inches_spin.setRange(0.0, 1.0)
        self.image_pad_inches_spin.setSingleStep(0.01)
        self.image_pad_inches_spin.setDecimals(2)
        self.image_pad_inches_spin.setValue(float(export_options.get('pad_inches', 0.02)))
        pad_row.addWidget(self.image_pad_inches_spin)
        image_layout.addLayout(pad_row)

        if self.image_tight_bbox_check is not None and self.image_pad_inches_spin is not None:
            self.image_tight_bbox_check.toggled.connect(self.image_pad_inches_spin.setEnabled)
            self.image_pad_inches_spin.setEnabled(self.image_tight_bbox_check.isChecked())

        button_row = QHBoxLayout()
        self.export_image_button = QPushButton(translate("Export Image"))
        self.export_image_button.setProperty('translate_key', 'Export Image')
        self.export_image_button.setFixedWidth(160)
        self.export_image_button.clicked.connect(self._on_export_image_clicked)
        button_row.addWidget(self.export_image_button, 0, Qt.AlignHCenter)

        self.preview_image_button = QPushButton(translate("Preview Export"))
        self.preview_image_button.setProperty('translate_key', 'Preview Export')
        self.preview_image_button.setFixedWidth(160)
        self.preview_image_button.clicked.connect(self._on_preview_image_clicked)
        button_row.addWidget(self.preview_image_button, 0, Qt.AlignHCenter)
        image_layout.addLayout(button_row)

        image_group.setLayout(image_layout)

        image_page = QWidget()
        image_page_layout = QVBoxLayout(image_page)
        image_page_layout.setContentsMargins(6, 6, 6, 6)
        image_page_layout.setSpacing(8)
        image_page_layout.addWidget(image_group)
        image_page_layout.addStretch()
        section_toolbox.addItem(image_page, translate("Image Export"))

        layout.addWidget(section_toolbox)

        self._on_image_preset_changed()
        point_size = export_options.get('point_size')
        if point_size is not None and self.image_point_size_spin is not None:
            self.image_point_size_spin.setValue(int(point_size))
        legend_size = export_options.get('legend_size')
        if legend_size is not None and self.image_legend_size_spin is not None:
            self.image_legend_size_spin.setValue(int(legend_size))
        if self.image_dpi_spin is not None:
            self.image_dpi_spin.setValue(int(export_options.get('dpi', self.image_dpi_spin.value())))

        layout.addStretch()
        return widget
