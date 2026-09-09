"""Data module - Data loading and geochemistry calculations.

Geochemistry symbols are resolved lazily (PEP 562) so importing the loader
does not pull in pandas/scipy-heavy modules.
"""
from .loader import read_data_frame

__all__ = [
    'read_data_frame',
    'geochemistry',
    'calculate_deltas',
    'calculate_v1v2_coordinates',
    'calculate_all_parameters',
    'calculate_single_stage_age',
    'calculate_two_stage_age',
    'engine',
    'GeochemistryEngine',
    'PRESET_MODELS',
]

_GEOCHEM_ATTRS = frozenset(name for name in __all__ if name != 'read_data_frame')


def __getattr__(name: str):
    if name in _GEOCHEM_ATTRS:
        # importlib avoids re-entering __getattr__ (``from . import x``
        # would recurse infinitely while the submodule is not yet bound).
        import importlib

        _geochemistry = importlib.import_module(f"{__name__}.geochemistry")
        if name == 'geochemistry':
            return _geochemistry
        return getattr(_geochemistry, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals().keys()) | set(__all__))
