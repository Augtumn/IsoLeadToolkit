"""Application use cases for tabular data export."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

#: Curve-data sheet names (also used as CSV comment section headers).
_SHEET_PALEOISOCHRON = "Paleoisochrons"
_SHEET_ISOCHRON = "Isochrons"
_SHEET_EQUATIONS = "Equations"

#: Geochemistry modes whose derived parameters are appended on export.
_GEO_CHEM_MODES: dict[str, list[str]] = {
    "V1V2": [
        "tSK (Ma)", "tCDT (Ma)", "mu", "kappa",
        "V1", "V2", "Delta_alpha", "Delta_beta", "Delta_gamma",
    ],
    "PB_EVOL_76": ["tSK (Ma)", "mu"],
    "PB_EVOL_86": ["tSK (Ma)", "mu", "kappa"],
    "PB_MU_AGE": ["tSK (Ma)", "mu"],
    "PB_KAPPA_AGE": ["tSK (Ma)", "kappa"],
    "PLUMBOTECTONICS_76": ["tSK (Ma)", "mu"],
    "PLUMBOTECTONICS_86": ["tSK (Ma)", "mu", "kappa"],
}

_PB206_COL = "206Pb/204Pb"
_PB207_COL = "207Pb/204Pb"
_PB208_COL = "208Pb/204Pb"


def _compute_geochem_params(
    df: pd.DataFrame,
    render_mode: str,
) -> dict[str, np.ndarray]:
    """Compute derived geochemistry parameters for the given DataFrame.

    Returns a dict mapping column-name → numpy array, keyed to the
    original DataFrame index so results can be joined back.
    """
    columns = _GEO_CHEM_MODES.get(render_mode, [])
    if not columns:
        return {}

    needed = {_PB206_COL, _PB207_COL}
    if "kappa" in columns:
        needed.add(_PB208_COL)
    missing = needed - set(df.columns)
    if missing:
        logger.debug("Skipping geochem export – missing columns: %s", missing)
        return {}

    try:
        from data.geochemistry import calculate_all_parameters

        pb206 = pd.to_numeric(df[_PB206_COL], errors="coerce").to_numpy(dtype=float)
        pb207 = pd.to_numeric(df[_PB207_COL], errors="coerce").to_numpy(dtype=float)
        pb208 = (
            pd.to_numeric(df[_PB208_COL], errors="coerce").to_numpy(dtype=float)
            if _PB208_COL in df.columns
            else np.full_like(pb206, 29.476)
        )

        results = calculate_all_parameters(pb206, pb207, pb208)

        out: dict[str, np.ndarray] = {}
        for col in columns:
            arr = results.get(col)
            if arr is not None:
                out[col] = np.asarray(arr, dtype=float)
        return out
    except Exception as err:
        logger.warning("Failed to compute geochem params for export: %s", err)
        return {}


def build_export_dataframe(
    *,
    selected_indices: Iterable[int],
    df_global: pd.DataFrame,
    algorithm: str | None,
    embedding: Sequence[Sequence[float]] | None,
    embedding_type: str | None,
    active_subset_indices: Iterable[int] | None,
    pca_component_indices: Sequence[int] | None,
    algorithm_params: Mapping[str, object] | None,
    axis_labels: Mapping[str, str] | None = None,
    render_mode: str | None = None,
) -> pd.DataFrame:
    """Create export DataFrame and append coordinate columns for every mode.

    Column names are taken from the current plot's axis labels so they
    reflect exactly what is shown on screen (e.g. "UMAP 1" / "UMAP 2",
    "206Pb/204Pb" / "207Pb/204Pb" for Pb evolution, etc.).

    For geochemistry modes (V1V2, PB_EVOL_*, PB_MU_AGE, PB_KAPPA_AGE,
    PLUMBOTECTONICS_*) derived parameters such as model age, mu, kappa,
    V1/V2, and Delta values are computed and appended automatically.
    """
    selected_list = list(selected_indices)
    selected_df = df_global.iloc[selected_list].copy()

    if embedding is None or len(embedding) == 0:
        return selected_df

    if active_subset_indices is not None:
        data_indices = sorted(list(active_subset_indices))
    else:
        data_indices = list(range(len(df_global)))

    axis_lbl = dict(axis_labels or {})

    index_map = {orig: i for i, orig in enumerate(data_indices)}
    n_dims = len(embedding[0]) if len(embedding) > 0 else 0

    for dim_idx in range(min(n_dims, 3)):
        col_values: list[float | None] = []
        for idx in selected_list:
            mapped_idx = index_map.get(idx)
            if mapped_idx is None or mapped_idx >= len(embedding):
                col_values.append(None)
                continue
            row = embedding[mapped_idx]
            col_values.append(
                float(row[dim_idx]) if dim_idx < len(row) else None
            )

        if dim_idx == 0:
            col_name = axis_lbl.get("x") or _dimension_label(embedding_type, 0, pca_component_indices)
        elif dim_idx == 1:
            col_name = axis_lbl.get("y") or _dimension_label(embedding_type, 1, pca_component_indices)
        else:
            col_name = axis_lbl.get("z") or _dimension_label(embedding_type, 2, pca_component_indices)

        selected_df[col_name] = col_values

    for key, value in (algorithm_params or {}).items():
        selected_df[f"param_{key}"] = value

    # ---- geochemistry derived parameters ----
    mode = str(render_mode or "") if render_mode else ""
    geo_params = _compute_geochem_params(selected_df, mode)
    for col_name, arr in geo_params.items():
        selected_df[col_name] = arr

    return selected_df


def _dimension_label(
    embedding_type: str | None,
    dim_idx: int,
    pca_component_indices: Sequence[int] | None,
) -> str:
    """Build a fallback column name for a dimension index."""
    if embedding_type in ("PCA", "RobustPCA"):
        pca_idx = list(pca_component_indices or [0, 1])
        pc = pca_idx[dim_idx] + 1 if dim_idx < len(pca_idx) else dim_idx + 1
        return f"PC{pc}"
    prefix = embedding_type or "Dim"
    return f"{prefix} {dim_idx + 1}"


def collect_geochem_curve_data() -> dict[str, pd.DataFrame]:
    """Collect overlay curve equations/data for export.

    Returns a dict mapping sheet-name → DataFrame.  Empty DataFrames
    are omitted.
    """
    from core import app_state

    sheets: dict[str, pd.DataFrame] = {}

    # ---- paleoisochrons ----
    paleo_entries = getattr(app_state, "paleoisochron_label_data", []) or []
    if paleo_entries:
        rows: list[dict[str, Any]] = []
        for e in paleo_entries:
            age = e.get("age")
            slope = e.get("slope")
            intercept = e.get("intercept")
            rows.append(
                {
                    "Age (Ma)": age,
                    "Slope": slope,
                    "Intercept": intercept,
                    "Equation": f"y = {slope:.6f}·x + {intercept:.6f}"
                    if slope is not None and intercept is not None
                    else "",
                }
            )
        if rows:
            sheets[_SHEET_PALEOISOCHRON] = pd.DataFrame(rows)

    # ---- isochron fits ----
    iso_results = getattr(app_state, "isochron_results", {}) or {}
    if iso_results:
        iso_rows: list[dict[str, Any]] = []
        for grp, r in iso_results.items():
            iso_rows.append(
                {
                    "Group": grp,
                    "Age (Ma)": r.get("age_ma") or r.get("age"),
                    "Slope": r.get("slope"),
                    "Intercept": r.get("intercept"),
                    "Slope_err": r.get("slope_err"),
                    "MSWD": r.get("mswd"),
                    "N_points": r.get("n_points"),
                }
            )
        if iso_rows:
            sheets[_SHEET_ISOCHRON] = pd.DataFrame(iso_rows)

    # ---- user equation overlays ----
    eq_overlays = getattr(app_state, "equation_overlays", []) or []
    if eq_overlays:
        eq_rows: list[dict[str, Any]] = []
        for i, ov in enumerate(eq_overlays):
            eq_rows.append(
                {
                    "ID": i + 1,
                    "Expression": ov.get("expression", ""),
                    "Slope": ov.get("slope"),
                    "Intercept": ov.get("intercept"),
                    "Visible": ov.get("visible", True),
                }
            )
        if eq_rows:
            sheets[_SHEET_EQUATIONS] = pd.DataFrame(eq_rows)

    return sheets


def _build_csv_with_comments(
    df: pd.DataFrame,
    file_path: str,
    curve_sheets: dict[str, pd.DataFrame],
) -> str:
    """Write CSV with curve equations as #-prefixed comment header lines."""
    target = _csv_target(file_path)
    with open(target, "w", encoding="utf-8", newline="") as fh:
        # Curve equations as header comments
        for sheet_name, cdf in curve_sheets.items():
            fh.write(f"# [{sheet_name}]\n")
            fh.write(f"# {', '.join(cdf.columns)}\n")
            for _, row in cdf.iterrows():
                vals = ", ".join(
                    f"{v:.6f}" if isinstance(v, float) else str(v)
                    for v in row.values
                )
                fh.write(f"# {vals}\n")
            fh.write("#\n")
        # Data
        df.to_csv(fh, index=False)
    return target


