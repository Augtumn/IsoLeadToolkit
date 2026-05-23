"""Plugin manager — discovery, loading, validation, lifecycle."""
from __future__ import annotations

import importlib
import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any

from .api import (
    BasePlugin, PluginError, PluginLoadError, PluginMeta, PluginValidationError,
)

logger = logging.getLogger(__name__)

_BUILTIN_DIR = Path(__file__).resolve().parent / "builtins"
_USER_PLUGIN_DIR = Path.home() / ".isotopes_analysis" / "plugins"


class PluginManager:
    """Discover, load, validate, and manage plugins."""

    def __init__(self) -> None:
        self._plugins: dict[str, BasePlugin] = {}
        self._meta: dict[str, PluginMeta] = {}
        self._failed: dict[str, str] = {}  # name → error message

    # ── discovery ──────────────────────────────────────────────────
    def discover(self) -> list[str]:
        """Scan plugin directories and return list of discovered names."""
        found: list[str] = []
        for directory in (_BUILTIN_DIR, _USER_PLUGIN_DIR):
            if not directory.exists():
                continue
            for entry in directory.iterdir():
                if entry.is_dir() and (entry / "__init__.py").exists():
                    found.append(entry.name)
                elif entry.suffix == ".py" and entry.stem != "__init__":
                    found.append(entry.stem)
        return sorted(set(found))

    @property
    def plugins(self) -> dict[str, BasePlugin]:
        return dict(self._plugins)

    @property
    def available(self) -> list[str]:
        return list(self._plugins.keys())

    def is_loaded(self, name: str) -> bool:
        return name in self._plugins

    def get(self, name: str) -> BasePlugin | None:
        # Check direct registration first (by file stem)
        plugin = self._plugins.get(name)
        if plugin is not None:
            return plugin
        # Fall back to meta.name lookup
        for key, meta in self._meta.items():
            if meta.name == name:
                return self._plugins.get(key)
        return None

    def get_meta(self, name: str) -> PluginMeta | None:
        return self._meta.get(name)

    def failure_info(self, name: str) -> str | None:
        return self._failed.get(name)

    # ── loading ────────────────────────────────────────────────────
    def load_plugin(self, name: str) -> BasePlugin:
        """Load a single plugin by name. Raises PluginLoadError on failure."""
        if name in self._plugins:
            return self._plugins[name]

        module_path = self._resolve_module(name)
        if module_path is None:
            raise PluginLoadError(f"Plugin '{name}' not found in search paths.")

        try:
            spec = importlib.util.spec_from_file_location(
                f"plugins.{name}", module_path
            )
            if spec is None or spec.loader is None:
                raise PluginLoadError(f"Cannot create spec for plugin '{name}'")
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
        except Exception as exc:
            self._failed[name] = str(exc)
            raise PluginLoadError(f"Failed to load plugin '{name}': {exc}") from exc

        plugin = self._extract_plugin(module, name)
        if plugin is None:
            raise PluginLoadError(f"No plugin class found in module '{name}'")

        ok, msg = plugin.validate_environment()
        if not ok:
            self._failed[name] = msg
            raise PluginValidationError(f"Plugin '{name}' validation failed: {msg}")

        self._plugins[name] = plugin
        self._meta[name] = plugin.meta
        logger.info("Plugin loaded: %s v%s (%s)", name, plugin.meta.version, plugin.meta.plugin_type)
        return plugin

    def load_all(self) -> dict[str, BasePlugin]:
        """Discover and load all available plugins."""
        for name in self.discover():
            try:
                self.load_plugin(name)
            except PluginError as exc:
                logger.warning("Skipping plugin '%s': %s", name, exc)
        return dict(self._plugins)

    # ── helpers ────────────────────────────────────────────────────
    def _resolve_module(self, name: str) -> Path | None:
        for directory in (_BUILTIN_DIR, _USER_PLUGIN_DIR):
            candidates = [
                directory / name / "__init__.py",
                directory / f"{name}.py",
            ]
            for candidate in candidates:
                if candidate.exists():
                    return candidate
        return None

    @staticmethod
    def _extract_plugin(module: Any, name: str) -> BasePlugin | None:
        for attr_name in dir(module):
            obj = getattr(module, attr_name)
            if not isinstance(obj, type):
                continue
            if obj is BasePlugin:
                continue
            try:
                if issubclass(obj, BasePlugin):
                    return obj()
            except TypeError:
                # Protocols with non-method members (e.g. meta) fail
                # issubclass() in Python ≥3.12. Fall back to duck-typing.
                if hasattr(obj, "meta") and hasattr(obj, "validate_environment"):
                    return obj()
        return None
