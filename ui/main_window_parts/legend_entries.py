"""Legend UI actions for main window."""
from __future__ import annotations

import logging
from typing import Any

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QColor, QCursor
from PyQt5.QtWidgets import (
    QAction,
    QCheckBox,
    QColorDialog,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from core import app_state, state_gateway, translate
from ui.icons import apply_color_swatch
from visualization.line_styles import resolve_line_style
from visualization.plotting.legend_model import OVERLAY_TOGGLE_MAP

logger = logging.getLogger(__name__)


def reorder_legend_keys(
    order_keys: list[str],
    src_full: str,
    target_full: str,
    below: bool,
) -> list[str]:
    """Return the reordered ``legend_item_order`` list after a drag.

    *src_full* is moved to the position of *target_full* (before it, or
    after it when *below*). Rows are identified by their full
    ``type:key`` order keys. No-op when either key is unknown.
    """
    order = list(order_keys)
    if src_full not in order or target_full not in order or src_full == target_full:
        return order
    order.remove(src_full)
    idx = order.index(target_full)
    if below:
        idx += 1
    order.insert(idx, src_full)
    return order

def build_legend_display_entries(
    entries: list[dict[str, Any]],
    top_parents: list[str],
    child_parent: dict[str, str],
    parent_names: set[str],
    order_index: dict[str, int],
) -> list[dict[str, Any]]:
    """Build the ordered legend display list with (possibly nested) parent blocks.

    Every visual unit participates in one unified ordering: a TOP-LEVEL parent
    block (its rows expanded recursively, children may themselves be parent
    groups at deeper indentation), an independent group, or an overlay. Units
    sort by their own ``legend_item_order`` position, so independent groups
    may be dragged above parent blocks. Children inside a block keep their
    own relative order.

    Args:
        entries: sorted group/overlay entries (groups carry "group" key).
        top_parents: top-level parent names (not nested inside another parent).
        child_parent: direct child name -> direct parent name (all levels).
        parent_names: set of ALL parent names (nested included).
        order_index: legend_item_order lookup.
    """
    if not top_parents:
        return list(entries)

    by_parent: dict[str, list[str]] = {}
    for child, parent in child_parent.items():
        by_parent.setdefault(parent, []).append(child)

    def _block(parent: str, depth: int) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = [
            {"type": "parent", "key": parent, "parent": parent, "depth": depth}
        ]
        children = sorted(
            by_parent.get(parent, []),
            key=lambda c: order_index.get(f"group:{c}", 10_000),
        )
        for child in children:
            if child in parent_names:
                out.extend(_block(child, depth + 1))
            else:
                out.append(
                    {
                        "type": "group",
                        "key": child,
                        "group": child,
                        "in_parent": parent,
                        "depth": depth + 1,
                    }
                )
        return out

    # Unified sort units: (order_index, unit_kind, payload).
    units: list[tuple[int, str, Any]] = []
    for parent in top_parents:
        units.append((order_index.get(f"parent:{parent}", 10_000), "parent", parent))
    for entry in entries:
        if entry["type"] == "group" and entry["group"] not in child_parent:
            units.append((order_index.get(f"group:{entry['group']}", 10_000), "group", entry))
        elif entry["type"] == "overlay":
            units.append((order_index.get(f"overlay:{entry['key']}", 10_000), "overlay", entry))

    # Stable sort: units with equal order keep their construction order.
    units.sort(key=lambda unit: unit[0])

    display_entries: list[dict[str, Any]] = []
    for _, unit_kind, payload in units:
        if unit_kind == "parent":
            display_entries.extend(_block(payload, 0))
        else:
            display_entries.append(payload)
    return display_entries
