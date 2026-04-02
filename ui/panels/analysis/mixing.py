"""Analysis mixing and ML actions mixin."""

import logging

from PyQt5.QtWidgets import QMessageBox

from core import app_state, state_gateway, translate

logger = logging.getLogger(__name__)


class AnalysisPanelMixingMixin:
    """Mixing/endmember/ML actions for analysis panel."""

    def _on_set_endmember(self):
        """Set current selection as endmember group."""
        group_name = self.mixing_group_name_edit.text().strip()
        if not group_name:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("Please enter a group name."),
            )
            return

        if not app_state.selected_indices:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("Please select data points first."),
            )
            return

        if not hasattr(app_state, 'mixing_endmembers'):
            state_gateway.set_mixing_endmembers({})
        if not hasattr(app_state, 'mixing_mixtures'):
            state_gateway.set_mixing_mixtures({})

        selected_list = list(app_state.selected_indices)
        updated_endmembers = dict(getattr(app_state, 'mixing_endmembers', {}) or {})
        updated_endmembers[group_name] = selected_list
        state_gateway.set_mixing_endmembers(updated_endmembers)
        self._update_mixing_status()
        self._clear_selection_after_mixing()
        QMessageBox.information(
            self,
            translate("Success"),
            translate("Endmember '{name}' set with {count} samples.").format(
                name=group_name,
                count=len(selected_list),
            ),
        )

    def _on_set_mixture(self):
        """Set current selection as mixture group."""
        group_name = self.mixing_group_name_edit.text().strip()
        if not group_name:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("Please enter a group name."),
            )
            return

        if not app_state.selected_indices:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("Please select data points first."),
            )
            return

        if not hasattr(app_state, 'mixing_endmembers'):
            state_gateway.set_mixing_endmembers({})
        if not hasattr(app_state, 'mixing_mixtures'):
            state_gateway.set_mixing_mixtures({})

        selected_list = list(app_state.selected_indices)
        updated_mixtures = dict(getattr(app_state, 'mixing_mixtures', {}) or {})
        updated_mixtures[group_name] = selected_list
        state_gateway.set_mixing_mixtures(updated_mixtures)
        self._update_mixing_status()
        self._clear_selection_after_mixing()
        QMessageBox.information(
            self,
            translate("Success"),
            translate("Mixture '{name}' set with {count} samples.").format(
                name=group_name,
                count=len(selected_list),
            ),
        )

    def _clear_selection_after_mixing(self):
        """Clear selection and refresh overlays after mixing changes."""
        if app_state.selected_indices:
            app_state.selected_indices.clear()
        try:
            from visualization.events import refresh_selection_overlay

            refresh_selection_overlay()
        except Exception:
            pass
        self.update_selection_controls()

    def _on_clear_mixing_groups(self):
        """Clear all mixing groups."""
        state_gateway.set_mixing_endmembers({})
        state_gateway.set_mixing_mixtures({})
        self._update_mixing_status()
        QMessageBox.information(
            self,
            translate("Info"),
            translate("All mixing groups cleared."),
        )

    def _on_compute_mixing(self):
        """Open mixing computation dialog."""
        if not hasattr(app_state, 'mixing_endmembers') or not app_state.mixing_endmembers:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("Please define at least one endmember."),
            )
            return

        if not hasattr(app_state, 'mixing_mixtures') or not app_state.mixing_mixtures:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("Please define at least one mixture."),
            )
            return

        try:
            from ui.dialogs.mixing_dialog import show_mixing_calculator

            show_mixing_calculator(self)
        except Exception as error:
            logger.error("Failed to compute mixing: %s", error)
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Failed to compute mixing: {error}").format(error=str(error)),
            )

    def _on_run_endmember_analysis(self):
        """Run endmember identification analysis."""
        if app_state.df_global is None:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("Please load data first."),
            )
            return
        try:
            from ui.dialogs.endmember_dialog import show_endmember_analysis

            show_endmember_analysis(self)
        except Exception as error:
            logger.error("Endmember analysis failed: %s", error)
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Endmember analysis failed: {error}").format(error=str(error)),
            )

    def _on_run_provenance_ml(self):
        """Run provenance machine learning workflow."""
        if app_state.df_global is None:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("Please load data first."),
            )
            return
        try:
            from ui.dialogs.provenance_ml_dialog import show_provenance_ml

            show_provenance_ml(self)
        except Exception as error:
            logger.error("Provenance ML failed: %s", error)
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Provenance ML failed: {error}").format(error=str(error)),
            )

    def _update_mixing_status(self):
        """Refresh mixing status text."""
        endmembers = getattr(app_state, 'mixing_endmembers', {})
        mixtures = getattr(app_state, 'mixing_mixtures', {})

        if not endmembers and not mixtures:
            self.mixing_status_label.setText(translate("No mixing groups defined"))
        else:
            status_parts = []
            if endmembers:
                status_parts.append(translate("Endmembers: {count}").format(count=len(endmembers)))
            if mixtures:
                status_parts.append(translate("Mixtures: {count}").format(count=len(mixtures)))
            self.mixing_status_label.setText(", ".join(status_parts))