def _build_excel_with_curves(
    df: pd.DataFrame,
    file_path: str,
    curve_sheets: dict[str, pd.DataFrame],
) -> str:
    """Write Excel with data on first sheet, curves on additional sheets."""
    target = _excel_target(file_path)
    with pd.ExcelWriter(target, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Data", index=False)
        for sheet_name, cdf in curve_sheets.items():
            cdf.to_excel(writer, sheet_name=sheet_name, index=False)
    return target


def _csv_target(file_path: str) -> str:
    target = Path(file_path)
    if target.suffix.lower().lstrip(".") != "csv":
        target = target.with_suffix(".csv") if target.suffix else Path(f"{file_path}.csv")
    return str(target)


def _excel_target(file_path: str) -> str:
    target = Path(file_path)
    if target.suffix.lower().lstrip(".") not in {"xlsx", "xls"}:
        target = target.with_suffix(".xlsx") if target.suffix else Path(f"{file_path}.xlsx")
    return str(target)


def export_dataframe_to_file(
    *,
    dataframe: pd.DataFrame,
    file_path: str,
    preferred_format: str | None = None,
    curve_sheets: dict[str, pd.DataFrame] | None = None,
) -> str:
    """Export DataFrame to CSV or Excel and return the normalized target path.

    For CSV output curve equations are written as ``#``-prefixed header
    lines.  For Excel they are placed on separate sheets.
    """
    curve = dict(curve_sheets or {})
    target = Path(file_path)
    normalized_preferred = str(preferred_format or "").strip().lower().lstrip(".")
    suffix = target.suffix.lower().lstrip(".")

    if suffix in {"xlsx", "xls"}:
        if curve:
            return _build_excel_with_curves(dataframe, file_path, curve)
        dataframe.to_excel(str(target), index=False)
        return str(target)

    if suffix == "csv":
        if curve:
            return _build_csv_with_comments(dataframe, file_path, curve)
        dataframe.to_csv(str(target), index=False)
        return str(target)

    if normalized_preferred in {"xlsx", "xls"}:
        if curve:
            return _build_excel_with_curves(dataframe, file_path, curve)
        dataframe.to_excel(str(_excel_target(file_path)), index=False)
        return str(_excel_target(file_path))

    if curve:
        return _build_csv_with_comments(dataframe, file_path, curve)
    dataframe.to_csv(str(_csv_target(file_path)), index=False)
    return str(_csv_target(file_path))


def export_selected_data_to_file(
    *,
    selected_indices: Iterable[int],
    df_global: pd.DataFrame,
    algorithm: str | None,
    embedding: Sequence[Sequence[float]] | None,
    embedding_type: str | None,
    active_subset_indices: Iterable[int] | None,
    pca_component_indices: Sequence[int] | None,
    algorithm_params: Mapping[str, object] | None,
    file_path: str,
    preferred_format: str | None = None,
    axis_labels: Mapping[str, str] | None = None,
    render_mode: str | None = None,
) -> str:
    """Build and export selected data to target file."""
    export_df = build_export_dataframe(
        selected_indices=selected_indices,
        df_global=df_global,
        algorithm=algorithm,
        embedding=embedding,
        embedding_type=embedding_type,
        active_subset_indices=active_subset_indices,
        pca_component_indices=pca_component_indices,
        algorithm_params=algorithm_params,
        axis_labels=axis_labels,
        render_mode=render_mode,
    )
    curve_sheets = collect_geochem_curve_data()
    return export_dataframe_to_file(
        dataframe=export_df,
        file_path=file_path,
        preferred_format=preferred_format,
        curve_sheets=curve_sheets,
    )


def append_selected_data_to_excel(
    *,
    selected_indices: Iterable[int],
    df_global: pd.DataFrame,
    algorithm: str | None,
    embedding: Sequence[Sequence[float]] | None,
    embedding_type: str | None,
    active_subset_indices: Iterable[int] | None,
    pca_component_indices: Sequence[int] | None,
    algorithm_params: Mapping[str, object] | None,
    file_path: str,
    sheet_name: str,
    axis_labels: Mapping[str, str] | None = None,
    render_mode: str | None = None,
) -> str:
    """Append selected data to an Excel sheet and return normalized path."""
    export_df = build_export_dataframe(
        selected_indices=selected_indices,
        df_global=df_global,
        algorithm=algorithm,
        embedding=embedding,
        embedding_type=embedding_type,
        active_subset_indices=active_subset_indices,
        pca_component_indices=pca_component_indices,
        algorithm_params=algorithm_params,
        axis_labels=axis_labels,
        render_mode=render_mode,
    )

    target = _excel_target(file_path)
    curve_sheets = collect_geochem_curve_data()

    import openpyxl  # noqa: F401

    if Path(target).exists():
        with pd.ExcelWriter(target, engine="openpyxl", mode="a", if_sheet_exists="new") as writer:
            export_df.to_excel(writer, sheet_name=sheet_name, index=False)
            for sname, cdf in curve_sheets.items():
                cdf.to_excel(writer, sheet_name=sname, index=False)
    else:
        with pd.ExcelWriter(target, engine="openpyxl") as writer:
            export_df.to_excel(writer, sheet_name=sheet_name, index=False)
            for sname, cdf in curve_sheets.items():
                cdf.to_excel(writer, sheet_name=sname, index=False)

    return target
