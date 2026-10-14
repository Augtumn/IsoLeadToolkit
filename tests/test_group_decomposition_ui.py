"""The write path of a legend decomposition: data column, parent map and state.

The arithmetic is covered in ``test_group_decomposition.py``; this file covers what the
window does with it - materialising the labels into a grouping column, registering the
children as a parent group, and restoring the original grouping when it is collapsed.

The mixin is driven directly with the two collaborators a real window supplies, so the
logic is exercised without building a window.
"""
from __future__ import annotations

import pandas as pd
import pytest

from core import app_state, state_gateway
from ui.main_window_parts.legend_groups import MainWindowLegendGroupMixin


class _Window(MainWindowLegendGroupMixin):
    """The grouping mixin with its window collaborators recorded instead of run."""

    def __init__(self) -> None:
        self.reloaded = 0
        self.refreshed: list = []

    def _reload_legend_panel(self) -> None:
        self.reloaded += 1

    def _refresh_after_decomposition(self, spec) -> None:
        self.refreshed.append(dict(spec))


@pytest.fixture()
def restore_state():
    previous = (
        app_state.df_global,
        list(app_state.group_cols or []),
        list(app_state.data_cols or []),
        app_state.last_group_col,
        dict(app_state.parent_groups or {}),
        dict(app_state.group_decomposition or {}),
        app_state.visible_groups,
    )
    yield
    (
        frame,
        group_cols,
        data_cols,
        last_group_col,
        parents,
        decomposition,
        visible,
    ) = previous
    state_gateway.set_dataframe_and_source(
        frame, file_path=app_state.file_path, sheet_name=app_state.sheet_name
    )
    state_gateway.set_group_data_columns(group_cols, data_cols)
    state_gateway.set_last_group_col(last_group_col)
    state_gateway.set_parent_groups(parents)
    state_gateway.set_group_decomposition(decomposition)
    state_gateway.set_visible_groups(visible)


def _install() -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "Site": ["Tarim", "Tarim", "Tarim", "Bronze", "Bronze"],
            "Phase": ["casting", "forging", "casting", "casting", "casting"],
            "Pb206_204": [18.1, 18.2, 18.3, 19.1, 19.2],
        }
    )
    state_gateway.set_dataframe_and_source(
        frame, file_path=app_state.file_path, sheet_name=app_state.sheet_name
    )
    state_gateway.set_group_data_columns(["Site", "Phase"], ["Pb206_204"])
    state_gateway.set_last_group_col("Site")
    state_gateway.set_parent_groups({})
    state_gateway.set_group_decomposition({})
    state_gateway.set_visible_groups(None)
    return frame


def test_decomposing_writes_labels_children_and_state(qapp, restore_state, monkeypatch) -> None:
    _install()
    warned: list[str] = []
    monkeypatch.setattr(
        "ui.main_window_parts.legend_groups.QMessageBox.warning",
        staticmethod(lambda *args, **kwargs: warned.append(str(args[2]))),
    )
    window = _Window()

    assert window.decompose_group_by("Tarim", "Phase") is True

    frame = app_state.df_global
    assert list(frame[window.DECOMPOSED_GROUP_COLUMN]) == [
        "Tarim / casting",
        "Tarim / forging",
        "Tarim / casting",
        "Bronze",
        "Bronze",
    ]
    # Children are registered as a parent group; the untouched value stays whole.
    assert app_state.parent_groups == {"Tarim": ["Tarim / casting", "Tarim / forging"]}
    assert app_state.last_group_col == window.DECOMPOSED_GROUP_COLUMN
    assert window.DECOMPOSED_GROUP_COLUMN in app_state.group_cols
    # The state records both what was split and what it was split from.
    assert app_state.group_decomposition == {
        window.BASE_DECOMPOSITION_KEY: "Site",
        "Tarim": "Phase",
    }
    assert app_state.visible_groups is None
    assert window.reloaded == 1 and window.refreshed
    assert warned == []


