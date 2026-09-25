"""Analysis panel: clustering, provenance ML and neighbourhood search actions."""
from __future__ import annotations

import logging

from PyQt5.QtWidgets import QMessageBox

from core import app_state, translate

logger = logging.getLogger(__name__)


class AnalysisPanelMlMixin:
    """Machine-learning actions for the analysis panel."""

    def _on_run_clustering(self):
        """Open HDBSCAN clustering dialog."""
        if app_state.df_global is None:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("Please load data first."),
            )
            return
        if getattr(app_state, "last_embedding", None) is None:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("No embedding available. Please run a dimensionality reduction first."),
            )
            return
        try:
            from ui.panels.analysis.dialogs.clustering_dialog import ClusteringDialog

            dialog = ClusteringDialog(self)
            dialog.exec_()
        except Exception as error:
            logger.error("HDBSCAN clustering failed: %s", error)
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Clustering failed: {error}").format(error=str(error)),
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
            from ui.panels.analysis.dialogs.provenance_ml_dialog import show_provenance_ml

            show_provenance_ml(self)
        except Exception as error:
            logger.error("Provenance ML failed: %s", error)
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Provenance ML failed: {error}").format(error=str(error)),
            )

    def _on_run_neighborhood_search(self):
        """Open neighborhood search dialog."""
        if app_state.df_global is None:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("Please load data first."),
            )
            return
        if getattr(app_state, "last_embedding", None) is None:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("No embedding data. Run a dimensionality reduction first."),
            )
            return
        try:
            from ui.panels.analysis.dialogs.neighborhood_dialog import show_neighborhood_search

            show_neighborhood_search(self)
        except Exception as error:
            logger.error("Neighborhood search failed: %s", error)
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Neighborhood search failed: {error}").format(error=str(error)),
            )
