"""Choosing how many figures the window shows and what each draws.

The dialog is driven directly, so no window and no render are needed. What is checked is that it
offers every mode the application has - the list is shared with the projection control, so a mode
added there appears here - that one panel means the ordinary window, that only the chosen panels
are editable, and that a mode this build does not offer is shown rather than replaced.
"""
from __future__ import annotations

import pytest

from ui.main_window_parts.multi_panel_dialog import MultiPanelDialog
from core.render_modes import RENDER_MODE_CHOICES, RENDER_MODE_VALUES


def test_it_offers_every_mode_the_application_draws(qapp) -> None:
    """Reported: the panel window offered too few plot types."""
    dialog = MultiPanelDialog(None)
    try:
        combo = dialog.mode_combos[0]
        offered = {combo.itemData(index) for index in range(combo.count())}
        assert offered == set(RENDER_MODE_VALUES), "every mode, none invented"
    finally:
        dialog.deleteLater()


def test_the_geochemistry_and_v1v2_views_are_there() -> None:
    for expected in ("V1V2", "PB_EVOL_76", "PB_EVOL_86", "PB_MU_AGE", "PB_KAPPA_AGE"):
        assert expected in RENDER_MODE_VALUES, f"{expected} must be selectable"


def test_it_opens_in_the_ordinary_window(qapp) -> None:
    dialog = MultiPanelDialog(None)
    try:
        assert dialog.count_spin.value() == 1
        assert dialog.selected_panels() == [], "one panel is the ordinary window"
    finally:
        dialog.deleteLater()


def test_it_opens_on_the_panels_already_chosen(qapp) -> None:
    dialog = MultiPanelDialog(None, panels=["2D", "Ternary"])
    try:
        assert dialog.count_spin.value() == 2
        assert dialog.selected_panels() == ["2D", "Ternary"]
    finally:
        dialog.deleteLater()


def test_a_saved_mode_is_matched_by_value_not_by_label(qapp) -> None:
    """The item carries the mode, so a translated label can never break the match."""
    dialog = MultiPanelDialog(None, panels=["2D", "PB_MU_AGE"])
    try:
        assert dialog.selected_panels() == ["2D", "PB_MU_AGE"]
    finally:
        dialog.deleteLater()


def test_only_the_chosen_panels_are_editable(qapp) -> None:
    dialog = MultiPanelDialog(None, panels=["2D", "Ternary", "UMAP"])
    try:
        enabled = [combo.isEnabled() for combo in dialog.mode_combos]
        assert enabled[:3] == [True, True, True]
        assert not any(enabled[3:]), "the panels beyond the chosen count are inactive"

        dialog.count_spin.setValue(2)

        enabled = [combo.isEnabled() for combo in dialog.mode_combos]
        assert enabled[:2] == [True, True]
        assert not any(enabled[2:])
        assert dialog.selected_panels() == ["2D", "Ternary"]
    finally:
        dialog.deleteLater()


def test_extra_panels_are_filled_with_the_active_mode(qapp) -> None:
    dialog = MultiPanelDialog(None, panels=["2D"], default_mode="Ternary")
    try:
        dialog.count_spin.setValue(3)
        assert dialog.selected_panels() == ["2D", "Ternary", "Ternary"]
    finally:
        dialog.deleteLater()


def test_a_mode_this_build_does_not_offer_is_still_shown(qapp) -> None:
    """A saved panel must not be silently replaced by something else."""
    dialog = MultiPanelDialog(None, panels=["2D", "SomeFutureMode"])
    try:
        assert dialog.selected_panels() == ["2D", "SomeFutureMode"]
    finally:
        dialog.deleteLater()


def test_the_count_is_bounded_by_what_a_window_can_show(qapp) -> None:
    from visualization.plotting.panels import MAX_PANELS

    dialog = MultiPanelDialog(None)
    try:
        assert dialog.count_spin.maximum() == MAX_PANELS
        dialog.count_spin.setValue(MAX_PANELS + 5)
        assert dialog.count_spin.value() == MAX_PANELS
        assert len(dialog.selected_panels()) == MAX_PANELS
    finally:
        dialog.deleteLater()


def test_raising_the_count_never_hides_the_dialog(qapp) -> None:
    """Reported: raising the panel count closed the window, with nothing in the log.

    The row labels used to be borrowed from the layout - and for a form row the row widget's
    parent widget is the dialog itself, so hiding an unused row hid the whole window. A Qt call
    that is perfectly legal raises nothing, which is why the log stayed quiet.
    """
    dialog = MultiPanelDialog(None)
    try:
        dialog.show()
        assert dialog.isVisible()
        for count in range(1, 5):
            dialog.count_spin.setValue(count)
            assert dialog.isVisible(), f"the window closed at {count} panel(s)"
            assert dialog.count_spin.isVisible()
            for index, (label, combo) in enumerate(zip(dialog.mode_labels, dialog.mode_combos)):
                assert label.isVisible() == (index < count)
                assert combo.isVisible() == (index < count)
    finally:
        dialog.close()
        dialog.deleteLater()


def test_the_shared_list_is_pairs_of_label_and_value() -> None:
    labels = [label for label, _value in RENDER_MODE_CHOICES]
    values = [value for _label, value in RENDER_MODE_CHOICES]

    assert len(set(values)) == len(values), "no mode twice"
    assert all(labels and values), "every entry names a label and a value"
