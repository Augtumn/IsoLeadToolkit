import logging
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
from core import app_state, state_gateway, translate
logger = logging.getLogger(__name__)
_IMAGE_FILE_FILTERS = (
    "PNG Files (*.png);;TIFF Files (*.tiff);;PDF Files (*.pdf);;"
    "SVG Files (*.svg);;EPS Files (*.eps);;All Files (*.*)"
)


class ExportPanelImageExportMixin:
    """Image export methods for ExportPanel."""

    def _on_image_preset_changed(self):
        """Update style source label when preset changes."""
        self._update_style_source_label()

    def _is_scienceplots_available(self) -> bool:
        """Cache SciencePlots availability for responsive UI interactions."""
        cached = getattr(self, '_scienceplots_available', None)
        if cached is None:
            cached = self._load_scienceplots()
            self._scienceplots_available = bool(cached)
        return bool(cached)

    def _update_style_source_label(self) -> None:
        """Refresh style source hint for current export preset."""
        if self.image_style_source_label is None:
            return
        if self._is_scienceplots_available():
            text = translate("Template Source: SciencePlots")
        else:
            text = translate("Template Source: Built-in fallback")
        self.image_style_source_label.setText(text)

    def _on_export_image_clicked(self):
        """Export figure directly using profile defaults (no panel param widgets)."""
        if app_state.df_global is None or len(app_state.df_global) == 0:
            QMessageBox.warning(self, translate("Warning"), translate("No data loaded."))
            return
        if app_state.fig is None:
            QMessageBox.warning(self, translate("Warning"), translate("Plot figure is not initialized."))
            return

        preset_key = self.image_preset_combo.currentData() if self.image_preset_combo is not None else 'science_single'
        profile = self._image_export_profile(str(preset_key))
        # Use profile defaults since panel parameter widgets have been removed.
        params = self._profile_default_params(profile)
        params['preset_key'] = str(preset_key)
        # Sizes/DPI come straight from the profile defaults dict (single source).
        point_size_for_export = int(params['point_size'])
        legend_size_for_export = int(params['legend_size'])
        label_size_for_export = int(params['label_size'])
        title_size_for_export = int(params['title_size'])
        tick_size_for_export = int(params['tick_size'])
        image_ext = str(params.get('image_ext', 'png'))
        save_options = self._resolve_export_save_options(profile, overrides=params)

        filters = _IMAGE_FILE_FILTERS
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            translate("Export Figure"),
            "",
            filters,
        )
        if not file_path:
            return

        file_path, image_ext = self._normalize_export_target(file_path, str(image_ext))

        export_fig = None
        try:
            export_fig = self._create_export_figure(
                profile,
                point_size_for_export,
                legend_size_for_export,
                label_size_for_export,
                title_size_for_export,
                tick_size_for_export,
            )
            self._save_export_figure(
                export_fig,
                file_path,
                image_ext,
                export_dpi=int(save_options['dpi']),
                bbox_tight=bool(save_options['bbox_tight']),
                pad_inches=float(save_options['pad_inches']),
                transparent=bool(save_options['transparent']),
            )
            QMessageBox.information(
                self,
                translate("Success"),
                translate("Figure exported successfully to {file}").format(file=file_path),
            )
        except Exception as export_err:
            logger.exception("Image export failed: %s", export_err)
            QMessageBox.critical(
                self,
                translate("Error"),
                translate("Failed to export image: {error}").format(error=str(export_err)),
            )
        finally:
            if export_fig is not None:
                try:
                    # The figure is created directly via Figure(...), so it
                    # is not registered with pyplot; clear() releases artists.
                    export_fig.clear()
                except Exception:
                    pass
