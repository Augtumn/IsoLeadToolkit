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
#: Keys must match calculate_all_parameters() result keys: the source
#: inversion returns 'mu'/'omega'/'nu'/'Init_*', while the model-reference
#: values are 'mu_model'/'kappa_model' (kappa_model is what the
#: PB_KAPPA_AGE / PB_EVOL_86 axes actually plot).
_GEO_CHEM_MODES: dict[str, list[str]] = {
    "V1V2": [
        "t_Model (Ma)", "mu", "mu_model", "kappa_model",
        "V1", "V2", "Delta_alpha", "Delta_beta", "Delta_gamma",
    ],
    "PB_EVOL_76": [
        "t_Model (Ma)", "mu", "mu_model", "omega", "nu",
        "Init_206_204", "Init_207_204", "Init_208_204",
    ],
    "PB_EVOL_86": [
        "t_Model (Ma)", "mu", "mu_model", "kappa_model", "omega", "nu",
        "Init_206_204", "Init_207_204", "Init_208_204",
    ],
    "PB_MU_AGE": ["t_Model (Ma)", "mu", "mu_model"],
    "PB_KAPPA_AGE": ["t_Model (Ma)", "kappa_model"],
    "PLUMBOTECTONICS_76": [
        "t_Model (Ma)", "mu", "mu_model", "omega", "nu",
        "Init_206_204", "Init_207_204", "Init_208_204",
    ],
    "PLUMBOTECTONICS_86": [
        "t_Model (Ma)", "mu", "mu_model", "kappa_model", "omega", "nu",
        "Init_206_204", "Init_207_204", "Init_208_204",
    ],
}

_PB206_COL = "206Pb/204Pb"
_PB207_COL = "207Pb/204Pb"
_PB208_COL = "208Pb/204Pb"

#: Modes whose plots actually carry overlay curves (paleoisochrons, isochron
#: fits, equations). Other modes must not inherit stale curve sheets from
#: previous geochemistry renders.
_CURVE_EXPORT_MODES = {
    "PB_EVOL_76",
    "PB_EVOL_86",
    "PLUMBOTECTONICS_76",
    "PLUMBOTECTONICS_86",
    "PB_MU_AGE",
    "PB_KAPPA_AGE",
}


def _curve_sheets_for_mode(render_mode: str | None) -> dict[str, pd.DataFrame]:
    """Return curve overlay sheets only for modes that plot them."""
    mode = str(render_mode or "").strip().upper()
    if mode not in _CURVE_EXPORT_MODES:
        return {}
    return collect_geochem_curve_data()


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
        logger.warning("Failed to compute geochem params for export (mode=%s): %s", render_mode, err)
        return {}


