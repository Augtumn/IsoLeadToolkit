"""Dialog-side tests for the SilverQuest parameter form.

These cover the pieces of logic that can silently corrupt a provenance call if
they get the columns or the rows wrong — mapping the session's column names onto
the R input format, naming the grouping columns the form offers, resolving which
of the grouping column's values play which role, and turning rows into artefact
records — plus the two end-to-end paths a user actually takes: pick a grouping
column and two group selections over the loaded data, or fall back to the R
package's galena workbook as the reference set.

Offscreen Qt only; no modal dialogs are triggered.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from core import app_state, state_gateway, translate
from plugins.builtins.silverquest_plugin import (
    ROLE_REFERENCE_MATCH_PREFIX,
    ROLE_MATCH_PREFIX,
    ROLE_OTHER,
    ROLE_REFERENCE_PREFIX,
)
from ui.panels.analysis.dialogs.silverquest_dialog import (
    MAX_DISPLAY_ROWS,
    ROLE_COLUMN,
    SilverQuestDialog,
    build_artefact_records,
    candidate_group_columns,
    resolve_artefact_columns,
)

#: The worked example from Readme.pdf ("Input Example").
_README_ROWS = pd.DataFrame(
    {
        "no": ["G107", "G089", "G013"],
        "group": [1, 1, 1],
        "subgroup": [1, 1, 2],
        "Pb206204": [18.5764, 18.5649, 18.8408],
        "Pb207204": [15.6597, 15.6561, 15.6947],
        "Pb208204": [38.589, 38.572, 38.903],
    }
)

#: Six rows in three groups: two artefact groups and one reference group.  A1 is
#: OreX verbatim (distance 0), A2 is 0.0100 above it (distance 0.383423); B1 is
#: not selected in most tests.  Same numbers as
#: ``tests/test_silverquest_plugin.py::_synthetic_grouped_frame``.
_GROUPED_ROWS = pd.DataFrame(
    {
        "Sample": ["A1", "A2", "B1", "X1", "X2", "Y1"],
        "Site": ["SiteA", "SiteA", "SiteB", "OreX", "OreX", "OreY"],
        "Pb206_204": [18.5764, 18.5864, 18.5964, 18.5764, 19.0000, 17.5000],
        "Pb207_204": [15.6597, 15.6697, 15.6797, 15.6597, 15.8000, 15.5000],
        "Pb208_204": [38.5890, 38.5990, 38.6090, 38.5890, 39.5000, 37.5000],
    }
)


@pytest.fixture()
def restore_state():
    """Leave the session state as it was found.

    The dialog persists its grouping column and group selection through the
    gateway, so a test that runs it must put those fields back.
    """
    previous_frame = app_state.df_global
    previous_group_cols = list(app_state.group_cols or [])
    previous_data_cols = list(app_state.data_cols or [])
    previous_last_group_col = app_state.last_group_col
    previous_visible = app_state.visible_groups
    previous_markers = dict(app_state.group_marker_map or {})
    previous_params = state_gateway.get_silverquest_params()
    yield
    state_gateway.set_dataframe_and_source(
        previous_frame,
        file_path=app_state.file_path,
        sheet_name=app_state.sheet_name,
    )
    state_gateway.set_group_data_columns(previous_group_cols, previous_data_cols)
    state_gateway.set_last_group_col(previous_last_group_col)
    state_gateway.set_visible_groups(previous_visible)
    state_gateway.set_group_marker_map(previous_markers)
    state_gateway.set_silverquest_params(previous_params)


def _install_grouped_frame(frame: pd.DataFrame, group_col: str = "Site") -> None:
    state_gateway.set_dataframe_and_source(
        frame,
        file_path=app_state.file_path,
        sheet_name=app_state.sheet_name,
    )
    state_gateway.set_group_data_columns([group_col], list(app_state.data_cols or []))
    state_gateway.set_last_group_col(group_col)
    state_gateway.set_visible_groups(None)
    # Start from the R Shiny defaults: a dialog created by an earlier test in the
    # same session may otherwise restore that test's persisted selection.
    state_gateway.set_silverquest_params({})


def _select(dialog: SilverQuestDialog, artefacts=(), references=()) -> None:
    """Check the named groups in each role list, as a user would."""
    for widget, wanted in (
        (dialog.artefact_list, artefacts),
        (dialog.reference_list, references),
    ):
        wanted = set(wanted)
        for row in range(widget.count()):
            item = widget.item(row)
            item.setSelected(item.data(0x0100) in wanted)  # Qt.UserRole


# ── column resolution and record building ───────────────────────────────────


def test_resolve_columns_accepts_the_r_input_format() -> None:
    resolved = resolve_artefact_columns(_README_ROWS.columns)
    assert resolved["Pb206204"] == "Pb206204"
    assert resolved["Pb207204"] == "Pb207204"
    assert resolved["Pb208204"] == "Pb208204"
    assert resolved["no"] == "no"
    assert resolved["group"] == "group"


def test_resolve_columns_accepts_the_application_spelling() -> None:
    """``data/geochemistry`` names the ratios ``Pb206_204``; both must work."""
    resolved = resolve_artefact_columns(["Pb206_204", "Pb207_204", "Pb208_204"])
    assert resolved["Pb206204"] == "Pb206_204"
    assert resolved["Pb207204"] == "Pb207_204"
    assert resolved["Pb208204"] == "Pb208_204"
    # No optional columns present: the caller falls back to sensible defaults.
    assert "no" not in resolved
    assert "group" not in resolved


def test_resolve_columns_accepts_slash_separated_headers() -> None:
    resolved = resolve_artefact_columns(
        ["206Pb/204Pb", "207Pb/204Pb", "208Pb/204Pb", "Sample"]
    )
    assert resolved["Pb206204"] == "206Pb/204Pb"
    assert resolved["no"] == "Sample"


def test_resolve_columns_names_what_it_tried_when_a_ratio_is_missing() -> None:
    with pytest.raises(KeyError) as excinfo:
        resolve_artefact_columns(["Pb206204", "Pb208204"])
    message = str(excinfo.value)
    assert "Pb207204" in message
    assert "Pb207_204" in message  # the alternatives are listed


def test_build_records_matches_the_readme_example() -> None:
    records = build_artefact_records(_README_ROWS)
    assert len(records) == 3
    assert records[0]["no"] == "G107"
    assert records[0]["group"] == 1
    assert records[0]["Pb206204"] == pytest.approx(18.5764)


def test_build_records_fills_defaults_when_optional_columns_are_absent() -> None:
    frame = pd.DataFrame(
        {"Pb206204": [18.5], "Pb207204": [15.6], "Pb208204": [38.5]}
    )
    records = build_artefact_records(frame)
    assert records[0]["no"] == "row1"
    assert records[0]["group"] == "1"


def test_build_records_skips_rows_with_unusable_ratios() -> None:
    """The R script dies on the first such row; the dialog skips it instead."""
    frame = pd.DataFrame(
        {
            "no": ["good", "text", "blank"],
            "Pb206204": [18.5, "Hosein", None],
            "Pb207204": [15.6, 15.7, 15.8],
            "Pb208204": [38.5, 38.6, 38.7],
        }
    )
    records = build_artefact_records(frame)
    assert [record["no"] for record in records] == ["good"]


def test_build_records_skips_non_finite_ratios() -> None:
    frame = pd.DataFrame(
        {
            "no": ["good", "inf"],
            "Pb206204": [18.5, np.inf],
            "Pb207204": [15.6, 15.7],
            "Pb208204": [38.5, 38.6],
        }
    )
    assert [record["no"] for record in build_artefact_records(frame)] == ["good"]


# ── grouping-column candidates ──────────────────────────────────────────────


def test_candidate_columns_follow_the_data_panels_declarations() -> None:
    """The grouping vocabulary is ``app_state.group_cols``, not every column."""
    frame = pd.DataFrame({"Site": ["A"], "Country": ["B"], "Pb206_204": [1.0]})
    assert candidate_group_columns(frame, ["Site", "Country"]) == ["Site", "Country"]


def test_candidate_columns_keep_the_active_grouping_column_first() -> None:
    frame = pd.DataFrame({"Site": ["A"], "Country": ["B"]})
    assert candidate_group_columns(frame, ["Country"])[0] == "Country"


def test_candidate_columns_fall_back_to_every_column() -> None:
    """With nothing declared yet the dialog stays usable instead of empty."""
    frame = pd.DataFrame({"Site": ["A"], "Country": ["B"]})
    assert candidate_group_columns(frame, []) == ["Site", "Country"]


def test_candidate_columns_ignore_columns_that_are_gone() -> None:
    frame = pd.DataFrame({"Site": ["A"]})
    assert candidate_group_columns(frame, ["Removed", "Site"]) == ["Site"]


# ── the dialog ──────────────────────────────────────────────────────────────


def test_dialog_builds_with_the_r_shiny_defaults(qapp, restore_state) -> None:
    _install_grouped_frame(_GROUPED_ROWS)
    dialog = SilverQuestDialog()
    try:
        # Defaults must reproduce the R Shiny inputs.
        assert dialog.normalization_combo.currentData() == "204Pb"
        assert dialog.dmax_spin.value() == pytest.approx(3.0)
        assert dialog.jitter_check.isChecked() is True
        assert dialog.radius_spin.value() == pytest.approx(0.01)
        assert dialog.export_button.isEnabled() is False
        assert dialog.apply_button.isEnabled() is False
        assert dialog.database_edit.text()
    finally:
        dialog.deleteLater()


def test_dialog_offers_the_declared_grouping_columns(qapp, restore_state) -> None:
    _install_grouped_frame(_GROUPED_ROWS, "Site")
    state_gateway.set_group_data_columns(
        ["Site", "Sample"], list(app_state.data_cols or [])
    )
    dialog = SilverQuestDialog()
    try:
        offered = [
            dialog.grouping_combo.itemData(index)
            for index in range(dialog.grouping_combo.count())
        ]
        assert offered == ["Site", "Sample"]
        assert dialog.grouping_combo.currentData() == "Site"
    finally:
        dialog.deleteLater()


def test_dialog_lists_every_group_of_the_chosen_column(qapp, restore_state) -> None:
    _install_grouped_frame(_GROUPED_ROWS, "Site")
    dialog = SilverQuestDialog()
    try:
        artefact_groups = [
            dialog.artefact_list.item(row).data(0x0100)
            for row in range(dialog.artefact_list.count())
        ]
        assert artefact_groups == ["OreX", "OreY", "SiteA", "SiteB"]
        # The item text carries the row count so the user can see the sizes.
        # Assert through translate() so the check holds in either UI language.
        assert translate("{group} ({count} rows)").format(
            group="SiteA", count=2
        ) in dialog.artefact_list.item(2).text()
    finally:
        dialog.deleteLater()


def test_dialog_offers_only_visible_groups_when_asked(qapp, restore_state) -> None:
    """The legend's visible/hidden state is honoured, not ignored."""
    _install_grouped_frame(_GROUPED_ROWS, "Site")
    state_gateway.set_visible_groups(["SiteA", "OreX"])
    dialog = SilverQuestDialog()
    try:
        dialog.visible_only_check.setChecked(True)
        offered = [
            dialog.artefact_list.item(row).data(0x0100)
            for row in range(dialog.artefact_list.count())
        ]
        assert offered == ["OreX", "SiteA"]
    finally:
        dialog.deleteLater()
        state_gateway.set_visible_groups(None)


