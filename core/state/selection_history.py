"""Undo history for destructive selection operations.

The plot window can delete or clear the selected samples; both lose information, so the
previous selection is kept on a small bounded stack and Ctrl+Z restores it. Deliberately
minimal: only the selection, only the destructive operations, no general command stack.
"""
from __future__ import annotations

from typing import Any, Iterable

#: How many previous selections are kept.
DEFAULT_DEPTH = 20


class SelectionHistory:
    """A bounded stack of previous selections, newest last."""

    def __init__(self, depth: int = DEFAULT_DEPTH) -> None:
        self._depth = max(1, int(depth))
        self._stack: list[list[Any]] = []

    def push(self, indices: Iterable[Any] | None) -> None:
        """Remember *indices* before they are discarded."""
        snapshot = list(indices or [])
        if self._stack and self._stack[-1] == snapshot:
            return
        self._stack.append(snapshot)
        if len(self._stack) > self._depth:
            del self._stack[0]

    def undo(self) -> list[Any] | None:
        """The previous selection, or None when there is nothing to restore."""
        if not self._stack:
            return None
        return self._stack.pop()

    def clear(self) -> None:
        self._stack.clear()

    @property
    def depth(self) -> int:
        return len(self._stack)
