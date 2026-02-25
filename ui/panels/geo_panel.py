"""地球化学面板 - 模型选择与参数管理"""
import logging

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QGridLayout, QComboBox, QDoubleSpinBox, QMessageBox,
)

from core import translate, app_state
from .base_panel import BasePanel

logger = logging.getLogger(__name__)


class GeoPanel(BasePanel):
    """地球化学标签页"""

    def reset_state(self):
        super().reset_state()
        self.geo_params = {}
        self.geo_model_combo = None

    def build(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)

        self.geo_params = {}

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
        layout.addWidget(model_select_group)

        # 时间参数
        time_group = QGroupBox(translate("Time Parameters (Ma)"))
        time_group.setProperty('translate_key', 'Time Parameters (Ma)')
        time_layout = QGridLayout()

        self._add_geo_param(time_layout, "T1", translate("T1 (1st Stage):"), 0, 0, 0.0, 10000.0, 4430.0)
        self._add_geo_param(time_layout, "T2", translate("T2 (Earth Age):"), 0, 2, 0.0, 10000.0, 4570.0)
        self._add_geo_param(time_layout, "Tsec", translate("Tsec (2nd Stage):"), 1, 0, 0.0, 10000.0, 3700.0)

        time_group.setLayout(time_layout)
        layout.addWidget(time_group)

        # 衰变常数
        decay_group = QGroupBox(translate("Decay Constants (a^-1)"))
        decay_group.setProperty('translate_key', 'Decay Constants (a^-1)')
        decay_layout = QGridLayout()

        self._add_geo_param(decay_layout, "lambda_238", translate("λ (238U):"), 0, 0, 0.0, 1.0, 1.55125e-10, scientific=True)
        self._add_geo_param(decay_layout, "lambda_235", translate("λ (235U):"), 0, 2, 0.0, 1.0, 9.8485e-10, scientific=True)
        self._add_geo_param(decay_layout, "lambda_232", translate("λ (232Th):"), 1, 0, 0.0, 1.0, 4.94752e-11, scientific=True)

        decay_group.setLayout(decay_layout)
        layout.addWidget(decay_group)

        # 初始铅组成
        init_group = QGroupBox(translate("Initial Lead Compositions"))
        init_group.setProperty('translate_key', 'Initial Lead Compositions')
        init_layout = QVBoxLayout()

        prim_label = QLabel(translate("Primordial (T1/T2):"))
        prim_label.setStyleSheet("font-weight: bold;")
        init_layout.addWidget(prim_label)

        prim_grid = QGridLayout()
        self._add_geo_param(prim_grid, "a0", translate("a0 (206/204):"), 0, 0, 0.0, 100.0, 9.307)
        self._add_geo_param(prim_grid, "b0", translate("b0 (207/204):"), 0, 2, 0.0, 100.0, 10.294)
        self._add_geo_param(prim_grid, "c0", translate("c0 (208/204):"), 1, 0, 0.0, 100.0, 29.476)
        init_layout.addLayout(prim_grid)

        sk_label = QLabel(translate("Stacey-Kramers 2nd Stage:"))
        sk_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        init_layout.addWidget(sk_label)

        sk_grid = QGridLayout()
        self._add_geo_param(sk_grid, "a1", translate("a1 (206/204):"), 0, 0, 0.0, 100.0, 11.152)
        self._add_geo_param(sk_grid, "b1", translate("b1 (207/204):"), 0, 2, 0.0, 100.0, 12.998)
        self._add_geo_param(sk_grid, "c1", translate("c1 (208/204):"), 1, 0, 0.0, 100.0, 31.23)
        init_layout.addLayout(sk_grid)

        init_group.setLayout(init_layout)
        layout.addWidget(init_group)

        # 地幔参数
        mantle_group = QGroupBox(translate("Mantle & Production"))
        mantle_group.setProperty('translate_key', 'Mantle & Production')
        mantle_layout = QGridLayout()

        self._add_geo_param(mantle_layout, "mu_M", translate("μ (Mantle):"), 0, 0, 0.0, 100.0, 9.74)
        self._add_geo_param(mantle_layout, "omega_M", translate("ω (Mantle):"), 0, 2, 0.0, 100.0, 36.84)
        self._add_geo_param(mantle_layout, "U_ratio", translate("U Ratio (235/238):"), 1, 0, 0.0, 1.0, 1.0 / 137.88, scientific=True)

        mantle_group.setLayout(mantle_layout)
        layout.addWidget(mantle_group)

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
        layout.addLayout(button_layout)

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

                app_state.geo_model_name = model_name
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
                if key in self.geo_params:
                    params[key] = self.geo_params[key].value() * 1e6

            for key in ('lambda_238', 'lambda_235', 'lambda_232'):
                if key in self.geo_params:
                    params[key] = self.geo_params[key].value()

            for key in ('a0', 'b0', 'c0', 'a1', 'b1', 'c1', 'mu_M', 'omega_M', 'U_ratio'):
                if key in self.geo_params:
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