def test_dialog_status_ignores_a_group_selected_on_both_sides(qapp, restore_state) -> None:
    """A contradictory selection is resolved the same way the search resolves it."""
    _install_grouped_frame(_GROUPED_ROWS, "Site")
    dialog = SilverQuestDialog()
    try:
        _select(dialog, artefacts=["SiteA", "OreX"], references=["OreX"])
        artefacts, references = dialog._selected_groups_for_run()
        assert artefacts == ["SiteA"]
        assert references == ["OreX"]
        assert translate("groups selected on both sides are used as references") in (
            dialog.selection_status.text()
        )
    finally:
        dialog.deleteLater()


def test_dialog_reports_a_missing_database_without_raising(qapp, restore_state) -> None:
    _install_grouped_frame(_GROUPED_ROWS, "Site")
    dialog = SilverQuestDialog()
    try:
        dialog.database_edit.setText("Z:/definitely/absent.xlsx")
        dialog._check_database()
        assert dialog._database_ok is False
        assert "absent.xlsx" in dialog.database_status.text()
    finally:
        dialog.deleteLater()


# ── end to end: the grouping column is the interface ────────────────────────


def test_dialog_runs_the_search_from_the_loaded_groups(qapp, restore_state) -> None:
    """Pick a grouping column, assign the roles, read the table.

    No workbook is involved: the references are the ``OreX``/``OreY`` rows of the
    loaded dataframe, which is what the plugin reports back through
    ``reference_source``.
    """
    _install_grouped_frame(_GROUPED_ROWS, "Site")
    dialog = SilverQuestDialog()
    try:
        assert dialog.grouping_combo.currentData() == "Site"
        _select(dialog, artefacts=["SiteA"], references=["OreX", "OreY"])
        dialog.dmax_spin.setValue(1.0)
        dialog.jitter_check.setChecked(False)

        payload = dialog._search_payload()

        assert payload is not None
        assert payload["reference_source"] == "groups"
        assert payload["reference_rows"] == 3
        assert dialog._result is payload["result"]
        assert dialog._result.database_rows == 3
        assert dialog.apply_button.isEnabled() is True
        assert dialog.export_button.isEnabled() is True
        assert translate("references: {count} selected row(s)").format(
            count=3
        ) in dialog.info_label.text()

        # The hit table is closest-first and names the matching ore.
        assert dialog.result_table.rowCount() == 2
        first_row = [
            dialog.result_table.item(0, column).text() for column in range(6)
        ]
        assert first_row[0] == "A1"
        assert first_row[1] == "OreX"
        assert float(first_row[4]) == pytest.approx(0.0, abs=0.0)
        distances = [
            float(dialog.result_table.item(row, 4).text())
            for row in range(dialog.result_table.rowCount())
        ]
        assert distances == sorted(distances)

        # The selection is persisted through the gateway (declarative state).
        saved = state_gateway.get_silverquest_params()
        assert saved["group_col"] == "Site"
        assert saved["artefact_groups"] == ["SiteA"]
        assert saved["reference_groups"] == ["OreX", "OreY"]
        assert saved["dmax"] == pytest.approx(1.0)
    finally:
        dialog.deleteLater()


