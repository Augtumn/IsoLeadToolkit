"""Copying the matplotlib toolbar must not produce an empty button."""
from __future__ import annotations

import pytest

pytest.importorskip("PyQt5")

from PyQt5.QtGui import QIcon  # noqa: E402
from PyQt5.QtWidgets import QAction, QApplication, QToolBar, QToolButton  # noqa: E402

from ui.main_window_parts.canvas import copy_toolbar_actions, is_blank_action  # noqa: E402

_APP = QApplication.instance() or QApplication([])
_ICON = QIcon.fromTheme("document-save")  # any icon object; may be null in offscreen


def _action(text="", tooltip="", icon=None, parent=None):
    # The parent matters: an unparented QAction passed to addAction() can be
    # collected by Python and vanish from the toolbar.
    action = QAction(text, parent)
    action.setToolTip(tooltip)
    if icon is not None:
        action.setIcon(icon)
    return action


def _toolbar(*specs):
    """A toolbar owning its actions, plus the actions for later assertions."""
    bar = QToolBar()
    actions = []
    for text, tooltip in specs:
        action = _action(text, tooltip, parent=bar)
        bar.addAction(action)
        actions.append(action)
    return bar, actions


def test_a_placeholder_action_is_recognised_as_blank() -> None:
    assert is_blank_action(_action()) is True


def test_an_action_with_a_tooltip_is_not_blank() -> None:
    assert is_blank_action(_action(tooltip="Something")) is False


def test_a_separator_is_not_a_blank_action() -> None:
    source = QToolBar()
    source.addSeparator()
    assert is_blank_action(source.actions()[0]) is False


def test_copying_skips_blank_actions() -> None:
    source, _actions = _toolbar(("Home", "Reset original view"), ("Save", "Save the figure"))
    source.addAction(_action(parent=source))  # the placeholder
    target = QToolBar()

    copy_toolbar_actions(source, target)

    assert [a.text() for a in target.actions()] == ["Home", "Save"]


def test_no_blank_widget_appears_on_the_target() -> None:
    source, _actions = _toolbar(("Home", "Reset original view"))
    source.addAction(_action(parent=source))
    target = QToolBar()

    copy_toolbar_actions(source, target)

    for action in target.actions():
        widget = target.widgetForAction(action)
        assert not (
            isinstance(widget, QToolButton)
            and action.icon().isNull()
            and not action.text().strip()
        ), "an empty button reached the toolbar"


def test_separators_are_recreated_on_the_target() -> None:
    source, _actions = _toolbar(("Home", "Reset original view"), ("Save", "Save the figure"))
    source.insertSeparator(_actions[1])
    target = QToolBar()

    copy_toolbar_actions(source, target)

    assert [a.isSeparator() for a in target.actions()] == [False, True, False]


def test_matplotlib_tooltips_are_translated() -> None:
    source, _actions = _toolbar(("Zoom", "Zoom to rectangle"))
    target = QToolBar()

    copy_toolbar_actions(source, target)

    from core import translate

    assert target.actions()[0].toolTip() == translate("Zoom to rectangle")


def test_the_customize_tooltip_is_translated() -> None:
    """The Customize action's own tooltip is English; the toolbar translates it."""
    source, _actions = _toolbar(("Customize", "Edit axis, curve and image parameters"))
    target = QToolBar()

    copy_toolbar_actions(source, target)

    from core import translate

    assert target.actions()[0].toolTip() == translate("Edit axis, curve and image parameters")
    assert target.actions()[0].toolTip() != "Edit axis, curve and image parameters", "untranslated"
