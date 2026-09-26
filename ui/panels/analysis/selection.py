"""Analysis selection actions mixin."""
from __future__ import annotations

import logging

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMessageBox

from core import app_state, state_gateway, translate

logger = logging.getLogger(__name__)


class AnalysisPanelSelectionMixin:
    """Selection and tooltip actions for analysis panel."""
    _sync_selection_buttons = None
    ellipse_selection_button = None
    export_append_button = None
    export_csv_button = None
    export_excel_button = None
    export_selected_button = None
    lasso_selection_button = None
    selection_button = None
    selection_status_label = None
    status_export_button = None

    # Declared by the class that uses them, so no probe is needed for widgets
    # that build() creates later (UI review item B).

    def _sync_selection_buttons(self):
        """Sync selection button states with active tool."""
        tool = app_state.selection_tool

        selection_button = self.selection_button
        if selection_button is not None:
            selection_button.blockSignals(True)
            selection_button.setChecked(tool == 'export')
            selection_button.setText(
                translate("Disable Selection") if tool == 'export' else translate("Enable Selection")
            )
            selection_button.blockSignals(False)

        ellipse_button = self.ellipse_selection_button
        if ellipse_button is not None:
            ellipse_active = app_state.draw_selection_ellipse
            ellipse_button.blockSignals(True)
            ellipse_button.setChecked(ellipse_active)
            ellipse_button.setText(
                translate("Disable Ellipse") if ellipse_active else translate("Draw Ellipse")
            )
            ellipse_button.blockSignals(False)

        lasso_button = self.lasso_selection_button
        if lasso_button is not None:
            lasso_button.blockSignals(True)
            lasso_button.setChecked(tool == 'lasso')
            lasso_button.setText(
                translate("Disable Custom Shape") if tool == 'lasso' else translate("Custom Shape")
            )
            lasso_button.blockSignals(False)

    def update_selection_controls(self):
        """Refresh selection UI state from app_state."""
        count = len(app_state.selected_indices)
        if self.selection_status_label is not None:
            self.selection_status_label.setText(
                translate("Selected Samples: {count}").format(count=count)
            )

        enable_exports = count > 0
        for button in (
            self.export_csv_button,
            self.export_excel_button,
            self.export_append_button,
            self.export_selected_button,
        ):
            if button is not None:
                button.setEnabled(enable_exports)
        status_export_button = self.status_export_button
        if status_export_button is not None:
            status_export_button.setEnabled(enable_exports)

        if self._sync_selection_buttons is not None:
            self._sync_selection_buttons()
        self._update_status_panel()

    def _clear_selection_only(self):
        """Clear selection and refresh overlays."""
        if app_state.selected_indices:
            state_gateway.clear_selected_indices()
        try:
            from visualization.events import refresh_selection_overlay

            refresh_selection_overlay()
        except Exception:
            pass
        self.update_selection_controls()

    def _require_selection_available(self) -> bool:
        """Warn when selection tools cannot run; return True when OK."""
        if app_state.df_global is None:
            QMessageBox.warning(
                self, translate("Warning"), translate("Please load data first.")
            )
            return False
        if app_state.render_mode == "3D":
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("Selection mode is only available in 2D views"),
            )
            return False
        return True

    def _on_toggle_selection(self):
        """Toggle export selection mode."""
        if not self._require_selection_available():
            self._sync_selection_buttons()
            return
        try:
            from visualization.events import toggle_selection_mode

            toggle_selection_mode('export')
        except Exception as error:
            logger.warning("Failed to toggle selection mode: %s", error)
        self._sync_selection_buttons()

    def _on_toggle_ellipse_selection(self):
        """Toggle confidence ellipse display."""
        try:
            state_gateway.set_draw_selection_ellipse(
                not app_state.draw_selection_ellipse
            )
            from visualization.events import refresh_selection_overlay

            refresh_selection_overlay()
        except Exception as error:
            logger.warning("Failed to toggle ellipse display: %s", error)
        self._sync_selection_buttons()

    def _on_toggle_lasso_selection(self):
        """Toggle lasso selection mode."""
        if not self._require_selection_available():
            self._sync_selection_buttons()
            return
        try:
            from visualization.events import toggle_selection_mode

            toggle_selection_mode('lasso')
        except Exception as error:
            logger.warning("Failed to toggle custom shape selection: %s", error)
        self._sync_selection_buttons()

    def _on_analyze_subset(self):
        """Analyze selected subset (delegates to the subset plugin)."""
        if not app_state.selected_indices:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("No data selected for analysis."),
            )
            return

        from plugins.registry import plugin_manager

        subset_plugin = plugin_manager.get("subset_analysis")
        if subset_plugin is None:
            logger.error("subset_analysis plugin is not available")
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Subset analysis plugin is not available."),
            )
            return
        try:
            result = subset_plugin.apply_subset(sorted(app_state.selected_indices))
            logger.info("Subset applied: %s", result)
            from visualization.events import on_slider_change

            on_slider_change()
            QMessageBox.information(
                self,
                translate("Success"),
                translate("Subset applied: {count} samples.").format(
                    count=result.get("active_subset_size", 0)
                ),
            )
        except Exception as exc:
            logger.exception("Failed to apply subset: %s", exc)
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Failed to apply subset: {error}").format(error=exc),
            )

    def _on_reset_data(self):
        """Reset the active subset (delegates to the subset plugin)."""
        from plugins.registry import plugin_manager

        subset_plugin = plugin_manager.get("subset_analysis")
        if subset_plugin is None:
            logger.error("subset_analysis plugin is not available")
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Subset analysis plugin is not available."),
            )
            return
        try:
            result = subset_plugin.clear_subset()
            logger.info("Subset cleared: %s", result)
            from visualization.events import on_slider_change

            on_slider_change()
            QMessageBox.information(
                self,
                translate("Success"),
                translate("Subset cleared."),
            )
        except Exception as exc:
            logger.exception("Failed to reset subset: %s", exc)
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Failed to reset subset: {error}").format(error=exc),
            )

    def _on_confidence_change(self, level):
        """Handle confidence level change."""
        state_gateway.set_confidence_level(level)
        logger.info("Confidence level changed to: %s", level)
        self._on_change()