def test_dialog_restores_the_persisted_selection(qapp, restore_state) -> None:
    """The trap from the brief: a second dialog comes back with the same picks."""
    _install_grouped_frame(_GROUPED_ROWS, "Site")
    first = SilverQuestDialog()
    try:
        _select(first, artefacts=["SiteA"], references=["OreX"])
        assert first._search_payload() is not None
    finally:
        first.deleteLater()

    second = SilverQuestDialog()
    try:
        assert second.grouping_combo.currentData() == "Site"
        assert second.selected_artefact_groups() == ["SiteA"]
        assert second.selected_reference_groups() == ["OreX"]
    finally:
        second.deleteLater()


def test_dialog_applies_the_roles_as_a_group_column(qapp, restore_state, monkeypatch) -> None:
    """Results reach the plot through the application's own grouping vocabulary."""
    _install_grouped_frame(_GROUPED_ROWS, "Site")
    dialog = SilverQuestDialog()
    applied: list[int] = []
    try:
        monkeypatch.setattr(
            "ui.panels.analysis.dialogs.silverquest_dialog.QMessageBox.information",
            staticmethod(lambda *args, **kwargs: None),
        )
        monkeypatch.setattr(
            "visualization.events.on_slider_change",
            lambda *args, **kwargs: applied.append(1),
        )
        _select(dialog, artefacts=["SiteA"], references=["OreX"])
        dialog.dmax_spin.setValue(1.0)
        dialog.jitter_check.setChecked(False)
        assert dialog._search_payload() is not None

        dialog._apply_to_data()

        frame = app_state.df_global
        assert ROLE_COLUMN in frame.columns
        assert frame[ROLE_COLUMN].tolist() == [
            ROLE_MATCH_PREFIX + "SiteA",
            ROLE_MATCH_PREFIX + "SiteA",
            ROLE_OTHER,
            ROLE_REFERENCE_MATCH_PREFIX + "OreX",
            ROLE_REFERENCE_PREFIX + "OreX",
            ROLE_OTHER,
        ]
        # The new column becomes the active grouping, so the plot colours by it
        # and the legend lists "[Match] SiteA" / "[Reference] OreX" / "[Other Data]".
        assert ROLE_COLUMN in app_state.group_cols
        assert app_state.last_group_col == ROLE_COLUMN
        # No shape by role: every value of one grouping column is drawn with the same
        # marker, so the roles are told apart by colour alone.
        assert applied == [1], "the plot must be refreshed"
    finally:
        dialog.deleteLater()


