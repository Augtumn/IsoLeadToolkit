"""Declared widget defaults: a table per panel, one reset for all of them.

Panels set their widget attributes back to None one assignment per line in reset_state, which hides the set and can
forget a member. The set is a declaration now - a table naming every widget and its fallback - and this is the one
function that applies it. Mutable defaults are given as factories (dict, list), so every reset hands out a fresh
object; a shared literal in the table is the bug these declarations replaced.
"""
from __future__ import annotations


def reset_widget_state(owner: object, defaults: dict[str, object]) -> None:
    """Set every widget declared in *defaults* back to its default on *owner*."""
    for name, default in defaults.items():
        setattr(owner, name, default() if callable(default) else default)
