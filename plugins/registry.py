"""Global plugin registry — shared PluginManager singleton."""
from __future__ import annotations

from .manager import PluginManager

plugin_manager = PluginManager()
