"""Widget construction for the export preview dialog."""
from __future__ import annotations

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QScrollArea,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from types import SimpleNamespace
from application.use_cases.export_image import available_image_presets
from core import app_state, state_gateway, translate


class ExportPreviewControlsMixin:
    """Widget construction for the export preview dialog."""

    def _build_preview_controls(self, dialog, main_layout, image_ext, label_size_for_export, legend_size_for_export, params, point_size_for_export, preset_key, tick_size_for_export, title_size_for_export):
        """Build the preview dialog controls (rows 1-4) and return them."""
        control_widget = QWidget()
        control_layout = QVBoxLayout(control_widget)
        control_layout.setContentsMargins(4, 4, 4, 4)
        control_layout.setSpacing(4)

        # Row 1: Preset + Format
        row1 = QHBoxLayout()
        row1.addWidget(QLabel(translate("Journal Preset")))
        preset_combo = QComboBox()
        for _preset_key, _preset_label in available_image_presets():
            preset_combo.addItem(translate(_preset_label), _preset_key)
        idx = preset_combo.findData(str(preset_key))
        if idx >= 0:
            preset_combo.setCurrentIndex(idx)
        row1.addWidget(preset_combo)

        row1.addSpacing(12)
        row1.addWidget(QLabel(translate("Image Format")))
        format_combo = QComboBox()
        format_combo.addItem("PNG", "png")
        format_combo.addItem("TIFF", "tiff")
        format_combo.addItem("PDF", "pdf")
        format_combo.addItem("SVG", "svg")
        format_combo.addItem("EPS", "eps")
        fidx = format_combo.findData(str(image_ext))
        if fidx >= 0:
            format_combo.setCurrentIndex(fidx)
        row1.addWidget(format_combo)
        row1.addStretch()
        control_layout.addLayout(row1)

        # Helper: slider + spin pair
        def _add_slider_spin(parent_layout, label_text, translate_key, min_val, max_val, step, init_val):
            row = QHBoxLayout()
            label = QLabel(label_text)
            label.setProperty('translate_key', translate_key)
            row.addWidget(label)
            slider = QSlider(Qt.Horizontal)
            slider.setRange(min_val, max_val)
            slider.setSingleStep(step)
            slider.setValue(int(init_val))
            spin = QSpinBox()
            spin.setRange(min_val, max_val)
            spin.setSingleStep(step)
            spin.setValue(int(init_val))
            row.addWidget(slider, 1)
            row.addWidget(spin)
            parent_layout.addLayout(row)
            return slider, spin

        # Row 2: DPI + Data Point Size + Legend Marker Scale
        row2 = QHBoxLayout()
        dpi_slider, dpi_spin = _add_slider_spin(row2, translate("DPI"), "DPI", 72, 1200, 25, params['dpi'])
        ps_slider, ps_spin = _add_slider_spin(row2, translate("Data Point Size"), "Data Point Size", 1, 80, 1, point_size_for_export)
        lms_slider, lms_spin = _add_slider_spin(row2, translate("Legend Marker Size"), "Legend Marker Size", 1, 80, 1, point_size_for_export)
        control_layout.addLayout(row2)

        # Row 3: Label / Title / Tick / Legend Font sizes
        row3 = QHBoxLayout()
        lab_slider, lab_spin = _add_slider_spin(row3, translate("Label Font Size"), "Label Font Size", 4, 24, 1, label_size_for_export)
        tit_slider, tit_spin = _add_slider_spin(row3, translate("Title Font Size"), "Title Font Size", 4, 24, 1, title_size_for_export)
        tck_slider, tck_spin = _add_slider_spin(row3, translate("Tick Font Size"), "Tick Font Size", 4, 24, 1, tick_size_for_export)
        ls_slider, ls_spin = _add_slider_spin(row3, translate("Legend Size"), "Legend Size", 1, 20, 1, legend_size_for_export)
        control_layout.addLayout(row3)

        # Row 4: Tight BBox + Padding + Transparent
        row4 = QHBoxLayout()
        tight_bbox_check = QCheckBox(translate("Tight BBox"))
        tight_bbox_check.setChecked(bool(params['tight_bbox']))
        row4.addWidget(tight_bbox_check)

        row4.addWidget(QLabel(translate("Padding")))
        pad_spin = QDoubleSpinBox()
        pad_spin.setRange(0.0, 1.0)
        pad_spin.setSingleStep(0.01)
        pad_spin.setDecimals(2)
        pad_spin.setValue(float(params['pad_inches']))
        pad_spin.setEnabled(tight_bbox_check.isChecked())
        tight_bbox_check.toggled.connect(pad_spin.setEnabled)
        row4.addWidget(pad_spin)

        transparent_check = QCheckBox(translate("Transparent"))
        transparent_check.setChecked(bool(params['transparent']))
        row4.addWidget(transparent_check)
        row4.addStretch()
        control_layout.addLayout(row4)

        main_layout.addWidget(control_widget)
        return SimpleNamespace(
            dpi_slider=dpi_slider,
            dpi_spin=dpi_spin,
            format_combo=format_combo,
            idx=idx,
            lab_slider=lab_slider,
            lab_spin=lab_spin,
            lms_slider=lms_slider,
            lms_spin=lms_spin,
            ls_slider=ls_slider,
            ls_spin=ls_spin,
            pad_spin=pad_spin,
            preset_combo=preset_combo,
            ps_slider=ps_slider,
            ps_spin=ps_spin,
            tck_slider=tck_slider,
            tck_spin=tck_spin,
            tight_bbox_check=tight_bbox_check,
            tit_slider=tit_slider,
            tit_spin=tit_spin,
            transparent_check=transparent_check,
        )
