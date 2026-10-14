"""SilverQuest — Pb-isotope provenance search by distance to galena reference data.

Ported from the R reference implementation
``reference/r_packages/SilverQuest_v1/SilverQuest_R_v1.R`` (SilverQuest v1).
Every ported piece of the R script is named in this module so the provenance is
traceable: the R function/variable name appears next to the Python object that
transcribes it.

What the algorithm computes
---------------------------
For each artefact and each galena ore analysis in the reference database it
builds the *mass-dependent fractionation line* through the ore — a ray in
(206Pb/204Pb, 207Pb/204Pb, 208Pb/204Pb) space whose direction is
(2x, 3y, 4z) under 204Pb normalisation and (-2x, y, 2z) under 206Pb
normalisation, because one mass unit of fractionation moves each ratio in
proportion to the mass difference from the normalising isotope.  The artefact is
projected onto the plane perpendicular to that ray and the distance inside the
plane is measured with the inverse of the analytical error matrix projected onto
the same plane (a Mahalanobis distance; the R comment cites "Wichern and Johnson
5A.2").  Ores whose squared distance falls below *dmax* are the hits, sorted
closest-last, coloured by distance and written to maps/KML/XLSX by the R script.

The R script additionally renders maps (``map``/``map2`` via ggplot2/tmap),
writes PNG/EPS/KML files and drives two Shiny parameter dialogs.  Those are
presentation concerns of a standalone R script and are *not* ported here; this
module carries the numeric core so it can be hosted by the application.

Upstream source, licence and attribution
----------------------------------------
* Source file: ``SilverQuest_R_v1.R`` (header comment: "search programm in 3D
  using the distance d of objects to the data on ores stored in a database to
  the mass-dependant fractionation line").  Version: v1.
* Reference: Albarède, F., Davis, G., Blichert-Toft, J., Gentelli, L., Gitler,
  H., Pinto, M., & Telouk, P. (2024). "A new algorithm for using Pb isotopes to
  determine the provenance of bullion in ancient Greek coinage." *Journal of
  Archaeological Science* 163, 105919.  https://doi.org/10.1016/j.jas.2024.105919
* Analytical error matrix (``romatrix``/``smatrix``): Albarède et al. (2004),
  "Precise and accurate isotopic measurements using multiple-collector ICPMS",
  *Geochimica et Cosmochimica Acta* 68, 2725-2744.  Values established on NIST
  SRM 981.
* Contact given in ``Readme.pdf``: laurachollet@sfr.fr,
  francis.albarede@ens-lyon.fr, falbarede@gmail.com.

**Licence (OPEN QUESTION — do not treat as resolved):** neither
``SilverQuest_R_v1.R`` nor ``Readme.pdf`` states a licence or any terms of use.
The script carries only the bibliographic reference above and the PDF only the
citation plus contact addresses.  This module is therefore a clearly-marked
port with the attribution reproduced above, and the licensing question is raised
in the port report; it must be settled with the upstream authors before this
port is redistributed.  This project as a whole is GPL-3.0-or-later.

Ambiguities in the R source
---------------------------
Where the R code is ambiguous or looks like an upstream defect, this port keeps
the R behaviour and says so at the relevant line with an ``R-AMBIGUITY:`` or
``R-QUIRK:`` comment.  The three substantive ones are:

1. ``dist`` holds a *squared* weighted distance (``dproj_squared``) but the
   threshold uses the *linear* parameter ``dmax`` (R line 364:
   ``sum(T1$dist < dmax)``).  The port keeps the comparison exactly as written
   and documents that ``dmax`` is therefore a squared-distance cut-off in
   practice.
2. ``sg`` is a length-1 R vector assigned inside the per-ore loop, so the hit
   table repeats the sign computed for the *last* database row only.  The port
   reproduces that and labels the column accordingly.
3. ``nocol`` (R line 418) is computed against the user parameter ``dmax`` and
   not against the largest hit distance, so the index can exceed the colour
   ramp.  See :meth:`SilverQuestArtifactResult.colour_indices`.
"""
from __future__ import annotations

import logging
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

__all__ = [
    "SILVERQUEST_DB_ENV_VAR",
    "SILVERQUEST_DB_RELATIVE_PATH",
    "SILVERQUEST_R_SOURCE",
    "RATIO_ALIASES",
    "SilverQuestArtifact",
    "SilverQuestArtifactResult",
    "SilverQuestConfig",
    "SilverQuestDatabase",
    "artefact_record_columns",
    "database_from_records",
    "default_database_path",
    "load_silverquest_database",
    "records_from_frame",
    "resolve_column",
    "run_silverquest",
    "silverquest_profile",
]


# ── upstream locations ───────────────────────────────────────────────────

#: The R reference implementation this module ports.
SILVERQUEST_R_SOURCE = "reference/r_packages/SilverQuest_v1/SilverQuest_R_v1.R"

#: Repository-relative location of the galena database shipped with the R
#: script's own folder.  The 791 KB workbook is deliberately *not* copied into
#: the tree: this project keeps bulk reference data out of version control
#: (``data/`` holds Python constants such as ``plumbotectonics_data.py``, not
#: workbooks) and loads it by path instead, which is what this default does.
SILVERQUEST_DB_RELATIVE_PATH = (
    "reference/r_packages/SilverQuest_v1/Pb_DB_20240310AllGalenas.xlsx"
)

#: Environment override for the database location (deployments may keep the
#: workbook outside the checkout).
SILVERQUEST_DB_ENV_VAR = "ISOTOPES_SILVERQUEST_DB"


def default_database_path() -> Path:
    """Return the repository-relative path of the bundled galena database.

    Resolved from this file rather than the process CWD so the app can be
    started from anywhere.
    """
    return Path(__file__).resolve().parents[1] / SILVERQUEST_DB_RELATIVE_PATH


