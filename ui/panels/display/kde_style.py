"""Analysis equation and KDE overlays mixin."""

from __future__ import annotations

import ast
import uuid

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core import app_state, state_gateway, translate
from ui.icons import apply_color_swatch
from visualization.line_styles import ensure_line_style


def _default_clip_bounds() -> tuple[float, float]:
    """Clip-range defaults taken from the current axes limits."""
    try:
        ax = app_state.ax
        x_low, x_high = ax.get_xlim()
        y_low, y_high = ax.get_ylim()
    except Exception:
        return (0.0, 1.0)
    low = min(float(x_low), float(y_low))
    high = max(float(x_high), float(y_high))
    return (low, high) if high > low else (0.0, 1.0)


class DisplayPanelKdeStyleMixin:
    """KDE curve style handlers and dialog for the display panel."""

    def _on_kde_change(self, state):
        """Handle KDE visibility change."""
        state_gateway.set_show_kde(state == Qt.Checked)
        self._sync_toggle_widgets(
            app_state.show_kde,
            getattr(self, 'kde_check', None),
            getattr(self, 'group_kde_check', None),
            getattr(self, 'tools_kde_check', None),
        )
        self._on_change()

    def _on_marginal_kde_change(self, state):
        """Handle marginal KDE visibility change."""
        state_gateway.set_show_marginal_kde(state == Qt.Checked)
        self._sync_toggle_widgets(
            app_state.show_marginal_kde,
            getattr(self, 'marginal_kde_check', None),
            getattr(self, 'tools_marginal_kde_check', None),
        )
        self._on_change()

    def _open_kde_style_dialog(self, target, swatch):
        """Open style dialog for KDE overlays."""
        dialog = QDialog(self)
        title_key = "KDE Style" if target == 'kde' else "Marginal KDE Style"
        dialog.setWindowTitle(translate(title_key))
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)

        style_key = 'kde_curve' if target == 'kde' else 'marginal_kde_curve'
        fallback_style: dict[str, Any] = {
            'color': None,
            'linewidth': 1.0,
            'linestyle': '-',
            'alpha': 0.6 if target == 'kde' else 0.25,
            'fill': True,
        }
        if target == 'kde':
            fallback_style['levels'] = 10
        else:
            fallback_style['bw_adjust'] = 1.0
            fallback_style['bandwidth'] = 0.0
            fallback_style['kernel'] = 'gaussian'
            fallback_style['auto_bandwidth_method'] = 'scott'
            fallback_style['gridsize'] = 256
            fallback_style['cut'] = 1.0
            fallback_style['log_transform'] = False
        style = ensure_line_style(app_state, style_key, fallback_style)

        alpha_row = QHBoxLayout()
        alpha_row.addWidget(QLabel(translate("Opacity")))
        alpha_spin = QDoubleSpinBox()
        alpha_spin.setRange(0.05, 1.0)
        alpha_spin.setSingleStep(0.05)
        alpha_spin.setValue(float(style.get('alpha', 0.6 if target == 'kde' else 0.25)))
        alpha_row.addWidget(alpha_spin)
        alpha_row.addStretch()
        layout.addLayout(alpha_row)

        width_row = QHBoxLayout()
        width_row.addWidget(QLabel(translate("Line Width")))
        width_spin = QDoubleSpinBox()
        width_spin.setRange(0.0, 4.0)
        width_spin.setSingleStep(0.1)
        width_spin.setValue(float(style.get('linewidth', 1.0)))
        width_row.addWidget(width_spin)
        width_row.addStretch()
        layout.addLayout(width_row)

        fill_row = QHBoxLayout()
        fill_row.addWidget(QLabel(translate("Fill")))
        fill_checkbox = QCheckBox()
        fill_checkbox.setChecked(bool(style.get('fill', True)))
        fill_row.addWidget(fill_checkbox)
        fill_row.addStretch()
        layout.addLayout(fill_row)

        levels_spin = None
        kde_bw_method_combo = None
        kde_bw_adjust_spin = None
        kde_gridsize_spin = None
        kde_thresh_spin = None
        kde_clip_check = None
        kde_clip_min_spin = None
        kde_clip_max_spin = None
        kde_common_norm_check = None
        kde_warn_singular_check = None
        if target == 'kde':
            levels_row = QHBoxLayout()
            levels_row.addWidget(QLabel(translate("KDE Levels")))
            levels_spin = QSpinBox()
            levels_spin.setRange(3, 30)
            levels_spin.setValue(int(style.get('levels', 10)))
            levels_row.addWidget(levels_spin)
            levels_row.addStretch()
            layout.addLayout(levels_row)

            computation_label = QLabel(translate("Density Computation"))
            computation_label.setStyleSheet('font-weight: bold;')
            layout.addWidget(computation_label)

            bw_method_row = QHBoxLayout()
            bw_method_row.addWidget(QLabel(translate("Bandwidth Method")))
            kde_bw_method_combo = QComboBox()
            kde_bw_method_combo.setObjectName('kde_bw_method_combo')
            for method_name in ('scott', 'silverman'):
                kde_bw_method_combo.addItem(method_name, method_name)
            kde_bw_method_combo.setCurrentIndex(
                max(0, kde_bw_method_combo.findData(str(app_state.kde_bw_method)))
            )
            bw_method_row.addWidget(kde_bw_method_combo)
            bw_method_row.addStretch()
            layout.addLayout(bw_method_row)

            kde_bw_row = QHBoxLayout()
            kde_bw_row.addWidget(QLabel(translate("Bandwidth Adjust")))
            kde_bw_adjust_spin = QDoubleSpinBox()
            kde_bw_adjust_spin.setObjectName('kde_bw_adjust_spin')
            kde_bw_adjust_spin.setRange(0.05, 5.0)
            kde_bw_adjust_spin.setSingleStep(0.05)
            kde_bw_adjust_spin.setValue(float(app_state.kde_bw_adjust))
            kde_bw_row.addWidget(kde_bw_adjust_spin)
            kde_bw_row.addStretch()
            layout.addLayout(kde_bw_row)

            grid_row = QHBoxLayout()
            grid_row.addWidget(QLabel(translate("Grid Size")))
            kde_gridsize_spin = QSpinBox()
            kde_gridsize_spin.setObjectName('kde_gridsize_spin')
            kde_gridsize_spin.setRange(32, 1024)
            kde_gridsize_spin.setSingleStep(32)
            kde_gridsize_spin.setValue(int(app_state.kde_gridsize))
            grid_row.addWidget(kde_gridsize_spin)
            grid_row.addStretch()
            layout.addLayout(grid_row)

            thresh_row = QHBoxLayout()
            thresh_row.addWidget(QLabel(translate("Contour Threshold")))
            kde_thresh_spin = QDoubleSpinBox()
            kde_thresh_spin.setObjectName('kde_thresh_spin')
            kde_thresh_spin.setRange(0.001, 1.0)
            kde_thresh_spin.setSingleStep(0.01)
            kde_thresh_spin.setDecimals(3)
            kde_thresh_spin.setValue(float(app_state.kde_thresh))
            thresh_row.addWidget(kde_thresh_spin)
            thresh_row.addStretch()
            layout.addLayout(thresh_row)

            kde_clip_check = QCheckBox(translate("Clip To Range"))
            kde_clip_check.setObjectName('kde_clip_check')
            kde_clip_min, kde_clip_max = _default_clip_bounds()
            kde_clip_check.setChecked(
                app_state.kde_clip_min is not None or app_state.kde_clip_max is not None
            )
            layout.addWidget(kde_clip_check)

            kde_clip_row = QHBoxLayout()
            kde_clip_row.addWidget(QLabel(translate("Clip Min")))
            kde_clip_min_spin = QDoubleSpinBox()
            kde_clip_min_spin.setObjectName('kde_clip_min_spin')
            kde_clip_min_spin.setRange(-1.0e6, 1.0e6)
            kde_clip_min_spin.setDecimals(3)
            kde_clip_min_spin.setValue(
                float(app_state.kde_clip_min)
                if app_state.kde_clip_min is not None
                else kde_clip_min
            )
            kde_clip_row.addWidget(kde_clip_min_spin)
            kde_clip_row.addWidget(QLabel(translate("Clip Max")))
            kde_clip_max_spin = QDoubleSpinBox()
            kde_clip_max_spin.setObjectName('kde_clip_max_spin')
            kde_clip_max_spin.setRange(-1.0e6, 1.0e6)
            kde_clip_max_spin.setDecimals(3)
            kde_clip_max_spin.setValue(
                float(app_state.kde_clip_max)
                if app_state.kde_clip_max is not None
                else kde_clip_max
            )
            kde_clip_row.addWidget(kde_clip_max_spin)
            kde_clip_row.addStretch()
            layout.addLayout(kde_clip_row)

            kde_common_norm_check = QCheckBox(translate("Common Normalization"))
            kde_common_norm_check.setObjectName('kde_common_norm_check')
            kde_common_norm_check.setChecked(bool(app_state.kde_common_norm))
            layout.addWidget(kde_common_norm_check)

            kde_warn_singular_check = QCheckBox(translate("Warn When Singular"))
            kde_warn_singular_check.setObjectName('kde_warn_singular_check')
            kde_warn_singular_check.setChecked(bool(app_state.kde_warn_singular))
            layout.addWidget(kde_warn_singular_check)

        top_size_spin = None
        right_size_spin = None
        max_points_spin = None
        bw_adjust_spin = None
        bandwidth_spin = None
        kernel_combo = None
        auto_bw_method_combo = None
        cut_spin = None
        log_transform_check = None
        marginal_clip_check = None
        marginal_clip_min_spin = None
        marginal_clip_max_spin = None
        marginal_cumulative_check = None
        if target == 'marginal_kde':
            top_row = QHBoxLayout()
            top_row.addWidget(QLabel(translate("Top KDE Height (%)")))
            top_size_spin = QDoubleSpinBox()
            top_size_spin.setRange(5.0, 40.0)
            top_size_spin.setSingleStep(1.0)
            top_size_spin.setValue(float(app_state.marginal_kde_top_size))
            top_row.addWidget(top_size_spin)
            top_row.addStretch()
            layout.addLayout(top_row)

            right_row = QHBoxLayout()
            right_row.addWidget(QLabel(translate("Right KDE Width (%)")))
            right_size_spin = QDoubleSpinBox()
            right_size_spin.setRange(5.0, 40.0)
            right_size_spin.setSingleStep(1.0)
            right_size_spin.setValue(float(app_state.marginal_kde_right_size))
            right_row.addWidget(right_size_spin)
            right_row.addStretch()
            layout.addLayout(right_row)

            max_points_row = QHBoxLayout()
            max_points_row.addWidget(QLabel(translate("Marginal KDE Max Points")))
            max_points_spin = QSpinBox()
            max_points_spin.setRange(200, 50000)
            max_points_spin.setSingleStep(100)
            max_points_spin.setValue(int(app_state.marginal_kde_max_points))
            max_points_row.addWidget(max_points_spin)
            max_points_row.addStretch()
            layout.addLayout(max_points_row)

            bw_row = QHBoxLayout()
            bw_row.addWidget(QLabel(translate("Bandwidth Adjust")))
            bw_adjust_spin = QDoubleSpinBox()
            bw_adjust_spin.setRange(0.05, 5.0)
            bw_adjust_spin.setSingleStep(0.05)
            bw_adjust_spin.setValue(float(app_state.marginal_kde_bw_adjust))
            bw_row.addWidget(bw_adjust_spin)
            bw_row.addStretch()
            layout.addLayout(bw_row)

            bandwidth_row = QHBoxLayout()
            bandwidth_row.addWidget(QLabel(translate("KDE Bandwidth (0 = Auto)")))
            bandwidth_spin = QDoubleSpinBox()
            bandwidth_spin.setRange(0.0, 10.0)
            bandwidth_spin.setSingleStep(0.05)
            bandwidth_spin.setDecimals(3)
            bandwidth_spin.setValue(
                float(
                    getattr(
                        app_state,
                        'marginal_kde_bandwidth',
                        style.get('bandwidth', 0.0),
                    )
                    or 0.0
                )
            )
            bandwidth_row.addWidget(bandwidth_spin)
            bandwidth_row.addStretch()
            layout.addLayout(bandwidth_row)

            kernel_row = QHBoxLayout()
            kernel_row.addWidget(QLabel(translate("KDE Kernel")))
            kernel_combo = QComboBox()
            for kernel_name in ('gaussian', 'tophat', 'epanechnikov', 'exponential', 'linear', 'cosine'):
                kernel_combo.addItem(kernel_name, kernel_name)
            current_kernel = str(
                getattr(
                    app_state,
                    'marginal_kde_kernel',
                    style.get('kernel', 'gaussian'),
                )
                or 'gaussian'
            ).strip().lower()
            kernel_index = kernel_combo.findData(current_kernel)
            if kernel_index < 0:
                kernel_index = kernel_combo.findData('gaussian')
            if kernel_index >= 0:
                kernel_combo.setCurrentIndex(kernel_index)
            kernel_row.addWidget(kernel_combo)
            kernel_row.addStretch()
            layout.addLayout(kernel_row)

            auto_bw_method_row = QHBoxLayout()
            auto_bw_method_row.addWidget(QLabel(translate("Auto Bandwidth Method")))
            auto_bw_method_combo = QComboBox()
            auto_bw_method_combo.addItem(translate("Scott"), "scott")
            auto_bw_method_combo.addItem(translate("Silverman"), "silverman")
            current_auto_bw_method = str(
                getattr(
                    app_state,
                    'marginal_kde_auto_bandwidth_method',
                    style.get('auto_bandwidth_method', 'scott'),
                )
                or 'scott'
            ).strip().lower()
            auto_bw_method_index = auto_bw_method_combo.findData(current_auto_bw_method)
            if auto_bw_method_index < 0:
                auto_bw_method_index = auto_bw_method_combo.findData('scott')
            if auto_bw_method_index >= 0:
                auto_bw_method_combo.setCurrentIndex(auto_bw_method_index)
            auto_bw_method_row.addWidget(auto_bw_method_combo)
            auto_bw_method_row.addStretch()
            layout.addLayout(auto_bw_method_row)

            auto_bw_hint = QLabel(
                translate(
                    "Scott suits near-normal unimodal data; Silverman provides smoother estimates for skewed or heavy-tail data."
                )
            )
            auto_bw_hint.setWordWrap(True)
            layout.addWidget(auto_bw_hint)

            cut_row = QHBoxLayout()
            cut_row.addWidget(QLabel(translate("KDE Cut")))
            cut_spin = QDoubleSpinBox()
            cut_spin.setRange(0.0, 5.0)
            cut_spin.setSingleStep(0.1)
            cut_spin.setValue(float(app_state.marginal_kde_cut))
            cut_row.addWidget(cut_spin)
            cut_row.addStretch()
            layout.addLayout(cut_row)

            log_row = QHBoxLayout()
            log_transform_check = QCheckBox(translate("Log Transform Density"))
            log_transform_check.setChecked(
                bool(app_state.marginal_kde_log_transform)
            )
            log_row.addWidget(log_transform_check)
            log_row.addStretch()
            layout.addLayout(log_row)

            marginal_clip_check = QCheckBox(translate("Clip To Range"))
            marginal_clip_check.setObjectName('marginal_clip_check')
            marginal_clip_min, marginal_clip_max = _default_clip_bounds()
            marginal_clip_check.setChecked(
                app_state.marginal_kde_clip_min is not None
                or app_state.marginal_kde_clip_max is not None
            )
            layout.addWidget(marginal_clip_check)

            marginal_clip_row = QHBoxLayout()
            marginal_clip_row.addWidget(QLabel(translate("Clip Min")))
            marginal_clip_min_spin = QDoubleSpinBox()
            marginal_clip_min_spin.setObjectName('marginal_clip_min_spin')
            marginal_clip_min_spin.setRange(-1.0e6, 1.0e6)
            marginal_clip_min_spin.setDecimals(3)
            marginal_clip_min_spin.setValue(
                float(app_state.marginal_kde_clip_min)
                if app_state.marginal_kde_clip_min is not None
                else marginal_clip_min
            )
            marginal_clip_row.addWidget(marginal_clip_min_spin)
            marginal_clip_row.addWidget(QLabel(translate("Clip Max")))
            marginal_clip_max_spin = QDoubleSpinBox()
            marginal_clip_max_spin.setObjectName('marginal_clip_max_spin')
            marginal_clip_max_spin.setRange(-1.0e6, 1.0e6)
            marginal_clip_max_spin.setDecimals(3)
            marginal_clip_max_spin.setValue(
                float(app_state.marginal_kde_clip_max)
                if app_state.marginal_kde_clip_max is not None
                else marginal_clip_max
            )
            marginal_clip_row.addWidget(marginal_clip_max_spin)
            marginal_clip_row.addStretch()
            layout.addLayout(marginal_clip_row)

            cumulative_row = QHBoxLayout()
            marginal_cumulative_check = QCheckBox(translate("Cumulative Distribution"))
            marginal_cumulative_check.setObjectName('marginal_cumulative_check')
            marginal_cumulative_check.setChecked(bool(app_state.marginal_kde_cumulative))
            cumulative_row.addWidget(marginal_cumulative_check)
            cumulative_row.addStretch()
            layout.addLayout(cumulative_row)

        buttons_row = QHBoxLayout()
        buttons_row.addStretch()
        cancel_button = QPushButton(translate("Cancel"))
        cancel_button.clicked.connect(dialog.reject)
        buttons_row.addWidget(cancel_button)
        save_button = QPushButton(translate("Save"))

        def _apply():
            if kde_clip_check is not None and kde_clip_check.isChecked():
                if float(kde_clip_max_spin.value()) <= float(kde_clip_min_spin.value()):
                    QMessageBox.warning(
                        dialog,
                        translate("Warning"),
                        translate("Clip maximum must exceed the clip minimum."),
                    )
                    return
            if marginal_clip_check is not None and marginal_clip_check.isChecked():
                if float(marginal_clip_max_spin.value()) <= float(marginal_clip_min_spin.value()):
                    QMessageBox.warning(
                        dialog,
                        translate("Warning"),
                        translate("Clip maximum must exceed the clip minimum."),
                    )
                    return
            current_styles = dict(app_state.line_styles or {})
            style_ref = dict(current_styles.get(style_key, {}) or {})
            style_ref['alpha'] = float(alpha_spin.value())
            style_ref['linewidth'] = float(width_spin.value())
            style_ref['fill'] = bool(fill_checkbox.isChecked())
            if target == 'kde' and levels_spin is not None:
                style_ref['levels'] = int(levels_spin.value())
            if target == 'kde':
                state_gateway.set_kde_compute_options(
                    bw_adjust=float(kde_bw_adjust_spin.value()),
                    bw_method=str(kde_bw_method_combo.currentData() or 'scott'),
                    gridsize=int(kde_gridsize_spin.value()),
                    thresh=float(kde_thresh_spin.value()),
                    common_norm=bool(kde_common_norm_check.isChecked()),
                    warn_singular=bool(kde_warn_singular_check.isChecked()),
                )
                if kde_clip_check.isChecked():
                    state_gateway.set_kde_compute_options(
                        clip_min=float(kde_clip_min_spin.value()),
                        clip_max=float(kde_clip_max_spin.value()),
                    )
                else:
                    state_gateway.set_kde_compute_options(clear_clip=True)
            if target == 'marginal_kde':
                if top_size_spin is not None:
                    state_gateway.set_marginal_kde_layout(top_size=float(top_size_spin.value()))
                if right_size_spin is not None:
                    state_gateway.set_marginal_kde_layout(right_size=float(right_size_spin.value()))
                if max_points_spin is not None:
                    state_gateway.set_marginal_kde_compute_options(max_points=int(max_points_spin.value()))
                if bw_adjust_spin is not None:
                    style_ref['bw_adjust'] = float(bw_adjust_spin.value())
                    state_gateway.set_marginal_kde_compute_options(bw_adjust=float(bw_adjust_spin.value()))
                if bandwidth_spin is not None:
                    style_ref['bandwidth'] = float(bandwidth_spin.value())
                    state_gateway.set_marginal_kde_compute_options(
                        bandwidth=float(bandwidth_spin.value())
                    )
                if kernel_combo is not None:
                    style_ref['kernel'] = str(kernel_combo.currentData() or 'gaussian')
                    state_gateway.set_marginal_kde_compute_options(
                        kernel=str(kernel_combo.currentData() or 'gaussian')
                    )
                if auto_bw_method_combo is not None:
                    style_ref['auto_bandwidth_method'] = str(
                        auto_bw_method_combo.currentData() or 'scott'
                    )
                    state_gateway.set_marginal_kde_compute_options(
                        auto_bandwidth_method=str(auto_bw_method_combo.currentData() or 'scott')
                    )
                if cut_spin is not None:
                    style_ref['cut'] = float(cut_spin.value())
                    state_gateway.set_marginal_kde_compute_options(cut=float(cut_spin.value()))
                if log_transform_check is not None:
                    style_ref['log_transform'] = bool(log_transform_check.isChecked())
                    state_gateway.set_marginal_kde_compute_options(
                        log_transform=bool(log_transform_check.isChecked())
                    )
                if marginal_clip_check is not None:
                    if marginal_clip_check.isChecked():
                        style_ref['clip_min'] = float(marginal_clip_min_spin.value())
                        style_ref['clip_max'] = float(marginal_clip_max_spin.value())
                        state_gateway.set_marginal_kde_compute_options(
                            clip_min=float(marginal_clip_min_spin.value()),
                            clip_max=float(marginal_clip_max_spin.value()),
                        )
                    else:
                        style_ref['clip_min'] = None
                        style_ref['clip_max'] = None
                        state_gateway.set_marginal_kde_compute_options(clear_clip=True)
                if marginal_cumulative_check is not None:
                    style_ref['cumulative'] = bool(marginal_cumulative_check.isChecked())
                    state_gateway.set_marginal_kde_compute_options(
                        cumulative=bool(marginal_cumulative_check.isChecked())
                    )
            current_styles[style_key] = style_ref
            state_gateway.set_line_styles(current_styles)

            if swatch is not None:
                # Reflect the actual style color (KDE styles carry a color).
                apply_color_swatch(swatch, style_ref.get('color') or '#e2e8f0')
            dialog.accept()
            self._on_change()

        save_button.clicked.connect(_apply)
        buttons_row.addWidget(save_button)
        layout.addLayout(buttons_row)

        dialog.exec_()
