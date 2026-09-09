"""Plugin manager tests: discovery, namespaced loading, reserved names."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

import plugins.manager as manager_module
from plugins.api import PluginLoadError
from plugins.manager import PluginManager

_PLUGIN_SOURCE = '''
"""Temp user plugin used by tests."""
from typing import Any

from plugins.api import BasePlugin, PluginMeta


class TempPlugin(BasePlugin):
    meta = PluginMeta(
        name="temp_user_plugin",
        version="0.1",
        api_version="1.0",
        plugin_type="analysis",
        source="user",
    )

    def validate_environment(self) -> tuple[bool, str]:
        return True, "ok"

    def get_default_params(self) -> dict[str, Any]:
        return {"k": 1}

    def build_ui(self, parent=None, callback=None):
        return None
'''

_BUILTIN_STEMS = {
    "clustering_plugin",
    "endmember_plugin",
    "mixing_plugin",
    "neighborhood_plugin",
    "provenance_ml_plugin",
    "subset_plugin",
}


def test_discover_finds_builtins() -> None:
    names = PluginManager().discover()
    assert _BUILTIN_STEMS <= set(names)
    assert "__init__" not in names


def test_load_builtin_plugin_and_registry() -> None:
    manager = PluginManager()
    plugin = manager.load_plugin("subset_plugin")

    assert manager.is_loaded("subset_plugin") is True
    assert manager.get("subset_plugin") is plugin
    assert manager.get("subset_analysis") is plugin  # meta.name lookup
    assert manager.get_meta("subset_plugin").plugin_type == "analysis"

    status = manager.get_status()
    assert status["loaded"]["subset_plugin"]["source"] == "builtin"

    assert manager.unload_plugin("subset_plugin") is True
    assert manager.is_loaded("subset_plugin") is False
    assert manager.unload_plugin("subset_plugin") is False


def test_reload_plugin_returns_fresh_instance() -> None:
    manager = PluginManager()
    first = manager.load_plugin("subset_plugin")
    second = manager.reload_plugin("subset_plugin")
    assert second is not first
    assert manager.is_loaded("subset_plugin") is True


def test_unknown_plugin_raises() -> None:
    manager = PluginManager()
    with pytest.raises(PluginLoadError, match="not found"):
        manager.load_plugin("does_not_exist_plugin")
    assert manager.available == []


@pytest.mark.parametrize("name", sorted(PluginManager.RESERVED_NAMES))
def test_reserved_names_rejected(name: str) -> None:
    manager = PluginManager()
    with pytest.raises(PluginLoadError, match="reserved"):
        manager.load_plugin(name)
    assert manager.is_loaded(name) is False


def test_user_plugin_loaded_under_private_namespace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "temp_user_plugin.py").write_text(_PLUGIN_SOURCE, encoding="utf-8")
    monkeypatch.setattr(manager_module, "_USER_PLUGIN_DIR", tmp_path)

    import plugins.api as real_api

    manager = PluginManager()
    try:
        plugin = manager.load_plugin("temp_user_plugin")
        assert plugin.meta.source == "user"
        assert plugin.get_default_params() == {"k": 1}
        # Namespaced module name keeps the real plugins.* modules intact.
        assert "plugins._loaded.temp_user_plugin" in sys.modules
        assert "plugins.temp_user_plugin" not in sys.modules
        assert sys.modules["plugins.api"] is real_api
    finally:
        sys.modules.pop("plugins._loaded.temp_user_plugin", None)


def test_user_file_named_api_cannot_shadow_real_module(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "api.py").write_text(
        "raise RuntimeError('must never be imported')", encoding="utf-8"
    )
    monkeypatch.setattr(manager_module, "_USER_PLUGIN_DIR", tmp_path)

    import plugins.api as real_api

    manager = PluginManager()
    with pytest.raises(PluginLoadError, match="reserved"):
        manager.load_plugin("api")
    assert sys.modules["plugins.api"] is real_api


def test_load_all_skips_reserved_and_broken_plugins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "api.py").write_text(
        "raise RuntimeError('must never be imported')", encoding="utf-8"
    )
    (tmp_path / "broken_plugin.py").write_text(
        "raise RuntimeError('boom')", encoding="utf-8"
    )
    monkeypatch.setattr(manager_module, "_USER_PLUGIN_DIR", tmp_path)

    manager = PluginManager()
    loaded = manager.load_all()
    assert "api" not in loaded
    assert "broken_plugin" not in loaded
    assert "boom" in (manager.failure_info("broken_plugin") or "")
    # Builtins are discovered and loaded alongside user plugins.
    assert _BUILTIN_STEMS <= set(manager.available)