# ── constants transcribed from the R script ──────────────────────────────

#: R lines 193-195 / 205-207: ``romatrix`` — correlation coefficients of the
#: analytical errors, from signal intensity (Albarède et al. 2004).
CORRELATION_MATRIX: dict[str, np.ndarray] = {
    # R: matrix(c(1, 0.96, 0.94, 0.96, 1, 0.96, 0.94, 0.96, 1), nrow = 3)
    "204Pb": np.array(
        [
            [1.0, 0.96, 0.94],
            [0.96, 1.0, 0.96],
            [0.94, 0.96, 1.0],
        ],
        dtype=float,
    ),
    # R: matrix(c(1, 0.16, 0.2, 0.16, 1, 0.57, 0.2, 0.57, 1), nrow = 3)
    "206Pb": np.array(
        [
            [1.0, 0.16, 0.2],
            [0.16, 1.0, 0.57],
            [0.2, 0.57, 1.0],
        ],
        dtype=float,
    ),
}

#: R line 287: ``f <- 0.001`` — constant (mass-dependent) fractionation factor
#: used to scale the *relative* external reproducibilities into absolute
#: variances.  These are the 1 s.d. values in percent per mass unit referred to
#: by the Readme ("the errors on Pb isotopic ratios are mass-dependent").
FRACTIONATION_FACTOR = 0.001

#: 1 s.d. of 206Pb/204Pb, 207Pb/204Pb, 208Pb/204Pb in percent, from the Readme
#: and the R script's numbers.
SIGMA_PCT = (18.7, 15.65, 39.0)

#: R lines 288-292: ``smatrix`` — diagonal of absolute 1 s.d. values.
#: 204Pb normalisation is ``f * diag(c(2*18.7, 3*15.65, 4*39))``; the factors
#: 2/3/4 are the mass differences from 204Pb.  206Pb normalisation is
#: ``f * diag(c(-2/18.7, 15.65/18.7, 2*39/18.7))``: the same slope coefficients
#: divided by 206Pb/204Pb, with the 206Pb ratio itself entering as 1/x (hence
#: the negative exponent and the sign carried in the R code).
SIGMA_MATRIX_DIAGONAL: dict[str, tuple[float, float, float]] = {
    "204Pb": (
        FRACTIONATION_FACTOR * (2.0 * SIGMA_PCT[0]),
        FRACTIONATION_FACTOR * (3.0 * SIGMA_PCT[1]),
        FRACTIONATION_FACTOR * (4.0 * SIGMA_PCT[2]),
    ),
    "206Pb": (
        FRACTIONATION_FACTOR * (-2.0 / SIGMA_PCT[0]),
        FRACTIONATION_FACTOR * (SIGMA_PCT[1] / SIGMA_PCT[0]),
        FRACTIONATION_FACTOR * (2.0 * SIGMA_PCT[2] / SIGMA_PCT[0]),
    ),
}

#: R lines 193-211: the two accepted normalisations ("Select Normalization:").
NORMALIZATIONS = ("204Pb", "206Pb")

#: R lines 396 / 462: the plotting colour ramp, black (closest) → white.  These
#: are the R colour *names* handed to ``colorRampPalette``; the interpolated
#: per-hit ramp is :func:`_colour_ramp`.
COLOUR_RAMP: tuple[str, ...] = ("black", "red", "orange", "yellow", "white")

#: R line 139: the database column names the script relies on.  ``no`` and
#: ``group`` belong to the *artefact* files (R line 5); the database needs
#: Country/Latitude/Longitude and the three ratios.
DATABASE_REQUIRED_COLUMNS: tuple[str, ...] = (
    "Country",
    "Latitude",
    "Longitude",
    "Pb206204",
    "Pb207204",
    "Pb208204",
)

#: Default UI values taken from the Shiny inputs (R lines 84-85).
DEFAULT_JITTER_RADIUS = 0.01
DEFAULT_DMAX = 3.0


# ── R behaviour helpers ──────────────────────────────────────────────────


def _r_round(value: np.ndarray | float) -> np.ndarray:
    """R's ``round()``: round half *away from zero*, not banker's rounding.

    ``np.round`` breaks ties to even, so ``round(0.5)`` is 0 there and 1 in R.
    ``nocol`` (R line 418) and the colour-intensity helper (R line 398) both
    call R's ``round``, so the difference is visible in the colour indexing.
    """
    array = np.asarray(value, dtype=float)
    rounded = np.floor(np.abs(array) + 0.5) * np.sign(array)
    return rounded if array.ndim else float(rounded)


