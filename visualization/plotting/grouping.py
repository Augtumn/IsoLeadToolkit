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
    """Return the direct parent group name for *group*, or None if unassigned.

    A parent group can itself be a child of another parent (nested levels);
    the direct parent is the innermost container.
    """
    parents = getattr(state, "parent_groups", None) or {}
    for parent, children in parents.items():
        if group in children:
            return parent
    return None


def is_parent(state: Any, name: Any) -> bool:
    """True when *name* is itself a parent group (internal tree node)."""
    return str(name) in (getattr(state, "parent_groups", None) or {})


def all_parents(state: Any) -> list[str]:
    """Return TOP-LEVEL parent group names in creation order.

    Parents nested inside another parent are not listed here; they render
    inside their ancestor's block.
    """
    parents = getattr(state, "parent_groups", None) or {}
    nested: set[str] = set()
    for children in parents.values():
        for child in children:
            if child in parents:
                nested.add(child)
    return [name for name in parents if name not in nested]


def top_parent_of_group(state: Any, group: Any) -> str | None:
    """Return the TOP-LEVEL parent of *group* (walking nested parents up)."""
    current: Any = group
    seen: set[str] = set()
    while True:
        parent = parent_of_group(state, current)
        if parent is None:
            return None if current == group else str(current)
        if parent in seen:
            return None  # cycle guard (should not happen)
        seen.add(parent)
        current = parent


def descendant_groups(state: Any, parent: str) -> list[str]:
    """Return all data groups nested (at any depth) under *parent*.

    Nested parent names are expanded recursively; their own children are
    included. Order is depth-first following the children lists.
    """
    parents = getattr(state, "parent_groups", None) or {}
    result: list[str] = []
    seen: set[str] = set()

    def _walk(name: str) -> None:
        if name in seen:
            return
        seen.add(name)
        for child in parents.get(name, []) or []:
            if child in parents:
                _walk(child)
            elif child not in result:
                result.append(child)

    _walk(parent)
    return result


def is_descendant(state: Any, candidate: str, ancestor: str) -> bool:
    """True when *candidate* is *ancestor* itself or nested under it."""
    if candidate == ancestor:
        return True
    parents = getattr(state, "parent_groups", None) or {}
    for parent in (ancestor,):
        for child in parents.get(parent, []) or []:
            if child in parents and is_descendant(state, candidate, child):
                return True
            if child == candidate:
                return True
    return False


def parent_shape(state: Any, parent: str) -> str:
    """Return the marker shape assigned to a TOP-LEVEL parent group.

    Nested parents inherit the shape of their top-level ancestor, so all
    groups merged under one root share one shape. A manual override in
    ``parent_shape_map`` wins; otherwise the shape follows the parent
    creation order (dict insertion order).
    """
    root = top_parent_of_group(state, parent) or parent
    overrides = getattr(state, "parent_shape_map", None) or {}
    manual = overrides.get(root)
    if manual:
        return str(manual)
    parents = all_parents(state)
    try:
        idx = parents.index(root)
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
