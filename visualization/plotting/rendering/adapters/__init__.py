"""The mode adapters, and the one place they are put on the registry.

Registering in one function rather than as an import side effect keeps the set of modes that have been
moved onto the pipeline explicit, and calling it twice is harmless: a mode already on the registry is
left alone.
"""
from __future__ import annotations

from .two_d import register_two_d


def register_adapters() -> tuple[str, ...]:
    """Register every adapter that exists, and report the modes that now have one."""
    from ..registry import registered_modes

    for mode, register in (("2D", register_two_d),):
        if mode not in registered_modes():
            register()
    return registered_modes()
