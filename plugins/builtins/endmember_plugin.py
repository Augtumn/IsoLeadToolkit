"""Builtin endmember identification plugin."""
from __future__ import annotations
from typing import Any

from plugins.api import BasePlugin, PluginMeta
from data.endmember import compute_geochron_slope, run_endmember_analysis


class EndmemberPlugin(BasePlugin):
    meta = PluginMeta(
        name="endmember",
        version="1.0",
        api_version="1.0",
        plugin_type="analysis",
        author="IsotopesAnalyse",
        description="PCA-based endmember identification with geochron filtering",
    )

    def validate_environment(self) -> tuple[bool, str]:
        return True, "ok"

    def get_default_params(self) -> dict[str, Any]:
        return {"tolerance": (0.01, 0.01)}

    def run(self, df, col_206, col_207, col_208, **kwargs):
        return run_endmember_analysis(df, col_206, col_207, col_208, **kwargs)
