"""Builtin SilverQuest provenance plugin — Pb-isotope ore-distance search.

Hosts the port of the R reference implementation ``SilverQuest_R_v1.R``; the
algorithm itself lives in :mod:`adapters.silverquest`, which carries the full
provenance, attribution and licence note.  This module is the extension-point
adapter: metadata, environment validation, defaults, the *integration* glue that
turns the application's loaded data into the R script's two inputs, and the
analysis-panel UI.

The R script takes its two inputs from two workbooks: the artefact file (R line
5: ``no``, ``group`` and the three Pb ratios) and the galena
database (R line 139, ``read_excel(...)``).  This application already holds one
loaded dataframe with a chosen grouping column, so the primary path here is:

* **artefacts** = the rows of the grouping-column values the user assigned to
  the artefact role,
* **references** = the rows of the grouping-column values the user assigned to
  the reference role,

and the R package's galena workbook is one *additional, optional* source of
references (:func:`resolve_references`), not the interface.  Both paths produce
the same :class:`adapters.silverquest.SilverQuestDatabase`, so the numeric core is
untouched and cannot tell them apart.

Throughout the application the two sides are called **Sample** and
**Reference**; the R port and :mod:`adapters.silverquest` call them the artefact
file and the ore database, so "artefact" in this module's parameters, helpers
and docstrings means "sample", and "reference" means one ore-database row.

Registered like every other builtin: the file stem ``silverquest_plugin`` is the
PluginManager key, ``meta.name`` (``silverquest``) is the fallback lookup, and
``ui/panels/analysis/build.py`` maps the key to the analysis-panel callback.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from plugins.api import BasePlugin, PluginMeta

logger = logging.getLogger(__name__)

__all__ = [
    # 角色标签（写回数据的分组列取值）
    "ROLE_OTHER",
    "ROLE_REFERENCE_MATCHED_PREFIX",
    "ROLE_REFERENCE_UNMATCHED_PREFIX",
    "ROLE_SAMPLE_MATCHED_PREFIX",
    "ROLE_SAMPLE_UNMATCHED_PREFIX",
    # 数据源探询（Qt 层只经这里，不直接 import adapters.silverquest）
    "SilverQuestDatabaseStatus",
    "silverquest_database_path",
    "silverquest_database_status",
    "silverquest_normalizations",
    # 插件与入口
    "SilverQuestPlugin",
    "resolve_references",
    "run_silverquest_on_groups",
    "run_silverquest_search",
]


@dataclass(frozen=True)
class SilverQuestDatabaseStatus:
    """What the galena workbook is worth right now.

    The numeric core stays behind this plugin surface: a Qt panel asks here instead of
    importing :mod:`adapters.silverquest` itself (docs/dev_conventions.md §18.1: the UI reaches
    the domain through the orchestration layer, here the plugin's own public API).

    ``missing`` and ``error`` are reported as they are - a file that is not there, or cannot
    be parsed, is an answer, never something to paper over with a substitute.
    """

    path: str
    readable: bool = False
    missing: bool = False
    rows: int = 0
    error: str = ""


def silverquest_normalizations() -> tuple[str, ...]:
    """The normalisations the numeric core accepts (R: "Select Normalization:")."""
    from adapters.silverquest import NORMALIZATIONS

    return tuple(NORMALIZATIONS)


def silverquest_database_path(path: str | os.PathLike[str] | None = None) -> Path:
    """Resolve the galena workbook path (explicit → env override → repository default)."""
    from adapters.silverquest import resolve_database_path

    return resolve_database_path(path)


def silverquest_database_status(
    path: str | os.PathLike[str] | None = None,
) -> SilverQuestDatabaseStatus:
    """Report whether the galena workbook can be read, and how many ores it holds."""
    from adapters.silverquest import load_silverquest_database, resolve_database_path

    resolved = resolve_database_path(path)
    if not resolved.is_file():
        return SilverQuestDatabaseStatus(path=str(resolved), missing=True)
    try:
        database = load_silverquest_database(resolved)
    except Exception as error:  # a corrupt workbook is a real answer, reported to the caller
        logger.warning("SilverQuest workbook unreadable: %s", error)
        return SilverQuestDatabaseStatus(path=str(resolved), error=str(error))
    return SilverQuestDatabaseStatus(path=str(resolved), readable=True, rows=database.n_rows)

#: Prefixes of the grouping values the plugin writes back into the dataframe
#: when the user applies a run.  They are ordinary group labels for the rest of
#: the application: the plot colours them, the legend lists them and the legend
#: checkboxes hide them, exactly like any other group column.
#:
#: The two sides of the search each get the same matched/unmatched pair, so the
#: legend reads symmetrically (``[Sample Matched]`` next to
#: ``[Reference Matched]``), and a row that never entered the matching is neither
#: of them:
#:
#: * :data:`ROLE_SAMPLE_MATCHED_PREFIX` — a sample that hit at least one reference;
#: * :data:`ROLE_SAMPLE_UNMATCHED_PREFIX` — a sample that entered and hit nothing;
#: * :data:`ROLE_REFERENCE_MATCHED_PREFIX` — a reference that was hit;
#: * :data:`ROLE_REFERENCE_UNMATCHED_PREFIX` — a reference that entered and was hit
#:   by nothing;
#: * :data:`ROLE_OTHER` — a row that never entered the matching (unusable ratios,
#:   or simply not selected for either side).
#:
#: "Sample" and "Reference" are the application's words for the two sides.  The R
#: port calls them the artefact file and the ore database, and the numeric core in
#: :mod:`adapters.silverquest` keeps those names; the mapping is Sample == artefact,
#: Reference == ore database row.
ROLE_SAMPLE_MATCHED_PREFIX = "[Sample Matched] "
ROLE_SAMPLE_UNMATCHED_PREFIX = "[Sample Unmatched] "
ROLE_REFERENCE_MATCHED_PREFIX = "[Reference Matched] "
ROLE_REFERENCE_UNMATCHED_PREFIX = "[Reference Unmatched] "
ROLE_OTHER = "[Other Data]"


def resolve_references(
    references: Iterable[dict[str, Any]] | None = None,
    *,
    database_path: str | None = None,
):
    """Resolve the reference ore table from the selection and/or the workbook.

    Precedence — the in-session reference rows always come first because they
    are the application's own data, and the R package's workbook is an optional
    extra set:

    1. ``references`` given: those rows become the reference set (the primary
       path), and the workbook is *not* read even when a path is configured.
    2. ``references`` empty and ``database_path`` (or the resolved default)
       present: the galena workbook is read.
    3. neither: the workbook loader runs anyway so its ``FileNotFoundError``
       names the expected location and the environment override — the caller
       surfaces that message.

    Returns:
        ``(database, source)`` where *source* is ``"groups"``, ``"workbook"``
        or ``"missing"`` — the label the dialog shows, so the user can tell
        which set of references a hit table came from.
    """
    from adapters.silverquest import database_from_records, load_silverquest_database

    rows = list(references or [])
    if rows:
        return database_from_records(rows), "groups"
    try:
        return load_silverquest_database(database_path), "workbook"
    except FileNotFoundError:
        logger.info(
            "SilverQuest: no in-session references and no workbook at %s",
            database_path,
        )
        return None, "missing"


def run_silverquest_search(
    records: list[dict[str, Any]],
    *,
    references: Iterable[dict[str, Any]] | None = None,
    normalization: str = "204Pb",
    dmax: float = 3.0,
    jittered: bool = True,
    jitter_radius: float = 0.01,
    database_path: str | None = None,
    seed: int | None = None,
) -> dict[str, Any]:
    """Run the ported SilverQuest search over *records*.

    Kept deliberately thin and free of Qt so the plugin's numeric entry point can
    be exercised without a QApplication (the panel and dialog import the same
    function through :meth:`SilverQuestPlugin.search`).

    Args:
        records: artefact rows with ``no, group, Pb206204, Pb207204,
            Pb208204`` (R input format, R line 5); the application's
            ``Pb206_204`` spelling is accepted as an alias.
        references: in-memory reference rows (the same shape, with optional
            ``Country``/``Latitude``/``Longitude``).  When given, this is the
            reference set; when empty, *database_path* is read instead.
        normalization: ``"204Pb"`` or ``"206Pb"`` (R Shiny input).
        dmax: hit cut-off (R Shiny input, default 3).
        jittered: apply the R jitter (R Shiny input, default "Yes").
        jitter_radius: ``r0``; the R script draws inside ``r0/5``.
        database_path: override for the galena workbook.
        seed: optional seed for the jitter draw (R's ``runif`` is unseeded).

    Returns:
        ``{"result": SilverQuestResult, "summary": str, "reference_source":
        str, "reference_rows": int}``.

    Raises:
        FileNotFoundError: no in-memory references and no workbook — the message
            names the expected location of the R package's database.
        ValueError: no usable artefact or reference row.
    """
    from adapters.silverquest import (
        SilverQuestConfig,
        artifacts_from_records,
        run_silverquest,
    )

    database, source = resolve_references(references, database_path=database_path)
    if database is None:
        # Re-run without the guard so the loader raises its descriptive error.
        from adapters.silverquest import load_silverquest_database

        load_silverquest_database(database_path)

    config = SilverQuestConfig(
        normalization=normalization,
        dmax=float(dmax),
        jittered=bool(jittered),
        jitter_radius=float(jitter_radius),
    )
    artifacts = artifacts_from_records(records)
    result = run_silverquest(artifacts, database, config, seed=seed)
    logger.info("SilverQuest: %s (references from %s)", result.summary(), source)
    return {
        "result": result,
        "summary": result.summary(),
        "reference_source": source,
        "reference_rows": database.n_rows,
    }


def run_silverquest_on_groups(
    frame,
    group_col: str,
    artefact_groups: Iterable[Any],
    reference_groups: Iterable[Any] = (),
    *,
    database_path: str | None = None,
    normalization: str = "204Pb",
    dmax: float = 3.0,
    jittered: bool = True,
    jitter_radius: float = 0.01,
    seed: int | None = None,
) -> dict[str, Any]:
    """Select samples and references *by grouping column value* and run.

    This is the integration entry point the dialog calls, and the one the tests
    drive: the dataframe and the grouping column are the application's own, and
    the two group selections decide which rows play which role.  Rows whose
    group is in neither selection stay out of the search.

    The returned ``roles`` maps dataframe row positions back to what the row *was
    for this run* — one of the role prefixes documented above (``[Sample Matched]``,
    ``[Sample Unmatched]``, ``[Reference Matched]``, ``[Reference Unmatched]``,
    ``[Other Data]``).  Each row is decided on its own, so a grouping value holding
    both a matched and an unmatched row yields both labels; a row whose ratios are
    unusable carries ``[Other Data]`` because it never entered the matching.
    ``role_counts`` reports the same split numerically (selected / entered /
    matched / unmatched / excluded, per side) for the dialog's result line, and
    ``matches`` records each sample's nearest reference (within *dmax*) so the
    outcome is visible away from the hit table.

    Raises:
        ValueError: the grouping column is absent, nothing was selected for a
            role, or a selection produced no usable ratio row.
        FileNotFoundError: no reference group was selected and the galena
            workbook is not present.
    """
    from adapters.silverquest import (
        artefact_record_columns,
        records_from_frame,
        resolve_database_path,
    )

    if group_col not in getattr(frame, "columns", []):
        raise ValueError(f"SilverQuest: no grouping column {group_col!r} in the data")

    #: True when the R package's workbook can supply the references instead of a
    #: selected reference group.  An explicit override is trusted (the search
    #: reports a missing file); otherwise the resolved default must exist, so a
    #: stale ``$ISOTOPES_SILVERQUEST_DB`` cannot make an empty selection look
    #: usable.
    workbook_usable = bool(database_path) or resolve_database_path(None).is_file()

    artefact_values = [str(value) for value in artefact_groups]
    reference_values = [str(value) for value in reference_groups]
    if not artefact_values:
        raise ValueError("SilverQuest: no artefact group selected")
    if not reference_values and not workbook_usable:
        raise ValueError("SilverQuest: no reference group selected and no workbook")

    labels = frame[group_col].astype(str).reset_index(drop=True)
    columns = artefact_record_columns(frame.columns)
    positions = range(len(labels))

    def _positions(values: list[str]):
        """Dataframe row *positions* (not index labels) whose group is selected."""
        mask = labels.isin(values)
        return [int(position) for position in positions if bool(mask.iloc[position])]

    artefact_indices = _positions(artefact_values)
    reference_indices = _positions(reference_values)
    if not artefact_indices:
        raise ValueError(
            "SilverQuest: the selected artefact group(s) hold no rows in the "
            "grouping column"
        )
    if not reference_indices and not workbook_usable:
        raise ValueError(
            "SilverQuest: the selected reference group(s) hold no rows in the "
            "grouping column"
        )

    artefact_frame = frame.iloc[artefact_indices]
    artefact_records = records_from_frame(
        artefact_frame,
        columns,
        group_labels=labels.iloc[artefact_indices].tolist(),
    )
    reference_frame = (
        frame.iloc[reference_indices] if reference_indices else frame.iloc[0:0]
    )
    reference_records = records_from_frame(
        reference_frame,
        columns,
        group_labels=labels.iloc[reference_indices].tolist(),
    )

    payload = run_silverquest_search(
        artefact_records,
        references=reference_records,
        normalization=normalization,
        dmax=float(dmax),
        jittered=bool(jittered),
        jitter_radius=float(jitter_radius),
        database_path=database_path,
        seed=seed,
    )
    if not artefact_records:
        raise ValueError("SilverQuest: no usable artefact row for the selection")

    result = payload["result"]

    # ── outcome per row, per side ───────────────────────────────────────
    #
    # The direction is sample -> database: the sample is the query point and every
    # reference is a candidate source, tested one reference at a time by the
    # perpendicular distance from the sample to that reference's mass-fractionation
    # line.  Both sides get the same matched/unmatched pair, and the role is decided
    # one *row* at a time — one grouping value can hold both a matched and an
    # unmatched row, so a per-group decision would mark a whole group matched as soon
    # as a single sample hit something:
    #
    #   [Sample Matched]      a sample that hit at least one reference
    #   [Sample Unmatched]    a sample that entered the search and hit nothing
    #   [Reference Matched]   a reference that was hit
    #   [Reference Unmatched] a reference that entered and was hit by nothing
    #   [Other Data]          a row that never entered the matching
    #
    # ``role_by_group`` stays a group-level summary and no shape is attached to any
    # role, so one grouping column is drawn with a single marker throughout.

    def _entered_positions(records, selected_positions) -> dict[int, dict]:
        """Map every usable record back to the frame position it was built from.

        ``records_from_frame`` withholds a row whose ratios are unusable and stamps
        each record it keeps with the row position it came from, so a row that never
        entered the matching simply has no entry here.
        """
        mapping: dict[int, dict] = {}
        for record in records:
            local = int(record.get("source_position", -1))
            if 0 <= local < len(selected_positions):
                mapping[int(selected_positions[local])] = record
        return mapping

    roles: dict[int, str] = {}
    entered_samples = _entered_positions(artefact_records, artefact_indices)
    entered_references = _entered_positions(reference_records, reference_indices)

    # ``run_silverquest`` returns one result per input artefact, in the input order,
    # so record i belongs to result i; going through the position each record was
    # built from keeps that right even when a row in between was skipped.
    matched_samples: set[int] = set()
    if len(result.artifacts) != len(artefact_records):
        logger.warning(
            "SilverQuest: %d result(s) for %d usable sample record(s) - matched rows "
            "may be misreported",
            len(result.artifacts),
            len(artefact_records),
        )
    for record, artifact in zip(artefact_records, result.artifacts):
        local = int(record.get("source_position", -1))
        if artifact.n_hits > 0 and 0 <= local < len(artefact_indices):
            matched_samples.add(int(artefact_indices[local]))

    # Trace every hit back to the row of its own reference set, rather than
    # re-identifying rows by their values afterwards.  The in-session table is built
    # from ``reference_records`` in order and a hit carries ``no`` = its 1-based row
    # (R: no = 1:m0); the workbook loader instead stamps each hit with the workbook
    # row it came from.  If the record count and the table size ever disagree the
    # assumption is reported, not silently absorbed.
    reference_source = payload["reference_source"]
    matched_references: set[int] = set()
    matched_workbook_rows: set[int] = set()
    for artifact in result.artifacts:
        for hit in artifact.hits:
            if reference_source == "workbook":
                carried = int(hit.get("source_position", -1))
                matched_workbook_rows.add(
                    carried if carried >= 0 else int(hit.get("no", 0))
                )
                continue
            local = int(hit.get("no", 0)) - 1
            if 0 <= local < len(reference_indices):
                matched_references.add(int(reference_indices[local]))
    if entered_references and len(entered_references) != int(payload["reference_rows"]):
        logger.warning(
            "SilverQuest: %d usable reference record(s) for a %d-row reference table "
            "- hit rows cannot be traced back to the frame",
            len(entered_references),
            int(payload["reference_rows"]),
        )

    matches: list[dict[str, Any]] = []
    for artifact in result.artifacts:
        if not artifact.hits:
            matches.append(
                {
                    "artefact": str(artifact.no),
                    "nearest": "",
                    "distance": None,
                    "reference_group": "",
                }
            )
            continue
        nearest = artifact.hits[-1]  # hits are sorted closest-last (R line 372)
        matches.append(
            {
                "artefact": str(artifact.no),
                "nearest": str(nearest.get("no", "")),
                "distance": float(nearest["dist"]),
                "reference_group": str(nearest.get("Country", "")),
            }
        )

    # The role of a row is its own outcome, never its grouping value's: a sample
    # that hit nothing next to a sample that hit something is exactly the case the
    # two labels exist for.  A row that never entered the matching keeps
    # ``[Other Data]`` instead of being reported as an unmatched one.
    for position in artefact_indices:
        position = int(position)
        if position not in entered_samples:
            roles[position] = ROLE_OTHER
        elif position in matched_samples:
            roles[position] = ROLE_SAMPLE_MATCHED_PREFIX + str(labels.iloc[position])
        else:
            roles[position] = ROLE_SAMPLE_UNMATCHED_PREFIX + str(labels.iloc[position])
    for position in reference_indices:
        position = int(position)
        if position not in entered_references:
            roles[position] = ROLE_OTHER
        elif position in matched_references:
            roles[position] = ROLE_REFERENCE_MATCHED_PREFIX + str(labels.iloc[position])
        else:
            roles[position] = ROLE_REFERENCE_UNMATCHED_PREFIX + str(labels.iloc[position])

    def _group_outcomes(positions, entered, matched) -> dict[str, tuple[bool, bool]]:
        """Per grouping value: did any row enter the search, and did any row match?"""
        outcomes: dict[str, list[bool]] = {}
        for position in positions:
            position = int(position)
            flags = outcomes.setdefault(str(labels.iloc[position]), [False, False])
            if position in entered:
                flags[0] = True
            if position in matched:
                flags[1] = True
        return {
            label: (bool(flags[0]), bool(flags[1])) for label, flags in outcomes.items()
        }

    role_by_group: dict[str, str] = {}
    for label, (entered_any, matched_any) in _group_outcomes(
        artefact_indices, entered_samples, matched_samples
    ).items():
        if matched_any:
            role_by_group[label] = ROLE_SAMPLE_MATCHED_PREFIX
        elif entered_any:
            role_by_group[label] = ROLE_SAMPLE_UNMATCHED_PREFIX
        else:
            role_by_group[label] = ROLE_OTHER
    for label, (entered_any, matched_any) in _group_outcomes(
        reference_indices, entered_references, matched_references
    ).items():
        if matched_any:
            role_by_group[label] = ROLE_REFERENCE_MATCHED_PREFIX
        elif entered_any:
            role_by_group[label] = ROLE_REFERENCE_UNMATCHED_PREFIX
        else:
            role_by_group[label] = ROLE_OTHER

    # The counts the dialog shows next to the hit table, so the two sides and their
    # two outcomes are readable without reading the legend.
    if reference_source == "workbook":
        reference_counts = {
            "selected": 0,
            "entered": int(payload["reference_rows"]),
            "matched": len(matched_workbook_rows),
        }
    else:
        reference_counts = {
            "selected": len(reference_indices),
            "entered": len(entered_references),
            "matched": len(matched_references),
        }
    reference_counts["unmatched"] = max(
        0, reference_counts["entered"] - reference_counts["matched"]
    )
    reference_counts["excluded"] = max(
        0, reference_counts["selected"] - reference_counts["entered"]
    )
    role_counts = {
        "samples": {
            "selected": len(artefact_indices),
            "entered": len(entered_samples),
            "matched": len(matched_samples),
            "unmatched": len(entered_samples) - len(matched_samples),
            "excluded": len(artefact_indices) - len(entered_samples),
        },
        "references": reference_counts,
    }

    # Every row carries a role. "other" is the data that never entered the matching -
    # not the sample rows that entered and found nothing, and not a catch-all that
    # swallows the whole frame.
    applied = [ROLE_OTHER] * len(frame)
    for position, role in roles.items():
        applied[int(position)] = role

    return {
        "result": result,
        "summary": payload["summary"],
        "reference_source": reference_source,
        "reference_rows": payload["reference_rows"],
        "artefact_groups": artefact_values,
        "reference_groups": reference_values,
        "artefact_indices": artefact_indices,
        "reference_indices": reference_indices,
        "roles": roles,
        "role_by_group": role_by_group,
        "role_counts": role_counts,
        "matches": matches,
        "applied_column": applied,
        "reference_only": not reference_values,
    }


class SilverQuestPlugin(BasePlugin):
    """SilverQuest provenance search as an analysis plugin."""

    meta = PluginMeta(
        name="silverquest",
        version="1.0",
        api_version="1.0",
        plugin_type="analysis",
        author="IsotopesAnalyse",
        description=(
            "SilverQuest (Albarède et al. 2024): Pb-isotope provenance search by "
            "weighted distance from selected sample groups to selected "
            "reference groups, or to the galena reference database"
        ),
        source="builtin",
    )

    def validate_environment(self) -> tuple[bool, str]:
        """The numeric core needs only numpy/pandas, which are hard requirements."""
        try:
            import numpy  # noqa: F401
            import pandas  # noqa: F401
        except ImportError as error:  # pragma: no cover - both are hard deps
            return False, f"numpy/pandas not available: {error}"
        return True, "ok"

    def get_default_params(self) -> dict[str, Any]:
        """Defaults for the numeric R Shiny inputs (R lines 80-87).

        The same R form also collected a map window and a basemap style for its
        own plotting; neither reaches the search, so neither is offered.
        """
        return {
            "normalization": "204Pb",
            "dmax": 3.0,
            "jittered": True,
            "jitter_radius": 0.01,
        }

    def search(self, records: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        """Run the search; see :func:`run_silverquest_search`."""
        return run_silverquest_search(records, **kwargs)

    def search_groups(
        self,
        frame,
        group_col: str,
        artefact_groups: Iterable[Any],
        reference_groups: Iterable[Any] = (),
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Run the grouping-column search; see :func:`run_silverquest_on_groups`."""
        return run_silverquest_on_groups(
            frame, group_col, artefact_groups, reference_groups, **kwargs
        )

    def database_available(self, database_path: str | None = None) -> tuple[bool, str]:
        """Report whether the galena workbook can be found.

        The R package's workbook is an optional extra reference set, so the
        dialog reports this instead of requiring it.
        """
        from adapters.silverquest import (
            SILVERQUEST_DB_ENV_VAR,
            resolve_database_path,
        )

        resolved = resolve_database_path(database_path)
        if resolved.is_file():
            return True, str(resolved)
        return (
            False,
            f"{resolved} not found — set {SILVERQUEST_DB_ENV_VAR} to the "
            "Pb_DB_20240310AllGalenas.xlsx location.",
        )

    def build_ui(self, parent=None, callback=None):
        """Return the SilverQuest QGroupBox section for the analysis panel."""
        from PyQt5.QtCore import Qt
        from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QLabel, QPushButton

        from core import translate

        group = QGroupBox(translate("SilverQuest Provenance"))
        group.setProperty('translate_key', 'SilverQuest Provenance')
        layout = QVBoxLayout()

        hint = QLabel(
            translate(
                "Search Pb-isotope samples against reference groups of your "
                "grouping column."
            )
        )
        hint.setProperty(
            'translate_key',
            "Search Pb-isotope samples against reference groups of your "
            "grouping column.",
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        button = QPushButton(translate("Run SilverQuest Provenance"))
        button.setProperty('translate_key', 'Run SilverQuest Provenance')
        button.setFixedWidth(200)
        if callback is not None:
            button.clicked.connect(callback)
        layout.addWidget(button, 0, Qt.AlignHCenter)

        group.setLayout(layout)
        return group