def _cross(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """``pracma::cross`` (R lines 313, 334) for 3-vectors.

    ``r_packages`` ships no copy of pracma, so this is the standard
    right-handed cross product, matching ``pracma::cross`` for length-3 input.
    """
    return np.cross(np.asarray(a, dtype=float), np.asarray(b, dtype=float))


def _unit(vector: np.ndarray) -> np.ndarray:
    """Normalise a 3-vector; raises when the vector has no direction.

    The R script divides by ``sqrt(sum(cosdir0^2))`` without a guard (R lines
    306-307, 311-312, 314-315); a degenerate ore (zero ratios, or ratios that
    make ``i11`` vanish) would yield NaN there rather than an error, so this
    port makes the failure explicit instead of propagating NaN into a
    provenance call.
    """
    vector = np.asarray(vector, dtype=float)
    norm = float(math.sqrt(float(np.sum(vector * vector))))
    if not math.isfinite(norm) or norm <= 0.0:
        raise ValueError(
            "SilverQuest: degenerate direction vector "
            f"{vector.tolist()} — cannot normalise (R divides by zero here)."
        )
    return vector / norm


def _colour_ramp(n_colours: int) -> list[str]:
    """``grDevices::colorRampPalette(c("black","red","orange","yellow","white"))``.

    R line 396.  ``colorRampPalette`` linearly interpolates in RGB over
    ``n_colours`` steps, giving *n_colours* colours from black to white; the
    interpolation is reproduced here so the colour indices that the R script
    writes into ``nocol``/``point_color`` keep their meaning.
    """
    if n_colours <= 0:
        return []
    anchors = np.array(
        [
            [0, 0, 0],
            [255, 0, 0],
            [255, 165, 0],
            [255, 255, 0],
            [255, 255, 255],
        ],
        dtype=float,
    )
    if n_colours == 1:
        return ["#000000"]
    positions = np.linspace(0.0, 1.0, n_colours)
    segments = np.linspace(0.0, 1.0, len(anchors))
    ramp: list[str] = []
    for position in positions:
        channel = np.array(
            [np.interp(position, segments, anchors[:, index]) for index in range(3)]
        )
        rgb = _r_round(channel).astype(int)
        ramp.append("#{:02x}{:02x}{:02x}".format(*rgb))
    return ramp


def _distance_colour_index(
    distances: np.ndarray, dmax: float, n_hits: int
) -> tuple[np.ndarray, bool]:
    """R line 418: ``nocol <- round((colsc / dmax) * (nprox - 1) + 0.5)``.

    ``colsc`` is the hit distances, ``nprox`` the number of hits and ``dmax``
    the *user parameter*, not the largest hit distance.  R additionally applies
    ``pmax(nocol, 1)`` (line 419) but no upper clamp, so indices above the ramp
    length are possible and would index past the end of ``colorList``.

    Returns ``(indices, clamped)`` where *clamped* reports whether any index had
    to be pulled back into ``[1, n_hits]``; the R script would either truncate
    the value (when assigning to ``T2$nocol``) or index out of range (when
    building ``colorList[nocol]``).
    """
    if n_hits <= 0:
        return np.zeros(0, dtype=int), False
    scaled = (np.asarray(distances, dtype=float) / float(dmax)) * (n_hits - 1) + 0.5
    raw = _r_round(scaled)
    # R-QUIRK: no upper clamp upstream; reproducing the value would index past
    # the colour ramp, so out-of-range indices are clamped and reported.
    clamped = bool(np.any(raw > n_hits))
    indices = np.clip(raw, 1, n_hits).astype(int)
    return indices, clamped


# ── database ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SilverQuestDatabase:
    """The galena reference table (R: ``database_PbS0`` / ``T0``).

    Attributes mirror the R columns 1:1: ``country``, ``latitude``,
    ``longitude`` and the three ratios.  ``n_rows`` is R's ``m0``.
    """

    country: np.ndarray
    latitude: np.ndarray
    longitude: np.ndarray
    pb206_204: np.ndarray
    pb207_204: np.ndarray
    pb208_204: np.ndarray
    dropped_rows: tuple[int, ...] = ()
    #: The source row each usable row came from, in the order of the arrays above. Carried so a hit
    #: can be traced back to the row it came from instead of being re-identified by its values.
    source_position: tuple[int, ...] = ()

    @property
    def n_rows(self) -> int:
        """R: ``m0 <- length(T0$Country)`` (line 143)."""
        return int(len(self.country))


def load_silverquest_database(path: str | os.PathLike[str] | None = None) -> SilverQuestDatabase:
    """Load the galena database workbook (R line 139: ``read_excel(...)``).

    Args:
        path: workbook path.  Defaults to :func:`default_database_path`, then to
            ``$ISOTOPES_SILVERQUEST_DB`` when that is set and the default does
            not exist.

    Returns:
        A :class:`SilverQuestDatabase`.

    Raises:
        FileNotFoundError: the workbook is not present — the message names the
            expected location and the environment override, because the file is
            intentionally not vendored into this repository.
        ValueError: required columns are missing.
    """
    import pandas as pd

    resolved = resolve_database_path(path)
    if not resolved.is_file():
        raise FileNotFoundError(
            "SilverQuest reference database not found at "
            f"'{resolved}'. It ships with the R package in "
            f"'{SILVERQUEST_DB_RELATIVE_PATH}'. Set {SILVERQUEST_DB_ENV_VAR} to "
            "point at Pb_DB_20240310AllGalenas.xlsx elsewhere."
        )

    frame = pd.read_excel(resolved)
    missing = [name for name in DATABASE_REQUIRED_COLUMNS if name not in frame.columns]
    if missing:
        raise ValueError(
            f"SilverQuest database '{resolved}' is missing column(s): "
            + ", ".join(missing)
        )

    # R-QUIRK: R's read_excel() type-guesses a column from its first rows, so a
    # single text value anywhere in a numeric column turns the whole column into
    # character and every arithmetic expression built from it into an error
    # ("non-numeric argument to binary operator").  The shipped workbook has
    # exactly one such row (a shifted record whose Latitude cell reads
    # "Mountains"), which makes the R script fail on its own bundled database.
    # This port coerces the numeric columns and drops only the unusable rows,
    # recording their positions so the caller can report the difference.
    numeric_values: dict[str, np.ndarray] = {}
    usable = np.ones(len(frame), dtype=bool)
    bad_any = np.zeros(len(frame), dtype=bool)
    for column in ("Latitude", "Longitude", "Pb206204", "Pb207204", "Pb208204"):
        coerced = pd.to_numeric(frame[column], errors="coerce")
        invalid = coerced.isna().to_numpy()
        # A genuine blank is unusable too; keep it out of the same mask.
        bad_any |= invalid
        numeric_values[column] = coerced.to_numpy(dtype=float)
    usable &= ~bad_any

    dropped = tuple(int(index) for index in np.flatnonzero(~usable))
    if dropped:
        logger.warning(
            "SilverQuest: dropped %d non-numeric row(s) from %s (rows %s)",
            len(dropped),
            resolved.name,
            ", ".join(str(index) for index in dropped[:10]),
        )

    country = frame["Country"].astype(str).to_numpy(dtype=object)[usable]
    return SilverQuestDatabase(
        country=country,
        latitude=numeric_values["Latitude"][usable],
        longitude=numeric_values["Longitude"][usable],
        pb206_204=numeric_values["Pb206204"][usable],
        pb207_204=numeric_values["Pb207204"][usable],
        pb208_204=numeric_values["Pb208204"][usable],
        dropped_rows=dropped,
        source_position=tuple(int(index) for index in np.flatnonzero(usable)),
    )


def resolve_database_path(path: str | os.PathLike[str] | None = None) -> Path:
    """Resolve the workbook path: explicit → env override → repository default."""
    if path is not None:
        return Path(path)
    override = os.environ.get(SILVERQUEST_DB_ENV_VAR)
    default = default_database_path()
    if override and not default.is_file():
        return Path(override)
    return default


# ── in-memory adapter: the application's own data as the reference set ────
#
# The numeric core above is a faithful transcription of the R script and stays
# untouched.  The R script reads its inputs from two workbooks (the artefact
# file, R line 5; the galena database, R line 139); the application instead has
# one loaded dataframe and a grouping column.  The helpers below are that
# adapter, and nothing else: they build the very same
# :class:`SilverQuestArtifact` / :class:`SilverQuestDatabase` values the
# workbook loaders build, so ``run_silverquest`` cannot tell the difference.

#: Column spellings accepted for the three Pb ratios.  The R input format is
#: ``Pb206204`` (Readme.pdf, "Input Example"); the application's geochemistry
#: code uses ``Pb206_204``, and slash-separated headers appear in imported
#: workbooks.
RATIO_ALIASES: dict[str, tuple[str, ...]] = {
    "Pb206204": ("Pb206204", "Pb206_204", "Pb206/204", "206Pb/204Pb"),
    "Pb207204": ("Pb207204", "Pb207_204", "Pb207/204", "207Pb/204Pb"),
    "Pb208204": ("Pb208204", "Pb208_204", "Pb208/204", "208Pb/204Pb"),
}

#: Optional artefact columns: the R input format's ``no`` / ``group`` (R line
#: 5).  Neither is required — the grouping column chosen in the dialog supplies
#: the group, and a missing ``no`` falls back to the row position.
_ARTEFACT_META_ALIASES: dict[str, tuple[str, ...]] = {
    "no": ("no", "No", "NO", "Name", "name", "Sample", "sample"),
    "group": ("group", "Group", "GroupName"),
}

#: Reference-table columns the R script reads (R line 139,
#: :data:`DATABASE_REQUIRED_COLUMNS`).  Not every reference set carries
#: coordinates, so they are optional here and default to 0.0; the hit table
#: still reports them when they are present.
_REFERENCE_OPTIONAL_ALIASES: dict[str, tuple[str, ...]] = {
    "Latitude": ("Latitude", "latitude", "Lat", "lat"),
    "Longitude": ("Longitude", "longitude", "Lon", "lon", "Long"),
}


def resolve_column(columns, aliases: tuple[str, ...]) -> str | None:
    """Return the first spelling of *aliases* present in *columns*, else None."""
    available = list(columns)
    for alias in aliases:
        if alias in available:
            return alias
    return None


def artefact_record_columns(columns) -> dict[str, str]:
    """Map *columns* onto the R input names, requiring only the three ratios.

    Returns a ``{canonical: actual column}`` mapping.  ``no`` and ``group``
    appear only when the frame happens to carry them.

    Raises:
        KeyError: a required ratio column has no recognised spelling — the
            message lists the spellings that were tried, because silently
            picking the wrong column would corrupt a provenance call.
    """
    resolved: dict[str, str] = {}
    for canonical, aliases in RATIO_ALIASES.items():
        column = resolve_column(columns, aliases)
        if column is None:
            raise KeyError(
                f"SilverQuest: no column for {canonical}; tried " + ", ".join(aliases)
            )
        resolved[canonical] = column
    for canonical, aliases in _ARTEFACT_META_ALIASES.items():
        column = resolve_column(columns, aliases)
        if column is not None:
            resolved[canonical] = column
    return resolved


def records_from_frame(
    frame,
    columns: dict[str, str] | None = None,
    *,
    group_labels=None,
) -> list[dict[str, Any]]:
    """Turn a DataFrame into the record dicts the numeric core expects.

    The *same* records feed :func:`run_silverquest` whether the caller treats
    the rows as artefacts or as reference data; the role is the caller's, not
    the record's.

    Rows with a non-numeric, missing, or non-finite ratio are skipped rather
    than passed on: the R script reads a whole workbook and dies on the first
    such row (``non-numeric argument to binary operator``), which is not a
    useful behaviour to reproduce in a GUI.  ``Latitude``/``Longitude`` are
    copied when present so a reference set's hit rows can report them.

    Args:
        frame: the rows to convert.
        columns: pre-resolved mapping from :func:`artefact_record_columns`.
        group_labels: optional per-row group labels, aligned with *frame*
            (typically the value of the dialog's grouping column).  Supplying
            them here rather than afterwards keeps a skipped row from shifting
            the group assignment of the rows behind it.
    """
    resolved = columns or artefact_record_columns(frame.columns)
    ratio_keys = tuple(RATIO_ALIASES)
    labels = None if group_labels is None else list(group_labels)
    records: list[dict[str, Any]] = []
    skipped = 0
    position = 0
    for row_position, (_, row) in enumerate(frame.iterrows()):
        position += 1
        record: dict[str, Any] = {}
        try:
            for key in ratio_keys:
                record[key] = float(row[resolved[key]])
        except (TypeError, ValueError):
            skipped += 1
            continue
        if not all(np.isfinite(record[key]) for key in ratio_keys):
            skipped += 1
            continue

        # The frame row this record came from. Kept so a hit can be traced back to its row instead of
        # being re-identified by its values afterwards - a row that is skipped here simply never
        # contributes a record, so the positions stay those of the original frame.
        record["source_position"] = int(row_position)

        no_column = resolved.get("no")
        record["no"] = (
            str(row[no_column]) if no_column is not None else f"row{position}"
        )
        group_column = resolved.get("group")
        if group_column is not None:
            record["group"] = row[group_column]
        if labels is not None and row_position < len(labels):
            record["group"] = labels[row_position]
        for key, aliases in _REFERENCE_OPTIONAL_ALIASES.items():
            column = resolve_column(frame.columns, aliases)
            if column is None:
                continue
            try:
                value = float(row[column])
            except (TypeError, ValueError):
                continue
            if np.isfinite(value):
                record[key] = value
        records.append(record)

    if skipped:
        logger.warning(
            "SilverQuest: skipped %d incomplete row(s) of %d",
            skipped,
            len(frame),
        )
    return records


def database_from_records(
    records: list[dict[str, Any]],
    *,
    default_country: str = "In-session data",
) -> SilverQuestDatabase:
    """Build the reference table from in-memory rows instead of a workbook.

    This is the counterpart of :func:`load_silverquest_database` for the
    application's own data: the *same* :class:`SilverQuestDatabase` comes out,
    so ``run_silverquest`` cannot tell the two sources apart.  Where the
    workbook loader coerces its numeric columns and records the unusable rows,
    this adapter drops records whose ratios are missing or non-finite and
    records their positions (the counter starts at 1, matching the 1-based R
    column ``no``).

    Args:
        records: rows carrying the three Pb ratios.  ``Country`` (or a country /
            grouping label) and ``Latitude``/``Longitude`` are optional; rows
            without coordinates default to ``0.0`` and the hit table reports
            whatever they carry.
        default_country: label used when a row carries no country and no group.

    Raises:
        ValueError: no record carries a usable ratio triple — an empty reference
            set cannot score anything, and the R script would stop at
            ``1:nrow(database_PbS0)``.
    """

    def pick(record: dict[str, Any], *names: str) -> Any:
        for name in names:
            if name in record and record[name] is not None:
                return record[name]
        return None

    countries: list[str] = []
    latitudes: list[float] = []
    longitudes: list[float] = []
    ratios: dict[str, list[float]] = {key: [] for key in RATIO_ALIASES}
    dropped: list[int] = []

    for position, record in enumerate(records, start=1):
        triple: dict[str, float] = {}
        for key in RATIO_ALIASES:
            raw = pick(record, key, key.replace("204", "_204"))
            try:
                triple[key] = float(raw)
            except (TypeError, ValueError):
                triple = {}
                break
        if not triple or not all(np.isfinite(value) for value in triple.values()):
            dropped.append(position)
            continue
        for key, value in triple.items():
            ratios[key].append(value)

        label = pick(record, "Country", "country", "Group", "group", "no", "No")
        countries.append(default_country if label is None else str(label))
        for target, names in (
            (latitudes, ("Latitude", "latitude", "Lat", "lat")),
            (longitudes, ("Longitude", "longitude", "Lon", "lon", "Long")),
        ):
            raw = pick(record, *names)
            try:
                value = 0.0 if raw is None else float(raw)
            except (TypeError, ValueError):
                value = 0.0
            target.append(value if math.isfinite(value) else 0.0)

    if not countries:
        raise ValueError(
            "SilverQuest: no usable reference row — every selected reference row "
            "is missing a finite Pb206204/Pb207204/Pb208204 triple."
        )
    if dropped:
        logger.warning(
            "SilverQuest: dropped %d unusable reference row(s) (rows %s)",
            len(dropped),
            ", ".join(str(index) for index in dropped[:10]),
        )

    return SilverQuestDatabase(
        country=np.array(countries, dtype=object),
        latitude=np.array(latitudes, dtype=float),
        longitude=np.array(longitudes, dtype=float),
        pb206_204=np.array(ratios["Pb206204"], dtype=float),
        pb207_204=np.array(ratios["Pb207204"], dtype=float),
        pb208_204=np.array(ratios["Pb208204"], dtype=float),
        dropped_rows=tuple(dropped),
    )


# ── configuration and results ────────────────────────────────────────────


@dataclass(frozen=True)
class SilverQuestConfig:
    """Analysis parameters (R: ``parameters`` from ``user_choices.csv``).

    Defaults reproduce the Shiny input defaults of R lines 80-87, restricted to
    the inputs that reach the numbers.  The same R form also collected a map
    window, a basemap style and an ore-overlay switch for its plotting code,
    which this port does not draw and therefore does not carry.
    """

    normalization: str = "204Pb"
    dmax: float = DEFAULT_DMAX
    jittered: bool = True
    jitter_radius: float = DEFAULT_JITTER_RADIUS

    def __post_init__(self) -> None:
        if self.normalization not in NORMALIZATIONS:
            raise ValueError(
                f"Invalid normalization {self.normalization!r}; "
                f"expected one of {NORMALIZATIONS} (R: stop('Invalid normalization value'))."
            )
        if self.jitter_radius < 0.0:
            raise ValueError("jitter_radius must be >= 0 (R input min = 0).")


@dataclass(frozen=True)
class SilverQuestArtifact:
    """One artefact to look up (an ``no`` in the R input files, R line 5)."""

    no: str
    pb206_204: float
    pb207_204: float
    pb208_204: float
    group: str = "1"


@dataclass(frozen=True)
class SilverQuestArtifactResult:
    """Hits for one artefact (R: the ``T1`` / ``T2`` hit tables).

    Attributes:
        no: artefact identifier (R ``dat$no[k]``).
        n_hits: R ``nprox`` — ``sum(T1$dist < dmax, na.rm = TRUE)``.
        hits: the hit table, closest **last** (R sorts ``decreasing = TRUE`` so
            the closest point plots on top), one dict per hit with the R column
            names ``no``, ``Country``, ``Latitude``, ``Longitude``, ``dist``,
            ``sg``, ``fract``, ``nocol`` and the three ratios.
        table: the full database scored for this artefact, sorted by increasing
            distance (R's ``T1``) — kept so callers can show near misses.
        colour_indices: ``nocol`` re-projected onto ``1..n_hits`` when the R
            value ran past the ramp; see :meth:`colour_for_distance`.
        colour_index_clamped: True when R's ``nocol`` exceeded the ramp length.
    """

    no: str
    n_hits: int
    hits: tuple[dict[str, Any], ...]
    table: tuple[dict[str, Any], ...]
    colour_indices: tuple[int, ...] = ()
    colour_index_clamped: bool = False

    def colour_for_distance(self, position: int, n_colours: int) -> str:
        """Colour ramp entry for hit ``position`` (0-based, closest last).

        R assigns ``T2[[k]]$point_color <- colorList[nocol]`` with
        ``colorList <- colorRampPalette(...)(nprox)``, so the ramp has as many
        entries as hits.  When R's ``nocol`` is out of range the index was
        clamped (see :attr:`colour_indices`) instead of raising.
        """
        if not (0 <= position < len(self.colour_indices)):
            raise IndexError(
                f"hit position {position} out of range for artefact "
                f"{self.no!r} ({len(self.colour_indices)} hits)"
            )
        ramp = _colour_ramp(n_colours)
        if not ramp:
            raise ValueError("colour ramp is empty (no hits)")
        return ramp[int(self.colour_indices[position]) - 1]


@dataclass(frozen=True)
class SilverQuestResult:
    """Result of a SilverQuest run (R: the per-artefact loop, lines 297-643)."""

    config: SilverQuestConfig
    artifacts: tuple[SilverQuestArtifactResult, ...]
    weight_matrix: np.ndarray
    database_rows: int

    @property
    def total_hits(self) -> int:
        return int(sum(artifact.n_hits for artifact in self.artifacts))

    def summary(self) -> str:
        """Human-readable one-liner for the UI/log."""
        return (
            f"SilverQuest ({self.config.normalization}, dmax={self.config.dmax:g}): "
            f"{len(self.artifacts)} artefact(s), {self.total_hits} hit(s) "
            f"against {self.database_rows} ore analyses."
        )


# ── core computation ─────────────────────────────────────────────────────


def silverquest_profile(
    artifact: tuple[float, float, float],
    ore: tuple[float, float, float],
    normalization: str = "204Pb",
    weight: np.ndarray | None = None,
) -> dict[str, float]:
    """Score one artefact against one ore — R lines 297-342, scalar in/out.

    This is the unit-testable heart of the port.  Both triples are given as
    ``(Pb206204, Pb207204, Pb208204)`` and the normalisation of R lines 189-211
    is applied internally, so *normalization* means the same thing here as in
    :func:`run_silverquest`.

    Returns:
        ``dist``
            R's ``dproj_squared`` — the weighted (Mahalanobis) squared distance
            between the ore and the artefact inside the plane perpendicular to
            the ore's mass-dependent fractionation line.  The R comment cites
            "Wichern and Johnson 5A.2".
        ``fract``
            R's ``fract[kk] <- cosdir0[1] * u`` with
            ``u = sum(cosdir0 * AP) / sum(cosdir0^2)``: the 206Pb/204Pb shift
            that would move the ore onto the artefact along its fractionation
            line.  The R script stores the raw shift, so multiply by 1000 to
            read it in the per-mil units of the fractionation factor
            ``f = 0.001``.
        ``sg``
            R's ``sign(normcros / dotp)`` — ``+1`` when the offset is dominated
            by movement along the fractionation line, ``-1`` when it is
            dominated by the perpendicular component.
        ``dotp``
            The projection of ``AP`` onto the (unnormalised) ``cosdir0``.
    """
    if normalization not in NORMALIZATIONS:
        raise ValueError(f"Invalid normalization {normalization!r}")
    x, y, z = _normalise_triple(artifact, normalization)
    x0, y0, z0 = _normalise_triple(ore, normalization)
    resolved_weight = _build_weight_matrix(normalization) if weight is None else weight

    distances, fractions, signs = _score_against_ores(
        (x, y, z),
        (np.array([x0]), np.array([y0]), np.array([z0])),
        normalization,
        resolved_weight,
    )

    # R lines 332-341 also yield dotp; recomputed here because the array helper
    # only needs the three values the hit table stores.
    if normalization == "204Pb":
        cosdir0 = np.array([2.0 * x0, 3.0 * y0, 4.0 * z0], dtype=float)
    else:
        cosdir0 = np.array([-2.0 * x0, y0, 2.0 * z0], dtype=float)
    i3 = _unit(cosdir0)
    ap = np.array([x0 - x, y0 - y, z0 - z], dtype=float)
    dotp = float(np.sum(ap * i3))

    return {
        "dist": float(distances[0]),
        "fract": float(fractions[0]),
        "sg": float(signs[0]),
        "dotp": float(dotp),
    }


def _normalise_triple(
    triple: tuple[float, float, float], normalization: str
) -> tuple[float, float, float]:
    """R lines 189-211: express a ``(206, 207, 208)`` triple in the normalisation.

    ``204Pb`` keeps the ratios as measured; ``206Pb`` converts them to
    ``1/206``, ``207/206``, ``208/206`` (the R script writes the reciprocal
    form as ``1/x``, ``y/x``, ``z/x``).
    """
    pb206, pb207, pb208 = (float(triple[0]), float(triple[1]), float(triple[2]))
    if normalization == "204Pb":
        return (pb206, pb207, pb208)
    if pb206 == 0.0:
        raise ValueError(
            "SilverQuest: 206Pb normalisation divides by Pb206204, which is 0."
        )
    return (1.0 / pb206, pb207 / pb206, pb208 / pb206)


def _build_weight_matrix(normalization: str) -> np.ndarray:
    """R line 294: ``W <- smatrix %*% romatrix %*% smatrix``.

    Both matrices are symmetric, so ``%*%`` order does not matter here; the R
    expression is transcribed literally.
    """
    if normalization not in NORMALIZATIONS:
        raise ValueError(f"Invalid normalization {normalization!r}")
    smatrix = np.diag(np.array(SIGMA_MATRIX_DIAGONAL[normalization], dtype=float))
    romatrix = CORRELATION_MATRIX[normalization]
    return smatrix @ romatrix @ smatrix


def _normalise_artifact(artifact: SilverQuestArtifact, normalization: str) -> tuple[float, float, float]:
    """R lines 189-211: express an artefact in the selected normalisation."""
    return _normalise_triple(
        (artifact.pb206_204, artifact.pb207_204, artifact.pb208_204), normalization
    )


def _score_against_ores(
    artifact: tuple[float, float, float],
    ores: tuple[np.ndarray, np.ndarray, np.ndarray],
    normalization: str,
    weight: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Score one *already normalised* artefact against every ore — R lines 297-342.

    The inner loop of the R script, in the same order, returning
    ``(dist, fract, sg)`` arrays indexed like the ore arrays.  Used by both
    :func:`silverquest_profile` (one ore) and :func:`run_silverquest` (all of
    them) so the arithmetic exists exactly once.
    """
    x, y, z = artifact
    x0, y0, z0 = ores
    count = int(len(x0))
    distances = np.empty(count, dtype=float)
    fractions = np.empty(count, dtype=float)
    signs = np.empty(count, dtype=float)
    if count == 0:
        return distances, fractions, signs

    for kk in range(count):
        # R lines 299-303: cosdir0 along the mass-dependent fractionation line.
        if normalization == "204Pb":
            cosdir0 = np.array([2.0 * x0[kk], 3.0 * y0[kk], 4.0 * z0[kk]], dtype=float)
        else:
            cosdir0 = np.array([-2.0 * x0[kk], y0[kk], 2.0 * z0[kk]], dtype=float)

        # R lines 305-315: orthonormal basis (i1, i2) of the plane ⟂ i3.
        i3 = _unit(cosdir0)
        i11 = np.array([1.0, 1.0, -(i3[0] + i3[1]) / i3[2]], dtype=float)
        i1 = _unit(i11)
        i2 = _unit(_cross(i1, i3))
        aperp = np.column_stack([i1, i2])  # R: Aperp <- cbind(i1, i2)

        ap = np.array([x0[kk] - x, y0[kk] - y, z0[kk] - z], dtype=float)  # R: AP
        projected = aperp.T @ ap  # R: aproj
        a_matrix = aperp.T @ weight @ aperp  # R: A = t(Aperp) %*% W %*% Aperp
        try:
            solved = np.linalg.solve(a_matrix, projected)  # R: solve(A) %*% aproj
        except np.linalg.LinAlgError as exc:
            raise ValueError(
                "SilverQuest: singular projected error matrix for ore row "
                f"{kk} (R's solve() would fail here)."
            ) from exc
        distances[kk] = float(projected @ solved)  # R: dproj_squared

        # R lines 332-341: fractionation and orientation sign.
        dotp = float(np.sum(ap * i3))
        cros = _cross(ap, cosdir0)
        normcros = float(math.sqrt(float(np.sum(cros * cros))))
        signs[kk] = float(np.sign(normcros / dotp)) if dotp != 0.0 else float("nan")
        u = float(np.sum(cosdir0 * ap) / np.sum(cosdir0 * cosdir0))
        fractions[kk] = float(cosdir0[0] * u)

    return distances, fractions, signs


def run_silverquest(
    artifacts: list[SilverQuestArtifact] | tuple[SilverQuestArtifact, ...],
    database: SilverQuestDatabase,
    config: SilverQuestConfig | None = None,
    *,
    seed: int | None = None,
) -> SilverQuestResult:
    """Run the ported SilverQuest search — R lines 296-643 (numeric core).

    Mirrors the R loop structure exactly: for every artefact, every database row
    is scored (R's inner ``for (kk in 1:nrow(database_PbS0))``), the table is
    sorted by increasing distance, hits are selected with the *strict* ``dist <
    dmax`` test, re-sorted closest-last, and coloured.

    Args:
        artifacts: artefact measurements (R: the rows of the input ``.xlsx``).
        database: ore reference data from :func:`load_silverquest_database`.
        config: parameters; defaults reproduce the Shiny input defaults.
        seed: seed for the jitter draw.  R uses ``runif`` from the global RNG
            (lines 379, 382) so its jitter is not reproducible without an
            external ``set.seed``; passing *seed* here makes the port
            reproducible without changing the distribution.

    Returns:
        A :class:`SilverQuestResult`.
    """
    resolved = config or SilverQuestConfig()
    if database.n_rows == 0:
        raise ValueError("SilverQuest database is empty.")

    weight = _build_weight_matrix(resolved.normalization)
    rng = np.random.default_rng(seed)

    # R lines 189-215: convert the whole database once, outside the loop.
    if resolved.normalization == "204Pb":
        x0 = database.pb206_204
        y0 = database.pb207_204
        z0 = database.pb208_204
    else:
        if np.any(database.pb206_204 == 0.0):
            raise ValueError("206Pb normalisation: database contains Pb206204 = 0.")
        x0 = 1.0 / database.pb206_204
        y0 = database.pb207_204 / database.pb206_204
        z0 = database.pb208_204 / database.pb206_204

    results: list[SilverQuestArtifactResult] = []
    for artifact in artifacts:
        x, y, z = _normalise_artifact(artifact, resolved.normalization)
        distances, fractions, signs = _score_against_ores(
            (x, y, z), (x0, y0, z0), resolved.normalization, weight
        )

        # R-QUIRK: R's `sg` is a length-1 vector written inside the ore loop, so
        # T1$sg (line 353) receives the value from the *last* database row for
        # every row of the table, not the per-row sign.  Reproduced verbatim.
        sg_column = float(signs[-1])

        order = np.argsort(distances, kind="stable")  # R: order(T1$dist)
        table: list[dict[str, Any]] = []
        for position in order:
            table.append(
                {
                    "no": int(position) + 1,  # R: no = 1:m0
                    # The row this ore came from, carried end to end so the caller never has to
                    # re-identify it. -1 when the source did not record positions.
                    "source_position": (
                        int(database.source_position[position])
                        if len(database.source_position) == database.n_rows
                        else -1
                    ),
                    "Country": str(database.country[position]),
                    "Latitude": float(database.latitude[position]),
                    "Longitude": float(database.longitude[position]),
                    "dist": float(distances[position]),
                    "sg": sg_column,
                    "fract": float(fractions[position]),
                    "nocol": 0,
                    "Pb206204": float(database.pb206_204[position]),
                    "Pb207204": float(database.pb207_204[position]),
                    "Pb208204": float(database.pb208_204[position]),
                }
            )

        # R line 364: nprox <- sum(T1$dist < dmax, na.rm = TRUE)
        # R-AMBIGUITY: `dist` is a squared distance while `dmax` is described as
        # a distance ("Maximum distance between ore and no", R line 85).  The
        # comparison is kept exactly as written.
        finite = np.isfinite(distances)
        in_range = (distances < resolved.dmax) & finite
        n_hits = int(np.count_nonzero(in_range))

        hits = table[:n_hits]
        # R line 372: closest last, so the closest point plots on top.
        hits = list(reversed(hits))

        colour_indices: tuple[int, ...] = ()
        colour_clamped = False
        if n_hits > 0:
            hit_distances = np.array([hit["dist"] for hit in hits], dtype=float)
            indices, colour_clamped = _distance_colour_index(
                hit_distances, resolved.dmax, n_hits
            )
            ramp = _colour_ramp(n_hits)
            for hit, index in zip(hits, indices):
                hit["nocol"] = int(index)
                # R line 423: point_color <- colorList[nocol]
                hit["point_color"] = ramp[int(index) - 1]
            colour_indices = tuple(int(index) for index in indices)

        # R lines 378-392: jitter the geographical coordinates of the hits.
        if resolved.jittered and n_hits > 0:
            _apply_jitter(hits, resolved.jitter_radius, rng)

        results.append(
            SilverQuestArtifactResult(
                no=str(artifact.no),
                n_hits=n_hits,
                hits=tuple(hits),
                table=tuple(table),
                colour_indices=colour_indices,
                colour_index_clamped=colour_clamped,
            )
        )

    return SilverQuestResult(
        config=resolved,
        artifacts=tuple(results),
        weight_matrix=weight,
        database_rows=database.n_rows,
    )


def _apply_jitter(
    hits: list[dict[str, Any]], radius: float, rng: np.random.Generator
) -> None:
    """R lines 378-392: displace each hit inside a disc of radius ``r0/5``.

    The R script draws ``a <- 2*pi*runif(nprox)`` and ``r <- (r0/5)*sqrt(runif(nprox))``
    (line 382 is guarded by ``jittered == "Yes"``, but line 387 uses ``r``
    unconditionally — so the R script errors out for "No"; the user-facing
    default is "Yes").  The radius factor is ``r0/5`` and ``sqrt`` makes the
    draw uniform over the disc area rather than concentrated at the centre.

    R-QUIRK: the loop at line 390 overwrites ``r`` and then reassigns the whole
    ``Lat2``/``Lon2`` vectors each iteration; the net effect is the same as this
    vectorised form, except that R adds ``xr`` to latitude and ``yr`` to
    longitude.
    """
    n_hits = len(hits)
    if n_hits == 0:
        return
    angle = 2.0 * math.pi * rng.random(n_hits)
    if radius <= 0.0:
        return
    magnitude = (radius / 5.0) * np.sqrt(rng.random(n_hits))
    delta_lat = magnitude * np.cos(angle)
    delta_lon = magnitude * np.sin(angle)
    for position, hit in enumerate(hits):
        hit["Latitude"] = float(hit["Latitude"] + delta_lat[position])
        hit["Longitude"] = float(hit["Longitude"] + delta_lon[position])


# ── convenience wrapper used by the plugin ───────────────────────────────


def artifacts_from_records(
    records: list[dict[str, Any]],
) -> list[SilverQuestArtifact]:
    """Build artefacts from row dicts.

    Column names follow the R input format ``no, group, Pb206204, Pb207204,
    Pb208204`` (R line 5) and accept the application's ``Pb206_204`` spelling
    as an alias.

    R's ``subgroup`` input column selected a plot marker and, with ``group``, a
    KML icon; this port draws neither, so no marker information is carried.
    """

    def pick(record: dict[str, Any], *names: str) -> Any:
        for name in names:
            if name in record:
                return record[name]
        raise KeyError(
            "SilverQuest artefact is missing column(s) "
            + "/".join(names)
            + " (R input format: no, group, Pb206204, Pb207204, Pb208204)"
        )

    artifacts: list[SilverQuestArtifact] = []
    for record in records:
        artifacts.append(
            SilverQuestArtifact(
                no=str(pick(record, "no", "No", "name")),
                pb206_204=float(pick(record, "Pb206204", "Pb206_204")),
                pb207_204=float(pick(record, "Pb207204", "Pb207_204")),
                pb208_204=float(pick(record, "Pb208204", "Pb208_204")),
                group=str(record.get("group", "1")),
            )
        )
    return artifacts
