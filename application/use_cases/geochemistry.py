"""Application use case for geochemistry preset/parameter access.

UI panels must not import ``data.geochemistry`` directly (layer rule:
ui → application use case → data). This facade exposes only the engine
operations the panels need: listing available presets, reading current
parameters, and loading a preset. The heavy geochemistry module is
lazy-imported so importing this module never pulls in numpy-heavy deps.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_engine = None
_engine_checked = False


def _get_engine() -> Any | None:
    """Lazy-load the geochemistry engine singleton."""
    global _engine, _engine_checked
    if _engine_checked:
        return _engine
    _engine_checked = True
    try:
        from data.geochemistry import engine as _engine_impl

        _engine = _engine_impl
    except ImportError as err:
        logger.warning("Geochemistry engine unavailable: %s", err)
        _engine = None
    return _engine


def get_available_models() -> list[str]:
    """Return the available geochemistry preset model names."""
    engine_impl = _get_engine()
    if engine_impl is None:
        return []
    return engine_impl.get_available_models()


def get_parameters() -> dict[str, Any]:
    """Return the current geochemistry model parameters."""
    engine_impl = _get_engine()
    if engine_impl is None:
        return {}
    return engine_impl.get_parameters()


def get_current_model_name() -> str:
    """Return the name of the currently loaded geochemistry preset."""
    engine_impl = _get_engine()
    if engine_impl is None:
        return ""
    return str(getattr(engine_impl, "current_model_name", "") or "")


def update_parameters(params: dict[str, Any]) -> None:
    """Apply parameter updates to the current geochemistry model."""
    engine_impl = _get_engine()
    if engine_impl is None:
        return
    try:
        engine_impl.update_parameters(params)
    except Exception as err:
        logger.warning("Failed to update geochemistry parameters: %s", err)


def load_preset(model_name: str) -> bool:
    """Load a named preset into the engine. Returns False on failure."""
    engine_impl = _get_engine()
    if engine_impl is None:
        return False
    try:
        return bool(engine_impl.load_preset(model_name))
    except Exception as err:
        logger.warning("Failed to load geochemistry preset %r: %s", model_name, err)
        return False
