"""分析面板 - KDE、选择与分析工具"""
import ast
import logging
import uuid

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QComboBox, QCheckBox, QSpinBox, QDoubleSpinBox,
    QLineEdit, QMessageBox, QDialog, QRadioButton,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

from core import translate, app_state
from .base_panel import BasePanel

logger = logging.getLogger(__name__)


class AnalysisPanel(BasePanel):
    """分析标签页"""

    def reset_state(self):
        super().reset_state()
        self.tools_kde_check = None
        self.tools_marginal_kde_check = None
        self.tools_equation_overlays_check = None
        self.equation_overlays_container = None
        self.equation_overlays_layout = None
        self.selection_button = None
        self.ellipse_selection_button = None
        self.lasso_selection_button = None
        self.selection_status_label = None
        self.mixing_group_name_edit = None
        self.mixing_status_label = None
        self.confidence_68_radio = None
        self.confidence_95_radio = None
        self.confidence_99_radio = None
        self.tooltip_check = None

    def build(self) -> QWidget:
        widget = self._build_analysis_section()
        self._is_initialized = True
        return widget

    def _update_status_panel(self):
        """Status panel is owned by the main control panel; no-op here."""
        return

    def _sync_toggle_widgets(self, checked, *widgets):
        """同步多个切换控件的状态"""
        for widget in widgets:
            if widget is None:
                continue
            if widget.isChecked() != checked:
                widget.blockSignals(True)
                widget.setChecked(checked)
                widget.blockSignals(False)



    def _build_analysis_section(self):
        """构建分析部分"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)

        kde_group = QGroupBox(translate("Kernel Density"))
        kde_group.setProperty('translate_key', 'Kernel Density')
        kde_layout = QVBoxLayout()

        kde_row = QHBoxLayout()
        self.tools_kde_check = QCheckBox(translate("Show Kernel Density"))
        self.tools_kde_check.setChecked(getattr(app_state, 'show_kde', False))
        self.tools_kde_check.stateChanged.connect(self._on_kde_change)
        kde_row.addWidget(self.tools_kde_check)

        kde_swatch = QLabel()
        kde_swatch.setFixedSize(16, 16)
        kde_swatch.setStyleSheet("background-color: #e2e8f0; border: 1px solid #111827;")
        kde_swatch.setProperty("keepStyle", True)
        kde_swatch.mousePressEvent = lambda event, s=kde_swatch: self._open_kde_style_dialog('kde', s)
        kde_row.addWidget(kde_swatch)
        kde_row.addStretch()
        kde_layout.addLayout(kde_row)

        mkde_row = QHBoxLayout()
        self.tools_marginal_kde_check = QCheckBox(translate("Show Marginal KDE"))
        self.tools_marginal_kde_check.setChecked(getattr(app_state, 'show_marginal_kde', False))
        self.tools_marginal_kde_check.stateChanged.connect(self._on_marginal_kde_change)
        mkde_row.addWidget(self.tools_marginal_kde_check)

        mkde_swatch = QLabel()
        mkde_swatch.setFixedSize(16, 16)
        mkde_swatch.setStyleSheet("background-color: #e2e8f0; border: 1px solid #111827;")
        mkde_swatch.setProperty("keepStyle", True)
        mkde_swatch.mousePressEvent = lambda event, s=mkde_swatch: self._open_kde_style_dialog('marginal_kde', s)
        mkde_row.addWidget(mkde_swatch)
        mkde_row.addStretch()
        kde_layout.addLayout(mkde_row)

        kde_group.setLayout(kde_layout)
        layout.addWidget(kde_group)

        equation_group = QGroupBox(translate("Equation Overlays"))
        equation_group.setProperty('translate_key', 'Equation Overlays')
        equation_layout = QVBoxLayout()

        equation_hint = QLabel(translate("Manage equations and visibility."))
        equation_hint.setWordWrap(True)
        equation_layout.addWidget(equation_hint)

        add_eq_btn = QPushButton(translate("Add Equation"))
        add_eq_btn.clicked.connect(self._open_add_equation_dialog)
        equation_layout.addWidget(add_eq_btn)

        equation_group.setLayout(equation_layout)
        layout.addWidget(equation_group)

        selection_group = QGroupBox(translate("Selection Tools"))
        selection_group.setProperty('translate_key', 'Selection Tools')
        selection_layout = QVBoxLayout()

        self.selection_button = QPushButton(translate("Enable Selection"))
        self.selection_button.setCheckable(True)
        self.selection_button.setFixedWidth(200)
        self.selection_button.clicked.connect(self._on_toggle_selection)
        selection_layout.addWidget(self.selection_button, 0, Qt.AlignHCenter)

        self.lasso_selection_button = QPushButton(translate("Custom Shape"))
        self.lasso_selection_button.setCheckable(True)
        self.lasso_selection_button.setFixedWidth(200)
        self.lasso_selection_button.clicked.connect(self._on_toggle_lasso_selection)
        selection_layout.addWidget(self.lasso_selection_button, 0, Qt.AlignHCenter)

        self.selection_status_label = QLabel(translate("Selected Samples: {count}").format(count=0))
        selection_layout.addWidget(self.selection_status_label)

        selection_group.setLayout(selection_layout)
        layout.addWidget(selection_group)

        analysis_group = QGroupBox(translate("Data Analysis"))
        analysis_group.setProperty('translate_key', 'Data Analysis')
        analysis_layout = QVBoxLayout()

        corr_btn = QPushButton(translate("Correlation Heatmap"))
        corr_btn.setFixedWidth(200)
        corr_btn.clicked.connect(self._on_show_correlation_heatmap)
        analysis_layout.addWidget(corr_btn, 0, Qt.AlignHCenter)

        axis_corr_btn = QPushButton(translate("Show Axis Corr."))
        axis_corr_btn.setFixedWidth(200)
        axis_corr_btn.clicked.connect(self._on_show_axis_correlation)
        analysis_layout.addWidget(axis_corr_btn, 0, Qt.AlignHCenter)

        shepard_btn = QPushButton(translate("Show Shepard Plot"))
        shepard_btn.setFixedWidth(200)
        shepard_btn.clicked.connect(self._on_show_shepard_diagram)
        analysis_layout.addWidget(shepard_btn, 0, Qt.AlignHCenter)

        analysis_group.setLayout(analysis_layout)
        layout.addWidget(analysis_group)

        subset_group = QGroupBox(translate("Subset Analysis"))
        subset_group.setProperty('translate_key', 'Subset Analysis')
        subset_layout = QVBoxLayout()

        analyze_btn = QPushButton(translate("Analyze Subset"))
        analyze_btn.setFixedWidth(200)
        analyze_btn.clicked.connect(self._on_analyze_subset)
        subset_layout.addWidget(analyze_btn, 0, Qt.AlignHCenter)

        reset_btn = QPushButton(translate("Reset Data"))
        reset_btn.setFixedWidth(200)
        reset_btn.clicked.connect(self._on_reset_data)
        subset_layout.addWidget(reset_btn, 0, Qt.AlignHCenter)

        subset_group.setLayout(subset_layout)
        layout.addWidget(subset_group)

        mixing_group = QGroupBox(translate("Mixing Groups"))
        mixing_group.setProperty('translate_key', 'Mixing Groups')
        mixing_layout = QVBoxLayout()

        group_name_layout = QHBoxLayout()
        group_name_layout.addWidget(QLabel(translate("Group Name:")))
        self.mixing_group_name_edit = QLineEdit()
        self.mixing_group_name_edit.setPlaceholderText(translate("Enter group name"))
        group_name_layout.addWidget(self.mixing_group_name_edit)
        mixing_layout.addLayout(group_name_layout)

        mixing_btn_layout = QHBoxLayout()

        endmember_btn = QPushButton(translate("Set as Endmember"))
        endmember_btn.setFixedWidth(170)
        endmember_btn.clicked.connect(self._on_set_endmember)
        mixing_btn_layout.addWidget(endmember_btn)

        mixture_btn = QPushButton(translate("Set as Mixture"))
        mixture_btn.setFixedWidth(170)
        mixture_btn.clicked.connect(self._on_set_mixture)
        mixing_btn_layout.addWidget(mixture_btn)

        mixing_layout.addLayout(mixing_btn_layout)

        self.mixing_status_label = QLabel(translate("No mixing groups defined"))
        self.mixing_status_label.setWordWrap(True)
        mixing_layout.addWidget(self.mixing_status_label)

        mixing_action_layout = QHBoxLayout()

        clear_mixing_btn = QPushButton(translate("Clear Mixing Groups"))
        clear_mixing_btn.setFixedWidth(170)
        clear_mixing_btn.clicked.connect(self._on_clear_mixing_groups)
        mixing_action_layout.addWidget(clear_mixing_btn)

        compute_mixing_btn = QPushButton(translate("Compute Mixing"))
        compute_mixing_btn.setFixedWidth(170)
        compute_mixing_btn.clicked.connect(self._on_compute_mixing)
        mixing_action_layout.addWidget(compute_mixing_btn)

        mixing_layout.addLayout(mixing_action_layout)

        mixing_group.setLayout(mixing_layout)
        layout.addWidget(mixing_group)

        # ---- 端元识别 ----
        endmember_group = QGroupBox(translate("Endmember Identification"))
        endmember_group.setProperty('translate_key', 'Endmember Identification')
        endmember_layout = QVBoxLayout()

        endmember_hint = QLabel(translate("Identify lead isotope endmembers using PCA."))
        endmember_hint.setWordWrap(True)
        endmember_layout.addWidget(endmember_hint)

        endmember_btn = QPushButton(translate("Run Endmember Analysis"))
        endmember_btn.setFixedWidth(200)
        endmember_btn.clicked.connect(self._on_run_endmember_analysis)
        endmember_layout.addWidget(endmember_btn, 0, Qt.AlignHCenter)

        endmember_group.setLayout(endmember_layout)
        layout.addWidget(endmember_group)

        # ---- ML Provenance ----
        provenance_group = QGroupBox(translate("Provenance ML"))
        provenance_group.setProperty('translate_key', 'Provenance ML')
        provenance_layout = QVBoxLayout()

        provenance_hint = QLabel(translate("Run ML provenance classification using DBSCAN, SMOTE and XGBoost."))
        provenance_hint.setWordWrap(True)
        provenance_layout.addWidget(provenance_hint)

        provenance_btn = QPushButton(translate("Run Provenance ML"))
        provenance_btn.setFixedWidth(200)
        provenance_btn.clicked.connect(self._on_run_provenance_ml)
        provenance_layout.addWidget(provenance_btn, 0, Qt.AlignHCenter)

        provenance_group.setLayout(provenance_layout)
        layout.addWidget(provenance_group)

        confidence_group = QGroupBox(translate("Confidence Ellipse"))
        confidence_group.setProperty('translate_key', 'Confidence Ellipse')
        confidence_layout = QVBoxLayout()

        self.ellipse_selection_button = QPushButton(translate("Draw Ellipse"))
        self.ellipse_selection_button.setCheckable(True)
        self.ellipse_selection_button.setFixedWidth(200)
        self.ellipse_selection_button.clicked.connect(self._on_toggle_ellipse_selection)
        confidence_layout.addWidget(self.ellipse_selection_button, 0, Qt.AlignHCenter)

        self.confidence_68_radio = QRadioButton(translate("68% (1σ)"))
        self.confidence_95_radio = QRadioButton(translate("95% (2σ)"))
        self.confidence_99_radio = QRadioButton(translate("99% (3σ)"))

        current_level = getattr(app_state, 'confidence_level', 0.95)
        if abs(current_level - 0.68) < 0.01:
            self.confidence_68_radio.setChecked(True)
        elif abs(current_level - 0.99) < 0.01:
            self.confidence_99_radio.setChecked(True)
        else:
            self.confidence_95_radio.setChecked(True)

        self.confidence_68_radio.toggled.connect(lambda: self._on_confidence_change(0.68))
        self.confidence_95_radio.toggled.connect(lambda: self._on_confidence_change(0.95))
        self.confidence_99_radio.toggled.connect(lambda: self._on_confidence_change(0.99))

        confidence_layout.addWidget(self.confidence_68_radio)
        confidence_layout.addWidget(self.confidence_95_radio)
        confidence_layout.addWidget(self.confidence_99_radio)

        confidence_group.setLayout(confidence_layout)
        layout.addWidget(confidence_group)

        layout.addStretch()
        return widget

    def _on_show_correlation_heatmap(self):
        """显示相关性热力图"""
        try:
            from visualization.plotting.analysis_qt import show_correlation_heatmap
            show_correlation_heatmap(self)
        except Exception as e:
            logger.error("Failed to show correlation heatmap: %s", e)

    def _on_show_axis_correlation(self):
        """显示轴相关性"""
        try:
            from visualization.plotting.analysis_qt import show_embedding_correlation
            show_embedding_correlation(self)
        except Exception as e:
            logger.error("Failed to show axis correlation: %s", e)

    def _on_show_shepard_diagram(self):
        """显示Shepard图"""
        try:
            from visualization.plotting.analysis_qt import show_shepard_diagram
            show_shepard_diagram(self)
        except Exception as e:
            logger.error("Failed to show Shepard diagram: %s", e)

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
        for btn in (
            getattr(self, 'export_csv_button', None),
            getattr(self, 'export_excel_button', None),
            getattr(self, 'export_append_button', None),
            getattr(self, 'export_selected_button', None),
        ):
            if btn is not None:
                btn.setEnabled(enable_exports)
        status_export = getattr(self, 'status_export_button', None)
        if status_export is not None:
            status_export.setEnabled(enable_exports)

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
        """切换选择模式"""
        try:
            from visualization.events import toggle_selection_mode
            toggle_selection_mode('export')
        except Exception as err:
            logger.warning("Failed to toggle selection mode: %s", err)
        self._sync_selection_buttons()

    def _on_toggle_ellipse_selection(self):
        """切换置信椭圆显示（不激活选择工具）"""
        try:
            app_state.draw_selection_ellipse = not getattr(app_state, 'draw_selection_ellipse', False)
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

    def _on_analyze_subset(self):
        """子集分析"""
        if not app_state.selected_indices:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("No data selected for analysis.")
            )
            return

        QMessageBox.information(
            self,
            translate("Info"),
            translate("Subset analysis will be implemented.")
        )

    def _on_reset_data(self):
        """重置数据"""
        # TODO: 实现数据重置
        QMessageBox.information(
            self,
            translate("Info"),
            translate("Data reset will be implemented.")
        )

    def _on_kde_change(self, state):
        """KDE 显示变化"""
        app_state.show_kde = (state == Qt.Checked)
        self._sync_toggle_widgets(
            app_state.show_kde,
            getattr(self, 'kde_check', None),
            getattr(self, 'group_kde_check', None),
            getattr(self, 'tools_kde_check', None)
        )
        self._on_change()

    def _on_marginal_kde_change(self, state):
        """边际 KDE 显示变化"""
        app_state.show_marginal_kde = (state == Qt.Checked)
        self._sync_toggle_widgets(
            app_state.show_marginal_kde,
            getattr(self, 'marginal_kde_check', None),
            getattr(self, 'tools_marginal_kde_check', None)
        )
        self._on_change()

    def _on_equation_overlays_change(self, state):
        """方程叠加显示变化"""
        app_state.show_equation_overlays = (state == Qt.Checked)
        self._on_change()

    def _on_equation_overlay_toggle(self, overlay, state):
        """单个方程叠加的启用状态变化"""
        overlay['enabled'] = (state == Qt.Checked)
        self._on_change()

    def _refresh_equation_overlays(self):
        """刷新方程叠加列表"""
        if self.equation_overlays_layout is None:
            return

        while self.equation_overlays_layout.count():
            item = self.equation_overlays_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        overlays = getattr(app_state, 'equation_overlays', []) or []
        for overlay in overlays:
            self._add_equation_overlay_row(overlay)

    def _add_equation_overlay_row(self, overlay):
        """添加方程叠加项"""
        if self.equation_overlays_layout is None:
            return

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)

        label_text = overlay.get('label', 'Equation')
        eq_chk = QCheckBox(translate(label_text))
        eq_chk.setChecked(overlay.get('enabled', True))
        eq_chk.stateChanged.connect(lambda state, ov=overlay: self._on_equation_overlay_toggle(ov, state))
        row_layout.addWidget(eq_chk)

        swatch = QLabel()
        swatch.setFixedSize(16, 16)
        color_val = overlay.get('color', '#ef4444')
        swatch.setStyleSheet(f"background-color: {color_val}; border: 1px solid #111827;")
        swatch.mousePressEvent = lambda event, ov=overlay, sw=swatch: self._open_equation_style_dialog(ov, sw)
        row_layout.addWidget(swatch)
        row_layout.addStretch()

        self.equation_overlays_layout.addWidget(row)

    def _open_equation_style_dialog(self, overlay, swatch):
        """打开方程线样式对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle(translate("Edit Equation Style"))
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)

        color_row = QHBoxLayout()
        color_row.addWidget(QLabel(translate("Line Color")))
        color_swatch = QLabel()
        color_swatch.setFixedSize(20, 16)
        color_val = overlay.get('color', '#ef4444')
        color_swatch.setStyleSheet(f"background-color: {color_val}; border: 1px solid #111827;")
        color_row.addWidget(color_swatch)

        def _pick_color():
            from PyQt5.QtWidgets import QColorDialog
            chosen = QColorDialog.getColor(QColor(color_val), self, translate("Line Color"))
            if chosen.isValid():
                new_color = chosen.name()
                overlay['color'] = new_color
                color_swatch.setStyleSheet(f"background-color: {new_color}; border: 1px solid #111827;")

        color_btn = QPushButton(translate("Choose Color"))
        color_btn.clicked.connect(_pick_color)
        color_row.addWidget(color_btn)
        color_row.addStretch()
        layout.addLayout(color_row)

        width_row = QHBoxLayout()
        width_row.addWidget(QLabel(translate("Line Width")))
        width_spin = QDoubleSpinBox()
        width_spin.setRange(0.2, 6.0)
        width_spin.setSingleStep(0.1)
        width_spin.setValue(float(overlay.get('linewidth', 1.0)))
        width_row.addWidget(width_spin)
        width_row.addStretch()
        layout.addLayout(width_row)

        style_row = QHBoxLayout()
        style_row.addWidget(QLabel(translate("Line Style")))
        style_combo = QComboBox()
        style_combo.addItems(['-', '--', '-.', ':'])
        style_combo.setCurrentText(overlay.get('linestyle', '--'))
        style_row.addWidget(style_combo)
        style_row.addStretch()
        layout.addLayout(style_row)

        alpha_row = QHBoxLayout()
        alpha_row.addWidget(QLabel(translate("Opacity")))
        alpha_spin = QDoubleSpinBox()
        alpha_spin.setRange(0.1, 1.0)
        alpha_spin.setSingleStep(0.05)
        alpha_spin.setValue(float(overlay.get('alpha', 0.85)))
        alpha_row.addWidget(alpha_spin)
        alpha_row.addStretch()
        layout.addLayout(alpha_row)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton(translate("Cancel"))
        cancel_btn.clicked.connect(dialog.reject)
        btn_row.addWidget(cancel_btn)
        save_btn = QPushButton(translate("Save"))

        def _apply():
            overlay['linewidth'] = float(width_spin.value())
            overlay['linestyle'] = style_combo.currentText()
            overlay['alpha'] = float(alpha_spin.value())
            swatch.setStyleSheet(f"background-color: {overlay.get('color', '#ef4444')}; border: 1px solid #111827;")
            dialog.accept()
            self._on_change()

        save_btn.clicked.connect(_apply)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

        dialog.exec_()

    def _open_kde_style_dialog(self, target, swatch):
        """打开 KDE 样式对话框"""
        dialog = QDialog(self)
        title_key = "KDE Style" if target == 'kde' else "Marginal KDE Style"
        dialog.setWindowTitle(translate(title_key))
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)

        style_key = 'kde_style' if target == 'kde' else 'marginal_kde_style'
        style = getattr(app_state, style_key, {}) or {}

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
        fill_check = QCheckBox()
        fill_check.setChecked(bool(style.get('fill', True)))
        fill_row.addWidget(fill_check)
        fill_row.addStretch()
        layout.addLayout(fill_row)

        levels_spin = None
        if target == 'kde':
            levels_row = QHBoxLayout()
            levels_row.addWidget(QLabel(translate("KDE Levels")))
            levels_spin = QSpinBox()
            levels_spin.setRange(3, 30)
            levels_spin.setValue(int(style.get('levels', 10)))
            levels_row.addWidget(levels_spin)
            levels_row.addStretch()
            layout.addLayout(levels_row)

        top_size_spin = None
        right_size_spin = None
        if target == 'marginal_kde':
            top_row = QHBoxLayout()
            top_row.addWidget(QLabel(translate("Top KDE Height (%)")))
            top_size_spin = QDoubleSpinBox()
            top_size_spin.setRange(5.0, 40.0)
            top_size_spin.setSingleStep(1.0)
            top_size_spin.setValue(float(getattr(app_state, 'marginal_kde_top_size', 15.0)))
            top_row.addWidget(top_size_spin)
            top_row.addStretch()
            layout.addLayout(top_row)

            right_row = QHBoxLayout()
            right_row.addWidget(QLabel(translate("Right KDE Width (%)")))
            right_size_spin = QDoubleSpinBox()
            right_size_spin.setRange(5.0, 40.0)
            right_size_spin.setSingleStep(1.0)
            right_size_spin.setValue(float(getattr(app_state, 'marginal_kde_right_size', 15.0)))
            right_row.addWidget(right_size_spin)
            right_row.addStretch()
            layout.addLayout(right_row)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton(translate("Cancel"))
        cancel_btn.clicked.connect(dialog.reject)
        btn_row.addWidget(cancel_btn)
        save_btn = QPushButton(translate("Save"))

        def _apply():
            style_ref = getattr(app_state, style_key, {}) or {}
            style_ref['alpha'] = float(alpha_spin.value())
            style_ref['linewidth'] = float(width_spin.value())
            style_ref['fill'] = bool(fill_check.isChecked())
            if target == 'kde' and levels_spin is not None:
                style_ref['levels'] = int(levels_spin.value())
            if target == 'marginal_kde':
                if top_size_spin is not None:
                    app_state.marginal_kde_top_size = float(top_size_spin.value())
                if right_size_spin is not None:
                    app_state.marginal_kde_right_size = float(right_size_spin.value())
            setattr(app_state, style_key, style_ref)

            if swatch is not None:
                swatch.setStyleSheet("background-color: #e2e8f0; border: 1px solid #111827;")
            dialog.accept()
            self._on_change()

        save_btn.clicked.connect(_apply)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

        dialog.exec_()

    def _open_add_equation_dialog(self):
        """打开新增方程对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle(translate("Manage Equations"))
        dialog.setModal(True)
        dialog.resize(520, 640)

        layout = QVBoxLayout(dialog)

        info_label = QLabel(translate("Select equations to display."))
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        presets = [
            {
                'label': translate("y=x"),
                'latex': translate("y=x"),
                'expression': 'x'
            },
            {
                'label': translate("y=1.0049x+20.259"),
                'latex': translate("y=1.0049x+20.259"),
                'expression': '1.0049*x+20.259'
            }
        ]

        working_overlays = list(getattr(app_state, 'equation_overlays', []) or [])

        list_group = QGroupBox(translate("Equation Library"))
        list_group.setProperty('translate_key', 'Equation Library')
        list_layout = QVBoxLayout()

        list_container = QWidget()
        list_container_layout = QVBoxLayout(list_container)
        list_container_layout.setContentsMargins(0, 0, 0, 0)
        list_container_layout.setSpacing(6)

        entries = []

        def _clear_layout(target_layout):
            while target_layout.count():
                item = target_layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()

        def _find_overlay(expression):
            for overlay in working_overlays:
                if overlay.get('expression') == expression:
                    return overlay
            return None

        def _add_entry_row(label_text, overlay, checked=False, is_preset=False):
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)

            chk = QCheckBox(label_text)
            chk.setChecked(bool(checked))
            row_layout.addWidget(chk)

            swatch = QLabel()
            swatch.setFixedSize(16, 16)
            swatch_color = overlay.get('color', '#ef4444')
            swatch.setStyleSheet(f"background-color: {swatch_color}; border: 1px solid #111827;")
            swatch.setProperty("keepStyle", True)
            swatch.mousePressEvent = lambda event, ov=overlay, sw=swatch: self._open_equation_style_dialog(ov, sw)
            row_layout.addWidget(swatch)
            row_layout.addStretch()

            list_container_layout.addWidget(row)
            entries.append({
                'checkbox': chk,
                'overlay': overlay,
                'is_preset': is_preset
            })

        def _rebuild_list():
            entries.clear()
            _clear_layout(list_container_layout)

            existing_label = QLabel(translate("Existing Equations"))
            existing_label.setStyleSheet("font-weight: bold;")
            list_container_layout.addWidget(existing_label)

            if working_overlays:
                for overlay in working_overlays:
                    label_text = overlay.get('label', 'Equation')
                    _add_entry_row(translate(label_text), overlay, checked=overlay.get('enabled', False))
            else:
                empty_label = QLabel(translate("No equations yet."))
                list_container_layout.addWidget(empty_label)

            preset_label = QLabel(translate("Preset Equations"))
            preset_label.setStyleSheet("font-weight: bold; margin-top: 6px;")
            list_container_layout.addWidget(preset_label)

            for preset in presets:
                existing = _find_overlay(preset['expression'])
                if existing is not None:
                    continue
                preset_overlay = {
                    'label': preset['label'],
                    'latex': preset['latex'],
                    'expression': preset['expression'],
                    'enabled': False,
                    'color': '#ef4444',
                    'linewidth': 1.0,
                    'linestyle': '--',
                    'alpha': 0.85
                }
                _add_entry_row(preset['label'], preset_overlay, checked=False, is_preset=True)

            list_container_layout.addStretch()

        _rebuild_list()

        list_layout.addWidget(list_container)
        list_group.setLayout(list_layout)
        layout.addWidget(list_group)

        custom_group = QGroupBox(translate("Custom Equation"))
        custom_group.setProperty('translate_key', 'Custom Equation')
        custom_layout = QVBoxLayout()

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel(translate("Equation Name")))
        name_edit = QLineEdit()
        name_row.addWidget(name_edit)
        custom_layout.addLayout(name_row)

        latex_row = QHBoxLayout()
        latex_row.addWidget(QLabel(translate("Equation (LaTeX)")))
        latex_edit = QLineEdit()
        latex_row.addWidget(latex_edit)
        custom_layout.addLayout(latex_row)

        expr_row = QHBoxLayout()
        expr_row.addWidget(QLabel(translate("Expression (Python, x only)")))
        expr_edit = QLineEdit()
        expr_row.addWidget(expr_edit)
        custom_layout.addLayout(expr_row)

        add_custom_row = QHBoxLayout()
        add_custom_row.addStretch()
        add_custom_btn = QPushButton(translate("Add to List"))
        add_custom_row.addWidget(add_custom_btn)
        custom_layout.addLayout(add_custom_row)

        custom_group.setLayout(custom_layout)
        layout.addWidget(custom_group)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton(translate("Cancel"))
        cancel_btn.clicked.connect(dialog.reject)
        btn_row.addWidget(cancel_btn)

        def _validate_expression(expression):
            expression = expression.strip()
            if not expression:
                QMessageBox.warning(dialog, translate("Warning"), translate("Expression cannot be empty."))
                return None
            try:
                ast.parse(expression, mode='eval')
            except Exception:
                QMessageBox.warning(dialog, translate("Warning"), translate("Invalid expression."))
                return None
            return expression

        def _add_custom_to_list():
            expression = _validate_expression(expr_edit.text())
            if expression is None:
                return
            label_text = name_edit.text().strip() or 'Equation'
            latex_text = latex_edit.text().strip() or label_text
            overlay = {
                'id': f"eq_custom_{uuid.uuid4().hex[:8]}",
                'label': label_text,
                'latex': latex_text,
                'expression': expression,
                'enabled': False,
                'color': '#ef4444',
                'linewidth': 1.0,
                'linestyle': '--',
                'alpha': 0.85
            }
            working_overlays.append(overlay)
            name_edit.clear()
            latex_edit.clear()
            expr_edit.clear()
            _rebuild_list()

        def _apply_selection():
            new_overlays = []
            for entry in entries:
                overlay = entry['overlay']
                checked = bool(entry['checkbox'].isChecked())
                if entry['is_preset']:
                    if not checked:
                        continue
                    overlay = dict(overlay)
                    overlay['id'] = overlay.get('id') or f"eq_preset_{uuid.uuid4().hex[:8]}"
                    overlay['enabled'] = True
                    new_overlays.append(overlay)
                else:
                    overlay['enabled'] = checked
                    new_overlays.append(overlay)

            app_state.equation_overlays = new_overlays
            app_state.show_equation_overlays = any(ov.get('enabled', False) for ov in new_overlays)
            self._on_change()
            dialog.accept()

        add_custom_btn.clicked.connect(_add_custom_to_list)

        apply_btn = QPushButton(translate("Apply"))
        apply_btn.clicked.connect(_apply_selection)
        btn_row.addWidget(apply_btn)
        layout.addLayout(btn_row)

        dialog.exec_()

    def _on_tooltip_change(self, state):
        """工具提示显示变化"""
        app_state.show_tooltip = (state == Qt.Checked)
        self._on_change()

    def _on_configure_tooltip(self):
        """打开工具提示配置对话框"""
        try:
            from ui.dialogs.tooltip_dialog import get_tooltip_configuration
            result = get_tooltip_configuration(self)
            if result:
                app_state.tooltip_columns = result
                logger.info("Tooltip columns configured: %s", result)
                self._on_change()
        except Exception as e:
            logger.error("Failed to open tooltip configuration dialog: %s", e)
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Failed to open tooltip configuration: {error}").format(error=str(e))
            )

    def _on_set_endmember(self):
        """设置端元"""
        group_name = self.mixing_group_name_edit.text().strip()
        if not group_name:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("Please enter a group name.")
            )
            return

        if not app_state.selected_indices:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("Please select data points first.")
            )
            return

        # 初始化混合组
        if not hasattr(app_state, 'mixing_endmembers'):
            app_state.mixing_endmembers = {}
        if not hasattr(app_state, 'mixing_mixtures'):
            app_state.mixing_mixtures = {}

        app_state.mixing_endmembers[group_name] = list(app_state.selected_indices)
        self._update_mixing_status()
        self._clear_selection_after_mixing()
        QMessageBox.information(
            self,
            translate("Success"),
            translate("Endmember '{name}' set with {count} samples.").format(
                name=group_name, count=len(app_state.selected_indices)
            )
        )

    def _on_set_mixture(self):
        """设置混合物"""
        group_name = self.mixing_group_name_edit.text().strip()
        if not group_name:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("Please enter a group name.")
            )
            return

        if not app_state.selected_indices:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("Please select data points first.")
            )
            return

        # 初始化混合组
        if not hasattr(app_state, 'mixing_endmembers'):
            app_state.mixing_endmembers = {}
        if not hasattr(app_state, 'mixing_mixtures'):
            app_state.mixing_mixtures = {}

        app_state.mixing_mixtures[group_name] = list(app_state.selected_indices)
        self._update_mixing_status()
        self._clear_selection_after_mixing()
        QMessageBox.information(
            self,
            translate("Success"),
            translate("Mixture '{name}' set with {count} samples.").format(
                name=group_name, count=len(app_state.selected_indices)
            )
        )

    def _clear_selection_after_mixing(self):
        """Clear selection and refresh overlays after mixing group changes."""
        if app_state.selected_indices:
            app_state.selected_indices.clear()
        try:
            from visualization.events import refresh_selection_overlay
            refresh_selection_overlay()
        except Exception:
            pass
        self.update_selection_controls()

    def _on_clear_mixing_groups(self):
        """清除混合组"""
        app_state.mixing_endmembers = {}
        app_state.mixing_mixtures = {}
        self._update_mixing_status()
        QMessageBox.information(
            self,
            translate("Info"),
            translate("All mixing groups cleared.")
        )

    def _on_compute_mixing(self):
        """计算混合"""
        if not hasattr(app_state, 'mixing_endmembers') or not app_state.mixing_endmembers:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("Please define at least one endmember.")
            )
            return

        if not hasattr(app_state, 'mixing_mixtures') or not app_state.mixing_mixtures:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("Please define at least one mixture.")
            )
            return

        try:
            from ui.dialogs.mixing_dialog import show_mixing_calculator
            show_mixing_calculator(self)
        except Exception as e:
            logger.error("Failed to compute mixing: %s", e)
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Failed to compute mixing: {error}").format(error=str(e))
            )

    def _on_run_endmember_analysis(self):
        """运行端元识别分析"""
        if app_state.df_global is None:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("Please load data first.")
            )
            return
        try:
            from ui.dialogs.endmember_dialog import show_endmember_analysis
            show_endmember_analysis(self)
        except Exception as e:
            logger.error("Endmember analysis failed: %s", e)
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Endmember analysis failed: {error}").format(error=str(e))
            )

    def _on_run_provenance_ml(self):
        """运行溯源机器学习"""
        if app_state.df_global is None:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("Please load data first.")
            )
            return
        try:
            from ui.dialogs.provenance_ml_dialog import show_provenance_ml
            show_provenance_ml(self)
        except Exception as e:
            logger.error("Provenance ML failed: %s", e)
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Provenance ML failed: {error}").format(error=str(e))
            )

    def _update_mixing_status(self):
        """更新混合组状态"""
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

    def _on_confidence_change(self, level):
        """置信水平变化"""
        app_state.confidence_level = level
        logger.info("Confidence level changed to: %s", level)
        self._on_change()
