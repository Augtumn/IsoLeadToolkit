"""Image export logic for export panel."""
from __future__ import annotations

import logging

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QScrollArea,
    QSlider,
    QSpinBox,
    QVBoxLayout,
)

from core import app_state, state_gateway, translate

logger = logging.getLogger(__name__)


class ExportPanelImageExportMixin:
    """Image export methods for ExportPanel."""

    def _on_image_preset_changed(self):
        """Sync export point size input with the selected preset defaults."""
        if self.image_preset_combo is None or self.image_point_size_spin is None:
            return
        preset_key = self.image_preset_combo.currentData() or 'science_single'
        profile = self._image_export_profile(str(preset_key))
        self.image_point_size_spin.blockSignals(True)
        self.image_point_size_spin.setValue(int(profile.get('point_size', 60)))
        self.image_point_size_spin.blockSignals(False)
        if self.image_legend_size_spin is not None:
            default_legend_size = int(round(float((profile.get('legend', {}) or {}).get('fontsize', 8.0))))
            self.image_legend_size_spin.blockSignals(True)
            self.image_legend_size_spin.setValue(default_legend_size)
            self.image_legend_size_spin.blockSignals(False)
        if self.image_dpi_spin is not None:
            self.image_dpi_spin.blockSignals(True)
            self.image_dpi_spin.setValue(int(profile.get('dpi', 400)))
            self.image_dpi_spin.blockSignals(False)
        legend_fontsize = float((profile.get('legend', {}) or {}).get('fontsize', 8.0))
        if self.image_label_size_spin is not None:
            self.image_label_size_spin.blockSignals(True)
            self.image_label_size_spin.setValue(int(round(legend_fontsize + 2.0)))
            self.image_label_size_spin.blockSignals(False)
        if self.image_title_size_spin is not None:
            self.image_title_size_spin.blockSignals(True)
            self.image_title_size_spin.setValue(int(round(legend_fontsize + 3.0)))
            self.image_title_size_spin.blockSignals(False)
        if self.image_tick_size_spin is not None:
            self.image_tick_size_spin.blockSignals(True)
            self.image_tick_size_spin.setValue(int(round(legend_fontsize - 0.5)))
            self.image_tick_size_spin.blockSignals(False)
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
        """Export figure directly without opening preview dialog."""
        import matplotlib.pyplot as plt

        if getattr(app_state, 'df_global', None) is None or len(app_state.df_global) == 0:
            QMessageBox.warning(self, translate("Warning"), translate("No data loaded."))
            return
        if getattr(app_state, 'fig', None) is None:
            QMessageBox.warning(self, translate("Warning"), translate("Plot figure is not initialized."))
            return

        preset_key = self.image_preset_combo.currentData() if self.image_preset_combo is not None else 'science_single'
        profile = self._image_export_profile(str(preset_key))
        preferred_ext = self.image_format_combo.currentData() if self.image_format_combo is not None else 'png'
        filters = (
            "PNG Files (*.png);;TIFF Files (*.tiff);;PDF Files (*.pdf);;"
            "SVG Files (*.svg);;EPS Files (*.eps);;All Files (*.*)"
        )
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            translate("Export Figure"),
            "",
            filters,
        )
        if not file_path:
            return

        file_path, image_ext = self._normalize_export_target(file_path, str(preferred_ext))
        point_size_for_export = self._resolve_export_point_size(profile)
        legend_size_for_export = self._resolve_export_legend_size(profile)
        label_size_for_export = self._resolve_export_label_size(profile)
        title_size_for_export = self._resolve_export_title_size(profile)
        tick_size_for_export = self._resolve_export_tick_size(profile)
        save_options = self._resolve_export_save_options(profile)

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
            QMessageBox.critical(
                self,
                translate("Error"),
                translate("Failed to export image: {error}").format(error=str(export_err)),
            )
        finally:
            if export_fig is not None:
                try:
                    plt.close(export_fig)
                except Exception:
                    pass

    def _create_export_figure(
        self,
        profile: dict,
        point_size_for_export: int,
        legend_size_for_export: int | None = None,
        label_size_for_export: int | None = None,
        title_size_for_export: int | None = None,
        tick_size_for_export: int | None = None,
    ):
        """Create an offscreen figure rendered with current mode and export profile."""
        import matplotlib.pyplot as plt
        from matplotlib.figure import Figure
        from visualization.plotting import refresh_paleoisochron_labels

        original_fig = app_state.fig
        original_ax = app_state.ax
        original_view = self._capture_axis_view(original_ax)
        original_palette = dict(getattr(app_state, 'current_palette', {}) or {})
        original_marker_map = dict(getattr(app_state, 'group_marker_map', {}) or {})
        locked_palette = self._palette_from_axis_collections(original_ax, original_palette)
        locked_marker_map = dict(original_marker_map)
        original_marginal_axes = getattr(app_state, 'marginal_axes', None)
        original_show_marginal_kde = bool(getattr(app_state, 'show_marginal_kde', False))
        original_has_marginal_axes = bool(original_fig is not None and len(getattr(original_fig, 'axes', [])) > 1)

        try:
            use_scienceplots = self._is_scienceplots_available()
            style_chain = profile['styles'] if use_scienceplots else ['default']
            with plt.style.context(style_chain):
                if not use_scienceplots:
                    plt.rcParams.update(self._fallback_export_rc(
                        profile,
                        label_fontsize=label_size_for_export,
                        title_fontsize=title_size_for_export,
                        tick_fontsize=tick_size_for_export,
                    ))
                export_fig = Figure(
                    figsize=profile['figsize'],
                    dpi=int(profile['dpi']),
                    constrained_layout=True,
                )
                export_ax = export_fig.add_subplot(111)

                state_gateway.set_figure_axes(export_fig, export_ax)
                state_gateway.set_palette_and_marker_map(locked_palette, locked_marker_map)

                # Preserve visible marginal KDE when current interactive figure uses marginal axes.
                if original_has_marginal_axes:
                    state_gateway.set_show_marginal_kde(True)

                render_ok = self._render_current_mode_sync(point_size=point_size_for_export)
                if not render_ok:
                    raise RuntimeError("Failed to render export figure.")

                # Re-run overlay label placement for the export/preview canvas.
                try:
                    refresh_paleoisochron_labels()
                except Exception as label_err:
                    logger.debug("Overlay label refresh skipped: %s", label_err)

                # Keep exported geometry consistent with what user sees currently.
                self._apply_axis_view(export_ax, original_view)
                try:
                    refresh_paleoisochron_labels()
                except Exception:
                    pass
                self._normalize_export_legends(
                    export_fig,
                    profile,
                    legend_size_override=legend_size_for_export,
                    point_size_override=point_size_for_export,
                )
                self._attach_preview_label_state(export_fig)
                return export_fig
        finally:
            state_gateway.set_figure_axes(original_fig, original_ax)
            state_gateway.set_palette_and_marker_map(original_palette, original_marker_map)
            state_gateway.set_show_marginal_kde(original_show_marginal_kde)
            state_gateway.set_marginal_axes(original_marginal_axes)
            try:
                self._render_current_mode_sync(point_size=int(getattr(app_state, 'point_size', 60)))
                if app_state.fig is not None and app_state.fig.canvas is not None:
                    app_state.fig.canvas.draw_idle()
            except Exception as restore_err:
                logger.warning("Failed to restore interactive canvas after export: %s", restore_err)

    def _on_preview_image_clicked(self):
        """Preview export result in a separate dialog before saving."""
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT

        if getattr(app_state, 'df_global', None) is None or len(app_state.df_global) == 0:
            QMessageBox.warning(self, translate("Warning"), translate("No data loaded."))
            return
        if getattr(app_state, 'fig', None) is None:
            QMessageBox.warning(self, translate("Warning"), translate("Plot figure is not initialized."))
            return

        preset_key = self.image_preset_combo.currentData() if self.image_preset_combo is not None else 'science_single'
        profile = self._image_export_profile(str(preset_key))
        point_size_for_export = self._resolve_export_point_size(profile)
        legend_size_for_export = self._resolve_export_legend_size(profile)
        label_size_for_export = self._resolve_export_label_size(profile)
        title_size_for_export = self._resolve_export_title_size(profile)
        tick_size_for_export = self._resolve_export_tick_size(profile)
        image_ext = self.image_format_combo.currentData() if self.image_format_combo is not None else 'png'

        try:
            preview_fig = self._create_export_figure(
                profile,
                point_size_for_export,
                legend_size_for_export,
                label_size_for_export,
                title_size_for_export,
                tick_size_for_export,
            )
            preview_width_px = int(round(float(profile['figsize'][0]) * float(profile['dpi'])))
            preview_height_px = int(round(float(profile['figsize'][1]) * float(profile['dpi'])))

            dialog = QDialog(self)
            dialog.setWindowTitle(translate("Export Preview"))
            dialog.resize(min(1400, preview_width_px + 120), min(1000, preview_height_px + 180))

            layout = QVBoxLayout(dialog)

            # Keep preview controls in dialog so users can fine-tune before exporting.
            control_row = QHBoxLayout()
            point_size_label = QLabel(translate("Point Size"))
            point_size_slider = QSlider(Qt.Horizontal)
            point_size_slider.setRange(1, 50)
            point_size_slider.setValue(int(point_size_for_export))
            point_size_spin = QSpinBox()
            point_size_spin.setRange(1, 50)
            point_size_spin.setValue(int(point_size_for_export))

            control_row.addWidget(point_size_label)
            control_row.addWidget(point_size_slider, 1)
            control_row.addWidget(point_size_spin)
            layout.addLayout(control_row)

            legend_control_row = QHBoxLayout()
            legend_size_label = QLabel(translate("Legend Size"))
            legend_size_slider = QSlider(Qt.Horizontal)
            legend_size_slider.setRange(1, 15)
            legend_size_slider.setValue(int(legend_size_for_export))
            legend_size_spin = QSpinBox()
            legend_size_spin.setRange(1, 15)
            legend_size_spin.setValue(int(legend_size_for_export))
            legend_control_row.addWidget(legend_size_label)
            legend_control_row.addWidget(legend_size_slider, 1)
            legend_control_row.addWidget(legend_size_spin)
            layout.addLayout(legend_control_row)

            canvas = FigureCanvasQTAgg(preview_fig)
            canvas.setFixedSize(preview_width_px, preview_height_px)
            toolbar = NavigationToolbar2QT(canvas, dialog)
            layout.addWidget(toolbar)

            scroll_area = QScrollArea(dialog)
            scroll_area.setWidget(canvas)
            scroll_area.setWidgetResizable(False)
            layout.addWidget(scroll_area)

            main_preview_ax = preview_fig.axes[0] if preview_fig.axes else None

            # Reposition overlay labels whenever preview viewport changes.
            refresh_guard = {'busy': False}

            def _refresh_preview_labels_now():
                if refresh_guard['busy'] or main_preview_ax is None:
                    return
                refresh_guard['busy'] = True
                try:
                    self._refresh_preview_overlay_labels(preview_fig, main_preview_ax)
                    canvas.draw_idle()
                finally:
                    refresh_guard['busy'] = False

            axis_callback_ids = []
            canvas_callback_ids = []
            if main_preview_ax is not None:
                try:
                    axis_callback_ids.append(main_preview_ax.callbacks.connect('xlim_changed', lambda _ax: _refresh_preview_labels_now()))
                    axis_callback_ids.append(main_preview_ax.callbacks.connect('ylim_changed', lambda _ax: _refresh_preview_labels_now()))
                except Exception:
                    axis_callback_ids = []
            try:
                canvas_callback_ids.append(canvas.mpl_connect('button_release_event', lambda _evt: _refresh_preview_labels_now()))
            except Exception:
                canvas_callback_ids = []

            _refresh_preview_labels_now()

            def _apply_preview_point_size(new_size: int):
                size_value = float(new_size)
                if main_preview_ax is None:
                    return
                for collection in main_preview_ax.collections:
                    if not hasattr(collection, 'get_sizes') or not hasattr(collection, 'set_sizes'):
                        continue
                    if not hasattr(collection, 'get_offsets'):
                        continue
                    try:
                        offsets = collection.get_offsets()
                        n_offsets = len(offsets) if offsets is not None else 0
                        if n_offsets <= 0:
                            continue
                        # Update scatter-like collections only; avoid touching KDE artists.
                        collection.set_sizes([size_value] * n_offsets)
                    except Exception:
                        continue
                for ax in preview_fig.axes:
                    legend = None
                    try:
                        legend = ax.get_legend()
                    except Exception:
                        legend = None
                    if legend is None:
                        continue
                    self._apply_legend_marker_size_from_point(legend, size_value)
                canvas.draw_idle()

            def _on_slider_changed(value: int):
                point_size_spin.blockSignals(True)
                point_size_spin.setValue(value)
                point_size_spin.blockSignals(False)
                if self.image_point_size_spin is not None:
                    self.image_point_size_spin.blockSignals(True)
                    self.image_point_size_spin.setValue(value)
                    self.image_point_size_spin.blockSignals(False)
                _apply_preview_point_size(value)

            def _on_spin_changed(value: int):
                point_size_slider.blockSignals(True)
                point_size_slider.setValue(value)
                point_size_slider.blockSignals(False)
                if self.image_point_size_spin is not None:
                    self.image_point_size_spin.blockSignals(True)
                    self.image_point_size_spin.setValue(value)
                    self.image_point_size_spin.blockSignals(False)
                _apply_preview_point_size(value)

            point_size_slider.valueChanged.connect(_on_slider_changed)
            point_size_spin.valueChanged.connect(_on_spin_changed)

            def _apply_preview_legend_size(new_size: int):
                legend_size = float(new_size)
                for ax in preview_fig.axes:
                    legend = None
                    try:
                        legend = ax.get_legend()
                    except Exception:
                        legend = None
                    if legend is None:
                        continue
                    for text in legend.get_texts():
                        try:
                            text.set_fontsize(legend_size)
                        except Exception:
                            pass
                    try:
                        legend.set_title("")
                        legend.get_title().set_visible(False)
                    except Exception:
                        pass
                canvas.draw_idle()

            def _on_legend_slider_changed(value: int):
                legend_size_spin.blockSignals(True)
                legend_size_spin.setValue(value)
                legend_size_spin.blockSignals(False)
                if self.image_legend_size_spin is not None:
                    self.image_legend_size_spin.blockSignals(True)
                    self.image_legend_size_spin.setValue(value)
                    self.image_legend_size_spin.blockSignals(False)
                _apply_preview_legend_size(value)

            def _on_legend_spin_changed(value: int):
                legend_size_slider.blockSignals(True)
                legend_size_slider.setValue(value)
                legend_size_slider.blockSignals(False)
                if self.image_legend_size_spin is not None:
                    self.image_legend_size_spin.blockSignals(True)
                    self.image_legend_size_spin.setValue(value)
                    self.image_legend_size_spin.blockSignals(False)
                _apply_preview_legend_size(value)

            legend_size_slider.valueChanged.connect(_on_legend_slider_changed)
            legend_size_spin.valueChanged.connect(_on_legend_spin_changed)

            def _save_preview_image():
                filters = (
                    "PNG Files (*.png);;TIFF Files (*.tiff);;PDF Files (*.pdf);;"
                    "SVG Files (*.svg);;EPS Files (*.eps);;All Files (*.*)"
                )
                file_path, _ = QFileDialog.getSaveFileName(
                    dialog,
                    translate("Save"),
                    "",
                    filters,
                )
                if not file_path:
                    return
                file_path, export_ext = self._normalize_export_target(file_path, str(image_ext))
                save_options = self._resolve_export_save_options(profile)
                try:
                    self._save_export_figure(
                        preview_fig,
                        file_path,
                        export_ext,
                        export_dpi=int(save_options['dpi']),
                        bbox_tight=bool(save_options['bbox_tight']),
                        pad_inches=float(save_options['pad_inches']),
                        transparent=bool(save_options['transparent']),
                    )
                    QMessageBox.information(
                        dialog,
                        translate("Success"),
                        translate("Figure exported successfully to {file}").format(file=file_path),
                    )
                except Exception as save_err:
                    QMessageBox.critical(
                        dialog,
                        translate("Error"),
                        translate("Failed to save preview image: {error}").format(error=str(save_err)),
                    )

            button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Close)
            save_button = button_box.button(QDialogButtonBox.Save)
            if save_button is not None:
                save_button.setText(translate("Save"))
            if save_button is not None:
                save_button.clicked.connect(_save_preview_image)
            close_button = button_box.button(QDialogButtonBox.Close)
            if close_button is not None:
                close_button.setText(translate("Close"))
                close_button.clicked.connect(dialog.reject)
            layout.addWidget(button_box)

            def _cleanup_preview(_result):
                try:
                    if main_preview_ax is not None:
                        for cid in axis_callback_ids:
                            try:
                                main_preview_ax.callbacks.disconnect(cid)
                            except Exception:
                                pass
                    for cid in canvas_callback_ids:
                        try:
                            canvas.mpl_disconnect(cid)
                        except Exception:
                            pass
                finally:
                    plt.close(preview_fig)

            dialog.finished.connect(_cleanup_preview)
            dialog.exec_()
        except Exception as err:
            logger.error("Failed to generate export preview: %s", err)
            QMessageBox.critical(
                self,
                translate("Error"),
                translate("Failed to generate export preview: {error}").format(error=str(err)),
            )
