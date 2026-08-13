#!/usr/bin/env python3
"""Generate a new plugin skeleton."""
import re
import sys
from pathlib import Path

_PLUGIN_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/new_plugin.py <plugin_name>")
        return 1
    
    name = sys.argv[1]
    if not _PLUGIN_NAME_RE.match(name):
        print(
            f"Invalid plugin name '{name}': must match [a-z][a-z0-9_]* "
            "(lowercase letters, digits, underscores)."
        )
        return 1
    plugin_dir = Path.home() / ".isotopes_analysis" / "plugins"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    
    plugin_file = plugin_dir / f"{name}.py"
    if plugin_file.exists():
        print(f"Plugin '{name}' already exists at {plugin_file}")
        return 1
    
    class_name = "".join(part.capitalize() for part in name.split("_")) + "Plugin"
    
    template = f'''"""Plugin: {name}"""
from __future__ import annotations
from typing import Any
from plugins.api import BasePlugin, PluginMeta

class {class_name}(BasePlugin):
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
    
    def build_ui(self, parent=None, callback=None):
        """Optional: return a QWidget shown in the analysis panel, or None."""
        return None
'''
    plugin_file.write_text(template)
    print(f"Plugin created: {plugin_file}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
