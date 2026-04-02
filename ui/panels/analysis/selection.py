"""Analysis selection actions mixin."""

import logging

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMessageBox

from core import app_state, state_gateway, translate

logger = logging.getLogger(__name__)


class AnalysisPanelSelectionMixin:
    """Selection and tooltip actions for analysis panel."""

    def _sync_selection_buttons(self):
        """Sync selection button states with active tool."""
        tool = getattr(app_state, 'selection_tool', None)

        selection_button = getattr(self, 'selection_button', None)
        if selection_button is not None:
            selection_button.blockSignals(True)
            selection_button.setChecked(tool == 'export')
            selection_button.setText(
                translate("Disable Selection") if tool == 'export' else translate("Enable Selection")
            )
            selection_button.blockSignals(False)

        ellipse_button = getattr(self, 'ellipse_selection_button', None)
        if ellipse_button is not None:
            ellipse_active = getattr(app_state, 'draw_selection_ellipse', False)
            ellipse_button.blockSignals(True)
            ellipse_button.setChecked(ellipse_active)
            ellipse_button.setText(
                translate("Disable Ellipse") if ellipse_active else translate("Draw Ellipse")
            )
            ellipse_button.blockSignals(False)

        lasso_button = getattr(self, 'lasso_selection_button', None)
        if lasso_button is not None:
            lasso_button.blockSignals(True)
            lasso_button.setChecked(tool == 'lasso')
            lasso_button.setText(
                translate("Disable Custom Shape") if tool == 'lasso' else translate("Custom Shape")
            )
            lasso_button.blockSignals(False)

    def update_selection_controls(self):
        """Refresh selection UI state from app_state."""
        count = len(getattr(app_state, 'selected_indices', []))
        if getattr(self, 'selection_status_label', None) is not None:
            self.selection_status_label.setText(
                translate("Selected Samples: {count}").format(count=count)
            )

        enable_exports = count > 0
        for button in (
            getattr(self, 'export_csv_button', None),
            getattr(self, 'export_excel_button', None),
            getattr(self, 'export_append_button', None),
            getattr(self, 'export_selected_button', None),
        ):
            if button is not None:
                button.setEnabled(enable_exports)
        status_export_button = getattr(self, 'status_export_button', None)
        if status_export_button is not None:
            status_export_button.setEnabled(enable_exports)

        if hasattr(self, '_sync_selection_buttons'):
            self._sync_selection_buttons()
        self._update_status_panel()

    def _clear_selection_only(self):
        """Clear selection and refresh overlays."""
        if app_state.selected_indices:
            app_state.selected_indices.clear()
        try:
            from visualization.events import refresh_selection_overlay

            refresh_selection_overlay()
        except Exception:
            pass
        self.update_selection_controls()

    def _on_toggle_selection(self):
        """Toggle export selection mode."""
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
                not getattr(app_state, 'draw_selection_ellipse', False)
            )
            from visualization.events import refresh_selection_overlay

            refresh_selection_overlay()
        except Exception as error:
            logger.warning("Failed to toggle ellipse display: %s", error)
        self._sync_selection_buttons()

    def _on_toggle_lasso_selection(self):
        """Toggle lasso selection mode."""
        try:
            from visualization.events import toggle_selection_mode

            toggle_selection_mode('lasso')
        except Exception as error:
            logger.warning("Failed to toggle custom shape selection: %s", error)
        self._sync_selection_buttons()

    def _on_analyze_subset(self):
        """Analyze selected subset."""
        if not app_state.selected_indices:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("No data selected for analysis."),
            )
            return

        QMessageBox.information(
            self,
            translate("Info"),
            translate("Subset analysis will be implemented."),
        )

    def _on_reset_data(self):
        """Reset data placeholder."""
        QMessageBox.information(
            self,
            translate("Info"),
            translate("Data reset will be implemented."),
        )

    def _on_tooltip_change(self, state):
        """Handle tooltip visibility change."""
        state_gateway.set_show_tooltip(state == Qt.Checked)
        self._on_change()

    def _on_configure_tooltip(self):
        """Open tooltip configuration dialog."""
        try:
            from ui.dialogs.tooltip_dialog import get_tooltip_configuration

            result = get_tooltip_configuration(self)
            if result:
                state_gateway.set_tooltip_columns(result)
                logger.info("Tooltip columns configured: %s", result)
                self._on_change()
        except Exception as error:
            logger.error("Failed to open tooltip configuration dialog: %s", error)
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Failed to open tooltip configuration: {error}").format(error=str(error)),
            )

    def _on_confidence_change(self, level):
        """Handle confidence level change."""
        state_gateway.set_attr('confidence_level', level)
        logger.info("Confidence level changed to: %s", level)
        self._on_change()
