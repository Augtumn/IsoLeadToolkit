"""SilverQuest provenance dialog — group selection over the application's data.

The R implementation collects its parameters through two ``shinyApp`` dialogs
(R lines 75-127 and 238-278) and reads *two* workbooks: the artefact file
(R line 5) and the galena database (R line 139).  Of the R form's inputs this
dialog keeps the ones that change the numbers — normalisation, ``dmax``, the
jitter switch and its radius — and leaves out the plotting-only ones (map
window, basemap style, ore overlay), which nothing here draws.  This dialog
replaces both forms with one Qt form over the loaded session data.

What the user picks
-------------------
1. the **grouping column** — the dialog lists the columns the data panel has
   already declared as grouping columns (``app_state.group_cols``), so the
   vocabulary is the application's own;
2. the column's distinct values twice: once as **sample groups** (the samples
   whose provenance is in question) and once as **reference groups** (the ores
   they are compared against).  "Both sides of the search come from
   ``df_global``" is the primary path;
3. optionally, the R package's galena workbook as *extra* references when no
   reference group is selected (or when the groups alone are not enough).

The algorithm itself is :mod:`adapters.silverquest`; the search entry point is
:func:`plugins.builtins.silverquest_plugin.run_silverquest_on_groups`, and
nothing numeric lives here.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from core import app_state, state_gateway, translate
from plugins.builtins.silverquest_plugin import (
    silverquest_database_path,
    silverquest_database_status,
    silverquest_normalizations,
)
from ui.dialogs.geometry import remember_geometry

logger = logging.getLogger(__name__)

#: Column spellings accepted for the three Pb ratios.  The R input format is
#: ``Pb206204`` (Readme.pdf, "Input Example"); the application's geochemistry
#: code uses ``Pb206_204``, and slash-separated headers appear in imported
#: workbooks.
_RATIO_ALIASES: dict[str, tuple[str, ...]] = {
    "Pb206204": ("Pb206204", "Pb206_204", "Pb206/204", "206Pb/204Pb"),
    "Pb207204": ("Pb207204", "Pb207_204", "Pb207/204", "207Pb/204Pb"),
    "Pb208204": ("Pb208204", "Pb208_204", "Pb208/204", "208Pb/204Pb"),
}

_GROUP_ALIASES = ("group", "Group", "GroupName")
_NO_ALIASES = ("no", "No", "NO", "Name", "name", "Sample", "sample")

#: Rows shown in the hit table.  A single artefact can hit hundreds of the 6900
#: database rows, and a QTableWidget row costs ~6 items; the file exports stay
#: complete.  R's own output (``hits.xlsx``) is not capped, so this is a display
#: limit only.
MAX_DISPLAY_ROWS = 500

#: Column written back by "Apply to Data".  Every other group column in the
#: application is used the same way: the plot colours the values, the legend
#: lists them and its checkboxes hide them.
ROLE_COLUMN = "_SilverQuest_Role"

def resolve_artefact_columns(columns) -> dict[str, str]:
    """Map the R input columns onto the columns actually present in *columns*.

    Raises:
        KeyError: a required ratio column has no recognised spelling.  The
            message lists what was tried, because a silent mismatch would send
            the wrong numbers into the provenance call.
    """
    available = list(columns)
    resolved: dict[str, str] = {}
    for canonical, aliases in _RATIO_ALIASES.items():
        for alias in aliases:
            if alias in available:
                resolved[canonical] = alias
                break
        else:
            raise KeyError(
                f"SilverQuest: no column for {canonical}; tried "
                + ", ".join(aliases)
            )
    for canonical, aliases in (
        ("no", _NO_ALIASES),
        ("group", _GROUP_ALIASES),
    ):
        for alias in aliases:
            if alias in available:
                resolved[canonical] = alias
                break
    return resolved


def build_artefact_records(frame, columns: dict[str, str] | None = None) -> list[dict]:
    """Turn a DataFrame into the record dicts ``adapters.silverquest`` expects.

    Rows with a non-numeric or missing ratio are skipped rather than passed on:
    the R script reads a whole workbook and fails on the first such row
    (``non-numeric argument to binary operator``), which is not a useful
    behaviour to reproduce in a GUI.
    """
    resolved = columns or resolve_artefact_columns(frame.columns)
    records: list[dict] = []
    skipped = 0
    for position, (_, row) in enumerate(frame.iterrows()):
        record: dict = {}
        try:
            for canonical, column in resolved.items():
                if canonical in ("no", "group"):
                    continue
                record[canonical] = float(row[column])
        except (TypeError, ValueError):
            skipped += 1
            continue
        if not all(np.isfinite(record[key]) for key in _RATIO_ALIASES):
            skipped += 1
            continue
        record["no"] = (
            str(row[resolved["no"]]) if "no" in resolved else f"row{position + 1}"
        )
        record["group"] = row[resolved["group"]] if "group" in resolved else "1"
        records.append(record)
    if skipped:
        logger.warning("SilverQuest: skipped %d incomplete artefact row(s)", skipped)
    return records


def candidate_group_columns(frame, declared: list[str] | None = None) -> list[str]:
    """The grouping columns the dialog offers, in the data panel's order.

    ``app_state.group_cols`` is the application's own notion of "the columns
    that group my data" (the data panel configures it, the legend and the plot
    consume it).  When nothing has been declared yet the last group column, and
    then any column of the frame, is offered so the dialog stays usable.
    """
    if frame is None:
        return []
    available = [str(column) for column in frame.columns]
    candidates: list[str] = []
    for column in list(declared or []):
        name = str(column)
        if name in available and name not in candidates:
            candidates.append(name)
    last = app_state.last_group_col
    if isinstance(last, str) and last in available and last not in candidates:
        candidates.insert(0, last)
    if not candidates:
        candidates = available
    return candidates


def role_counts_text(payload: dict | None) -> str:
    """Summarise the two sides' outcomes, one line each.

    The hit table lists only the pairs that *did* match, so the split the role
    column draws — ``[Sample Matched]`` / ``[Sample Unmatched]`` on one side,
    ``[Reference Matched]`` / ``[Reference Unmatched]`` on the other — is counted
    here instead: how many rows of each side entered the search, how many of those
    matched, and how many rows were left out because their Pb ratios are unusable.

    Returns an empty string when *payload* carries no counts (an older payload).

    Args:
        payload: the dict returned by
            :func:`plugins.builtins.silverquest_plugin.run_silverquest_on_groups`.

    Returns:
        One line per side, newline-separated; ``""`` when there is nothing to say.
    """
    counts = (payload or {}).get("role_counts")
    if not counts:
        return ""
    samples = counts.get("samples") or {}
    references = counts.get("references") or {}
    lines = [
        translate(
            "Samples: {entered} in the search, {matched} matched, {unmatched} unmatched."
        ).format(
            entered=int(samples.get("entered", 0)),
            matched=int(samples.get("matched", 0)),
            unmatched=int(samples.get("unmatched", 0)),
        ),
        translate(
            "References: {entered} in the search, {matched} matched, {unmatched} unmatched."
        ).format(
            entered=int(references.get("entered", 0)),
            matched=int(references.get("matched", 0)),
            unmatched=int(references.get("unmatched", 0)),
        ),
    ]
    excluded_samples = int(samples.get("excluded", 0))
    if excluded_samples:
        lines.append(
            translate("Samples: {excluded} row(s) left out (unusable Pb ratios).").format(
                excluded=excluded_samples
            )
        )
    excluded_references = int(references.get("excluded", 0))
    if excluded_references:
        lines.append(
            translate(
                "References: {excluded} row(s) left out (unusable Pb ratios)."
            ).format(excluded=excluded_references)
        )
    return "\n".join(lines)


class SilverQuestDialog(QDialog):
    """Grouping-column form + hit table for the SilverQuest provenance search."""

    _search_worker = None

    # Declared by the class that uses them, so no probe is needed for widgets
    # that build() creates later (UI review item B).
    database_edit = None
    export_button = None
    apply_button = None
    info_label = None
    result_table = None

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(translate("SilverQuest Provenance"))
        self.setMinimumWidth(940)
        self.setMinimumHeight(680)
        self._result = None
        self._payload: dict | None = None
        self._records: list[dict] = []
        #: Group names restored from the persisted selection, consumed by the
        #: first ``_refresh_group_lists`` (the lists do not exist before it).
        self._pending_artefact_groups: list[str] = []
        self._pending_reference_groups: list[str] = []
        self._setup_ui()
        self._restore_saved_params()
        self._populate_grouping_columns()
        self._check_database()
        self._refresh_group_lists()
        remember_geometry(self, 'SilverQuestDialog')

    # ── construction ───────────────────────────────────────────────────
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        hint = QLabel(
            translate(
                "Pick a grouping column, then assign its values to the sample "
                "and reference roles."
            )
        )
        hint.setProperty(
            'translate_key',
            "Pick a grouping column, then assign its values to the sample "
            "and reference roles.",
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        layout.addWidget(self._build_grouping_group())
        layout.addWidget(self._build_selection_group(), 1)
        layout.addWidget(self._build_database_group())
        layout.addWidget(self._build_parameters_group())

        button_row = QHBoxLayout()
        run_button = QPushButton(translate("Run SilverQuest Provenance"))
        run_button.setProperty('translate_key', 'Run SilverQuest Provenance')
        run_button.setDefault(True)
        run_button.clicked.connect(self._run_search)
        button_row.addWidget(run_button)
        self.run_button = run_button

        self.apply_button = QPushButton(translate("Apply to Data"))
        self.apply_button.setProperty('translate_key', 'Apply to Data')
        self.apply_button.setToolTip(
            translate("Write the roles back as a group column and make it active.")
        )
        self.apply_button.setEnabled(False)
        self.apply_button.clicked.connect(self._apply_to_data)
        button_row.addWidget(self.apply_button)

        self.export_button = QPushButton(translate("Export Hits"))
        self.export_button.setProperty('translate_key', 'Export Hits')
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self._export_hits)
        button_row.addWidget(self.export_button)
        button_row.addStretch()
        layout.addLayout(button_row)

        self.info_label = QLabel("")
        self.info_label.setWordWrap(True)
        # Survives the application-wide _NativeStyleFilter (see the sibling
        # neighbourhood dialog for the same marker).
        self.info_label.setProperty("keepStyle", True)
        self.info_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.info_label)

        self.result_table = QTableWidget()
        self.result_table.setColumnCount(6)
        self.result_table.setHorizontalHeaderLabels(
            [
                translate("Analysis"),
                translate("Country"),
                translate("Latitude"),
                translate("Longitude"),
                translate("Distance"),
                translate("Fractionation"),
            ]
        )
        self.result_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Stretch
        )
        layout.addWidget(self.result_table, 1)

        close_box = QDialogButtonBox(QDialogButtonBox.Close)
        close_box.rejected.connect(self.reject)
        layout.addWidget(close_box)

    def _build_grouping_group(self) -> QGroupBox:
        """The grouping column the two role lists are drawn from."""
        group = QGroupBox(translate("Grouping"))
        group.setProperty('translate_key', 'Grouping')
        form = QFormLayout(group)

        self.grouping_combo = QComboBox()
        self.grouping_combo.setMinimumWidth(240)
        self.grouping_combo.setToolTip(
            translate(
                "Column whose distinct values are assigned to the sample and "
                "reference roles."
            )
        )
        self.grouping_combo.currentIndexChanged.connect(self._on_grouping_changed)
        form.addRow(translate("Grouping Column:"), self.grouping_combo)

        self.visible_only_check = QCheckBox(
            translate("Offer only the groups currently visible in the legend")
        )
        self.visible_only_check.setProperty(
            'translate_key', 'Offer only the groups currently visible in the legend'
        )
        self.visible_only_check.toggled.connect(self._refresh_group_lists)
        form.addRow("", self.visible_only_check)

        self.grouping_status = QLabel("")
        self.grouping_status.setWordWrap(True)
        self.grouping_status.setProperty("keepStyle", True)
        form.addRow("", self.grouping_status)
        return group

    def _build_selection_group(self) -> QGroupBox:
        """Sample groups and reference groups, side by side."""
        group = QGroupBox(translate("Sample and Reference Groups"))
        group.setProperty('translate_key', 'Sample and Reference Groups')
        layout = QVBoxLayout(group)

        splitter = QSplitter(Qt.Horizontal)

        artefact_box = QGroupBox(translate("Sample Groups"))
        artefact_box.setProperty('translate_key', 'Sample Groups')
        artefact_layout = QVBoxLayout(artefact_box)
        self.artefact_list = QListWidget()
        self.artefact_list.setSelectionMode(
            QAbstractItemView.ExtendedSelection
        )
        self.artefact_list.setToolTip(
            translate("Samples to look up.")
        )
        artefact_layout.addWidget(self.artefact_list)
        artefact_buttons = QHBoxLayout()
        artefact_all = QPushButton(translate("All"))
        artefact_all.clicked.connect(lambda: self._select_all(self.artefact_list))
        artefact_buttons.addWidget(artefact_all)
        artefact_none = QPushButton(translate("None"))
        artefact_none.clicked.connect(lambda: self.artefact_list.clearSelection())
        artefact_buttons.addWidget(artefact_none)
        artefact_buttons.addStretch()
        artefact_layout.addLayout(artefact_buttons)
        splitter.addWidget(artefact_box)

        reference_box = QGroupBox(translate("Reference Groups"))
        reference_box.setProperty('translate_key', 'Reference Groups')
        reference_layout = QVBoxLayout(reference_box)
        self.reference_list = QListWidget()
        self.reference_list.setSelectionMode(
            QAbstractItemView.ExtendedSelection
        )
        self.reference_list.setToolTip(
            translate("Ores the samples are compared against.")
        )
        reference_layout.addWidget(self.reference_list)
        reference_buttons = QHBoxLayout()
        reference_all = QPushButton(translate("All"))
        reference_all.clicked.connect(lambda: self._select_all(self.reference_list))
        reference_buttons.addWidget(reference_all)
        reference_none = QPushButton(translate("None"))
        reference_none.clicked.connect(lambda: self.reference_list.clearSelection())
        reference_buttons.addWidget(reference_none)
        reference_buttons.addStretch()
        reference_layout.addLayout(reference_buttons)
        splitter.addWidget(reference_box)

        layout.addWidget(splitter, 1)

        self.selection_status = QLabel("")
        self.selection_status.setWordWrap(True)
        self.selection_status.setProperty("keepStyle", True)
        layout.addWidget(self.selection_status)

        self.artefact_list.itemSelectionChanged.connect(self._update_selection_status)
        self.reference_list.itemSelectionChanged.connect(self._update_selection_status)
        return group

    def _build_database_group(self) -> QGroupBox:
        group = QGroupBox(translate("Optional Extra References"))
        group.setProperty('translate_key', 'Optional Extra References')
        layout = QVBoxLayout(group)

        self.use_database_check = QCheckBox(
            translate("Add the galena reference database")
        )
        self.use_database_check.setProperty(
            'translate_key', 'Add the galena reference database'
        )
        self.use_database_check.setToolTip(
            translate(
                "Used when no reference group is selected, or in addition to the "
                "reference groups."
            )
        )
        self.use_database_check.toggled.connect(self._update_selection_status)
        layout.addWidget(self.use_database_check)

        row = QHBoxLayout()
        self.database_edit = QLineEdit()
        self.database_edit.setText(str(silverquest_database_path(None)))
        self.database_edit.setToolTip(
            translate("Path to Pb_DB_20240310AllGalenas.xlsx.")
        )
        row.addWidget(self.database_edit, 1)
        browse = QPushButton(translate("Browse..."))
        browse.setProperty('translate_key', 'Browse...')
        browse.clicked.connect(self._browse_database)
        row.addWidget(browse)
        layout.addLayout(row)

        self.database_status = QLabel("")
        self.database_status.setWordWrap(True)
        self.database_status.setProperty("keepStyle", True)
        layout.addWidget(self.database_status)
        return group

    def _build_parameters_group(self) -> QGroupBox:
        """Mirrors the numeric Shiny inputs of R lines 80-87."""
        group = QGroupBox(translate("Analysis Parameters"))
        group.setProperty('translate_key', 'Analysis Parameters')
        form = QFormLayout(group)

        self.normalization_combo = QComboBox()
        for choice in silverquest_normalizations():
            self.normalization_combo.addItem(choice, choice)
        self.normalization_combo.setToolTip(
            translate("Normalise the ratios to 204Pb or to 206Pb.")
        )
        form.addRow(translate("Normalization:"), self.normalization_combo)

        # R line 85: numericInput("dmax", "Maximum distance between ore and no ?",
        # 3, min = 1, max = 10).  The port keeps the R default and range.
        self.dmax_spin = QDoubleSpinBox()
        self.dmax_spin.setRange(1.0, 10.0)
        self.dmax_spin.setSingleStep(0.1)
        self.dmax_spin.setDecimals(3)
        self.dmax_spin.setValue(3.0)
        self.dmax_spin.setToolTip(
            translate(
                "Maximum distance between ore and analysis. Larger values keep more hits."
            )
        )
        form.addRow(translate("Maximum distance:"), self.dmax_spin)

        # R line 83-84: jitter "Yes"/"No" plus numericInput Radius 0.01 step 0.005.
        jitter_row = QHBoxLayout()
        self.jitter_check = QCheckBox(translate("Apply Jitter"))
        self.jitter_check.setProperty('translate_key', 'Apply Jitter')
        self.jitter_check.setChecked(True)
        jitter_row.addWidget(self.jitter_check)
        self.radius_spin = QDoubleSpinBox()
        self.radius_spin.setRange(0.0, 1.0)
        self.radius_spin.setSingleStep(0.005)
        self.radius_spin.setDecimals(3)
        self.radius_spin.setValue(0.01)  # R line 84 default
        self.radius_spin.setEnabled(True)
        jitter_row.addWidget(QLabel(translate("Jitter Radius:")))
        jitter_row.addWidget(self.radius_spin)
        jitter_row.addStretch()
        self.jitter_check.toggled.connect(self.radius_spin.setEnabled)
        form.addRow(translate("Jitter:"), jitter_row)

        return group

    # ── grouping column and group lists ────────────────────────────────
    def _populate_grouping_columns(self) -> None:
        """Fill the grouping-column combo from the data panel's declarations."""
        frame = app_state.df_global
        candidates = candidate_group_columns(
            frame, list(app_state.group_cols or [])
        )
        self.grouping_combo.blockSignals(True)
        try:
            self.grouping_combo.clear()
            for column in candidates:
                self.grouping_combo.addItem(str(column), str(column))
        finally:
            self.grouping_combo.blockSignals(False)

    def _on_grouping_changed(self, *_args) -> None:
        self._refresh_group_lists()

    def _grouping_column(self) -> str | None:
        data = self.grouping_combo.currentData()
        return str(data) if data is not None else None

    def _candidate_groups(self) -> list[str]:
        """Distinct values of the grouping column, subject to legend visibility."""
        frame = app_state.df_global
        column = self._grouping_column()
        if frame is None or not column or column not in frame.columns:
            return []
        values_series = frame[column].fillna("Unknown").astype(str)
        groups = sorted(set(values_series.tolist()), key=str)
        visible = app_state.visible_groups
        if self.visible_only_check.isChecked() and visible:
            allowed = {str(group) for group in visible}
            groups = [group for group in groups if group in allowed]
        return groups

    def _group_counts(self) -> dict[str, int]:
        frame = app_state.df_global
        column = self._grouping_column()
        if frame is None or not column or column not in frame.columns:
            return {}
        values_series = frame[column].fillna("Unknown").astype(str)
        return {str(key): int(value) for key, value in values_series.value_counts().items()}

    def _refresh_group_lists(self) -> None:
        """Rebuild both role lists, preserving whatever is still selectable."""
        keep_artefacts = set(self._pending_artefact_groups) or set(
            self.selected_artefact_groups()
        )
        keep_references = set(self._pending_reference_groups) or set(
            self.selected_reference_groups()
        )
        self._pending_artefact_groups = []
        self._pending_reference_groups = []
        groups = self._candidate_groups()
        counts = self._group_counts()

        for widget, keep in (
            (self.artefact_list, keep_artefacts),
            (self.reference_list, keep_references),
        ):
            widget.blockSignals(True)
            try:
                widget.clear()
                for group in groups:
                    item = QListWidgetItem(
                        translate("{group} ({count} rows)").format(
                            group=group, count=counts.get(group, 0)
                        )
                    )
                    item.setData(Qt.UserRole, group)
                    widget.addItem(item)
                    item.setSelected(group in keep)
            finally:
                widget.blockSignals(False)
        self._update_selection_status()

    @staticmethod
    def _select_all(widget: QListWidget) -> None:
        widget.selectAll()

    @staticmethod
    def _selected_groups(widget: QListWidget) -> list[str]:
        return [
            str(item.data(Qt.UserRole))
            for item in widget.selectedItems()
            if item.data(Qt.UserRole) is not None
        ]

    def selected_artefact_groups(self) -> list[str]:
        return self._selected_groups(self.artefact_list)

    def selected_reference_groups(self) -> list[str]:
        return self._selected_groups(self.reference_list)

    def _selected_groups_for_run(self) -> tuple[list[str], list[str]]:
        """Resolve the two role selections for the search.

        A group selected on both sides is a contradiction; the reference role
        wins and the artefact side drops it, which is reported in the status
        line rather than silently searched twice.
        """
        references = self.selected_reference_groups()
        reference_set = set(references)
        artefacts = [
            group
            for group in self.selected_artefact_groups()
            if group not in reference_set
        ]
        return artefacts, references

    def _update_selection_status(self, *_args) -> None:
        artefacts, references = self._selected_groups_for_run()
        overlap = set(self.selected_artefact_groups()) & set(
            self.selected_reference_groups()
        )
        counts = self._group_counts()
        parts = [
            translate("Samples: {groups} group(s), {rows} row(s)").format(
                groups=len(artefacts),
                rows=sum(counts.get(group, 0) for group in artefacts),
            ),
            translate("References: {groups} group(s), {rows} row(s)").format(
                groups=len(references),
                rows=sum(counts.get(group, 0) for group in references),
            ),
        ]
        if self.use_database_check.isChecked():
            parts.append(translate("plus the galena database"))
        if overlap:
            parts.append(
                translate("groups selected on both sides are used as references")
            )
        self.selection_status.setText("  |  ".join(parts))

    # ── saved parameters ───────────────────────────────────────────────
    def _restore_saved_params(self) -> None:
        """Re-apply the declarative state the last run persisted."""
        params = state_gateway.get_silverquest_params() or {}
        if not params:
            return
        column = params.get("group_col")
        if column:
            index = self.grouping_combo.findData(str(column))
            if index >= 0:
                self.grouping_combo.setCurrentIndex(index)
        self.visible_only_check.setChecked(bool(params.get("visible_only", False)))
        self.use_database_check.setChecked(bool(params.get("use_database", False)))
        self._pending_artefact_groups = [str(v) for v in params.get("artefact_groups", [])]
        self._pending_reference_groups = [str(v) for v in params.get("reference_groups", [])]
        if params.get("database_path"):
            self.database_edit.setText(str(params["database_path"]))
        normalization = params.get("normalization")
        if normalization is not None:
            index = self.normalization_combo.findData(normalization)
            if index >= 0:
                self.normalization_combo.setCurrentIndex(index)
        if params.get("dmax") is not None:
            self.dmax_spin.setValue(float(params["dmax"]))
        if params.get("jittered") is not None:
            self.jitter_check.setChecked(bool(params["jittered"]))
        if params.get("jitter_radius") is not None:
            self.radius_spin.setValue(float(params["jitter_radius"]))

    def _persist_params(self, artefact_groups, reference_groups) -> None:
        """Write the selection through the gateway (declarative state pattern).

        The field is declared once in ``core/state/fields.py`` and listed in
        ``core/persistence/schema.py``; the gateway is the only writer, so the
        StateStore snapshot and the saved session cannot drift from the dialog.
        """
        state_gateway.set_silverquest_params(
            {
                "group_col": self._grouping_column(),
                "artefact_groups": list(artefact_groups),
                "reference_groups": list(reference_groups),
                "use_database": self.use_database_check.isChecked(),
                "database_path": self.database_edit.text() or None,
                "visible_only": self.visible_only_check.isChecked(),
                "normalization": self.normalization_combo.currentData(),
                "dmax": float(self.dmax_spin.value()),
                "jittered": bool(self.jitter_check.isChecked()),
                "jitter_radius": float(self.radius_spin.value()),
            }
        )

    # ── database handling ──────────────────────────────────────────────
    def _browse_database(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            translate("Select Galena Database"),
            "",
            translate("Excel Files (*.xlsx *.xls)"),
        )
        if path:
            self.database_edit.setText(path)
            self._check_database()

    def _database_path_for_run(self) -> str | None:
        """The workbook path to use when the extra reference set is enabled."""
        if not self.use_database_check.isChecked():
            return None
        return self.database_edit.text() or None

    def _check_database(self) -> None:
        """Report whether the workbook can be read, before any click."""
        status = silverquest_database_status(self.database_edit.text() or None)
        if status.missing:
            self._database_ok = False
            self.database_status.setText(
                translate("Database not found: {path}").format(path=status.path)
            )
            return
        if not status.readable:
            self._database_ok = False
            self.database_status.setText(
                translate("Database could not be read: {error}").format(error=status.error)
            )
            return
        self._database_ok = True
        self.database_status.setText(
            translate("Database loaded: {count} ore analyses.").format(count=status.rows)
        )

    # ── search ─────────────────────────────────────────────────────────
    def _plugin(self):
        from plugins.registry import plugin_manager

        plugin = plugin_manager.get("silverquest_plugin")
        if plugin is None:
            # The app loads plugins at startup (ui/app.py), but a dialog opened
            # from a test harness or a headless session may not have run it yet.
            plugin = plugin_manager.load_plugin("silverquest_plugin")
        return plugin

    def _collect_run_params(self) -> dict | None:
        """Validate the form and snapshot it on the main thread.

        Returns the ``run_silverquest_on_groups`` keyword arguments, or ``None``
        after warning the user.  The worker closure must not read Qt widgets, so
        every value is copied here.
        """
        frame = app_state.df_global
        if frame is None:
            QMessageBox.warning(
                self, translate("Warning"), translate("Please load data first.")
            )
            return None

        column = self._grouping_column()
        if not column:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("Please select a grouping column."),
            )
            return None

        artefact_groups, reference_groups = self._selected_groups_for_run()
        if not artefact_groups:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("Please select at least one sample group."),
            )
            return None
        database_path = self._database_path_for_run()
        if not reference_groups and not database_path:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate(
                    "Please select at least one reference group or enable the "
                    "galena database."
                ),
            )
            return None
        if not reference_groups and database_path:
            # The workbook is the only reference set: verify it before the run so
            # the user gets the message here instead of an exception later.
            resolved = silverquest_database_path(database_path)
            if not resolved.is_file():
                QMessageBox.warning(
                    self,
                    translate("Warning"),
                    translate("Database not found: {path}").format(path=str(resolved)),
                )
                return None

        try:
            self._plugin()
        except Exception as error:  # pragma: no cover - startup misconfiguration
            logger.error("SilverQuest plugin unavailable: %s", error)
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("SilverQuest plugin not loaded."),
            )
            return None

        try:
            resolve_artefact_columns(frame.columns)
        except KeyError as error:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("Missing columns for SilverQuest: {error}").format(
                    error=str(error)
                ),
            )
            return None

        self._persist_params(artefact_groups, reference_groups)
        return {
            "group_col": column,
            "artefact_groups": list(artefact_groups),
            "reference_groups": list(reference_groups),
            "database_path": database_path,
            "normalization": self.normalization_combo.currentData(),
            "dmax": float(self.dmax_spin.value()),
            "jittered": bool(self.jitter_check.isChecked()),
            "jitter_radius": float(self.radius_spin.value()),
        }

    def _search_payload(self, frame=None, run_params: dict | None = None) -> dict | None:
        """Run the search and show it.  The synchronous core of the dialog.

        Kept separate from :meth:`_run_search` (which wraps it in a worker so the
        GUI stays responsive) so the whole select→search→display path can be
        driven from a test without an event loop.
        """
        frame = app_state.df_global if frame is None else frame
        if frame is None:
            return None
        params = self._collect_run_params() if run_params is None else run_params
        if params is None:
            return None

        payload = self._plugin().search_groups(frame, **params)
        self._payload = payload
        self._result = payload["result"]
        self._records = build_artefact_records(
            frame.iloc[payload["artefact_indices"]]
        )
        self._populate_results(payload)
        self.apply_button.setEnabled(True)
        self.export_button.setEnabled(True)
        return payload

    def _run_search(self) -> None:
        """Run the search off the GUI thread and show the hits when it lands."""
        if app_state.df_global is None:
            QMessageBox.warning(
                self, translate("Warning"), translate("Please load data first.")
            )
            return
        run_params = self._collect_run_params()
        if run_params is None:
            return

        if self._search_worker is not None and self._search_worker.isRunning():
            QMessageBox.information(
                self,
                translate("Info"),
                translate("A SilverQuest search is already running."),
            )
            return

        frame_input = app_state.df_global.copy()

        def _search():
            return self._plugin().search_groups(frame_input, **run_params)

        from ui.panels.analysis.dialogs.analysis_worker import AnalysisWorker

        def _on_finished(payload):
            _restore_wait_cursor()
            self._search_worker = None
            self.run_button.setEnabled(True)
            self._payload = payload
            self._result = payload["result"]
            self._records = build_artefact_records(
                frame_input.iloc[payload["artefact_indices"]]
            )
            self._populate_results(payload)
            self.apply_button.setEnabled(True)
            self.export_button.setEnabled(True)

        def _on_failed(message):
            _restore_wait_cursor()
            self._search_worker = None
            self.run_button.setEnabled(True)
            logger.error("SilverQuest search failed: %s", message)
            QMessageBox.critical(
                self,
                translate("Error"),
                translate("SilverQuest search failed: {error}").format(error=message),
            )

        from PyQt5.QtCore import Qt as _Qt
        from PyQt5.QtWidgets import QApplication

        QApplication.setOverrideCursor(_Qt.WaitCursor)
        self.run_button.setEnabled(False)
        self._search_worker = AnalysisWorker(_search)
        self._search_worker.finished_signal.connect(_on_finished)
        self._search_worker.failed.connect(_on_failed)
        self._search_worker.start()

    def closeEvent(self, event):
        from ui.panels.analysis.dialogs.analysis_worker import stop_analysis_worker

        stop_analysis_worker(self._search_worker)
        super().closeEvent(event)

    def _populate_results(self, payload: dict) -> None:
        """Fill the hit table, closest hit first.

        The R script stores ``T2`` sorted *decreasing* by distance because the
        plotting code draws it in that order so the closest point lands on top
        (R line 372).  A table reads top-down, so this reverses that internal
        order for display; ``SilverQuestArtifactResult.hits`` keeps the R order.
        """
        result = self._result
        rows: list[tuple] = []
        for artifact in result.artifacts:
            for hit in reversed(artifact.hits):
                rows.append(
                    (
                        artifact.no,
                        hit["Country"],
                        f"{hit['Latitude']:.3f}",
                        f"{hit['Longitude']:.3f}",
                        f"{hit['dist']:.4f}",
                        f"{hit['fract'] * 1000.0:.3f}",
                    )
                )
        total_rows = len(rows)
        displayed = rows[:MAX_DISPLAY_ROWS]

        self.result_table.setUpdatesEnabled(False)
        try:
            self.result_table.setRowCount(len(displayed))
            for index, values in enumerate(displayed):
                for column, value in enumerate(values):
                    self.result_table.setItem(
                        index, column, QTableWidgetItem(str(value))
                    )
        finally:
            self.result_table.setUpdatesEnabled(True)
        self.result_table.resizeColumnsToContents()

        summary = f"{result.config.normalization}, dmax={result.config.dmax:g}"
        source = payload.get("reference_source")
        if source == "groups":
            source_text = translate("references: {count} selected row(s)").format(
                count=payload.get("reference_rows", 0)
            )
        elif source == "workbook":
            source_text = translate("references: galena database ({count} rows)").format(
                count=payload.get("reference_rows", 0)
            )
        else:  # pragma: no cover - the search refuses to run without references
            source_text = translate("references: none")
        if total_rows > MAX_DISPLAY_ROWS:
            self.info_label.setText(
                translate(
                    "SilverQuest ({summary}, {source}): showing the {shown} closest "
                    "of {total} hits; export for the full list."
                ).format(
                    summary=summary,
                    source=source_text,
                    shown=MAX_DISPLAY_ROWS,
                    total=total_rows,
                )
            )
        else:
            self.info_label.setText(
                translate("SilverQuest ({summary}, {source}): {total} hits.").format(
                    summary=summary, source=source_text, total=total_rows
                )
            )
        counts_text = role_counts_text(payload)
        if counts_text:
            # The table shows the matches; this line shows the split behind them.
            self.info_label.setText(self.info_label.text() + "\n" + counts_text)
        if any(artifact.colour_index_clamped for artifact in result.artifacts):
            # R-QUIRK made visible rather than silent: nocol is scaled by the
            # dmax parameter, so it can run past the colour ramp.
            self.info_label.setText(
                self.info_label.text()
                + " "
                + translate(
                    "Colour indices exceeded the ramp and were clamped; lower the "
                    "maximum distance."
                )
            )
        logger.info(
            "SilverQuest dialog: %s (references from %s, %d hit rows, %d displayed)",
            result.summary(),
            source,
            total_rows,
            len(displayed),
        )

    # ── results in the application ─────────────────────────────────────
    def _apply_to_data(self) -> None:
        """Write the roles back as a group column and make it the active grouping.

        This is how the outcome reaches the plot: the application colours points
        by the grouping column, lists its values in the legend and lets the
        legend checkboxes hide them, so ``[Sample Matched]``/
        ``[Sample Unmatched]``/``[Reference Matched]``/``[Reference Unmatched]``/
        ``[Other Data]`` need no separate drawing path.  A row's role is its own
        outcome, so one grouping value can contribute both a matched and an
        unmatched label.
        """
        if self._payload is None or app_state.df_global is None:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("Please run the search first."),
            )
            return

        frame = app_state.df_global.copy()
        roles = list(self._payload.get("applied_column", []))
        if len(roles) != len(frame):
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate(
                    "The data changed since the search; run it again before applying."
                ),
            )
            return
        frame[ROLE_COLUMN] = roles

        # Commit through the gateway so the StateStore snapshot stays in sync;
        # direct app_state.df_global writes bypass it and are silently lost.
        state_gateway.set_dataframe_and_source(
            frame,
            file_path=app_state.file_path,
            sheet_name=app_state.sheet_name,
        )

        groups = list(app_state.group_cols or [])
        if ROLE_COLUMN not in groups:
            groups.append(ROLE_COLUMN)
        state_gateway.set_group_data_columns(groups, list(app_state.data_cols or []))
        state_gateway.set_last_group_col(ROLE_COLUMN)
        state_gateway.set_visible_groups(None)
        state_gateway.bump_data_version()

        try:
            from visualization.events import on_slider_change

            on_slider_change()
        except Exception as notify_err:  # pragma: no cover - headless harness
            logger.warning("Failed to refresh the plot after applying: %s", notify_err)

        QMessageBox.information(
            self,
            translate("Done"),
            translate("Roles added as group column {column}.").format(
                column=ROLE_COLUMN
            ),
        )

    def _export_hits(self) -> None:
        """Write the hit table the R script accumulated into ``hits.xlsx``."""
        if self._result is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            translate("Export Hits"),
            "",
            translate("CSV (*.csv);;Excel (*.xlsx)"),
        )
        if not path:
            return

        rows: list[dict] = []
        for artifact in self._result.artifacts:
            for hit in artifact.hits:
                row = dict(hit)
                row["analysis"] = artifact.no
                rows.append(row)
        try:
            frame = pd.DataFrame(rows)
            if path.lower().endswith(".csv"):
                frame.to_csv(path, index=False, encoding="utf-8-sig")
            else:
                frame.to_excel(path, index=False)
        except Exception as error:
            logger.exception("SilverQuest export failed: %s", error)
            QMessageBox.critical(
                self,
                translate("Error"),
                translate("Export failed: {error}").format(error=str(error)),
            )
            return
        QMessageBox.information(
            self,
            translate("Done"),
            translate("Data exported to: {path}").format(path=path),
        )


def show_silverquest(parent=None) -> None:
    """Open the SilverQuest dialog, warning when the session cannot support it."""
    if app_state.df_global is None:
        QMessageBox.warning(
            parent if parent else None,
            translate("Warning"),
            translate("Please load data first."),
        )
        return
    dialog = SilverQuestDialog(parent)
    dialog.exec_()


def _restore_wait_cursor() -> None:
    """Undo the wait cursor a search sets, whatever the outcome.

    Qt restores an override cursor only when asked. Both result paths used to return without asking,
    so after a search the whole application kept showing a busy cursor - which is what "it freezes as
    soon as I run it" looked like, with the search itself finishing in about 84 ms for 20 artefacts
    against 90 references. Draining the stack also covers a search started while another cursor was
    already overridden.
    """
    from PyQt5.QtWidgets import QApplication

    while QApplication.overrideCursor() is not None:
        QApplication.restoreOverrideCursor()