def test_dialog_falls_back_to_the_galena_workbook(qapp, restore_state) -> None:
    """The R package's database stays available as an *optional* reference set."""
    _install_grouped_frame(_GROUPED_ROWS, "Site")
    dialog = SilverQuestDialog()
    try:
        _select(dialog, artefacts=["SiteA"], references=[])
        dialog.use_database_check.setChecked(True)
        dialog.jitter_check.setChecked(False)

        payload = dialog._search_payload()

        assert payload is not None
        assert payload["reference_source"] == "workbook"
        assert payload["reference_rows"] > 1000
        assert translate("references: galena database ({count} rows)").format(
            count=payload["reference_rows"]
        ) in dialog.info_label.text()
        assert dialog.result_table.rowCount() >= 1
    finally:
        dialog.deleteLater()


def test_dialog_warns_when_no_role_is_selected(qapp, restore_state, monkeypatch) -> None:
    """A missing role is answered with a warning, never an exception."""
    _install_grouped_frame(_GROUPED_ROWS, "Site")
    dialog = SilverQuestDialog()
    warned: list[str] = []
    monkeypatch.setattr(
        "ui.panels.analysis.dialogs.silverquest_dialog.QMessageBox.warning",
        staticmethod(lambda *args, **kwargs: warned.append(args[2])),
    )
    try:
        _select(dialog, artefacts=[], references=["OreX"])
        assert dialog._search_payload() is None
        assert warned and warned[-1] == translate(
            "Please select at least one artefact group."
        )

        warned.clear()
        _select(dialog, artefacts=["SiteA"], references=[])
        dialog.use_database_check.setChecked(False)
        assert dialog._collect_run_params() is None
        assert warned and warned[-1] == translate(
            "Please select at least one reference group or enable the galena database."
        )
        assert dialog._result is None
    finally:
        dialog.deleteLater()


