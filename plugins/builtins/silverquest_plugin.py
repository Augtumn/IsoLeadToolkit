"""Builtin SilverQuest provenance plugin — Pb-isotope ore-distance search.

Hosts the port of the R reference implementation ``SilverQuest_R_v1.R``; the
algorithm itself lives in :mod:`data.silverquest`, which carries the full
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
the same :class:`data.silverquest.SilverQuestDatabase`, so the numeric core is
untouched and cannot tell them apart.

Registered like every other builtin: the file stem ``silverquest_plugin`` is the
PluginManager key, ``meta.name`` (``silverquest``) is the fallback lookup, and
``ui/panels/analysis/build.py`` maps the key to the analysis-panel callback.
"""
from __future__ import annotations

import logging
from typing import Any, Iterable

from plugins.api import BasePlugin, PluginMeta

logger = logging.getLogger(__name__)

__all__ = [
    "SilverQuestPlugin",
    "resolve_references",
    "run_silverquest_on_groups",
    "run_silverquest_search",
]

#: Prefixes of the grouping values the plugin writes back into the dataframe
#: when the user applies a run.  They are ordinary group labels for the rest of
#: the application: the plot colours them, the legend lists them and the legend
#: checkboxes hide them, exactly like any other group column.
ROLE_ARTEFACT_PREFIX = "[Artefact] "
ROLE_REFERENCE_PREFIX = "[Reference] "
#: A reference that at least one artefact was matched to.
ROLE_REFERENCE_MATCH_PREFIX = "[Reference Match] "
ROLE_MATCH_PREFIX = "[Match] "
#: A sample that entered the matching but hit nothing in the database.
ROLE_NO_MATCH_PREFIX = "[No Match] "
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
    from data.silverquest import database_from_records, load_silverquest_database

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
    from data.silverquest import (
        SilverQuestConfig,
        artifacts_from_records,
        run_silverquest,
    )

    database, source = resolve_references(references, database_path=database_path)
    if database is None:
        # Re-run without the guard so the loader raises its descriptive error.
        from data.silverquest import load_silverquest_database

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
    """Select artefacts and references *by grouping column value* and run.

    This is the integration entry point the dialog calls, and the one the tests
    drive: the dataframe and the grouping column are the application's own, and
    the two group selections decide which rows play which role.  Rows whose
    group is in neither selection stay out of the search.

    The returned ``roles`` maps dataframe row positions back to what they were
    used as, which is what the dialog writes into the applied group column, and
    ``matches`` records each artefact's nearest reference (within *dmax*) so the
    outcome is visible away from the hit table.

    Raises:
        ValueError: the grouping column is absent, nothing was selected for a
            role, or a selection produced no usable ratio row.
        FileNotFoundError: no reference group was selected and the galena
            workbook is not present.
    """
    from data.silverquest import (
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

    # Map the artefacts back onto the dataframe: the records builder can skip a
    # row (a text ratio, a blank), so the *no* the core reports is matched to the
    # group labels we recorded rather than to a position.
    artefact_labels = labels.iloc[artefact_indices].tolist()
    artefact_names = [
        str(record.get("no", "")) for record in artefact_records
    ]
    roles: dict[int, str] = {}
    for position in artefact_indices:
        roles[position] = ROLE_ARTEFACT_PREFIX + str(labels.iloc[position])
    for position in reference_indices:
        roles[position] = ROLE_REFERENCE_PREFIX + str(labels.iloc[position])

    matched_artefacts = {
        str(artifact.no) for artifact in result.artifacts if artifact.n_hits > 0
    }
    #: Group names holding at least one artefact with a hit inside *dmax*.
    matched_groups = {
        artefact_labels[index]
        for index, name in enumerate(artefact_names)
        if name in matched_artefacts and index < len(artefact_labels)
    }
    # The direction is sample -> database: the sample is the query point and every database ore is a
    # candidate source, tested one ore at a time by the perpendicular distance from the sample to
    # that ore's mass-fractionation line. The roles are therefore decided per row:
    #   [Other Data]      data that never entered the matching
    #   [Match]           a sample that hit at least one ore
    #   [No Match]        a sample that hit nothing
    #   [Reference Match] an ore that was hit
    #   [Reference]       an ore that was not hit
    # ``role_by_group`` stays a group-level summary, and no shape is attached to any role, so one
    # grouping column is drawn with a single marker throughout.
    group_has_hit = {
        str(label): str(label) in matched_groups
        for label in dict.fromkeys(artefact_labels)
    }
    role_by_group: dict[str, str] = {}
    for label, has_hit in group_has_hit.items():
        role_by_group[str(label)] = ROLE_MATCH_PREFIX if has_hit else ROLE_NO_MATCH_PREFIX
    for label in dict.fromkeys(labels.iloc[reference_indices].tolist()):
        role_by_group[str(label)] = ROLE_REFERENCE_PREFIX
    for position in artefact_indices:
        group_label = str(labels.iloc[position])
        roles[int(position)] = (
            ROLE_MATCH_PREFIX if group_has_hit.get(group_label, False) else ROLE_NO_MATCH_PREFIX
        ) + group_label

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

    # Trace every hit back to the frame row it came from, rather than re-identifying rows by their
    # values afterwards. A hit carries "no" = its 1-based index into the database (R: no = 1:m0); the
    # database was built from reference_records in order, and records_from_frame already withholds
    # non-finite rows, so that index addresses the same record - and each record carries the frame
    # position it was built from. If the two lengths ever disagree the assumption is reported, not
    # silently absorbed.
    reference_source_rows = [int(record["source_position"]) for record in reference_records]
    # The builder numbers rows within the frame it was handed - here the reference subset - so the
    # positions are rewritten to the rows they occupy in the caller's frame. The caller knows exactly
    # which rows it selected, so this is bookkeeping, not inference.
    for index, position in enumerate(reference_indices):
        if index < len(reference_records):
            reference_records[index]["source_position"] = int(position)
            reference_source_rows[index] = int(position)
    if len(reference_source_rows) != len(reference_indices):
        import logging

        logging.getLogger(__name__).warning(
            "SilverQuest: %d reference record(s) for %d selected row(s) - hit rows cannot be traced",
            len(reference_source_rows),
            len(reference_indices),
        )
    hit_rows: set[int] = set()
    for artifact in result.artifacts:
        for hit in artifact.hits:
            carried = int(hit.get("source_position", -1))
            if carried >= 0:
                # Carried end to end by the core - also the only route for the workbook source,
                # whose rows the plugin never sees.
                hit_rows.add(carried)
                continue
            index = int(hit.get("no", 0)) - 1
            if 0 <= index < len(reference_source_rows):
                hit_rows.add(reference_source_rows[index])
    for position in reference_indices:
        group_label = str(labels.iloc[position])
        if int(position) in hit_rows:
            roles[int(position)] = ROLE_REFERENCE_MATCH_PREFIX + group_label
            role_by_group[group_label] = ROLE_REFERENCE_MATCH_PREFIX

    # Every row carries a role. "other" is the data that never entered the matching - not the
    # sample rows that entered and found nothing, and not a catch-all that swallows the whole frame.
    applied = [ROLE_OTHER] * len(frame)
    for position, role in roles.items():
        applied[int(position)] = role

    return {
        "result": result,
        "summary": payload["summary"],
        "reference_source": payload["reference_source"],
        "reference_rows": payload["reference_rows"],
        "artefact_groups": artefact_values,
        "reference_groups": reference_values,
        "artefact_indices": artefact_indices,
        "reference_indices": reference_indices,
        "roles": roles,
        "role_by_group": role_by_group,
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
            "weighted distance from selected artefact groups to selected "
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
        from data.silverquest import (
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
                "Search Pb-isotope analyses against reference groups selected "
                "from your own grouping column, optionally extended with the "
                "galena reference database (Albarède et al. 2024)."
            )
        )
        hint.setProperty(
            'translate_key',
            "Search Pb-isotope analyses against reference groups selected "
            "from your own grouping column, optionally extended with the "
            "galena reference database (Albarède et al. 2024).",
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
