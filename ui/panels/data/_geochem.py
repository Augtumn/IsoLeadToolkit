"""Data panel geochemistry UI construction."""
from __future__ import annotations

import logging

from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from core import app_state, translate
from ui.icons import apply_color_swatch

logger = logging.getLogger(__name__)


class _DataPanelGeochemBuild:
    """Build geochemistry plot controls UI for data panel."""

    def _build_geochem_controls(self, layout):
        """Build geochemistry plot controls group.

        Creates model curve, paleoisochron, plumbotectonics, model age, growth curve,
        Mu/Kappa age, and isochron controls.

        Args:
            layout: The parent layout to add widgets into.
        """
        self.geochem_plot_group = QGroupBox(translate("Geochemistry Plot Controls"))
        self.geochem_plot_group.setProperty("translate_key", "Geochemistry Plot Controls")
        geochem_layout = QVBoxLayout()

        def _add_geochem_toggle(label_text, checked, handler, style_key=None):
            row = QHBoxLayout()
            chk = QCheckBox(translate(label_text))
            chk.setChecked(checked)
            chk.stateChanged.connect(handler)
            row.addWidget(chk)

            if style_key:
                style = getattr(app_state, "line_styles", {}).get(style_key, {}) or {}
                swatch_color = style.get("color") or "#e2e8f0"
                swatch = QLabel()
                swatch.setFixedSize(16, 16)
                apply_color_swatch(swatch, swatch_color)
                swatch.mousePressEvent = lambda event, k=style_key, s=swatch: self._open_line_style_dialog(k, s)
                row.addWidget(swatch)
                chk._style_swatch = swatch

            row.addStretch()
            geochem_layout.addLayout(row)
            return chk

        self.modeling_show_model_check = _add_geochem_toggle(
            "Show Model Curves",
            getattr(app_state, "show_model_curves", True),
            self._on_model_curves_change,
            style_key="model_curve",
        )

        self.modeling_show_paleoisochron_check = _add_geochem_toggle(
            "Show Paleoisochrons",
            getattr(app_state, "show_paleoisochrons", True),
            self._on_paleoisochron_change,
            style_key="paleoisochron",
        )

        self.modeling_show_plumbotectonics_check = _add_geochem_toggle(
            "Show Plumbotectonics Curves",
            getattr(app_state, "show_plumbotectonics_curves", True),
            self._on_plumbotectonics_curves_change,
            style_key="plumbotectonics_curve",
        )

        plumb_row = QHBoxLayout()
        self.plumbotectonics_model_label = QLabel(translate("Plumbotectonics Model"))
        self.plumbotectonics_model_label.setProperty("translate_key", "Plumbotectonics Model")
        plumb_row.addWidget(self.plumbotectonics_model_label)

        self.plumbotectonics_model_combo = QComboBox()
        self.plumbotectonics_model_combo.currentIndexChanged.connect(self._on_plumbotectonics_model_change)
        plumb_row.addWidget(self.plumbotectonics_model_combo)
        plumb_row.addStretch()
        geochem_layout.addLayout(plumb_row)

        self._refresh_plumbotectonics_models()

        paleo_step_layout = QHBoxLayout()
        paleo_step_label = QLabel(translate("Paleoisochron Step (Ma):"))
        paleo_step_label.setProperty("translate_key", "Paleoisochron Step (Ma):")
        paleo_step_layout.addWidget(paleo_step_label)
        self.paleo_step_spin = QSpinBox()
        self.paleo_step_spin.setRange(50, 5000)
        self.paleo_step_spin.setSingleStep(50)
        self.paleo_step_spin.setValue(getattr(app_state, "paleoisochron_step", 1000))
        self._connect_spinbox_deferred(self.paleo_step_spin, self._on_paleo_step_change)
        paleo_step_layout.addWidget(self.paleo_step_spin)
        paleo_step_layout.addStretch()
        geochem_layout.addLayout(paleo_step_layout)

        self.modeling_show_model_age_check = _add_geochem_toggle(
            "Show Model Age Lines",
            getattr(app_state, "show_model_age_lines", True),
            self._on_model_age_change,
            style_key="model_age_line",
        )

        self.modeling_show_growth_curve_check = _add_geochem_toggle(
            "Show Growth Curves",
            getattr(app_state, "show_growth_curves", True),
            self._on_growth_curves_change,
            style_key="growth_curve",
        )

        self.modeling_use_real_age_check = _add_geochem_toggle(
            "Use Real Age for Mu/Kappa",
            getattr(app_state, "use_real_age_for_mu_kappa", False),
            self._on_mu_kappa_real_age_change,
        )

        age_row = QHBoxLayout()
        self.mu_kappa_age_title_label = QLabel(translate("Age Column"))
        self.mu_kappa_age_title_label.setProperty("translate_key", "Age Column")
        age_row.addWidget(self.mu_kappa_age_title_label)

        self.mu_kappa_age_label = QLabel()
        age_row.addWidget(self.mu_kappa_age_label)
        age_row.addStretch()

        self.mu_kappa_age_button = QPushButton(translate("Select Age Column"))
        self.mu_kappa_age_button.setProperty("translate_key", "Select Age Column")
        self.mu_kappa_age_button.clicked.connect(self._on_select_mu_kappa_age_column)
        age_row.addWidget(self.mu_kappa_age_button)
        geochem_layout.addLayout(age_row)

        self._refresh_mu_kappa_age_label()
        self._refresh_mu_kappa_age_controls()

        isochron_row = QHBoxLayout()
        self.calc_isochron_btn = QPushButton(translate("Calculate Isochron Age"))
        self.calc_isochron_btn.setProperty("translate_key", "Calculate Isochron Age")
        self.calc_isochron_btn.clicked.connect(self._on_calculate_isochron)
        if getattr(app_state, "show_isochrons", False):
            self.calc_isochron_btn.setText(translate("Hide Isochron"))
        isochron_row.addWidget(self.calc_isochron_btn)

        self.isochron_settings_btn = QPushButton(translate("Isochron Settings"))
        self.isochron_settings_btn.setProperty("translate_key", "Isochron Settings")
        self.isochron_settings_btn.clicked.connect(self._on_isochron_settings)
        isochron_row.addWidget(self.isochron_settings_btn)

        iso_style = getattr(app_state, "line_styles", {}).get("isochron", {}) or {}
        iso_color = iso_style.get("color") or "#e2e8f0"
        self.isochron_swatch = QLabel()
        self.isochron_swatch.setFixedSize(16, 16)
        apply_color_swatch(self.isochron_swatch, iso_color)
        self.isochron_swatch.mousePressEvent = lambda event, s=self.isochron_swatch: self._open_line_style_dialog(
            "isochron", s
        )
        isochron_row.addWidget(self.isochron_swatch)
        isochron_row.addStretch()
        geochem_layout.addLayout(isochron_row)

        self.geochem_plot_group.setLayout(geochem_layout)
        layout.addWidget(self.geochem_plot_group)