def build_export_dataframe(
    *,
    selected_indices: Iterable[int],
    df_global: pd.DataFrame,
    embedding: Sequence[Sequence[float]] | None,
    embedding_type: str | None,
    active_subset_indices: Iterable[int] | None,
    pca_component_indices: Sequence[int] | None,
    algorithm_params: Mapping[str, object] | None,
    axis_labels: Mapping[str, str] | None = None,
    render_mode: str | None = None,
    pca_variance: Sequence[float] | None = None,
) -> pd.DataFrame:
    """Create export DataFrame and append coordinate columns for every mode.

    Column names are taken from the current plot's axis labels so they
    reflect exactly what is shown on screen (e.g. "UMAP 1" / "UMAP 2",
    "206Pb/204Pb" / "207Pb/204Pb" for Pb evolution, etc.).

    For geochemistry modes (V1V2, PB_EVOL_*, PB_MU_AGE, PB_KAPPA_AGE,
    PLUMBOTECTONICS_*) derived parameters such as model age, mu, kappa,
    V1/V2, and Delta values are computed and appended automatically.
    """
    selected_list = sorted(selected_indices)
    selected_df = df_global.iloc[selected_list].copy()

    # 2D/3D raw modes plot the raw columns themselves — their axis labels
    # are real column names. last_embedding is stale there (left over from
    # a previous embedding render), so appending it would silently write
    # wrong coordinates under real column names.
    mode_upper = str(render_mode or "").strip().upper()
    if mode_upper in ("2D", "3D"):
        embedding = None

    # ---- geochemistry derived parameters (independent of coordinates) ----
    mode = str(render_mode or "") if render_mode else ""
    geo_params = _compute_geochem_params(selected_df, mode)
    for col_name, arr in geo_params.items():
        selected_df[col_name] = arr

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

    # PCA / RobustPCA: append the explained-variance ratio of the plotted
    # components (diagnostic extra data carried in app_state.last_pca_variance).
    if embedding_type in ("PCA", "RobustPCA") and pca_variance is not None:
        pca_idx = list(pca_component_indices or [0, 1])
        variance = np.asarray(pca_variance, dtype=float)
        for dim_idx in range(min(n_dims, len(pca_idx))):
            if dim_idx < len(variance):
                pc = int(pca_idx[dim_idx]) + 1
                selected_df[f"variance_ratio_PC{pc}"] = float(variance[dim_idx])

    for key, value in (algorithm_params or {}).items():
        selected_df[f"param_{key}"] = value

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
            expression = str(ov.get("expression", "") or "")
            slope, intercept = _parse_linear_expression(expression)
            eq_rows.append(
                {
                    "ID": i + 1,
                    "Expression": expression,
                    "Slope": slope,
                    "Intercept": intercept,
                    # Overlays store their visibility under 'enabled'.
                    "Visible": bool(ov.get("enabled", True)),
                }
            )
        if eq_rows:
            sheets[_SHEET_EQUATIONS] = pd.DataFrame(eq_rows)

    return sheets


_LINEAR_EXPRESSION_RE = None


def _parse_linear_expression(expression: str) -> tuple[float | None, float | None]:
    """Parse ``y = m*x + b`` style overlay expressions into (slope, intercept).

    Returns (None, None) when the expression is not a simple linear form.
    """
    global _LINEAR_EXPRESSION_RE
    if _LINEAR_EXPRESSION_RE is None:
        import re

        _LINEAR_EXPRESSION_RE = re.compile(
            r"y\s*=\s*([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)"
            r"\s*\*?\s*x\s*([+-]\s*(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)"
        )
    match = _LINEAR_EXPRESSION_RE.search(str(expression))
    if not match:
        return None, None
    try:
        slope = float(match.group(1))
        intercept = float(match.group(2).replace(" ", ""))
    except (TypeError, ValueError):
        return None, None
    return slope, intercept


def _csv_comment_value(value: Any) -> str:
    """Format a value for a #-comment line, quoting commas/quotes/newlines."""
    text = f"{value:.6f}" if isinstance(value, float) else str(value)
    if any(ch in text for ch in ',"\n'):
        text = '"' + text.replace('"', '""') + '"'
    return text


def _build_csv_with_comments(
    df: pd.DataFrame,
    file_path: str,
    curve_sheets: dict[str, pd.DataFrame],
) -> str:
    """Write CSV with curve equations as #-prefixed comment header lines."""
    target = _csv_target(file_path)
    # utf-8-sig: Excel otherwise renders CJK column/group names as mojibake.
    with open(target, "w", encoding="utf-8-sig", newline="") as fh:
        # Curve equations as header comments
        for sheet_name, cdf in curve_sheets.items():
            fh.write(f"# [{sheet_name}]\n")
            fh.write(f"# {', '.join(str(c) for c in cdf.columns)}\n")
            for _, row in cdf.iterrows():
                vals = ", ".join(_csv_comment_value(v) for v in row.values)
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
    # openpyxl only supports .xlsx; treat any other suffix (incl. .xls) as
    # a missing extension rather than attempting a failing write.
    if target.suffix.lower() != ".xlsx":
        target = target.with_suffix(".xlsx") if target.suffix else Path(f"{file_path}.xlsx")
    return str(target)


