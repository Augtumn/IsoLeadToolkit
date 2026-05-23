"""Builtin mixing model plugin."""
from __future__ import annotations
from typing import Any

from plugins.api import BasePlugin, PluginMeta
from data.mixing import calculate_mixing, calculate_mixing_with_uncertainty


class MixingModelPlugin(BasePlugin):
    meta = PluginMeta(
        name="mixing",
        version="1.0",
        api_version="1.0",
        plugin_type="analysis",
        author="IsotopesAnalyse",
        description="Endmember mixing proportion solver with Monte Carlo uncertainty",
    )

    def validate_environment(self) -> tuple[bool, str]:
        return True, "ok"

    def get_default_params(self) -> dict[str, Any]:
        return {}

    def calculate(self, df, endmember_groups, mixture_groups, columns, **kwargs):
        return calculate_mixing(df, endmember_groups, mixture_groups, columns)

    def calculate_with_uncertainty(self, df, endmember_groups, mixture_groups, columns, **kwargs):
        return calculate_mixing_with_uncertainty(
            df, endmember_groups, mixture_groups, columns, **kwargs
        )
