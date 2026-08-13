"""Analysis diagnostics actions mixin."""
from __future__ import annotations

import logging

from PyQt5.QtWidgets import QMessageBox

from core import app_state, translate

logger = logging.getLogger(__name__)

_NEEDS_DATA_MSG = "Please load data first."
_NEEDS_EMBEDDING_MSG = "No embedding available. Please run a dimensionality reduction first."


class AnalysisPanelDiagnosticsMixin:
    """Diagnostics tools for analysis panel."""

    def _require_embedding(self) -> bool:
        """Warn the user when diagnostics cannot run; return True when OK."""
        if getattr(app_state, "df_global", None) is None:
            QMessageBox.warning(self, translate("Warning"), translate(_NEEDS_DATA_MSG))
            return False
        if getattr(app_state, "last_embedding", None) is None:
            QMessageBox.warning(self, translate("Warning"), translate(_NEEDS_EMBEDDING_MSG))
            return False
        return True

    def _on_show_correlation_heatmap(self):
        """Show correlation heatmap."""
        if not self._require_embedding():
            return
        try:
            from visualization.plotting.analysis_qt import show_correlation_heatmap

            show_correlation_heatmap(self)
        except Exception as error:
            logger.error("Failed to show correlation heatmap: %s", error)
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Failed to show correlation heatmap: {error}").format(error=error),
            )

    def _on_show_axis_correlation(self):
        """Show embedding axis correlation."""
        if not self._require_embedding():
            return
        try:
            from visualization.plotting.analysis_qt import show_embedding_correlation

            show_embedding_correlation(self)
        except Exception as error:
            logger.error("Failed to show axis correlation: %s", error)
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Failed to show axis correlation: {error}").format(error=error),
            )

    def _on_show_shepard_diagram(self):
        """Show Shepard diagram."""
        if not self._require_embedding():
            return
        try:
            from visualization.plotting.analysis_qt import show_shepard_diagram

            show_shepard_diagram(self)
        except Exception as error:
            logger.error("Failed to show Shepard diagram: %s", error)
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Failed to show Shepard diagram: {error}").format(error=error),
            )