def test_collapsing_restores_the_original_grouping(qapp, restore_state, monkeypatch) -> None:
    """The falsification case: after collapsing, the data is as it was before."""
    frame = _install()
    monkeypatch.setattr(
        "ui.main_window_parts.legend_groups.QMessageBox.warning",
        staticmethod(lambda *args, **kwargs: None),
    )
    window = _Window()
    assert window.decompose_group_by("Tarim", "Phase") is True

    assert window.clear_group_decomposition("Tarim") is True

    restored = app_state.df_global
    assert window.DECOMPOSED_GROUP_COLUMN not in restored.columns
    assert list(restored["Site"]) == list(frame["Site"])
    assert app_state.last_group_col == "Site"
    assert window.DECOMPOSED_GROUP_COLUMN not in (app_state.group_cols or [])
    assert app_state.group_decomposition == {}
    assert app_state.parent_groups == {}


def test_a_column_cannot_split_its_own_grouping(qapp, restore_state, monkeypatch) -> None:
    _install()
    warned: list[str] = []
    monkeypatch.setattr(
        "ui.main_window_parts.legend_groups.QMessageBox.warning",
        staticmethod(lambda *args, **kwargs: warned.append(str(args[2]))),
    )
    window = _Window()

    assert window.decompose_group_by("Tarim", "Site") is False
    # Refused loudly rather than skipped: the data is untouched. The message is translated, so the
    # test asserts that one was shown instead of matching English text.
    assert warned, "the refusal is reported, not silent"
    assert window.DECOMPOSED_GROUP_COLUMN not in app_state.df_global.columns
    assert app_state.parent_groups == {}


def test_decomposing_without_a_dataframe_is_refused(qapp, restore_state, monkeypatch) -> None:
    _install()
    warned: list[str] = []
    monkeypatch.setattr(
        "ui.main_window_parts.legend_groups.QMessageBox.warning",
        staticmethod(lambda *args, **kwargs: warned.append(str(args[2]))),
    )
    state_gateway.set_dataframe_and_source(None, file_path=None, sheet_name=None)
    window = _Window()

    assert window.decompose_group_by("Tarim", "Phase") is False
    assert warned


def test_every_column_is_offered_and_used_ones_are_disabled(qapp, restore_state) -> None:
    """Reported: too few columns were listed, and a window was wanted instead of a submenu.

    The window offers everything the data has - which columns make sense to refine by is the
    user's call - and shows the ones that cannot be used disabled rather than hiding them.
    """
    frame = pd.DataFrame(
        {
            "Site": ["Tarim", "Bronze"],
            "Phase": ["casting", "forging"],
            "Pb206_204": [18.0, 19.0],
        }
    )
    state_gateway.set_dataframe_and_source(
        frame, file_path=app_state.file_path, sheet_name=app_state.sheet_name
    )
    state_gateway.set_group_data_columns(["Site"], ["Pb206_204"])
    state_gateway.set_last_group_col("Site")
    state_gateway.set_group_decomposition({})
    window = _Window()

    columns = window._decomposition_columns()
    assert "Phase" in columns, "a category column must be offered"
    assert "Pb206_204" in columns, "a measurement is offered too; the user decides"

    used = window._used_decomposition_columns()
    assert "Site" in used, "the active column cannot refine the groups it produced"
    assert "Phase" not in used


def test_columns_used_deeper_in_the_chain_are_disabled_too(qapp, restore_state, monkeypatch) -> None:
    frame = pd.DataFrame({"Site": ["Tarim"], "Phase": ["casting"], "Kind": ["tool"]})
    state_gateway.set_dataframe_and_source(
        frame, file_path=app_state.file_path, sheet_name=app_state.sheet_name
    )
    state_gateway.set_group_data_columns(["Site", "Phase", "Kind"], [])
    state_gateway.set_last_group_col("Site")
    state_gateway.set_parent_groups({})
    state_gateway.set_group_decomposition({})
    monkeypatch.setattr(
        "ui.main_window_parts.legend_groups.QMessageBox.warning",
        staticmethod(lambda *args, **kwargs: None),
    )
    window = _Window()
    assert window.decompose_group_by("Tarim", "Phase") is True

    used = window._used_decomposition_columns("Tarim / casting")
    assert {"Site", "Phase"} <= used, "the active column and Phase are both already in use"
    assert "Kind" not in used


