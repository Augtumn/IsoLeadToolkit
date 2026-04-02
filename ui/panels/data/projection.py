"""Data panel projection behavior mixin."""

import logging

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMessageBox

from core import app_state, state_gateway, translate

logger = logging.getLogger(__name__)


class DataPanelProjectionMixin:
    """Projection and algorithm handlers for data panel."""

    def _on_render_mode_change(self, mode):
        """Handle render mode changes."""
        mode = self._normalize_render_mode(self._combo_value(self.render_combo, mode))
        state_gateway.set_render_mode(mode)

        if mode in ["UMAP", "tSNE", "PCA", "RobustPCA"]:
            self._set_combo_value(self.algo_combo, mode)

        if mode == "2D" and not app_state.selected_2d_confirmed:
            self._show_2d_column_dialog()
        elif mode == "3D" and not app_state.selected_3d_confirmed:
            self._show_3d_column_dialog()
        elif mode == "Ternary" and not app_state.selected_ternary_confirmed:
            self._show_ternary_column_dialog()

        self._sync_geochem_model_for_mode(mode)
        self._update_algorithm_visibility()
        self._on_change()

    def _on_algorithm_change(self, algorithm):
        """Handle algorithm changes."""
        algorithm = self._normalize_algorithm(self._combo_value(self.algo_combo, algorithm))
        state_gateway.set_render_mode(algorithm)
        self._set_combo_value(self.render_combo, algorithm)
        self._update_algorithm_visibility()
        self._on_change()

    def _update_algorithm_visibility(self):
        """Update visible parameter groups for current render mode."""
        mode = self._normalize_render_mode(app_state.render_mode)

        self.algo_group.setVisible(False)
        self.umap_group.setVisible(mode == "UMAP")
        self.tsne_group.setVisible(mode == "tSNE")
        self.pca_group.setVisible(mode == "PCA")
        self.robust_pca_group.setVisible(mode == "RobustPCA")
        self.ternary_group.setVisible(mode == "Ternary")
        self._refresh_ternary_limit_controls_enabled()

        if self.v1v2_group is not None:
            self.v1v2_group.setVisible(mode == "V1V2")

        self.twod_group.setVisible(mode == "2D")
        if mode == "2D":
            self._refresh_2d_axis_combos()

        if self.geochem_plot_group is not None:
            self.geochem_plot_group.setVisible(
                mode in (
                    "PB_EVOL_76",
                    "PB_EVOL_86",
                    "PB_MU_AGE",
                    "PB_KAPPA_AGE",
                    "PLUMBOTECTONICS_76",
                    "PLUMBOTECTONICS_86",
                )
            )

        is_pb_evol = mode in ("PB_EVOL_76", "PB_EVOL_86")
        is_pb_evol_76 = mode == "PB_EVOL_76"
        is_plumbotectonics = mode in ("PLUMBOTECTONICS_76", "PLUMBOTECTONICS_86")

        if self.modeling_show_model_check is not None:
            self.modeling_show_model_check.setVisible(is_pb_evol)
            swatch = getattr(self.modeling_show_model_check, "_style_swatch", None)
            if swatch is not None:
                swatch.setVisible(is_pb_evol)
        if self.modeling_show_plumbotectonics_check is not None:
            self.modeling_show_plumbotectonics_check.setVisible(is_plumbotectonics)
            swatch = getattr(self.modeling_show_plumbotectonics_check, "_style_swatch", None)
            if swatch is not None:
                swatch.setVisible(is_plumbotectonics)
        if self.modeling_show_model_age_check is not None:
            self.modeling_show_model_age_check.setVisible(is_pb_evol)
            swatch = getattr(self.modeling_show_model_age_check, "_style_swatch", None)
            if swatch is not None:
                swatch.setVisible(is_pb_evol)
        if self.modeling_show_growth_curve_check is not None:
            self.modeling_show_growth_curve_check.setVisible(False)
            swatch = getattr(self.modeling_show_growth_curve_check, "_style_swatch", None)
            if swatch is not None:
                swatch.setVisible(False)

        if self.calc_isochron_btn is not None:
            self.calc_isochron_btn.setVisible(is_pb_evol_76)
        if self.isochron_settings_btn is not None:
            self.isochron_settings_btn.setVisible(is_pb_evol_76)
        if self.isochron_swatch is not None:
            self.isochron_swatch.setVisible(is_pb_evol_76)

        if self.plumbotectonics_model_label is not None:
            self.plumbotectonics_model_label.setVisible(is_plumbotectonics)
            self.plumbotectonics_model_label.setEnabled(is_plumbotectonics)
        if self.plumbotectonics_model_combo is not None:
            self.plumbotectonics_model_combo.setVisible(is_plumbotectonics)
            self.plumbotectonics_model_combo.setEnabled(is_plumbotectonics)
            if is_plumbotectonics:
                self._refresh_plumbotectonics_models()

        self._refresh_mu_kappa_age_controls()

    def _on_umap_slider_changed(self, param, value, label, slider):
        """Handle UMAP slider move without scheduling redraw."""
        app_state.umap_params[param] = value
        if label:
            if param == "min_dist":
                label.setText(translate("{param}: {value:.2f}").format(param=param, value=value))
            else:
                label.setText(translate("{param}: {value}").format(param=param, value=value))

    def _on_umap_param_change(self, param, value, label):
        """Handle UMAP parameter changes for non-slider controls."""
        app_state.umap_params[param] = value
        if label:
            if param == "min_dist":
                label.setText(translate("{param}: {value:.2f}").format(param=param, value=value))
            else:
                label.setText(translate("{param}: {value}").format(param=param, value=value))
        self._schedule_slider_callback(f"umap_{param}")

    def _on_tsne_slider_changed(self, param, value, label):
        """Handle t-SNE slider move without scheduling redraw."""
        app_state.tsne_params[param] = value
        if label:
            label.setText(translate("{param}: {value}").format(param=param, value=int(value)))

    def _on_tsne_param_change(self, param, value, label):
        """Handle t-SNE parameter changes for non-slider controls."""
        app_state.tsne_params[param] = value
        if label:
            label.setText(translate("{param}: {value}").format(param=param, value=value))
        self._schedule_slider_callback(f"tsne_{param}")

    def _on_pca_param_change(self, param, value, label=None):
        """Handle PCA parameter changes."""
        app_state.pca_params[param] = value
        if label and param == "random_state":
            label.setText(translate("random_state: {value}").format(value=value))
        self._schedule_slider_callback(f"pca_{param}")

    def _on_robust_pca_param_change(self, param, value, label=None):
        """Handle RobustPCA parameter changes."""
        app_state.robust_pca_params[param] = value
        if label and param == "support_fraction":
            label.setText(translate("support_fraction: {value:.2f}").format(value=value))
        self._schedule_slider_callback(f"robust_pca_{param}")

    def _on_standardize_change(self, state):
        """Handle standardization checkbox changes."""
        state_gateway.set_standardize_data(state == Qt.Checked)
        self._on_change()

    def _on_pca_dim_change(self):
        """Handle PCA projection dimension changes."""
        try:
            x_idx = self.pca_x_spin.value() - 1
            y_idx = self.pca_y_spin.value() - 1

            if hasattr(self, "rpca_x_spin"):
                self.rpca_x_spin.blockSignals(True)
                self.rpca_x_spin.setValue(x_idx + 1)
                self.rpca_x_spin.blockSignals(False)

            if hasattr(self, "rpca_y_spin"):
                self.rpca_y_spin.blockSignals(True)
                self.rpca_y_spin.setValue(y_idx + 1)
                self.rpca_y_spin.blockSignals(False)

            state_gateway.set_pca_component_indices([x_idx, y_idx])
            logger.info("PCA dimensions changed to: PC%d vs PC%d", x_idx + 1, y_idx + 1)

            if app_state.render_mode in ["PCA", "RobustPCA"]:
                self._on_change()

        except Exception as exc:
            logger.error("Failed to change PCA dimensions: %s", exc)

    def _on_show_scree_plot(self):
        """Show scree plot dialog."""
        try:
            from visualization import show_scree_plot

            show_scree_plot(None)
        except Exception as exc:
            logger.error("Failed to show scree plot: %s", exc)
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Failed to show scree plot: {error}").format(error=str(exc)),
            )

    def _on_show_pca_loadings(self):
        """Show PCA loadings dialog."""
        try:
            from visualization import show_pca_loadings

            show_pca_loadings(None)
        except Exception as exc:
            logger.error("Failed to show PCA loadings: %s", exc)
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Failed to show PCA loadings: {error}").format(error=str(exc)),
            )

    def _on_ternary_zoom_change(self, state):
        """Handle ternary auto-zoom toggle."""
        state_gateway.set_ternary_auto_zoom(state == Qt.Checked)
        self._refresh_ternary_limit_controls_enabled()
        self._on_change()

    def _refresh_ternary_limit_controls_enabled(self):
        """Enable/disable ternary limit controls based on auto-zoom/manual toggles."""
        auto_zoom_enabled = bool(getattr(app_state, "ternary_auto_zoom", True))
        base_widgets = [
            getattr(self, "ternary_limit_mode_combo", None),
            getattr(self, "ternary_boundary_percent_spin", None),
            getattr(self, "ternary_auto_optimize_btn", None),
            getattr(self, "ternary_manual_limits_check", None),
        ]
        for widget in base_widgets:
            if widget is not None:
                widget.setEnabled(auto_zoom_enabled)

        manual_enabled = auto_zoom_enabled and bool(getattr(app_state, "ternary_manual_limits_enabled", False))
        for spin in (getattr(self, "ternary_limit_spins", None) or {}).values():
            spin.setEnabled(manual_enabled)

    def _on_ternary_limit_mode_change(self, index):
        """Handle ternary limit mode changes."""
        mode = str(self._combo_value(self.ternary_limit_mode_combo, index)).strip().lower()
        if mode not in ("min", "max", "both"):
            mode = "min"

        state_gateway.set_ternary_limit_mode(mode)
        if mode in ("min", "max"):
            state_gateway.set_ternary_limit_anchor(mode)
        self._on_change()

    def _on_ternary_boundary_percent_change(self, value):
        """Handle boundary percent changes for ternary limit optimization."""
        try:
            percent = float(value)
        except (TypeError, ValueError):
            percent = 5.0
        percent = max(0.0, min(30.0, percent))
        state_gateway.set_ternary_boundary_percent(percent)
        self._on_change()

    def _on_ternary_manual_limits_change(self, state):
        """Toggle manual ternary min/max parameter mode."""
        enabled = state == Qt.Checked
        state_gateway.set_ternary_manual_limits_enabled(enabled)
        self._refresh_ternary_limit_controls_enabled()
        self._on_change()

    def _on_ternary_limit_param_change(self, key, value):
        """Update a single manual ternary limit parameter."""
        manual = dict(getattr(app_state, "ternary_manual_limits", {}) or {})
        try:
            val = float(value)
        except (TypeError, ValueError):
            return
        manual[key] = max(0.0, min(1.0, val))
        state_gateway.set_ternary_manual_limits(manual)

        if bool(getattr(app_state, "ternary_manual_limits_enabled", False)):
            self._on_change()

    def _on_ternary_auto_optimize(self):
        """Auto-optimize ternary boundary parameters from current data distribution."""
        try:
            from visualization.plotting.ternary import optimize_current_ternary_limits

            mode = str(getattr(app_state, "ternary_limit_mode", "min")).strip().lower()
            if mode not in ("min", "max", "both"):
                mode = "min"
            boundary_percent = float(getattr(app_state, "ternary_boundary_percent", 5.0))

            optimized = optimize_current_ternary_limits(mode=mode, boundary_percent=boundary_percent)
            if not optimized:
                logger.warning("Ternary auto-optimize skipped: no valid ternary data available.")
                return

            optimized_mode = str(optimized.get("mode", mode)).strip().lower()
            limits = optimized.get("limits")

            manual_limits: dict[str, float] = {}
            if isinstance(limits, (list, tuple)) and len(limits) == 6:
                manual_limits = {
                    "tmin": float(limits[0]),
                    "tmax": float(limits[1]),
                    "lmin": float(limits[2]),
                    "lmax": float(limits[3]),
                    "rmin": float(limits[4]),
                    "rmax": float(limits[5]),
                }

            state_gateway.set_ternary_limit_mode(optimized_mode)
            if optimized_mode in ("min", "max"):
                state_gateway.set_ternary_limit_anchor(optimized_mode)
            if manual_limits:
                state_gateway.set_ternary_manual_limits(manual_limits)

            if getattr(self, "ternary_limit_mode_combo", None) is not None:
                self.ternary_limit_mode_combo.blockSignals(True)
                self._set_combo_value(self.ternary_limit_mode_combo, optimized_mode)
                self.ternary_limit_mode_combo.blockSignals(False)

            for key, spin in (getattr(self, "ternary_limit_spins", None) or {}).items():
                if key not in manual_limits:
                    continue
                spin.blockSignals(True)
                spin.setValue(float(manual_limits[key]))
                spin.blockSignals(False)

            logger.info(
                "Ternary auto-optimized: mode=%s, boundary=%.1f%% (fixed), limits=%s",
                optimized_mode,
                boundary_percent,
                limits,
            )
            self._on_change()
        except Exception as err:
            logger.warning("Failed ternary auto-optimize: %s", err)

    def _on_ternary_stretch_mode_change(self, index):
        """Handle ternary stretch mode changes."""
        modes = ["power", "minmax", "hybrid"]
        if 0 <= index < len(modes):
            state_gateway.set_ternary_stretch_mode(modes[index])
            self._on_change()

    def _on_ternary_scale_change(self, value):
        """Handle ternary stretch mode slider changes."""
        idx = max(0, min(2, int(value)))
        mode = self._ternary_stretch_modes[idx]
        state_gateway.set_ternary_stretch_mode(mode)
        self._update_ternary_scale_label(mode)
        state_gateway.set_ternary_stretch(True)
        if hasattr(self, "ternary_stretch_check"):
            self.ternary_stretch_check.blockSignals(True)
            self.ternary_stretch_check.setChecked(True)
            self.ternary_stretch_check.blockSignals(False)
        self._on_change()

    def _on_ternary_stretch_change(self, state):
        """Handle ternary stretch toggle."""
        state_gateway.set_ternary_stretch(state == Qt.Checked)
        self._on_change()

    def _update_ternary_scale_label(self, mode):
        """Update stretch mode label text."""
        label_map = {
            "power": translate("Power"),
            "minmax": translate("Min-Max"),
            "hybrid": translate("Hybrid"),
        }
        if self.ternary_scale_label is not None:
            self.ternary_scale_label.setText(label_map.get(mode, mode))

    def _refresh_2d_axis_combos(self):
        """Refresh 2D axis selection combo boxes."""
        if not hasattr(self, "xaxis_combo") or not hasattr(self, "yaxis_combo"):
            return

        cols = [c for c in getattr(app_state, "data_cols", []) if c in app_state.df_global.columns]
        self.xaxis_combo.clear()
        self.yaxis_combo.clear()
        self.xaxis_combo.addItems(cols)
        self.yaxis_combo.addItems(cols)

        current = getattr(app_state, "selected_2d_cols", [])
        if (not current or len(current) != 2) and len(cols) >= 2:
            current = [cols[0], cols[1]]
            state_gateway.set_selected_2d_columns(current, confirmed=True)

        if len(current) == 2:
            if current[0] in cols:
                self.xaxis_combo.setCurrentText(current[0])
            if current[1] in cols:
                self.yaxis_combo.setCurrentText(current[1])

    def _on_2d_axis_change(self):
        """Handle 2D axis selection changes."""
        x_col = self.xaxis_combo.currentText()
        y_col = self.yaxis_combo.currentText()

        if x_col and y_col:
            state_gateway.set_selected_2d_columns([x_col, y_col], confirmed=True)
            logger.debug("2D Axes Changed: X=%s, Y=%s", x_col, y_col)
            self._on_change()

    def _show_2d_column_dialog(self):
        """Show 2D column selection dialog."""
        from ui.dialogs.two_d_dialog import get_2d_column_selection

        result = get_2d_column_selection()
        if result:
            state_gateway.set_selected_2d_columns(result, confirmed=True)
            logger.info("Selected 2D columns: %s", result)
            self._on_change()

    def _show_3d_column_dialog(self):
        """Show 3D column selection dialog."""
        from ui.dialogs.three_d_dialog import get_3d_column_selection

        result = get_3d_column_selection()
        if result:
            state_gateway.set_selected_3d_columns(result, confirmed=True)
            logger.info("Selected 3D columns: %s", result)
            self._on_change()

    def _show_ternary_column_dialog(self):
        """Show ternary column selection dialog."""
        from ui.dialogs.ternary_dialog import get_ternary_column_selection

        result = get_ternary_column_selection()
        if result:
            state_gateway.set_selected_ternary_columns(result["columns"], confirmed=True)
            state_gateway.set_attrs({"ternary_stretch": result["stretch"], "ternary_factors": result["factors"]})
            logger.info("Selected ternary columns: %s", result["columns"])
            logger.info("Ternary stretch: %s, factors: %s", result["stretch"], result["factors"])
            self._on_change()





