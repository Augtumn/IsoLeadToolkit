"""Application use case for geochemistry preset/parameter access.

UI panels must not import ``data.geochemistry`` directly (layer rule:
ui → application use case → data). This facade exposes only the engine
operations the panels need: listing available presets, reading current
parameters, and loading a preset. The heavy geochemistry module is
lazy-imported so importing this module never pulls in numpy-heavy deps.
"""

from __future__ import annotations

from typing import Any

_engine = None


def _get_engine() -> Any:
    """Lazy-load the geochemistry engine singleton.

    Raises:
        ImportError: ``data.geochemistry`` is part of this project and a declared dependency
            chain (numpy/scipy), so a failed import means a broken installation - reported,
            never turned into "no models available".
    """
    global _engine
    if _engine is None:
        from data.geochemistry import engine as _engine_impl

        _engine = _engine_impl
    return _engine


def get_available_models() -> list[str]:
    """Return the available geochemistry preset model names."""
    return _get_engine().get_available_models()


def get_parameters() -> dict[str, Any]:
    """Return the current geochemistry model parameters."""
    return _get_engine().get_parameters()


def get_current_model_name() -> str:
    """Return the name of the currently loaded geochemistry preset."""
    return str(_get_engine().current_model_name or "")


def update_parameters(params: dict[str, Any]) -> None:
    """Apply parameter updates to the current geochemistry model.

    Raises:
        ValueError: a supplied value is not numeric for its parameter.
    """
    _get_engine().update_parameters(params)


def load_preset(model_name: str) -> bool:
    """Load a named preset into the engine.

    Returns:
        False when the engine does not know the preset; the caller shows that to the user.

    Raises:
        Exception: whatever the engine raises for a preset it knows but cannot apply.
    """
    return bool(_get_engine().load_preset(model_name))