def test_the_choose_window_disables_used_columns(qapp) -> None:
    from PyQt5.QtCore import Qt

    from ui.main_window_parts.legend_decompose_dialog import LegendDecomposeDialog

    dialog = LegendDecomposeDialog(
        None, ["Site", "Phase", "Kind"], used=["Site", "Phase"], group_label="Tarim"
    )
    try:
        items = {
            dialog.list_widget.item(row).text(): dialog.list_widget.item(row)
            for row in range(dialog.list_widget.count())
        }
        assert not (items["Site"].flags() & Qt.ItemIsEnabled), "a used column is disabled"
        assert not (items["Phase"].flags() & Qt.ItemIsEnabled)
        assert items["Kind"].flags() & Qt.ItemIsEnabled, "an unused column stays selectable"
        assert dialog.selected_column() == "Kind", "the first usable column is preselected"
    finally:
        dialog.deleteLater()


def test_a_split_keeps_the_selection_the_user_had(qapp, restore_state, monkeypatch) -> None:
    """Reported: decomposing ticked everything, undoing the selection that was made."""
    frame = pd.DataFrame(
        {
            "Site": ["Tarim", "Tarim", "Bronze"],
            "Phase": ["casting", "forging", "casting"],
        }
    )
    state_gateway.set_dataframe_and_source(
        frame, file_path=app_state.file_path, sheet_name=app_state.sheet_name
    )
    state_gateway.set_group_data_columns(["Site", "Phase"], [])
    state_gateway.set_last_group_col("Site")
    state_gateway.set_parent_groups({})
    state_gateway.set_group_decomposition({})
    state_gateway.set_visible_groups(["Tarim"])  # only one group is ticked
    monkeypatch.setattr(
        "ui.main_window_parts.legend_groups.QMessageBox.warning",
        staticmethod(lambda *args, **kwargs: None),
    )
    window = _Window()

    assert window.decompose_group_by("Tarim", "Phase") is True

    # Tarim's children take its place; nothing else becomes visible.
    assert set(app_state.visible_groups or []) == {"Tarim / casting", "Tarim / forging"}


def test_no_columns_are_offered_without_data(qapp, restore_state) -> None:
    state_gateway.set_dataframe_and_source(None, file_path=None, sheet_name=None)
    assert _Window()._decomposition_columns() == []


def test_drilling_into_a_child_refines_that_child_only(qapp, restore_state, monkeypatch) -> None:
    """The recursive case: a group is split, then one of its children is split again."""
    frame = pd.DataFrame(
        {
            "Site": ["Tarim", "Tarim", "Tarim", "Bronze"],
            "Phase": ["casting", "casting", "forging", "casting"],
            "Kind": ["weapon", "tool", "tool", "weapon"],
        }
    )
    state_gateway.set_dataframe_and_source(
        frame, file_path=app_state.file_path, sheet_name=app_state.sheet_name
    )
    state_gateway.set_group_data_columns(["Site", "Phase", "Kind"], [])
    state_gateway.set_last_group_col("Site")
    state_gateway.set_parent_groups({})
    state_gateway.set_group_decomposition({})
    state_gateway.set_visible_groups(None)
    warned: list[str] = []
    monkeypatch.setattr(
        "ui.main_window_parts.legend_groups.QMessageBox.warning",
        staticmethod(lambda *args, **kwargs: warned.append(str(args[2]))),
    )
    window = _Window()

    # Step one, then a second step inside the group the first one produced.
    assert window.decompose_group_by("Tarim", "Phase") is True
    assert window.decompose_group_by("Tarim / casting", "Kind") is True

    column = window.DECOMPOSED_GROUP_COLUMN
    assert list(app_state.df_global[column]) == [
        "Tarim / casting / weapon",
        "Tarim / casting / tool",
        "Tarim / forging",
        "Bronze",
    ]
    # A child that was split again is a parent in its own right; the flat map is still a tree.
    assert app_state.parent_groups == {
        "Tarim": ["Tarim / casting", "Tarim / forging"],
        "Tarim / casting": ["Tarim / casting / weapon", "Tarim / casting / tool"],
    }
    assert warned == []

    # Collapsing the child undoes that step only.
    assert window.clear_group_decomposition("Tarim / casting") is True
    assert list(app_state.df_global[column]) == [
        "Tarim / casting",
        "Tarim / casting",
        "Tarim / forging",
        "Bronze",
    ]
    assert "Tarim / casting" not in app_state.parent_groups
    assert app_state.parent_groups == {"Tarim": ["Tarim / casting", "Tarim / forging"]}

    # Collapsing the top removes the column and restores the grouping that was in force.
    assert window.clear_group_decomposition("Tarim") is True
    assert column not in app_state.df_global.columns
    assert app_state.last_group_col == "Site"
    assert app_state.group_decomposition == {}
    assert app_state.parent_groups == {}
    assert list(app_state.df_global["Site"]) == list(frame["Site"])


