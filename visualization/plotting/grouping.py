"""Parent-group marker resolution helpers.

A parent group merges several existing groups (children) for display: all
children of the same parent share one marker shape (assigned from a fixed
cycle by parent creation order), while each child keeps its own color.
"""
from __future__ import annotations

from typing import Any

# Marker shapes assigned to parent groups in creation order.
PARENT_SHAPE_CYCLE: tuple[str, ...] = ("o", "s", "^", "D", "v", "P", "X", "h", "d", "*")

_DEFAULT_SHAPE = "o"


def parent_of_group(state: Any, group: Any) -> str | None:
    """Return the parent group name for *group*, or None if unassigned."""
    parents = getattr(state, "parent_groups", None) or {}
    for parent, children in parents.items():
        if group in children:
            return parent
    return None


def parent_shape(state: Any, parent: str) -> str:
    """Return the marker shape assigned to a parent group.

    Shapes follow the parent creation order (dict insertion order), which is
    stable across session save/restore because JSON preserves key order.
    """
    parents = list((getattr(state, "parent_groups", None) or {}).keys())
    try:
        idx = parents.index(parent)
    except ValueError:
        idx = 0
    cycle = PARENT_SHAPE_CYCLE or (_DEFAULT_SHAPE,)
    return cycle[idx % len(cycle)]


def resolve_group_marker(state: Any, group: Any) -> str:
    """Resolve the marker shape for a group.

    Children of a parent group always use the parent's shape; independent
    groups keep their per-group marker map entry (or the global default).
    """
    parent = parent_of_group(state, group)
    if parent is not None:
        return parent_shape(state, parent)
    marker_map = getattr(state, "group_marker_map", None) or {}
    return marker_map.get(group, getattr(state, "plot_marker_shape", _DEFAULT_SHAPE))


def parent_children(state: Any, parent: str) -> list[str]:
    """Return the ordered children of *parent* (may include stale names)."""
    parents = getattr(state, "parent_groups", None) or {}
    return list(parents.get(parent, []) or [])


def all_parents(state: Any) -> list[str]:
    """Return parent group names in creation order."""
    return list((getattr(state, "parent_groups", None) or {}).keys())
