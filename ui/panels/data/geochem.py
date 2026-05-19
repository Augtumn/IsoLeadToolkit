"""Data panel geochemistry behavior mixin."""
from __future__ import annotations

import logging

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMessageBox

from core import app_state, state_gateway, translate

logger = logging.getLogger(__name__)


class DataPanelGeochemMixin:
    """Geochemistry-related handlers for data panel."""

    def _on_model_curves_change(self, state):
        """Handle model curves toggle."""
        state_gateway.set_show_model_curves(state == Qt.Checked)
        self._sync_geochem_toggle_widgets(
            app_state.show_model_curves,
            getattr(self, "modeling_show_model_check", None),
            getattr(self, "show_model_check", None),
        )
        self._on_change()

    def _on_plumbotectonics_curves_change(self, state):
        """Handle plumbotectonics curves toggle."""
        state_gateway.set_show_plumbotectonics_curves(state == Qt.Checked)
        self._sync_geochem_toggle_widgets(
            app_state.show_plumbotectonics_curves,
            getattr(self, "modeling_show_plumbotectonics_check", None),
        )
        self._on_change()

    def _on_paleoisochron_change(self, state):
        """Handle paleoisochron toggle."""
        state_gateway.set_show_paleoisochrons(state == Qt.Checked)
        self._sync_geochem_toggle_widgets(
            app_state.show_paleoisochrons,
            getattr(self, "modeling_show_paleoisochron_check", None),
            getattr(self, "show_paleoisochron_check", None),
        )
        self._on_change()

    def _on_model_age_change(self, state):
        """Handle model age lines toggle."""
        state_gateway.set_show_model_age_lines(state == Qt.Checked)
        self._sync_geochem_toggle_widgets(
            app_state.show_model_age_lines,
            getattr(self, "modeling_show_model_age_check", None),
            getattr(self, "show_model_age_check", None),
        )
        self._on_change()

    def _on_growth_curves_change(self, state):
        """Handle growth curves toggle."""
        state_gateway.set_show_growth_curves(state == Qt.Checked)
        self._sync_geochem_toggle_widgets(
            app_state.show_growth_curves,
            getattr(self, "modeling_show_growth_curve_check", None),
        )
        self._on_change()

    def _on_mu_kappa_real_age_change(self, state):
        """Handle Mu/Kappa real age toggle."""
        state_gateway.set_use_real_age_for_mu_kappa(state == Qt.Checked)
        self._sync_geochem_toggle_widgets(
            app_state.use_real_age_for_mu_kappa,
            getattr(self, "modeling_use_real_age_check", None),
        )
        self._refresh_mu_kappa_age_label()
        if app_state.render_mode in ("PB_MU_AGE", "PB_KAPPA_AGE"):
            self._on_change()

    def _on_select_mu_kappa_age_column(self):
        """Select Mu/Kappa age column."""
        if app_state.df_global is None:
            QMessageBox.warning(self, translate("Warning"), translate("Please load data first."))
            return

        import pandas as pd

        df = app_state.df_global
        try:
            numeric_cols = df.select_dtypes(include="number").columns.tolist()
        except Exception:
            numeric_cols = []
            for col in df.columns:
                try:
                    pd.to_numeric(df[col], errors="raise")
                    numeric_cols.append(col)
                except Exception:
                    continue

        if not numeric_cols:
            QMessageBox.warning(self, translate("Warning"), translate("No numeric columns available."))
            return

        none_label = translate("None")
        items = [none_label] + numeric_cols

        current = getattr(app_state, "mu_kappa_age_col", None)
        if current in items:
            current_index = items.index(current)
        else:
            current_index = 0

        from PyQt5.QtWidgets import QInputDialog

        selection, ok = QInputDialog.getItem(
            self,
            translate("Select Age Column"),
            translate("Select Age Column"),
            items,
            current_index,
            False,
        )
        if not ok:
            return

        if selection == none_label:
            state_gateway.set_mu_kappa_age_col(None)
        else:
            state_gateway.set_mu_kappa_age_col(selection)

        state_gateway.set_use_real_age_for_mu_kappa(False)
        self._sync_geochem_toggle_widgets(
            app_state.use_real_age_for_mu_kappa,
            getattr(self, "modeling_use_real_age_check", None),
        )
        self._refresh_mu_kappa_age_label()
        self._refresh_mu_kappa_age_controls()
        if app_state.render_mode in ("PB_MU_AGE", "PB_KAPPA_AGE"):
            self._on_change()

    def _refresh_mu_kappa_age_label(self):
        """Refresh Mu/Kappa age label."""
        if self.mu_kappa_age_label is None:
            return
        label = getattr(app_state, "mu_kappa_age_col", None) or translate("Not Selected")
        self.mu_kappa_age_label.setText(label)

    def _refresh_plumbotectonics_models(self):
        """Refresh plumbotectonics model combo options."""
        combo = getattr(self, "plumbotectonics_model_combo", None)
        if combo is None:
            return
        try:
            from visualization.plotting.geo import get_plumbotectonics_variants

            variants = get_plumbotectonics_variants()
        except Exception:
            variants = []

        combo.blockSignals(True)
        combo.clear()
        self.plumbotectonics_model_keys = []
        if variants:
            for key, label in variants:
                combo.addItem(translate(label), key)
                self.plumbotectonics_model_keys.append(key)
            current_key = str(getattr(app_state, "plumbotectonics_variant", "0"))
            if current_key in self.plumbotectonics_model_keys:
                combo.setCurrentIndex(self.plumbotectonics_model_keys.index(current_key))
            else:
                combo.setCurrentIndex(0)
                state_gateway.set_plumbotectonics_variant(self.plumbotectonics_model_keys[0])
            combo.setEnabled(True)
        else:
            combo.addItem(translate("No plumbotectonics data"))
            combo.setEnabled(False)
        combo.blockSignals(False)

    def _on_plumbotectonics_model_change(self, index):
        """Handle plumbotectonics model changes."""
        if not self.plumbotectonics_model_keys:
            return
        if index < 0 or index >= len(self.plumbotectonics_model_keys):
            return
        state_gateway.set_plumbotectonics_variant(self.plumbotectonics_model_keys[index])
        if app_state.render_mode in ("PLUMBOTECTONICS_76", "PLUMBOTECTONICS_86"):
            self._on_change()

    def _refresh_mu_kappa_age_controls(self):
        """Refresh Mu/Kappa age-related controls."""
        mode = self._normalize_render_mode(app_state.render_mode)
        enabled = mode in ("PB_MU_AGE", "PB_KAPPA_AGE")
        has_col = bool(getattr(app_state, "mu_kappa_age_col", None))

        if self.mu_kappa_age_title_label is not None:
            self.mu_kappa_age_title_label.setVisible(enabled)
            self.mu_kappa_age_title_label.setEnabled(enabled)
        if self.mu_kappa_age_label is not None:
            self.mu_kappa_age_label.setVisible(enabled)
            self.mu_kappa_age_label.setEnabled(enabled)
        if self.mu_kappa_age_button is not None:
            self.mu_kappa_age_button.setVisible(enabled)
            self.mu_kappa_age_button.setEnabled(enabled)

        if self.modeling_use_real_age_check is not None:
            if not has_col:
                state_gateway.set_use_real_age_for_mu_kappa(False)
            self.modeling_use_real_age_check.blockSignals(True)
            self.modeling_use_real_age_check.setVisible(enabled)
            self.modeling_use_real_age_check.setEnabled(enabled and has_col)
            self.modeling_use_real_age_check.setChecked(
                bool(getattr(app_state, "use_real_age_for_mu_kappa", False)) and has_col
            )
            self.modeling_use_real_age_check.blockSignals(False)

    def _on_isochron_change(self, state):
        """Handle isochron toggle."""
        state_gateway.set_show_isochrons(state == Qt.Checked)
        self._sync_geochem_toggle_widgets(
            app_state.show_isochrons,
            getattr(self, "modeling_show_isochron_check", None),
            getattr(self, "show_isochron_check", None),
        )
        self._on_change()

    def _on_v1v2_model_change(self, index):
        """Handle V1V2 model selection changes."""
        combo = getattr(self, "v1v2_model_combo", None)
        if combo is None:
            return
        model_name = combo.currentData()
        if model_name not in ("V1V2 (Geokit)", "V1V2 (Zhu 1993)"):
            return
        try:
            from data.geochemistry import engine

            engine.load_preset(model_name)
            if app_state.render_mode == "V1V2":
                self._on_change()
        except Exception:
            pass

    def _on_v1v2_param_change(self):
        """Update V1V2 time parameters."""
        try:
            from data.geochemistry import engine
        except Exception:
            return

        try:
            params = {}
            if self.v1v2_t1_spin is not None:
                params["T1"] = self.v1v2_t1_spin.value() * 1e6
            if self.v1v2_t2_spin is not None:
                params["T2"] = self.v1v2_t2_spin.value() * 1e6

            if params:
                engine.update_parameters(params)
                if app_state.render_mode == "V1V2":
                    self._on_change()
        except Exception:
            pass

    def _on_calculate_isochron(self):
        """Calculate or hide selected isochron."""
        try:
            from visualization.events import calculate_selected_isochron, on_slider_change
        except Exception as exc:
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Failed to start isochron selection: {error}").format(error=str(exc)),
            )
            return

        if getattr(app_state, "show_isochrons", False) or getattr(app_state, "selected_isochron_data", None):
            state_gateway.set_show_isochrons(False)
            state_gateway.set_isochron_results({})
            state_gateway.set_selected_isochron_data(None)
            self._update_isochron_btn_text()
            try:
                on_slider_change()
            except Exception:
                pass
            return

        if app_state.render_mode == "3D":
            QMessageBox.information(
                self,
                translate("Isochron Age Calculation"),
                translate("Isochron calculation is only available in 2D views"),
            )
            return

        if app_state.render_mode != "PB_EVOL_76":
            QMessageBox.information(
                self,
                translate("Isochron Age Calculation"),
                translate("Isochron calculation is only available for Pb evolution plot (PB_EVOL_76)"),
            )
            return

        if not self._ensure_isochron_error_settings():
            return

        selected = set(getattr(app_state, "selected_indices", set()) or set())

        if selected:
            calculate_selected_isochron()
        else:
            state_gateway.set_show_isochrons(True)

        try:
            on_slider_change()
        except Exception as refresh_err:
            logger.warning("Failed to refresh plot: %s", refresh_err)

        self._update_isochron_btn_text()
        self._on_isochron_settings()

    def _update_isochron_btn_text(self):
        """Update isochron button text by visibility state."""
        btn = getattr(self, "calc_isochron_btn", None)
        if btn is None:
            return
        if getattr(app_state, "show_isochrons", False) or getattr(app_state, "selected_isochron_data", None):
            btn.setText(translate("Hide Isochron"))
        else:
            btn.setText(translate("Calculate Isochron Age"))

    def _ensure_isochron_error_settings(self):
        """Ensure isochron error settings are usable before calculation."""
        mode = getattr(app_state, "isochron_error_mode", "fixed")
        if mode != "columns":
            return True

        df = getattr(app_state, "df_global", None)
        sx_col = getattr(app_state, "isochron_sx_col", "")
        sy_col = getattr(app_state, "isochron_sy_col", "")

        if df is None or not sx_col or not sy_col:
            return self._on_isochron_settings()

        if sx_col not in df.columns or sy_col not in df.columns:
            return self._on_isochron_settings()

        return True

    def _on_isochron_settings(self):
        """Open isochron regression settings dialog."""
        try:
            from ui.dialogs.isochron_dialog import get_isochron_error_settings
        except Exception as exc:
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Failed to open isochron settings: {error}").format(error=str(exc)),
            )
            return False

        settings = get_isochron_error_settings(self)
        if not settings:
            return False

        mode = settings.get("mode")
        if mode == "columns":
            state_gateway.set_isochron_error_columns(
                settings.get("sx_col", ""),
                settings.get("sy_col", ""),
                settings.get("rxy_col", ""),
            )
        else:
            state_gateway.set_isochron_error_fixed(
                float(settings.get("sx_value", 0.001)),
                float(settings.get("sy_value", 0.001)),
                float(settings.get("rxy_value", 0.0)),
            )

        self._on_change()
        return True

    def _on_paleo_step_change(self, value):
        """Handle paleoisochron step changes."""
        step_val = max(10, int(value))
        state_gateway.set_paleoisochron_step(step_val)
        min_age = int(getattr(app_state, "paleoisochron_min_age", 0))
        max_age = int(getattr(app_state, "paleoisochron_max_age", 3000))
        if max_age < min_age:
            max_age, min_age = min_age, max_age
        ages = list(range(max_age, min_age - 1, -step_val))
        if not ages or ages[-1] != min_age:
            ages.append(min_age)
        state_gateway.set_paleoisochron_ages(ages)
        self._on_change()
