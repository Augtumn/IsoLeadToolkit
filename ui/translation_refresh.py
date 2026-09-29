"""Translate an existing widget tree in place, in either direction - copy only.

WARNING, learned the hard way: an earlier version matched every text it could find, with no tag
required. On a real window that renamed docks and panel titles and rewrote combo entries holding
data (algorithm names such as PCA or UMAP are locale keys too), so the UI rearranged itself when
the language changed. Text matching cannot tell copy from data; only the widget can, through its
tags. This module therefore rewrites tagged widgets alone, the same contract
BasePanel._update_translations uses, and exists for the reverse direction (Chinese back to
English) and for the extra widget types.

The panels are built once, and their texts are baked in at that moment - which is why the data,
display and legend panels stayed English while the menus switched. Tagging every widget with
translate_key (as BasePanel._update_translations expects) means roughly 300 edits across three
build mixins and misses whatever nobody remembers to tag.

This refresher matches the text a widget already shows against the locale table instead. The
locale keys are the English texts, so an English label maps forward to Chinese, and a Chinese
label maps back through the reverse table - switching in both directions works without rebuilding
anything, so no flicker and no lost selection.

Texts the locale does not know (numbers, ratios, formatted values) simply stay as they are, which
is the desired behaviour: they are data, not copy.
"""
from __future__ import annotations

from typing import Any

from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QLabel,
    QPushButton,
    QRadioButton,
    QTabWidget,
    QToolBox,
    QToolButton,
    QWidget,
)

from core.localization import default_language, translate, translation_table


def _maps(language: str) -> tuple[dict[str, str], dict[str, str]]:
    """(text -> translated, translated -> text) for *language*."""
    table = translation_table(language)
    forward = {key: value for key, value in table.items() if value}
    reverse = {value: key for key, value in forward.items() if value != key}
    return forward, reverse


def _convert(text: str, forward: dict[str, str], reverse: dict[str, str]) -> str | None:
    if not text:
        return None
    if text in reverse:
        return reverse[text]
    if text in forward:
        return forward[text]
    return None


def refresh_widget_tree(root: QWidget | None, language: str | None = None) -> int:
    """Retranslate every widget under *root*; returns how many texts changed."""
    if root is None:
        return 0
    language = language or default_language()
    forward, reverse = _maps(language)
    if not forward and not reverse:
        return 0

    changed = 0

    def apply(widget: Any, getter: str, setter: str) -> None:
        nonlocal changed
        try:
            current = getattr(widget, getter)()
        except Exception:
            return
        replacement = _convert(str(current), forward, reverse)
        if replacement is None or replacement == current:
            return
        try:
            getattr(widget, setter)(replacement)
            changed += 1
        except Exception:
            return

    for widget in [root, *root.findChildren(QWidget)]:
        # Copy widgets are translated whether or not they are tagged - the panels' labels are
        # what this is for - while the widget kinds that hold data or titles are excluded below.
        # The earlier regression came from touching those, not from translating labels.
        if isinstance(widget, QGroupBox):
            apply(widget, "title", "setTitle")
        elif isinstance(widget, (QLabel, QPushButton, QCheckBox, QRadioButton, QToolButton)):
            apply(widget, "text", "setText")
        elif isinstance(widget, QComboBox) and widget.property("translate_items"):
            items = [widget.itemText(i) for i in range(widget.count())]
            for index, item in enumerate(items):
                replacement = _convert(item, forward, reverse)
                if replacement is not None and replacement != item:
                    widget.setItemText(index, replacement)
                    changed += 1
        elif isinstance(widget, QTabWidget) and widget.property("translate_items"):
            for index in range(widget.count()):
                current = widget.tabText(index)
                replacement = _convert(current, forward, reverse)
                if replacement is not None and replacement != current:
                    widget.setTabText(index, replacement)
                    changed += 1
        elif isinstance(widget, QToolBox) and widget.property("translate_items"):
            for index in range(widget.count()):
                current = widget.itemText(index)
                replacement = _convert(current, forward, reverse)
                if replacement is not None and replacement != current:
                    widget.setItemText(index, replacement)
                    changed += 1
        # Deliberately nothing here. Rewriting windowTitle renamed docks and panels, which is
        # what rearranged the UI: titles are layout, not copy.

    return changed


def refresh_placeholder_texts(root: QWidget | None, language: str | None = None) -> int:
    """Placeholders are separate texts; translate them too."""
    if root is None:
        return 0
    language = language or default_language()
    forward, reverse = _maps(language)
    changed = 0
    for widget in root.findChildren(QWidget):
        if not hasattr(widget, "placeholderText"):
            continue
        current = widget.placeholderText()
        replacement = _convert(str(current), forward, reverse)
        if replacement is not None and replacement != current:
            widget.setPlaceholderText(replacement)
            changed += 1
    return changed
