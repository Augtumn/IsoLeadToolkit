"""Which adapter draws which mode.

The dispatch was a chain of ``if``/``elif`` in the application layer, ending in an ``else`` that handed
whatever it was given to the embedding renderer as an algorithm name - so a mode that no renderer knew
still reached one, and the mistake surfaced deep inside a computation as "Unknown algorithm". Here a
mode either has an adapter or it does not, registering one is checked against the list of modes the
application offers, and asking for one that is not there is an error rather than a guess.
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from core.render_modes import RENDER_MODE_VALUES

from .context import RenderContext


class UnknownRenderMode(LookupError):
    """Raised when a mode has no adapter, so nothing can be drawn for it."""

    def __init__(self, mode: object) -> None:
        self.mode = str(mode)
        offered = ", ".join(registered_modes()) or "none yet"
        super().__init__(
            f"no adapter for render mode {self.mode!r}; registered: {offered}"
        )


class DuplicateAdapter(ValueError):
    """Raised when two adapters claim the same mode."""


class NotARenderMode(ValueError):
    """Raised when an adapter claims a mode the application does not offer."""


@runtime_checkable
class ModeAdapter(Protocol):
    """What one plot type contributes to a render.

    The pipeline owns the sequence every render shares; an adapter owns the parts that differ - what
    the plot is made of, what identifies it, what it draws, and how it is named.
    """

    #: The mode this adapter draws, one of ``core.render_modes.RENDER_MODE_VALUES``.
    mode: str

    def validate(self, context: RenderContext) -> None:
        """Refuse a render this mode cannot do, before anything is cleared."""

    def token(self, context: RenderContext) -> Any:
        """What identifies the picture, beyond the context's own token."""

    def axes_dimensions(self, context: RenderContext) -> Any:
        """The axes this mode draws into, as ``core.ensure_axes`` takes it."""

    def draw(self, context: RenderContext) -> None:
        """Draw the plot itself."""

    def legend(self, context: RenderContext) -> None:
        """Draw the legend for this plot."""

    def title(self, context: RenderContext) -> None:
        """Name the plot and label its axes."""


#: The adapters, by the mode they draw.
_ADAPTERS: dict[str, ModeAdapter] = {}


def register(adapter: ModeAdapter) -> ModeAdapter:
    """Add *adapter* to the table, refusing a duplicate or a mode that is not offered."""
    mode = str(getattr(adapter, "mode", "") or "")
    if mode not in RENDER_MODE_VALUES:
        raise NotARenderMode(
            f"{mode!r} is not a render mode; the modes are {', '.join(RENDER_MODE_VALUES)}"
        )
    if mode in _ADAPTERS:
        raise DuplicateAdapter(f"an adapter for {mode!r} is already registered")
    _ADAPTERS[mode] = adapter
    return adapter


def adapter_for(mode: object) -> ModeAdapter:
    """The adapter for *mode*, or :class:`UnknownRenderMode`."""
    try:
        return _ADAPTERS[str(mode)]
    except KeyError:
        raise UnknownRenderMode(mode) from None


def registered_modes() -> tuple[str, ...]:
    """The modes that have an adapter, in the order the application offers them."""
    return tuple(mode for mode in RENDER_MODE_VALUES if mode in _ADAPTERS)


def unregistered_modes() -> tuple[str, ...]:
    """The modes still to be moved onto the pipeline."""
    return tuple(mode for mode in RENDER_MODE_VALUES if mode not in _ADAPTERS)


def clear() -> None:
    """Forget every adapter. For tests, and for a reload that must start from nothing."""
    _ADAPTERS.clear()
