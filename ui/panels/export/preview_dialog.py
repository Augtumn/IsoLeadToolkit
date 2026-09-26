"""Preview dialog for image export (controls, refresh, save)."""
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
_IMAGE_FILE_FILTERS = (
    "PNG Files (*.png);;TIFF Files (*.tiff);;PDF Files (*.pdf);;"
    "SVG Files (*.svg);;EPS Files (*.eps);;All Files (*.*)"
)


def _hide_inert_subplot_action(toolbar) -> None:
    """Remove the toolbar's subplot tool: constrained_layout ignores it."""
    try:
        actions = list(toolbar.actions())
    except Exception:
        return
    for action in actions:
        label = str(action.text() or "").replace("&", "").strip().lower()
        if label == "configure subplots":
            action.setVisible(False)
            action.setEnabled(False)


class ExportPreviewDialogMixin:
    """Preview dialog for image export (controls, refresh, save)."""

    def _on_preview_image_clicked(self):
        """Preview export result with full parameter adjustment in a separate dialog."""
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT

        if app_state.df_global is None or len(app_state.df_global) == 0:
            QMessageBox.warning(self, translate("Warning"), translate("No data loaded."))
            return
        if app_state.fig is None:
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
            _controls = self._build_preview_controls(dialog, main_layout, image_ext, label_size_for_export, legend_size_for_export, params, point_size_for_export, preset_key, tick_size_for_export, title_size_for_export)
            dpi_slider = _controls.dpi_slider
            dpi_spin = _controls.dpi_spin
            format_combo = _controls.format_combo
            idx = _controls.idx
            lab_slider = _controls.lab_slider
            lab_spin = _controls.lab_spin
            lms_slider = _controls.lms_slider
            lms_spin = _controls.lms_spin
            ls_slider = _controls.ls_slider
            ls_spin = _controls.ls_spin
            pad_spin = _controls.pad_spin
            preset_combo = _controls.preset_combo
            ps_slider = _controls.ps_slider
            ps_spin = _controls.ps_spin
            tck_slider = _controls.tck_slider
            tck_spin = _controls.tck_spin
            tight_bbox_check = _controls.tight_bbox_check
            tit_slider = _controls.tit_slider
            tit_spin = _controls.tit_spin
            transparent_check = _controls.transparent_check

            # ── Output quality ─────────────────────────────────────
            quality_row = QHBoxLayout()
            quality_row.addWidget(QLabel(translate("Output Quality")))
            embed_fonts_check = QCheckBox(translate("Embed Fonts"))
            embed_fonts_check.setObjectName('preview_embed_fonts_check')
            embed_fonts_check.setChecked(bool(params.get('embed_fonts', True)))
            embed_fonts_check.setToolTip(
                translate("Embed TrueType fonts in PDF/EPS and keep SVG text editable.")
            )
            quality_row.addWidget(embed_fonts_check)
            white_background_check = QCheckBox(translate("White Background"))
            white_background_check.setObjectName('preview_white_background_check')
            white_background_check.setChecked(bool(params.get('white_background', True)))
            white_background_check.setToolTip(
                translate("Export on a white background regardless of the current theme.")
            )
            quality_row.addWidget(white_background_check)
            quality_row.addStretch()
            main_layout.addLayout(quality_row)

            # ── Canvas and toolbar ─────────────────────────────────
            canvas = FigureCanvasQTAgg(preview_fig)
            canvas.setFixedSize(preview_width_px, preview_height_px)
            toolbar = NavigationToolbar2QT(canvas, dialog)
            _hide_inert_subplot_action(toolbar)
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
                'toolbar': toolbar,
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
                        except Exception as err:
                            logger.warning("_do_refresh failed: %s", err)
                    state['axis_callbacks'] = []
                    for cid in state['canvas_callbacks']:
                        try:
                            state['canvas'].mpl_disconnect(cid)
                        except Exception as err:
                            logger.warning("_do_refresh failed: %s", err)
                    state['canvas_callbacks'] = []

                    # Apply current DPI to the profile for figure creation.
                    # Cap the preview render DPI so huge slider values do not
                    # allocate a multi-thousand-pixel canvas; the saved file
                    # still uses the user's requested DPI.
                    effective_profile = dict(state['profile'])
                    preview_dpi = min(
                        int(state['params'].get('dpi', effective_profile.get('dpi', 400))),
                        300,
                    )
                    effective_profile['dpi'] = preview_dpi

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

                    # Release the previous preview figure; otherwise every
                    # preview adjustment leaks one full Figure.
                    if old_fig is not None and old_fig is not new_fig:
                        try:
                            old_fig.clear()
                        except Exception as err:
                            logger.warning("_do_refresh failed: %s", err)

                    # Update canvas size to match new figure (use the capped
                    # preview DPI so huge requested values do not allocate a
                    # multi-thousand-pixel canvas widget).
                    new_w = int(round(float(effective_profile['figsize'][0]) * preview_dpi))
                    new_h = int(round(float(effective_profile['figsize'][1]) * preview_dpi))
                    state['canvas'].figure = new_fig
                    # Keep the reverse reference so code reaching the canvas
                    # through the figure (draw paths) does not hit None.
                    try:
                        new_fig.canvas = state['canvas']
                    except Exception as err:
                        logger.warning("_do_refresh failed: %s", err)
                    state['canvas'].setFixedSize(new_w, new_h)

                    # Re-register overlay label callbacks
                    if new_ax is not None:
                        try:
                            cid1 = new_ax.callbacks.connect('xlim_changed', lambda _ax: _refresh_labels_preview())
                            cid2 = new_ax.callbacks.connect('ylim_changed', lambda _ax: _refresh_labels_preview())
                            state['axis_callbacks'] = [cid1, cid2]
                        except Exception as err:
                            logger.warning("_do_refresh failed: %s", err)
                    try:
                        cid3 = state['canvas'].mpl_connect('button_release_event', lambda _evt: _refresh_labels_preview())
                        state['canvas_callbacks'] = [cid3]
                    except Exception as err:
                        logger.warning("_do_refresh failed: %s", err)

                    _refresh_labels_preview()
                    state['canvas'].draw_idle()

                    # Replace toolbar to keep it connected to the new figure
                    if state['toolbar'] is not None:
                        try:
                            main_layout.removeWidget(state['toolbar'])
                            state['toolbar'].setParent(None)
                            state['toolbar'].deleteLater()
                        except Exception as err:
                            logger.warning("_do_refresh failed: %s", err)
                    state['toolbar'] = NavigationToolbar2QT(state['canvas'], dialog)
                    _hide_inert_subplot_action(state['toolbar'])
                    main_layout.insertWidget(1, state['toolbar'])  # after control_widget
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
                except Exception as err:
                    logger.warning("_refresh_labels_preview failed: %s", err)

            # Initial label refresh
            _refresh_labels_preview()

            if main_preview_ax is not None:
                try:
                    cid1 = main_preview_ax.callbacks.connect('xlim_changed', lambda _ax: _refresh_labels_preview())
                    cid2 = main_preview_ax.callbacks.connect('ylim_changed', lambda _ax: _refresh_labels_preview())
                    state['axis_callbacks'] = [cid1, cid2]
                except Exception as err:
                    logger.warning("_on_preview_image_clicked failed: %s", err)
            try:
                cid3 = canvas.mpl_connect('button_release_event', lambda _evt: _refresh_labels_preview())
                state['canvas_callbacks'] = [cid3]
            except Exception as err:
                logger.warning("_on_preview_image_clicked failed: %s", err)

            # ── Wire slider ↔ spin bi-directional sync ─────────────
            def _wire_pair(slider, spin, state_key):
                def _apply_value(v):
                    state[state_key] = v
                    _schedule_refresh()

                def _slider_changed(v):
                    spin.blockSignals(True)
                    spin.setValue(v)
                    spin.blockSignals(False)
                    # Debounced apply also covers keyboard arrows, which only
                    # emit valueChanged (sliderReleased is mouse-only).
                    _apply_value(v)

                def _spin_changed(v):
                    slider.blockSignals(True)
                    slider.setValue(v)
                    slider.blockSignals(False)
                    _apply_value(v)

                slider.valueChanged.connect(_slider_changed)       # sync spin + debounced apply
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
                    _apply_dpi(v)

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
                state['legend_marker_size'] = new_defaults['point_size']
                state['legend_size'] = new_defaults['legend_size']
                state['label_size'] = new_defaults['label_size']
                state['title_size'] = new_defaults['title_size']
                state['tick_size'] = new_defaults['tick_size']
                # Only size/DPI fields follow the new preset; toggle/format
                # choices (transparent, tight_bbox, pad, image_ext) keep the
                # user's current values so the UI and the saved output agree.
                for key in ('dpi', 'point_size', 'legend_size', 'label_size',
                            'title_size', 'tick_size'):
                    state['params'][key] = new_defaults[key]
                state['params']['preset_key'] = str(new_preset_key)

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
                filters = _IMAGE_FILE_FILTERS
                file_path, _ = QFileDialog.getSaveFileName(
                    dialog,
                    translate("Save"),
                    "",
                    filters,
                )
                if not file_path:
                    return
                file_path, export_ext = self._normalize_export_target(file_path, str(state['params'].get('image_ext', 'png')))
                state['params']['embed_fonts'] = bool(embed_fonts_check.isChecked())
                state['params']['white_background'] = bool(white_background_check.isChecked())
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
                        embed_fonts=bool(embed_fonts_check.isChecked()),
                        white_background=bool(white_background_check.isChecked()),
                    )
                    QMessageBox.information(
                        dialog,
                        translate("Success"),
                        translate("Figure exported successfully to {file}").format(file=file_path),
                    )
                except Exception as save_err:
                    logger.exception("Failed to save preview image: %s", save_err)
                    QMessageBox.critical(
                        dialog,
                        translate("Error"),
                        translate("Failed to save preview image: {error}").format(error=str(save_err)),
                    )

            button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Close)
            save_button = button_box.button(QDialogButtonBox.Save)
            if save_button is not None:
                save_button.setText(translate("Save"))
                save_button.setDefault(True)  # Enter saves
                save_button.clicked.connect(_save_preview_image)
            close_button = button_box.button(QDialogButtonBox.Close)
            if close_button is not None:
                close_button.setText(translate("Close"))
                close_button.setAutoDefault(False)
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
                            except Exception as err:
                                logger.warning("_cleanup_preview failed: %s", err)
                    for cid in state['canvas_callbacks']:
                        try:
                            state['canvas'].mpl_disconnect(cid)
                        except Exception as err:
                            logger.warning("_cleanup_preview failed: %s", err)
                finally:
                    try:
                        state['preview_fig'].clear()
                    except Exception as err:
                        logger.warning("_cleanup_preview failed: %s", err)

            dialog.finished.connect(_cleanup_preview)
            dialog.exec_()
        except Exception as err:
            logger.exception("Failed to generate export preview: %s", err)
            QMessageBox.critical(
                self,
                translate("Error"),
                translate("Failed to generate export preview: {error}").format(error=str(err)),
            )
