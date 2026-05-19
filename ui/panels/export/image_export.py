"""Image export logic for export panel."""
from __future__ import annotations

import logging

from PyQt5.QtCore import Qt, QTimer
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

_PREVIEW_DEBOUNCE_MS = 400


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
        import matplotlib.pyplot as plt

        if getattr(app_state, 'df_global', None) is None or len(app_state.df_global) == 0:
            QMessageBox.warning(self, translate("Warning"), translate("No data loaded."))
            return
        if getattr(app_state, 'fig', None) is None:
            QMessageBox.warning(self, translate("Warning"), translate("Plot figure is not initialized."))
            return

        preset_key = self.image_preset_combo.currentData() if self.image_preset_combo is not None else 'science_single'
        profile = self._image_export_profile(str(preset_key))
        # Use profile defaults since panel parameter widgets have been removed.
        params = self._profile_default_params(profile)
        params['preset_key'] = str(preset_key)
        # Resolve default sizes from profile.
        point_size_for_export = int(profile.get('point_size', 60))
        legend_fontsize = float((profile.get('legend', {}) or {}).get('fontsize', 8.0))
        legend_size_for_export = int(round(legend_fontsize))
        label_size_for_export = int(round(legend_fontsize + 2.0))
        title_size_for_export = int(round(legend_fontsize + 3.0))
        tick_size_for_export = int(round(legend_fontsize - 0.5))
        image_ext = str(params.get('image_ext', 'png'))
        save_options = self._resolve_export_save_options(profile, overrides=params)

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
        legend_marker_size: int | None = None,
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
                # Always apply font size overrides regardless of SciencePlots availability
                rc_overrides = self._fallback_export_rc(
                    profile,
                    label_fontsize=label_size_for_export,
                    title_fontsize=title_size_for_export,
                    tick_fontsize=tick_size_for_export,
                )
                if not use_scienceplots:
                    plt.rcParams.update(rc_overrides)
                else:
                    # Apply font size overrides on top of SciencePlots styles
                    plt.rcParams.update({
                        'axes.labelsize': float(label_size_for_export) if label_size_for_export else rc_overrides.get('axes.labelsize', 10),
                        'axes.titlesize': float(title_size_for_export) if title_size_for_export else rc_overrides.get('axes.titlesize', 12),
                        'xtick.labelsize': float(tick_size_for_export) if tick_size_for_export else rc_overrides.get('xtick.labelsize', 9),
                        'ytick.labelsize': float(tick_size_for_export) if tick_size_for_export else rc_overrides.get('ytick.labelsize', 9),
                    })
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
                    legend_marker_override=legend_marker_size,
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
        """Preview export result with full parameter adjustment in a separate dialog."""
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
        defaults = self._profile_default_params(profile)
        params = dict(defaults)
        params['preset_key'] = str(preset_key)
        point_size_for_export = int(profile.get('point_size', 60))
        legend_fontsize = float((profile.get('legend', {}) or {}).get('fontsize', 8.0))
        legend_size_for_export = int(round(legend_fontsize))
        label_size_for_export = int(round(legend_fontsize + 2.0))
        title_size_for_export = int(round(legend_fontsize + 3.0))
        tick_size_for_export = int(round(legend_fontsize - 0.5))
        image_ext = str(params.get('image_ext', 'png'))

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
            dialog.resize(min(1400, preview_width_px + 120), min(1000, preview_height_px + 350))

            main_layout = QVBoxLayout(dialog)

            # ── Control panel ──────────────────────────────────────
            control_widget = QWidget()
            control_layout = QVBoxLayout(control_widget)
            control_layout.setContentsMargins(4, 4, 4, 4)
            control_layout.setSpacing(4)

            # Row 1: Preset + Format
            row1 = QHBoxLayout()
            row1.addWidget(QLabel(translate("Journal Preset")))
            preset_combo = QComboBox()
            preset_combo.addItem(translate("Science Single Column"), 'science_single')
            preset_combo.addItem(translate("IEEE Single Column"), 'ieee_single')
            preset_combo.addItem(translate("Nature Double Column"), 'nature_double')
            preset_combo.addItem(translate("Presentation"), 'presentation')
            idx = preset_combo.findData(str(preset_key))
            if idx >= 0:
                preset_combo.setCurrentIndex(idx)
            row1.addWidget(preset_combo)

            row1.addSpacing(12)
            row1.addWidget(QLabel(translate("Image Format")))
            format_combo = QComboBox()
            format_combo.addItem("PNG", "png")
            format_combo.addItem("TIFF", "tiff")
            format_combo.addItem("PDF", "pdf")
            format_combo.addItem("SVG", "svg")
            format_combo.addItem("EPS", "eps")
            fidx = format_combo.findData(str(image_ext))
            if fidx >= 0:
                format_combo.setCurrentIndex(fidx)
            row1.addWidget(format_combo)
            row1.addStretch()
            control_layout.addLayout(row1)

            # Helper: slider + spin pair
            def _add_slider_spin(parent_layout, label_text, translate_key, min_val, max_val, step, init_val):
                row = QHBoxLayout()
                label = QLabel(label_text)
                label.setProperty('translate_key', translate_key)
                row.addWidget(label)
                slider = QSlider(Qt.Horizontal)
                slider.setRange(min_val, max_val)
                slider.setSingleStep(step)
                slider.setValue(int(init_val))
                spin = QSpinBox()
                spin.setRange(min_val, max_val)
                spin.setSingleStep(step)
                spin.setValue(int(init_val))
                row.addWidget(slider, 1)
                row.addWidget(spin)
                parent_layout.addLayout(row)
                return slider, spin

            # Row 2: DPI + Data Point Size + Legend Marker Scale
            row2 = QHBoxLayout()
            dpi_slider, dpi_spin = _add_slider_spin(row2, translate("DPI"), "DPI", 72, 1200, 25, params['dpi'])
            ps_slider, ps_spin = _add_slider_spin(row2, translate("Data Point Size"), "Data Point Size", 1, 80, 1, point_size_for_export)
            lms_slider, lms_spin = _add_slider_spin(row2, translate("Legend Marker Size"), "Legend Marker Size", 1, 80, 1, point_size_for_export)
            control_layout.addLayout(row2)

            # Row 3: Label / Title / Tick / Legend Font sizes
            row3 = QHBoxLayout()
            lab_slider, lab_spin = _add_slider_spin(row3, translate("Label Font Size"), "Label Font Size", 4, 24, 1, label_size_for_export)
            tit_slider, tit_spin = _add_slider_spin(row3, translate("Title Font Size"), "Title Font Size", 4, 24, 1, title_size_for_export)
            tck_slider, tck_spin = _add_slider_spin(row3, translate("Tick Font Size"), "Tick Font Size", 4, 24, 1, tick_size_for_export)
            ls_slider, ls_spin = _add_slider_spin(row3, translate("Legend Size"), "Legend Size", 1, 20, 1, legend_size_for_export)
            control_layout.addLayout(row3)

            # Row 4: Tight BBox + Padding + Transparent
            row4 = QHBoxLayout()
            tight_bbox_check = QCheckBox(translate("Tight BBox"))
            tight_bbox_check.setChecked(bool(params['tight_bbox']))
            row4.addWidget(tight_bbox_check)

            row4.addWidget(QLabel(translate("Padding")))
            pad_spin = QDoubleSpinBox()
            pad_spin.setRange(0.0, 1.0)
            pad_spin.setSingleStep(0.01)
            pad_spin.setDecimals(2)
            pad_spin.setValue(float(params['pad_inches']))
            pad_spin.setEnabled(tight_bbox_check.isChecked())
            tight_bbox_check.toggled.connect(pad_spin.setEnabled)
            row4.addWidget(pad_spin)

            transparent_check = QCheckBox(translate("Transparent"))
            transparent_check.setChecked(bool(params['transparent']))
            row4.addWidget(transparent_check)
            row4.addStretch()
            control_layout.addLayout(row4)

            main_layout.addWidget(control_widget)

            # ── Canvas and toolbar ─────────────────────────────────
            canvas = FigureCanvasQTAgg(preview_fig)
            canvas.setFixedSize(preview_width_px, preview_height_px)
            toolbar = NavigationToolbar2QT(canvas, dialog)
            main_layout.addWidget(toolbar)

            scroll_area = QScrollArea(dialog)
            scroll_area.setWidget(canvas)
            scroll_area.setWidgetResizable(False)
            main_layout.addWidget(scroll_area)

            main_preview_ax = preview_fig.axes[0] if preview_fig.axes else None

            # ── State references for closures ──────────────────────
            state = {
                'preview_fig': preview_fig,
                'canvas': canvas,
                'profile': profile,
                'params': dict(params),
                'point_size': point_size_for_export,
                'legend_marker_size': point_size_for_export,
                'legend_size': legend_size_for_export,
                'label_size': label_size_for_export,
                'title_size': title_size_for_export,
                'tick_size': tick_size_for_export,
                'main_ax': main_preview_ax,
                'axis_callbacks': [],
                'canvas_callbacks': [],
                'debounce_timer': QTimer(dialog),
                'refreshing': False,
            }
            state['debounce_timer'].setSingleShot(True)
            state['debounce_timer'].setInterval(_PREVIEW_DEBOUNCE_MS)

            # ── Re-render: full figure regen via _create_export_figure ──
            def _do_refresh():
                if state['refreshing']:
                    return
                state['refreshing'] = True
                try:
                    old_fig = state['preview_fig']
                    old_ax = state['main_ax']

                    # Disconnect old callbacks
                    for cid in state['axis_callbacks']:
                        try:
                            if old_ax is not None:
                                old_ax.callbacks.disconnect(cid)
                        except Exception:
                            pass
                    state['axis_callbacks'] = []
                    for cid in state['canvas_callbacks']:
                        try:
                            state['canvas'].mpl_disconnect(cid)
                        except Exception:
                            pass
                    state['canvas_callbacks'] = []

                    # Apply current DPI to the profile for figure creation
                    import copy
                    effective_profile = dict(state['profile'])
                    effective_profile['dpi'] = int(state['params'].get('dpi', effective_profile.get('dpi', 400)))

                    new_fig = self._create_export_figure(
                        effective_profile,
                        state['point_size'],
                        state['legend_size'],
                        state['label_size'],
                        state['title_size'],
                        state['tick_size'],
                        legend_marker_size=state['legend_marker_size'],
                    )
                    state['preview_fig'] = new_fig
                    new_ax = new_fig.axes[0] if new_fig.axes else None
                    state['main_ax'] = new_ax

                    # Update canvas size to match new figure
                    new_w = int(round(float(effective_profile['figsize'][0]) * float(state['params']['dpi'])))
                    new_h = int(round(float(effective_profile['figsize'][1]) * float(state['params']['dpi'])))
                    state['canvas'].figure = new_fig
                    state['canvas'].setFixedSize(new_w, new_h)

                    # Re-register overlay label callbacks
                    if new_ax is not None:
                        try:
                            cid1 = new_ax.callbacks.connect('xlim_changed', lambda _ax: _refresh_labels_preview())
                            cid2 = new_ax.callbacks.connect('ylim_changed', lambda _ax: _refresh_labels_preview())
                            state['axis_callbacks'] = [cid1, cid2]
                        except Exception:
                            pass
                    try:
                        cid3 = state['canvas'].mpl_connect('button_release_event', lambda _evt: _refresh_labels_preview())
                        state['canvas_callbacks'] = [cid3]
                    except Exception:
                        pass

                    _refresh_labels_preview()
                    state['canvas'].draw_idle()

                    try:
                        plt.close(old_fig)
                    except Exception:
                        pass
                except Exception as err:
                    logger.warning("Preview re-render failed: %s", err)
                finally:
                    state['refreshing'] = False

            # Connect after _do_refresh is defined
            state['debounce_timer'].timeout.connect(_do_refresh)

            def _schedule_refresh():
                # Restart single-shot timer — safe, auto-cancels previous
                state['debounce_timer'].start()

            def _refresh_labels_preview():
                try:
                    self._refresh_preview_overlay_labels(state['preview_fig'], state['main_ax'])
                except Exception:
                    pass

            # Initial label refresh
            _refresh_labels_preview()

            if main_preview_ax is not None:
                try:
                    cid1 = main_preview_ax.callbacks.connect('xlim_changed', lambda _ax: _refresh_labels_preview())
                    cid2 = main_preview_ax.callbacks.connect('ylim_changed', lambda _ax: _refresh_labels_preview())
                    state['axis_callbacks'] = [cid1, cid2]
                except Exception:
                    pass
            try:
                cid3 = canvas.mpl_connect('button_release_event', lambda _evt: _refresh_labels_preview())
                state['canvas_callbacks'] = [cid3]
            except Exception:
                pass

            # ── Wire slider ↔ spin bi-directional sync ─────────────
            def _wire_pair(slider, spin, state_key):
                def _apply_value(v):
                    state[state_key] = v
                    _schedule_refresh()

                def _slider_changed(v):
                    spin.blockSignals(True)
                    spin.setValue(v)
                    spin.blockSignals(False)
                def _spin_changed(v):
                    slider.blockSignals(True)
                    slider.setValue(v)
                    slider.blockSignals(False)
                    _apply_value(v)

                slider.valueChanged.connect(_slider_changed)       # sync spin only
                slider.sliderReleased.connect(lambda: _apply_value(slider.value()))  # apply on release
                spin.valueChanged.connect(_spin_changed)            # spin: apply immediately

            _wire_pair(ps_slider, ps_spin, 'point_size')
            _wire_pair(lms_slider, lms_spin, 'legend_marker_size')
            _wire_pair(ls_slider, ls_spin, 'legend_size')
            _wire_pair(lab_slider, lab_spin, 'label_size')
            _wire_pair(tit_slider, tit_spin, 'title_size')
            _wire_pair(tck_slider, tck_spin, 'tick_size')

            # DPI needs bidirectional slider↔spin sync but writes to params dict
            def _wire_dpi_sync():
                def _apply_dpi(v):
                    state['params']['dpi'] = v
                    _schedule_refresh()
                def _dpi_slider_changed(v):
                    dpi_spin.blockSignals(True)
                    dpi_spin.setValue(v)
                    dpi_spin.blockSignals(False)
                def _dpi_spin_changed(v):
                    dpi_slider.blockSignals(True)
                    dpi_slider.setValue(v)
                    dpi_slider.blockSignals(False)
                    _apply_dpi(v)
                dpi_slider.valueChanged.connect(_dpi_slider_changed)
                dpi_slider.sliderReleased.connect(lambda: _apply_dpi(dpi_slider.value()))
                dpi_spin.valueChanged.connect(_dpi_spin_changed)
            _wire_dpi_sync()
            state['params']['dpi'] = params['dpi']  # initial value

            def _format_changed(idx):
                ext = format_combo.itemData(idx) or 'png'
                state['params']['image_ext'] = str(ext)
            format_combo.currentIndexChanged.connect(_format_changed)

            def _tight_changed(checked):
                state['params']['tight_bbox'] = bool(checked)
                # tight_bbox only affects save, no re-render needed
            tight_bbox_check.toggled.connect(_tight_changed)

            def _transparent_changed(checked):
                state['params']['transparent'] = bool(checked)
            transparent_check.toggled.connect(_transparent_changed)

            def _pad_changed(v):
                state['params']['pad_inches'] = float(v)
            pad_spin.valueChanged.connect(_pad_changed)

            def _preset_changed(idx):
                new_preset_key = preset_combo.itemData(idx) or 'science_single'
                state['params']['preset_key'] = str(new_preset_key)
                new_profile = self._image_export_profile(str(new_preset_key))
                state['profile'] = new_profile
                new_defaults = self._profile_default_params(new_profile)
                legend_fs = float((new_profile.get('legend', {}) or {}).get('fontsize', 8.0))

                # Reset all controls to new preset defaults
                _block_and_set(dpi_slider, dpi_spin, new_defaults['dpi'])
                _block_and_set(ps_slider, ps_spin, new_defaults['point_size'])
                _block_and_set(lms_slider, lms_spin, new_defaults['point_size'])
                _block_and_set(ls_slider, ls_spin, new_defaults['legend_size'])
                _block_and_set(lab_slider, lab_spin, new_defaults['label_size'])
                _block_and_set(tit_slider, tit_spin, new_defaults['title_size'])
                _block_and_set(tck_slider, tck_spin, new_defaults['tick_size'])

                # Reset state
                state['point_size'] = new_defaults['point_size']
                state['legend_size'] = new_defaults['legend_size']
                state['label_size'] = new_defaults['label_size']
                state['title_size'] = new_defaults['title_size']
                state['tick_size'] = new_defaults['tick_size']
                state['params'].update(new_defaults)
                state['params']['preset_key'] = str(new_preset_key)
                state['params']['dpi'] = new_defaults['dpi']

                _schedule_refresh()
            preset_combo.currentIndexChanged.connect(_preset_changed)

            def _block_and_set(slider, spin, value):
                slider.blockSignals(True)
                spin.blockSignals(True)
                slider.setValue(int(value))
                spin.setValue(int(value))
                slider.blockSignals(False)
                spin.blockSignals(False)

            # ── Save ───────────────────────────────────────────────
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
                file_path, export_ext = self._normalize_export_target(file_path, str(state['params'].get('image_ext', 'png')))
                save_options = self._resolve_export_save_options(state['profile'], overrides=state['params'])
                try:
                    self._save_export_figure(
                        state['preview_fig'],
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
                save_button.clicked.connect(_save_preview_image)
            close_button = button_box.button(QDialogButtonBox.Close)
            if close_button is not None:
                close_button.setText(translate("Close"))
                close_button.clicked.connect(dialog.reject)
            main_layout.addWidget(button_box)

            # ── Cleanup ────────────────────────────────────────────
            def _cleanup_preview(_result):
                try:
                    state['debounce_timer'].stop()
                    if state['main_ax'] is not None:
                        for cid in state['axis_callbacks']:
                            try:
                                state['main_ax'].callbacks.disconnect(cid)
                            except Exception:
                                pass
                    for cid in state['canvas_callbacks']:
                        try:
                            state['canvas'].mpl_disconnect(cid)
                        except Exception:
                            pass
                finally:
                    try:
                        plt.close(state['preview_fig'])
                    except Exception:
                        pass

            dialog.finished.connect(_cleanup_preview)
            dialog.exec_()
        except Exception as err:
            logger.error("Failed to generate export preview: %s", err)
            QMessageBox.critical(
                self,
                translate("Error"),
                translate("Failed to generate export preview: {error}").format(error=str(err)),
            )
