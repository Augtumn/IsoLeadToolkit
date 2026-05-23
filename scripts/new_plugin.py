#!/usr/bin/env python3
"""Generate a new plugin skeleton."""
import sys
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/new_plugin.py <plugin_name>")
        return 1
    
    name = sys.argv[1]
    plugin_dir = Path.home() / ".isotopes_analysis" / "plugins"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    
    plugin_file = plugin_dir / f"{name}.py"
    if plugin_file.exists():
        print(f"Plugin '{name}' already exists at {plugin_file}")
        return 1
    
    template = f'''"""Plugin: {name}"""
from __future__ import annotations
from typing import Any
from plugins.api import BasePlugin, PluginMeta

class {name.title().replace("_", "")}Plugin(BasePlugin):
    meta = PluginMeta(
        name="{name}", version="0.1", api_version="1.0",
        plugin_type="analysis", author="Your Name",
        description="Describe your plugin",
        source="user",
    )
    
    def validate_environment(self) -> tuple[bool, str]:
        return True, "ok"
    
    def get_default_params(self) -> dict[str, Any]:
        return {{}}
    
    def run(self, *args, **kwargs):
        return {{"status": "ok"}}
'''
    plugin_file.write_text(template)
    print(f"Plugin created: {plugin_file}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