def test_a_column_used_in_one_branch_is_free_in_another(qapp, restore_state, monkeypatch) -> None:
    """Reported: "the same group locks the column it used - why does a different group lock it?"

    Only the columns on a group's own path are constant inside it. A column used elsewhere in
    the legend says nothing about this group and stays selectable.
    """
    frame = pd.DataFrame(
        {
            "Site": ["Tarim", "Tarim", "Bronze", "Bronze"],
            "Phase": ["casting", "forging", "casting", "forging"],
            "Kind": ["tool", "tool", "weapon", "weapon"],
        }
    )
    state_gateway.set_dataframe_and_source(
        frame, file_path=app_state.file_path, sheet_name=app_state.sheet_name
    )
    state_gateway.set_group_data_columns(["Site", "Phase", "Kind"], [])
    state_gateway.set_last_group_col("Site")
    state_gateway.set_parent_groups({})
    state_gateway.set_group_decomposition({})
    monkeypatch.setattr(
        "ui.main_window_parts.legend_groups.QMessageBox.warning",
        staticmethod(lambda *args, **kwargs: None),
    )
    window = _Window()
    assert window.decompose_group_by("Tarim", "Phase") is True

    # Inside Tarim, Phase is the column that produced those children, so it is locked there.
    assert window._used_decomposition_columns("Tarim / casting") == {"Site", "Phase"}
    # Bronze was never split: Phase is still free for it.
    assert window._used_decomposition_columns("Bronze") == {"Site"}, (
        "a column used by another group must not be locked here"
    )


def test_collapsing_frees_the_columns_again(qapp, restore_state, monkeypatch) -> None:
    """Reported: after cancelling the decomposition, the used column stayed locked."""
    frame = pd.DataFrame(
        {
            "Site": ["Tarim", "Tarim", "Bronze"],
            "Phase": ["casting", "forging", "casting"],
            "Kind": ["tool", "tool", "weapon"],
        }
    )
    state_gateway.set_dataframe_and_source(
        frame, file_path=app_state.file_path, sheet_name=app_state.sheet_name
    )
    state_gateway.set_group_data_columns(["Site", "Phase", "Kind"], [])
    state_gateway.set_last_group_col("Site")
    state_gateway.set_parent_groups({})
    state_gateway.set_group_decomposition({})
    state_gateway.set_visible_groups(None)
    monkeypatch.setattr(
        "ui.main_window_parts.legend_groups.QMessageBox.warning",
        staticmethod(lambda *args, **kwargs: None),
    )
    window = _Window()

    assert window.decompose_group_by("Tarim", "Phase") is True
    assert "Phase" in window._used_decomposition_columns("Tarim / casting")

    assert window.clear_group_decomposition("Tarim") is True

    assert app_state.group_decomposition == {}
    assert window._used_decomposition_columns("Tarim") == {"Site"}, "Phase is free again"
    assert window._used_decomposition_columns("Tarim / casting") == {"Site"}


def test_a_locked_column_is_refused_by_the_method_too(qapp, restore_state, monkeypatch) -> None:
    """The window disables it, but the method must not accept it either."""
    frame = pd.DataFrame({"Site": ["Tarim"], "Phase": ["casting"], "Kind": ["tool"]})
    state_gateway.set_dataframe_and_source(
        frame, file_path=app_state.file_path, sheet_name=app_state.sheet_name
    )
    state_gateway.set_group_data_columns(["Site", "Phase", "Kind"], [])
    state_gateway.set_last_group_col("Site")
    state_gateway.set_parent_groups({})
    state_gateway.set_group_decomposition({})
    warned: list[str] = []
    monkeypatch.setattr(
        "ui.main_window_parts.legend_groups.QMessageBox.warning",
        staticmethod(lambda *args, **kwargs: warned.append(str(args[2]))),
    )
    window = _Window()
    assert window.decompose_group_by("Tarim", "Phase") is True

    # Site is constant inside Tarim and Phase produced Tarim/casting: neither can refine it.
    assert window.decompose_group_by("Tarim / casting", "Site") is False
    assert window.decompose_group_by("Tarim / casting", "Phase") is False
    assert warned, "the refusal is reported, not silent"
    assert app_state.group_decomposition.get("Tarim\x1fcasting") is None
