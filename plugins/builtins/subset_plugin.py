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
