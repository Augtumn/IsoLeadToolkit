"""Example plugin — copy this to create your own."""
from __future__ import annotations
from typing import Any
from plugins.api import BasePlugin, PluginMeta

class ExamplePlugin(BasePlugin):
    meta = PluginMeta(
        name="example", version="0.1", api_version="1.0",
        plugin_type="analysis", author="Your Name",
        description="Describe what your plugin does",
        source="user",  # set automatically by PluginManager
    )
    
    def validate_environment(self) -> tuple[bool, str]:
        return True, "ok"
    
    def get_default_params(self) -> dict[str, Any]:
        return {}
    
    def run(self, *args, **kwargs):
        """Your computation here."""
        return {"status": "ok"}
