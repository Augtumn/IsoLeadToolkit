"""Builtin subset analysis plugin."""
from __future__ import annotations
from typing import Any

from plugins.api import BasePlugin, PluginMeta


class SubsetAnalysisPlugin(BasePlugin):
    meta = PluginMeta(
        name="subset_analysis",
        version="1.0",
        api_version="1.0",
        plugin_type="analysis",
        author="IsotopesAnalyse",
        description="Subset selection and focused re-analysis",
        source="builtin",
    )

    def validate_environment(self) -> tuple[bool, str]:
        return True, "ok"

    def get_default_params(self) -> dict[str, Any]:
        return {}

    def build_ui(self, parent=None, callback=None):
        """Return the Subset Analysis QGroupBox section."""
        from PyQt5.QtCore import Qt
        from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QPushButton
        from core import translate

        group = QGroupBox(translate("Subset Analysis"))
        group.setProperty('translate_key', 'Subset Analysis')
        layout = QVBoxLayout()

        analyze_btn = QPushButton(translate("Analyze Subset"))
        analyze_btn.setProperty('translate_key', 'Analyze Subset')
        analyze_btn.setFixedWidth(200)
        if callback is not None:
            analyze_btn.clicked.connect(callback._on_analyze_subset)
        layout.addWidget(analyze_btn, 0, Qt.AlignHCenter)

        reset_btn = QPushButton(translate("Reset Data"))
        reset_btn.setProperty('translate_key', 'Reset Data')
        reset_btn.setFixedWidth(200)
        if callback is not None:
            reset_btn.clicked.connect(callback._on_reset_data)
        layout.addWidget(reset_btn, 0, Qt.AlignHCenter)

        group.setLayout(layout)
        return group

    def apply_subset(self, indices):
        from core import state_gateway

        state_gateway.set_active_subset_indices(
            set(indices) if indices else None
        )
        return {"active_subset_size": len(indices) if indices else 0}

    def clear_subset(self):
        from core import state_gateway

        state_gateway.set_active_subset_indices(None)
        return {"cleared": True}