def test_dialog_search_warns_when_data_is_absent(qapp, monkeypatch, restore_state) -> None:
    """A missing dataframe is answered with a warning, never an exception."""
    _install_grouped_frame(_GROUPED_ROWS, "Site")
    dialog = SilverQuestDialog()
    warned: list[str] = []
    monkeypatch.setattr(
        "ui.panels.analysis.dialogs.silverquest_dialog.QMessageBox.warning",
        staticmethod(lambda *args, **kwargs: warned.append(args[2])),
    )
    try:
        state_gateway.set_dataframe_and_source(
            None, file_path=None, sheet_name=None
        )
        dialog._run_search()
        assert warned, "expected a warning about missing data"
        assert dialog._result is None
    finally:
        dialog.deleteLater()


def test_display_cap_is_a_sane_positive_number() -> None:
    assert MAX_DISPLAY_ROWS >= 100


def test_a_search_leaves_no_wait_cursor_behind(qapp, restore_state) -> None:
    """Reported as "it freezes as soon as I run it, 20 samples and 90 rows".

    The maths is not the cause - 20 x 90 measures about 84 ms - so this test asserts the thing that
    actually stuck: the dialog sets a wait cursor before starting the worker and both result paths
    used to return without restoring it, which leaves the application looking frozen for good.
    """
    from PyQt5.QtWidgets import QApplication

    rng = np.random.default_rng(0)

    def triple():
        return (float(rng.normal(18.7, 0.3)), float(rng.normal(15.65, 0.2)), float(rng.normal(39.0, 0.4)))

    rows = []
    for _ in range(90):                                   # the reference set
        a, b, c = triple()
        rows.append({"Sample": f"R{len(rows)}", "Site": "OreX", "Pb206_204": a, "Pb207_204": b, "Pb208_204": c})
    artefacts = [f"S{i}" for i in range(20)]              # 20 artefact groups
    for name in artefacts:
        a, b, c = triple()
        rows.append({"Sample": name, "Site": name, "Pb206_204": a, "Pb207_204": b, "Pb208_204": c})
    _install_grouped_frame(pd.DataFrame(rows), "Site")

    dialog = SilverQuestDialog()
    try:
        dialog._populate_grouping_columns()
        dialog.grouping_combo.setCurrentText("Site")
        dialog._on_grouping_changed()
        dialog._refresh_group_lists()
        _select(dialog, artefacts=artefacts, references=["OreX"])

        dialog._run_search()

        for _ in range(300):                              # bounded: never hang the suite
            QApplication.processEvents()
            if dialog._search_worker is None:
                break
            QApplication.instance().thread().msleep(50)

        assert dialog._search_worker is None, "the search never finished"
        assert QApplication.overrideCursor() is None, (
            "a wait cursor was left behind: the application looks frozen after a search"
        )
        assert dialog.run_button.isEnabled(), "the Run button stayed disabled"
    finally:
        while QApplication.overrideCursor() is not None:
            QApplication.restoreOverrideCursor()
        dialog.deleteLater()