def _unique_sheet_name(sheet_name: str, existing: set[str]) -> str:
    """Return *sheet_name*, uniquified against *existing* (Sheet -> Sheet1)."""
    name = str(sheet_name)
    if name not in existing:
        return name
    base = name
    suffix = 1
    while f"{base}{suffix}" in existing:
        suffix += 1
    return f"{base}{suffix}"


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

    if suffix == "xlsx":
        if curve:
            return _build_excel_with_curves(dataframe, file_path, curve)
        dataframe.to_excel(str(target), index=False)
        return str(target)

    if suffix == "csv":
        if curve:
            return _build_csv_with_comments(dataframe, file_path, curve)
        dataframe.to_csv(str(target), index=False, encoding="utf-8-sig")
        return str(target)

    if normalized_preferred == "xlsx":
        if curve:
            return _build_excel_with_curves(dataframe, file_path, curve)
        dataframe.to_excel(str(_excel_target(file_path)), index=False)
        return str(_excel_target(file_path))

    if curve:
        return _build_csv_with_comments(dataframe, file_path, curve)
    dataframe.to_csv(str(_csv_target(file_path)), index=False, encoding="utf-8-sig")
    return str(_csv_target(file_path))


def export_selected_data_to_file(
    *,
    selected_indices: Iterable[int],
    df_global: pd.DataFrame,
    embedding: Sequence[Sequence[float]] | None,
    embedding_type: str | None,
    active_subset_indices: Iterable[int] | None,
    pca_component_indices: Sequence[int] | None,
    algorithm_params: Mapping[str, object] | None,
    file_path: str,
    preferred_format: str | None = None,
    axis_labels: Mapping[str, str] | None = None,
    render_mode: str | None = None,
    pca_variance: Sequence[float] | None = None,
) -> str:
    """Build and export selected data to target file."""
    export_df = build_export_dataframe(
        selected_indices=selected_indices,
        df_global=df_global,
        embedding=embedding,
        embedding_type=embedding_type,
        active_subset_indices=active_subset_indices,
        pca_component_indices=pca_component_indices,
        algorithm_params=algorithm_params,
        axis_labels=axis_labels,
        render_mode=render_mode,
        pca_variance=pca_variance,
    )
    curve_sheets = _curve_sheets_for_mode(render_mode)
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
    embedding: Sequence[Sequence[float]] | None,
    embedding_type: str | None,
    active_subset_indices: Iterable[int] | None,
    pca_component_indices: Sequence[int] | None,
    algorithm_params: Mapping[str, object] | None,
    file_path: str,
    sheet_name: str,
    axis_labels: Mapping[str, str] | None = None,
    render_mode: str | None = None,
    pca_variance: Sequence[float] | None = None,
) -> str:
    """Append selected data to an Excel sheet and return normalized path."""
    export_df = build_export_dataframe(
        selected_indices=selected_indices,
        df_global=df_global,
        embedding=embedding,
        embedding_type=embedding_type,
        active_subset_indices=active_subset_indices,
        pca_component_indices=pca_component_indices,
        algorithm_params=algorithm_params,
        axis_labels=axis_labels,
        render_mode=render_mode,
        pca_variance=pca_variance,
    )

    target = _excel_target(file_path)
    curve_sheets = _curve_sheets_for_mode(render_mode)

    if Path(target).exists():
        # Resolve sheet-name collisions up front: if_sheet_exists="new"
        # would silently rename the sheet (Data -> Data1) while the UI
        # reports the requested name; curve sheets would also accumulate.
        import openpyxl

        wb = openpyxl.load_workbook(target)
        try:
            existing = set(wb.sheetnames)
        finally:
            wb.close()
        actual_sheet = _unique_sheet_name(sheet_name, existing)
        if actual_sheet != sheet_name:
            logger.info(
                "Sheet '%s' already exists; appending as '%s'", sheet_name, actual_sheet
            )
        curve_sheets = {
            sname: cdf
            for sname, cdf in curve_sheets.items()
            if sname not in existing
        }
        with pd.ExcelWriter(target, engine="openpyxl", mode="a", if_sheet_exists="new") as writer:
            export_df.to_excel(writer, sheet_name=actual_sheet, index=False)
            for sname, cdf in curve_sheets.items():
                cdf.to_excel(writer, sheet_name=sname, index=False)
    else:
        with pd.ExcelWriter(target, engine="openpyxl") as writer:
            export_df.to_excel(writer, sheet_name=sheet_name, index=False)
            for sname, cdf in curve_sheets.items():
                cdf.to_excel(writer, sheet_name=sname, index=False)

    return target
