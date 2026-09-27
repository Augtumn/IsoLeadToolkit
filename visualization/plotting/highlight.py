"""Hover highlight: the point under the cursor is drawn slightly larger.

A small state object so the hover handler can ask "did anything change?" and only then
redraw - the base sizes are cached per collection and restored when the cursor leaves.
"""
from __future__ import annotations

from typing import Any

#: How much larger the hovered point is drawn.
HOVER_SCALE = 1.6


class HoverHighlighter:
    """Remembers the base sizes of the scatter collections it has highlighted."""

    def __init__(self, scale: float = HOVER_SCALE) -> None:
        self._scale = scale
        self._base_sizes: dict[int, list[float]] = {}
        self._collections: dict[int, Any] = {}
        self._current: tuple[int, int] | None = None

    def _base_for(self, collection: Any) -> list[float]:
        key = id(collection)
        if key not in self._base_sizes:
            sizes = collection.get_sizes()
            self._base_sizes[key] = [float(size) for size in sizes] if sizes is not None and len(sizes) else []
            self._collections[key] = collection
        return self._base_sizes[key]

    def highlighted_sizes(self, collection: Any, index: int) -> list[float] | None:
        """The size array with *index* enlarged, or None when that is not possible."""
        base = self._base_for(collection)
        if not base or not 0 <= index < len(base):
            return None
        sizes = list(base)
        sizes[index] = sizes[index] * self._scale
        return sizes

    def highlight(self, collection: Any, index: int) -> bool:
        """Highlight one point; returns True when the plot has to be redrawn."""
        if collection is None:
            return self.clear()
        key = (id(collection), index)
        if key == self._current:
            return False
        sizes = self.highlighted_sizes(collection, index)
        if sizes is None:
            return self.clear()
        self.clear(restore=True)
        collection.set_sizes(sizes)
        self._current = key
        return True

    def clear(self, restore: bool = True) -> bool:
        """Drop the highlight; returns True when something had been highlighted."""
        if self._current is None:
            return False
        key, _index = self._current
        self._current = None
        if restore:
            collection = self._collections.get(key)
            base = self._base_sizes.get(key)
            if collection is not None and base:
                collection.set_sizes(list(base))
        return True

    @property
    def current(self) -> tuple[int, int] | None:
        """The highlighted ``(collection id, index)``, if any."""
        return self._current
