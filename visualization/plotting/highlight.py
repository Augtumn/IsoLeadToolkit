"""Hover highlight: the point under the cursor is drawn slightly larger.

A small state object so the hover handler can ask "did anything change?" and only then
redraw - the base sizes are cached per collection and restored when the cursor leaves.

The identity used for highlighting is the **sample index** - the row of the data - not the
position inside one scatter collection. That is what lets several panels show the same
sample at once: the cursor sits in one panel, the sample is resolved there, and every panel
that draws that sample highlights its own artist. A sample may appear in no panel, in one,
or in all of them.
"""
from __future__ import annotations

import logging
import weakref
from typing import Any, Iterable

#: How much larger the hovered point is drawn.
HOVER_SCALE = 1.6

#: Points of outline added to the highlighted point, and the least it is given - a marker whose
#: outline is thin or absent still shows one.
HIGHLIGHT_EXTRA_WIDTH = 1.6
HIGHLIGHT_MIN_WIDTH = 2.2

logger = logging.getLogger(__name__)

#: One place a sample is drawn: the scatter collection and the position inside it.
HighlightTarget = tuple[Any, int]


class HoverHighlighter:
    """Remembers the base sizes of every scatter collection it has highlighted."""

    def __init__(self, scale: float = HOVER_SCALE) -> None:
        self._scale = scale
        # Keyed by the collection itself, weakly. Keying by id() needed a strong reference beside each id to keep
        # the number from being reused, and that reference kept every collection a re-render detached - and its data
        # arrays - alive for the life of the application: fifty renders, fifty kept collections, proven.
        self._base_sizes: "weakref.WeakKeyDictionary[Any, list[float]]" = weakref.WeakKeyDictionary()
        self._base_widths: "weakref.WeakKeyDictionary[Any, list[float]]" = weakref.WeakKeyDictionary()
        self._highlighted: list[HighlightTarget] = []
        self._sample: int | None = None

    def _base_for(self, collection: Any) -> list[float]:
        if collection not in self._base_sizes:
            sizes = collection.get_sizes()
            self._base_sizes[collection] = [float(size) for size in sizes] if sizes is not None and len(sizes) else []
        return self._base_sizes[collection]

    def _base_widths_for(self, collection: Any) -> list[float]:
        """The outline widths a collection had before anything highlighted it."""
        if collection not in self._base_widths:
            try:
                widths = collection.get_linewidths()
            except Exception:
                widths = None
            count = len(self._base_for(collection))
            if widths is None or len(widths) == 0:
                self._base_widths[collection] = [1.0] * count
            elif len(widths) == 1 and count > 1:
                self._base_widths[collection] = [float(widths[0])] * count
            else:
                self._base_widths[collection] = [float(width) for width in widths]
        return self._base_widths[collection]

    def highlighted_widths(self, collection: Any, index: int) -> list[float] | None:
        """The outline widths with *index* emphasised - the thicker edge of the highlight."""
        base = self._base_widths_for(collection)
        if not base or not 0 <= index < len(base):
            return None
        widths = list(base)
        widths[index] = max(widths[index] + HIGHLIGHT_EXTRA_WIDTH, HIGHLIGHT_MIN_WIDTH)
        return widths

    def highlighted_sizes(self, collection: Any, index: int) -> list[float] | None:
        """The size array with *index* enlarged, or None when that is not possible."""
        base = self._base_for(collection)
        if not base or not 0 <= index < len(base):
            return None
        sizes = list(base)
        sizes[index] = sizes[index] * self._scale
        return sizes

    def _usable(self, targets: Iterable[HighlightTarget]) -> list[tuple[Any, int, list[float]]]:
        """The targets that can actually be enlarged, with the sizes to apply."""
        usable: list[tuple[Any, int, list[float]]] = []
        for collection, index in targets:
            if collection is None:
                continue
            sizes = self.highlighted_sizes(collection, int(index))
            if sizes is not None:
                usable.append((collection, int(index), sizes))
        return usable

    def highlight_sample(self, sample: int | None, targets: Iterable[HighlightTarget]) -> bool:
        """Highlight one sample everywhere it is drawn; True when a redraw is needed.

        *targets* is one ``(collection, index)`` pair per panel that draws the sample. A
        sample that no panel draws clears the highlight rather than leaving a stale one.
        """
        if sample is None:
            return self.clear()
        usable = self._usable(targets)
        if not usable:
            return self.clear()
        state = [(collection, index) for collection, index, _sizes in usable]
        if int(sample) == self._sample and state == self._highlighted:
            return False
        self.clear(restore=True)
        for collection, index, sizes in usable:
            collection.set_sizes(sizes)
            widths = self.highlighted_widths(collection, index)
            if widths is not None:
                try:
                    collection.set_linewidths(widths)
                except Exception as err:
                    logger.warning("Could not thicken the highlight outline: %s", err)
        self._highlighted = state
        self._sample = int(sample)
        return True

    def highlight(self, collection: Any, index: int) -> bool:
        """Highlight one point in one collection (the single-panel case)."""
        return self.highlight_sample(index, [(collection, index)])

    def clear(self, restore: bool = True) -> bool:
        """Drop every highlight; returns True when something had been highlighted."""
        if not self._highlighted:
            self._sample = None
            return False
        highlighted = list(self._highlighted)
        self._highlighted = []
        self._sample = None
        if restore:
            for collection, _index in highlighted:
                base = self._base_sizes.get(collection)
                if base:
                    collection.set_sizes(list(base))
                widths = self._base_widths.get(collection)
                if widths:
                    try:
                        collection.set_linewidths(list(widths))
                    except Exception as err:
                        logger.warning("Could not restore the outline widths: %s", err)
        return True

    @property
    def current(self) -> HighlightTarget | None:
        """The highlighted ``(collection, index)`` of the first panel, if any."""
        return self._highlighted[0] if self._highlighted else None

    @property
    def current_sample(self) -> int | None:
        """The sample index currently highlighted, if any."""
        return self._sample
