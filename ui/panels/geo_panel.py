"""地球化学面板 - 模型选择与参数管理"""
import logging

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QGridLayout, QComboBox, QDoubleSpinBox, QMessageBox, QToolBox,
)

from core import translate, app_state, state_gateway
from .base_panel import BasePanel

logger = logging.getLogger(__name__)


class GeoPanel(BasePanel):
    """地球化学标签页"""

    def reset_state(self):
        super().reset_state()
        self.geo_params = {}
        self.geo_param_labels = {}
        self.geo_section_labels = {}
        self.geo_model_combo = None

    def build(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.geo_params = {}
        self.geo_param_labels = {}
        self.geo_section_labels = {}

        section_toolbox = QToolBox()
        section_toolbox.setObjectName('geo_section_toolbox')

        def _add_group_page(group_widget: QGroupBox, title_key: str) -> None:
            page = QWidget()
            page_layout = QVBoxLayout(page)
            page_layout.setContentsMargins(6, 6, 6, 6)
            page_layout.setSpacing(8)
            page_layout.addWidget(group_widget)
            page_layout.addStretch()
            section_toolbox.addItem(page, translate(title_key))

        # 模型选择
        model_select_group = QGroupBox(translate("Geochemistry Model"))
        model_select_group.setProperty('translate_key', 'Geochemistry Model')
        model_select_layout = QVBoxLayout()

        model_label = QLabel(translate("Select Model:"))
        model_label.setProperty('translate_key', 'Select Model:')
        model_select_layout.addWidget(model_label)

        self.geo_model_combo = QComboBox()
        try:
            from data.geochemistry import engine
            available_models = engine.get_available_models()
            self.geo_model_combo.addItems(available_models)
            current_model = getattr(app_state, 'geo_model_name', 'Stacey & Kramers (2nd Stage)')
            if current_model in available_models:
                self.geo_model_combo.setCurrentText(current_model)
        except Exception as e:
            logger.warning("Failed to load geochemistry models: %s", e)
            self.geo_model_combo.addItem("Default")

        self.geo_model_combo.currentTextChanged.connect(self._on_geo_model_change)
        model_select_layout.addWidget(self.geo_model_combo)

        model_select_group.setLayout(model_select_layout)
        _add_group_page(model_select_group, 'Geochemistry Model')

        # 时间参数
        time_group = QGroupBox(translate("Time Parameters (Ma)"))
        time_group.setProperty('translate_key', 'Time Parameters (Ma)')
        time_layout = QGridLayout()

        self._add_geo_param(time_layout, "T1", translate("T1 (1st Stage):"), 0, 0, 0.0, 10000.0, 4430.0)
        self._add_geo_param(time_layout, "T2", translate("T2 (Earth Age):"), 0, 2, 0.0, 10000.0, 4570.0)
        self._add_geo_param(time_layout, "Tsec", translate("Tsec (2nd Stage):"), 1, 0, 0.0, 10000.0, 3700.0)

        time_group.setLayout(time_layout)
        _add_group_page(time_group, 'Time Parameters (Ma)')

        # 衰变常数
        decay_group = QGroupBox(translate("Decay Constants (a^-1)"))
        decay_group.setProperty('translate_key', 'Decay Constants (a^-1)')
        decay_layout = QGridLayout()

        self._add_geo_param(decay_layout, "lambda_238", translate("λ (238U):"), 0, 0, 0.0, 1.0, 1.55125e-10, scientific=True)
        self._add_geo_param(decay_layout, "lambda_235", translate("λ (235U):"), 0, 2, 0.0, 1.0, 9.8485e-10, scientific=True)
        self._add_geo_param(decay_layout, "lambda_232", translate("λ (232Th):"), 1, 0, 0.0, 1.0, 4.94752e-11, scientific=True)

        decay_group.setLayout(decay_layout)
        _add_group_page(decay_group, 'Decay Constants (a^-1)')

        # 初始铅组成
        init_group = QGroupBox(translate("Initial Lead Compositions"))
        init_group.setProperty('translate_key', 'Initial Lead Compositions')
        init_layout = QVBoxLayout()

        prim_label = QLabel(translate("Primordial (T1/T2):"))
        prim_label.setProperty('translate_key', 'Primordial (T1/T2):')
        prim_label.setStyleSheet("font-weight: bold;")
        self.geo_section_labels['primordial'] = prim_label
        init_layout.addWidget(prim_label)

        prim_grid = QGridLayout()
        self._add_geo_param(prim_grid, "a0", translate("a0 (206/204):"), 0, 0, 0.0, 100.0, 9.307)
        self._add_geo_param(prim_grid, "b0", translate("b0 (207/204):"), 0, 2, 0.0, 100.0, 10.294)
        self._add_geo_param(prim_grid, "c0", translate("c0 (208/204):"), 1, 0, 0.0, 100.0, 29.476)
        init_layout.addLayout(prim_grid)

        sk_label = QLabel(translate("Stacey-Kramers 2nd Stage:"))
        sk_label.setProperty('translate_key', 'Stacey-Kramers 2nd Stage:')
        sk_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        self.geo_section_labels['second_stage'] = sk_label
        init_layout.addWidget(sk_label)

        sk_grid = QGridLayout()
        self._add_geo_param(sk_grid, "a1", translate("a1 (206/204):"), 0, 0, 0.0, 100.0, 11.152)
        self._add_geo_param(sk_grid, "b1", translate("b1 (207/204):"), 0, 2, 0.0, 100.0, 12.998)
        self._add_geo_param(sk_grid, "c1", translate("c1 (208/204):"), 1, 0, 0.0, 100.0, 31.23)
        init_layout.addLayout(sk_grid)

        init_group.setLayout(init_layout)
        _add_group_page(init_group, 'Initial Lead Compositions')

        # 地幔参数
        mantle_group = QGroupBox(translate("Mantle & Production"))
        mantle_group.setProperty('translate_key', 'Mantle & Production')
        mantle_layout = QGridLayout()

        self._add_geo_param(mantle_layout, "mu_M", translate("μ (Mantle):"), 0, 0, 0.0, 100.0, 9.74)
        self._add_geo_param(mantle_layout, "omega_M", translate("ω (Mantle):"), 0, 2, 0.0, 100.0, 36.84)
        self._add_geo_param(mantle_layout, "U_ratio", translate("U Ratio (235/238):"), 1, 0, 0.0, 1.0, 1.0 / 137.88, scientific=True)

        mantle_group.setLayout(mantle_layout)
        _add_group_page(mantle_group, 'Mantle & Production')

        # 按钮组
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        apply_btn = QPushButton(translate("Apply Changes"))
        apply_btn.setProperty('translate_key', 'Apply Changes')
        apply_btn.setFixedWidth(180)
        apply_btn.clicked.connect(self._on_apply_geo_params)
        button_layout.addWidget(apply_btn)

        reset_btn = QPushButton(translate("Reset Defaults"))
        reset_btn.setProperty('translate_key', 'Reset Defaults')
        reset_btn.setFixedWidth(180)
        reset_btn.clicked.connect(self._on_reset_geo_params)
        button_layout.addWidget(reset_btn)

        button_layout.addStretch()
        action_page = QWidget()
        action_layout = QVBoxLayout(action_page)
        action_layout.setContentsMargins(6, 6, 6, 6)
        action_layout.setSpacing(8)
        action_layout.addLayout(button_layout)
        action_layout.addStretch()
        section_toolbox.addItem(action_page, translate('Apply Changes'))

        layout.addWidget(section_toolbox)

        try:
            from data.geochemistry import engine

            self._update_geo_param_visibility(self.geo_model_combo.currentText(), engine.get_parameters())
        except Exception:
            pass

        layout.addStretch()
        return widget

    def _add_geo_param(self, grid_layout, param_name, label_text, row, col, min_val, max_val, default_val, scientific=False):
        """添加地球化学参数控件"""
        label = QLabel(label_text)
        grid_layout.addWidget(label, row, col)

        spinbox = QDoubleSpinBox()
        spinbox.setRange(min_val, max_val)
        spinbox.setDecimals(6 if scientific else 3)
        if scientific:
            spinbox.setDecimals(12)
        spinbox.setSingleStep(0.001 if not scientific else 1e-11)
        spinbox.setValue(default_val)

        grid_layout.addWidget(spinbox, row, col + 1)
        self.geo_params[param_name] = spinbox
        self.geo_param_labels[param_name] = label

    def _set_geo_param_visible(self, param_name: str, visible: bool) -> None:
        """Set visibility for parameter label and input control."""
        spinbox = self.geo_params.get(param_name)
        label = self.geo_param_labels.get(param_name)
        if label is not None:
            label.setVisible(visible)
        if spinbox is not None:
            spinbox.setVisible(visible)

    def _update_geo_param_visibility(self, model_name: str, params: dict) -> None:
        """Update parameter visibility according to model semantics."""
        age_mode = str(params.get('age_model', '')).strip().lower().replace('_', '-')
        is_two_stage = age_mode in ('two-stage', 'two stage', '2-stage', '2nd', 'second')
        is_geokit = 'Geokit' in str(model_name)

        if is_two_stage:
            self._set_geo_param_visible('T1', True)
            self._set_geo_param_visible('T2', True)
            self._set_geo_param_visible('Tsec', True)
            for key in ('a1', 'b1', 'c1'):
                self._set_geo_param_visible(key, True)
        else:
            # Single-stage: only Geokit requires two age controls (T1/T2).
            self._set_geo_param_visible('T1', is_geokit)
            self._set_geo_param_visible('T2', True)
            self._set_geo_param_visible('Tsec', False)
            for key in ('a1', 'b1', 'c1'):
                self._set_geo_param_visible(key, False)

        # Primordial reference always relevant.
        for key in ('a0', 'b0', 'c0'):
            self._set_geo_param_visible(key, True)

        second_stage_label = self.geo_section_labels.get('second_stage')
        if second_stage_label is not None:
            second_stage_label.setVisible(is_two_stage)

    # ------ 事件处理 ------

    def _on_geo_model_change(self, model_name):
        """地球化学模型选择变化"""
        if not model_name:
            return

        try:
            from data.geochemistry import engine

            if engine.load_preset(model_name):
                current_params = engine.get_parameters()

                for key in ('T1', 'T2', 'Tsec'):
                    if key in self.geo_params:
                        self.geo_params[key].setValue(current_params[key] / 1e6)

                for key in ('lambda_238', 'lambda_235', 'lambda_232'):
                    if key in self.geo_params:
                        self.geo_params[key].setValue(current_params[key])

                for key in ('a0', 'b0', 'c0', 'a1', 'b1', 'c1', 'mu_M', 'omega_M', 'U_ratio'):
                    if key in self.geo_params:
                        self.geo_params[key].setValue(current_params[key])

                self._update_geo_param_visibility(model_name, current_params)

                state_gateway.set_geo_model_name(model_name)
                logger.info("Loaded Geochemistry Model: %s", model_name)

                if app_state.render_mode in ('V1V2', 'PB_EVOL_76', 'PB_EVOL_86', 'PB_MU_AGE', 'PB_KAPPA_AGE'):
                    self._on_change()

        except Exception as e:
            logger.error("Failed to load geochemistry model: %s", e)
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Failed to load geochemistry model: {error}").format(error=str(e))
            )

    def _on_apply_geo_params(self):
        """应用地球化学参数"""
        try:
            from data.geochemistry import engine

            params = {}

            for key in ('T1', 'T2', 'Tsec'):
                if key in self.geo_params and self.geo_params[key].isVisible():
                    params[key] = self.geo_params[key].value() * 1e6

            for key in ('lambda_238', 'lambda_235', 'lambda_232'):
                if key in self.geo_params and self.geo_params[key].isVisible():
                    params[key] = self.geo_params[key].value()

            for key in ('a0', 'b0', 'c0', 'a1', 'b1', 'c1', 'mu_M', 'omega_M', 'U_ratio'):
                if key in self.geo_params and self.geo_params[key].isVisible():
                    params[key] = self.geo_params[key].value()

            engine.update_parameters(params)
            logger.info("Applied geochemistry parameters")

            if app_state.render_mode in ('V1V2', 'PB_EVOL_76', 'PB_EVOL_86', 'PB_MU_AGE', 'PB_KAPPA_AGE'):
                self._on_change()

            QMessageBox.information(
                self,
                translate("Success"),
                translate("Geochemistry parameters applied successfully.")
            )

        except Exception as e:
            logger.error("Failed to apply geochemistry parameters: %s", e)
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Failed to apply parameters: {error}").format(error=str(e))
            )

    def _on_reset_geo_params(self):
        """重置地球化学参数为默认值"""
        try:
            from data.geochemistry import engine

            model_name = self.geo_model_combo.currentText()
            if engine.load_preset(model_name):
                self._on_geo_model_change(model_name)
                QMessageBox.information(
                    self,
                    translate("Success"),
                    translate("Parameters reset to defaults.")
                )

        except Exception as e:
            logger.error("Failed to reset geochemistry parameters: %s", e)
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Failed to reset parameters: {error}").format(error=str(e))
            )