def _silence_dialogs(monkeypatch, sink):
    """No modal QMessageBox: under the offscreen platform this Qt build access-violates on one."""
    for name in ("warning", "information", "critical"):
        monkeypatch.setattr(
            f"ui.panels.analysis.dialogs.silverquest_dialog.QMessageBox.{name}",
            staticmethod(lambda *a, **k: sink.append(str(a[2]) if len(a) > 2 else "")),
        )


def _run_and_wait(dialog) -> None:
    from PyQt5.QtWidgets import QApplication

    dialog._run_search()
    for _ in range(300):
        QApplication.processEvents()
        if dialog._search_worker is None:
            break
        QApplication.instance().thread().msleep(50)
    assert dialog._search_worker is None, "the search never finished"


def test_a_search_leaves_no_wait_cursor_behind(qapp, restore_state, monkeypatch) -> None:
    """Reported as "it freezes as soon as I run it": the maths finishes in ~84 ms for 20 x 90."""
    from PyQt5.QtWidgets import QApplication

    _silence_dialogs(monkeypatch, [])
    _install_grouped_frame(_GROUPED_ROWS, "Site")
    dialog = SilverQuestDialog()
    try:
        dialog._populate_grouping_columns()
        dialog.grouping_combo.setCurrentText("Site")
        dialog._on_grouping_changed()
        dialog._refresh_group_lists()
        _select(dialog, artefacts=["SiteA", "SiteB"], references=["OreX", "OreY"])
        _run_and_wait(dialog)
        assert QApplication.overrideCursor() is None, "a wait cursor was left behind"
        assert dialog.run_button.isEnabled(), "the Run button stayed disabled"
    finally:
        while QApplication.overrideCursor() is not None:
            QApplication.restoreOverrideCursor()
        dialog.deleteLater()


def test_apply_to_data_opens_a_group_column(qapp, restore_state, monkeypatch) -> None:
    """Reported as "the hits applied, but no separate group column appeared".

    Asserts the facts: the role column is in the dataframe, registered as a grouping column and
    active, with the roles the search decided. The dialogs are captured so a guard that fires shows
    up in the failure message instead of looking like a silent no-op.
    """
    from ui.panels.analysis.dialogs.silverquest_dialog import ROLE_COLUMN

    messages: list[str] = []
    _silence_dialogs(monkeypatch, messages)
    # One extra artefact far from every reference, so the roles include an unmatched sample as well
    # as matches: with only SiteA/SiteB every artefact happens to fall inside dmax of a reference.
    frame = pd.concat(
        [
            _GROUPED_ROWS,
            pd.DataFrame(
                {
                    "Sample": ["Z1"],
                    "Site": ["SiteZ"],
                    "Pb206_204": [17.0000],
                    "Pb207_204": [15.0000],
                    "Pb208_204": [36.0000],
                }
            ),
        ],
        ignore_index=True,
    )
    _install_grouped_frame(frame, "Site")
    dialog = SilverQuestDialog()
    try:
        dialog._populate_grouping_columns()
        dialog.grouping_combo.setCurrentText("Site")
        dialog._on_grouping_changed()
        dialog._refresh_group_lists()
        _select(dialog, artefacts=["SiteA", "SiteB", "SiteZ"], references=["OreX", "OreY"])
        _run_and_wait(dialog)
        assert dialog._payload is not None, "the search produced no payload"

        dialog._apply_to_data()

        frame = app_state.df_global
        assert ROLE_COLUMN in frame.columns, f"no role column; dialogs={messages}; cols={list(frame.columns)}"
        assert ROLE_COLUMN in (app_state.group_cols or []), f"not registered; dialogs={messages}"
        assert app_state.last_group_col == ROLE_COLUMN, f"active grouping is {app_state.last_group_col!r}"
        roles = [str(v) for v in frame[ROLE_COLUMN]]
        assert any(r.startswith("[Reference]") for r in roles), roles
        assert any(r.startswith(("[No Match]", "[Other Data]")) for r in roles), roles
    finally:
        dialog.deleteLater()
