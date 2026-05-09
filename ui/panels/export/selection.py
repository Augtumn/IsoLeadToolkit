"""Selection/status behaviors for export panel."""
from __future__ import annotations

import logging

from core import app_state, state_gateway, translate

logger = logging.getLogger(__name__)


class ExportPanelSelectionMixin:
    """Selection and status methods for ExportPanel."""

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

        # Always enable export buttons — when nothing is selected the
        # handler exports the full dataset instead of a subset.
        _ = count  # still update the status label above
        enable_exports = True
        for btn in (
            getattr(self, 'export_csv_button', None),
            getattr(self, 'export_excel_button', None),
            getattr(self, 'export_append_button', None),
        ):
            if btn is not None:
                btn.setEnabled(enable_exports)
        status_export = getattr(self, 'status_export_button', None)
        if status_export is not None:
            status_export.setEnabled(enable_exports)

        if hasattr(self, '_sync_selection_buttons'):
            self._sync_selection_buttons()

    def _update_status_panel(self):
        """Refresh right-side status panel."""
        status_data_label = getattr(self, 'status_data_label', None)
        status_render_label = getattr(self, 'status_render_label', None)
        status_algo_label = getattr(self, 'status_algo_label', None)
        status_group_label = getattr(self, 'status_group_label', None)
        status_selected_label = getattr(self, 'status_selected_label', None)
        if any(label is None for label in (
            status_data_label,
            status_render_label,
            status_algo_label,
            status_group_label,
            status_selected_label,
        )):
            return

        data_count = len(app_state.df_global) if app_state.df_global is not None else 0
        render_mode = getattr(app_state, 'render_mode', '')
        algorithm = getattr(app_state, 'algorithm', '')
        group_col = getattr(app_state, 'last_group_col', '')
        selected_count = len(getattr(app_state, 'selected_indices', []))

        status_data_label.setText(
            translate("Loaded Data: {count} rows", count=data_count)
        )
        status_render_label.setText(
            translate("Render Mode: {mode}").format(mode=render_mode)
        )
        status_algo_label.setText(
            translate("Algorithm: {mode}").format(mode=algorithm)
        )
        status_group_label.setText(
            translate("Group Column: {col}").format(col=group_col)
        )
        status_selected_label.setText(
            translate("Selected Samples: {count}").format(count=selected_count)
        )

    def _clear_selection_only(self):
        """Clear selection and refresh overlays."""
        state_gateway.clear_selected_indices()
        try:
            from visualization.events import refresh_selection_overlay
            refresh_selection_overlay()
        except Exception:
            pass
        self.update_selection_controls()

    def _on_toggle_selection(self):
        """切换选择模式"""
        try:
            from visualization.events import toggle_selection_mode
            toggle_selection_mode('export')
        except Exception as err:
            logger.warning("Failed to toggle selection mode: %s", err)
        self._sync_selection_buttons()

    def _on_toggle_ellipse_selection(self):
        """切换置信椭圆显示"""
        try:
            state_gateway.set_draw_selection_ellipse(
                not getattr(app_state, 'draw_selection_ellipse', False)
            )
            from visualization.events import refresh_selection_overlay
            refresh_selection_overlay()
        except Exception as err:
            logger.warning("Failed to toggle ellipse display: %s", err)
        self._sync_selection_buttons()

    def _on_toggle_lasso_selection(self):
        """切换自定义图形选择模式"""
        try:
            from visualization.events import toggle_selection_mode
            toggle_selection_mode('lasso')
        except Exception as err:
            logger.warning("Failed to toggle custom shape selection: %s", err)
        self._sync_selection_buttons()
