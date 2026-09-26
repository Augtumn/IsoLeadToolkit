"""Origin project export use case.

Extracts plot data from the current matplotlib axes and app_state,
constructs an Origin project (.opju) with worksheets and graphs that
replicate the current view.  Also exports a companion image via
Origin's save_fig when requested.

Supports all render modes:
  - UMAP, tSNE, PCA, RobustPCA → scatter data only
  - V1V2 → scatter with V1/V2 labels
  - 2D → raw data scatter
  - 3D → 3D scatter
  - TERNARY → ternary scatter (t, l, r columns)
  - PB_EVOL_76, PB_EVOL_86 → scatter + model curves + paleoisochrons
    + isochrons + equation overlays
  - PLUMBOTECTONICS_76, PLUMBOTECTONICS_86 → scatter + plumbotectonics curves
  - PB_MU_AGE, PB_KAPPA_AGE → scatter data

Worksheet naming:
  - Scatter sheets: named by group label
  - Overlay sheets: "OV_" prefix with descriptive name
  - Isochron sheets: "ISO_" prefix with age in name
  - Ternary sheets: "TER_" prefix
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from core import app_state

logger = logging.getLogger(__name__)

_originpro = None
_originpro_checked = False

_MARKER_TO_ORIGIN: dict[str, int] = {
    "o": 1,  "s": 0,  "^": 2,  "v": 3,  "D": 4,  "d": 4,
    "*": 7,  "+": 5,  "x": 6,  "p": 8,  "h": 9,  "H": 10,
    ".": 11, "<": 12, ">": 13, "1": 2,  "2": 3,  "3": 12,
    "4": 13, "8": 4,  "P": 8,  "X": 6,  "|": 14, "_": 15,
}

# ── lazy import ──────────────────────────────────────────────────────

def _lazy_import_originpro() -> Any:
    """Lazy import originpro; returns module or None if unavailable."""
    global _originpro, _originpro_checked
    if _originpro_checked:
        return _originpro
    _originpro_checked = True
    try:
        import originpro as _op
        _originpro = _op
    except ImportError as err:
        logger.info("originpro not available: %s", err)
        _originpro = None
    return _originpro


def is_origin_available() -> bool:
    """Return True if originpro can be imported."""
    return _lazy_import_originpro() is not None


#: Origin ternary axes and worksheet columns are conventionally 0-100.
_TERNARY_PERCENT_SCALE = 100.0

#: Symbol size bounds accepted by the Origin plot object.
_SYMBOL_SIZE_MIN = 3
_SYMBOL_SIZE_MAX = 20


def _ternary_percent(values: Any) -> list[float]:
    """Convert fractional ternary components (0-1) to Origin's 0-100 scale."""
    return [float(value) * _TERNARY_PERCENT_SCALE for value in (values or [])]


def _ternary_column_names(ternary_cols: Any) -> list[str]:
    """Column headers for the three ternary components."""
    names = [str(name) for name in (ternary_cols or ["Top", "Left", "Right"])]
    while len(names) < 3:
        names.append(["Top", "Left", "Right"][len(names)])
    return [f"{name} (%)" for name in names[:3]]


def _export_symbol_size() -> int:
    """Origin symbol size derived from the plot point size."""
    try:
        size = int(round(float(getattr(app_state, "point_size", 8) or 8) / 5.0))
    except Exception:
        size = 8
    return max(_SYMBOL_SIZE_MIN, min(size, _SYMBOL_SIZE_MAX))


def _safe_sheet_call(notes: list[str], label: str, func, *args) -> bool:
    """Call a worksheet/plot API that may be missing in older originpro builds."""
    try:
        func(*args)
        return True
    except Exception as err:
        logger.debug("Origin capability %s unavailable: %s", label, err)
        notes.append(f"{label} not applied")
        return False


def _set_column_long_name(notes: list[str], wks: Any, column: int, name: str) -> None:
    """Give a worksheet column a long name (what Origin displays as its header)."""
    if not name:
        return
    _safe_sheet_call(notes, f"column long name {name}", wks.set_label, column, 'L', name)


def _apply_axis_range(
    notes: list[str], op: Any, layer: Any, axis_name: str, start: float, end: float
) -> bool:
    """Set an axis range through LabTalk, which every Origin build understands."""
    if end <= start:
        return False
    command = f"layer.{axis_name}.from = {start:g}; layer.{axis_name}.to = {end:g};"
    try:
        op.lt_exec(command)
    except Exception as err:
        logger.debug("Origin axis range for %s not applied: %s", axis_name, err)
        notes.append(f"axis range {axis_name} not applied")
        return False
    return True


# ── colour & marker helpers ──────────────────────────────────────────

def _hex_color(color: Any) -> str:
    """Convert a matplotlib color spec to a hex string."""
    import matplotlib.colors as mcolors
    try:
        return mcolors.to_hex(color)
    except Exception as err:
        logger.debug("Unrecognized color spec %r: %s", color, err)
        return "#333333"


def _origin_marker(matplotlib_marker: str) -> int:
    """Map a matplotlib marker string to an Origin symbol index."""
    return _MARKER_TO_ORIGIN.get(str(matplotlib_marker), 1)


# ═══════════════════════════════════════════════════════════════════════
#  Data extraction helpers
# ═══════════════════════════════════════════════════════════════════════

def _extract_scatter_groups(ax: Any) -> list[dict[str, Any]]:
    """Extract per-group (x, y) data from matplotlib scatter collections."""
    if ax is None:
        return []

    groups: list[dict[str, Any]] = []
    marker_map = app_state.group_marker_map or {}
    seen: set[str] = set()

    for coll in getattr(ax, "collections", []):
        try:
            label = str(coll.get_label() or "")
        except Exception:
            continue
        if not label or label.startswith("_"):
            continue
        if label in seen:
            continue
        seen.add(label)

        try:
            offsets = coll.get_offsets()
            if offsets is None or len(offsets) == 0:
                continue
        except Exception:
            continue

        try:
            fc = coll.get_facecolors()
            color = _hex_color(fc[0]) if len(fc) > 0 else "#333333"
        except Exception:
            color = "#333333"

        groups.append({
            "label": label,
            "x": offsets[:, 0].tolist(),
            "y": offsets[:, 1].tolist(),
            "color": color,
            "marker": _origin_marker(marker_map.get(label, "o")),
        })

    return groups


def _extract_scatter_groups_3d(ax: Any) -> list[dict[str, Any]]:
    """Extract per-group (x, y, z) data from 3D scatter collections."""
    if ax is None:
        return []

    groups: list[dict[str, Any]] = []
    marker_map = app_state.group_marker_map or {}
    seen: set[str] = set()

    for coll in getattr(ax, "collections", []):
        try:
            label = str(coll.get_label() or "")
        except Exception:
            continue
        if not label or label.startswith("_"):
            continue
        if label in seen:
            continue
        seen.add(label)

        offsets3d = getattr(coll, "_offsets3d", None)
        if offsets3d is None or len(offsets3d) != 3:
            continue
        xs, ys, zs = offsets3d
        if len(xs) == 0:
            continue

        try:
            fc = coll.get_facecolors()
            color = _hex_color(fc[0]) if len(fc) > 0 else "#333333"
        except Exception:
            color = "#333333"

        groups.append({
            "label": label,
            "x": np.asarray(xs).tolist(),
            "y": np.asarray(ys).tolist(),
            "z": np.asarray(zs).tolist(),
            "color": color,
            "marker": _origin_marker(marker_map.get(label, "o")),
        })

    return groups


# ── TASK 1: Ternary data extraction ──────────────────────────────────

def _extract_ternary_data(ax: Any) -> list[dict[str, Any]]:
    """Extract ternary scatter data grouped by category label.

    mpltern axes store ternary coords differently from standard 2-D
    axes: ``scatter(t, l, r)`` produces collections whose
    ``get_offsets()`` returns *Cartesian* coordinates.  We therefore
    recover original ternary values from ``app_state.last_embedding``
    (an N×3 array of [top, left, right]) together with the group
    assignment stored in the plot dataframe.
    """
    if ax is None:
        return []

    # ── recover raw ternary columns and per-sample group ─────────
    embedding = getattr(app_state, "last_embedding", None)
    if embedding is None or embedding.shape[1] < 3:
        logger.debug("_extract_ternary_data: no embedding or <3 columns")
        return []

    group_col = app_state.last_group_col
    if group_col is None:
        return []

    df = getattr(app_state.data, "df_global", app_state.df_global)
    if df is None:
        return []

    indices = app_state.active_subset_indices
    if indices is not None and len(indices) > 0:
        df_sub = df.iloc[sorted(indices)]
        groups_series = df_sub[group_col].fillna("Unknown").astype(str).values
    else:
        groups_series = df[group_col].fillna("Unknown").astype(str).values

    # embedding may be longer than groups_series; clip to min length
    n = min(len(embedding), len(groups_series))
    embedding = embedding[:n]
    groups_series = groups_series[:n]

    marker_map = app_state.group_marker_map or {}
    palette = app_state.current_palette or {}
    ternary_cols = app_state.selected_ternary_cols

    groups_out: list[dict[str, Any]] = []
    for cat in sorted(set(groups_series)):
        mask = groups_series == cat
        if not np.any(mask):
            continue
        cat_data = embedding[mask]
        # Normalize ternary components to 0–1 range (t / (t+l+r))
        t_raw, l_raw, r_raw = cat_data[:, 0], cat_data[:, 1], cat_data[:, 2]
        from visualization.plotting.ternary import normalize_ternary_components
        t_norm, l_norm, r_norm = normalize_ternary_components(t_raw, l_raw, r_raw)
        color = palette.get(cat, "#333333")
        groups_out.append({
            "label": cat,
            "t": t_norm.tolist(),
            "l": l_norm.tolist(),
            "r": r_norm.tolist(),
            "color": color,
            "marker": _origin_marker(marker_map.get(cat, "o")),
            "ternary_cols": ternary_cols,
        })

    return groups_out


# ── TASK 2: Isochron regression line extraction ──────────────────────

def _extract_isochron_lines(ax: Any) -> list[dict[str, Any]]:
    """Extract isochron regression lines from ``app_state.isochron_results``.

    Each result dict contains *slope*, *intercept*, *slope_err*,
    *intercept_err*, *n_points*, *mswd*, and optionally *age_ma*.
    We export each as a line overlay covering the current axis x-range.
    """
    results = app_state.isochron_results or {}
    if not results:
        return []

    # choose x-range: prefer current axis limits, else fallback
    if ax is not None:
        try:
            xlim = ax.get_xlim()
            x_min, x_max = float(xlim[0]), float(xlim[1])
        except Exception:
            x_min, x_max = 0.0, 45.0
    else:
        x_min, x_max = 0.0, 45.0

    xs = np.linspace(x_min, x_max, 100)
    lines: list[dict[str, Any]] = []

    for group, fit in sorted(results.items()):
        slope = fit.get("slope")
        intercept = fit.get("intercept")
        if slope is None or intercept is None:
            continue
        ys = float(slope) * xs + float(intercept)

        age = fit.get("age_ma") or fit.get("age")
        mswd = fit.get("mswd")
        n_pts = fit.get("n_points")
        slope_err = fit.get("slope_err")
        intercept_err = fit.get("intercept_err")

        # build descriptive label
        label_parts = []
        if age is not None and float(age) >= 0:
            label_parts.append(f"{float(age):.0f} Ma")
        if n_pts is not None:
            label_parts.append(f"n={n_pts}")
        if mswd is not None:
            label_parts.append(f"MSWD={mswd:.2f}")
        label = ", ".join(label_parts) if label_parts else group

        # equation comment
        eq = f"y = {slope:.6f} * x + {intercept:.6f}"
        if slope_err is not None:
            eq += f"  (slope_err={slope_err:.6f})"
        if intercept_err is not None:
            eq += f"  (intercept_err={intercept_err:.6f})"

        lines.append({
            "x": xs.tolist(),
            "y": ys.tolist(),
            "label": label,
            "group": group,
            "color": "#ef4444",   # distinguished colour for isochrons
            "width": 1.5,
            "equation": eq,
            "slope": slope,
            "intercept": intercept,
            "age": age,
        })

    return lines


# ── Overlay extraction: model curves + paleoisochrons ────────────────

def _extract_pb_evolution_overlay_data(
    actual_algorithm: str,
    xlim: tuple[float, float] = (0.0, 45.0),
) -> dict[str, list[tuple[np.ndarray, np.ndarray, str, dict[str, Any]]]]:
    """Recompute overlay curves for Pb evolution plots via the
    geochemistry engine (model curves + paleoisochrons).

    *xlim* is the axis range used to sample paleoisochron lines; callers
    pass the current plot's range so overlays match the on-screen view.
    """
    result: dict[str, list[tuple[np.ndarray, np.ndarray, str, dict[str, Any]]]] = {}

    try:
        from visualization.plotting.data import _lazy_import_geochemistry
        geochemistry, _ = _lazy_import_geochemistry()
        if geochemistry is None:
            logger.debug("_extract_pb_evolution_overlay_data: geochemistry not available")
            return result
        params = geochemistry.engine.get_parameters()
    except Exception as err:
        logger.warning("Failed to load geochemistry engine: %s", err)
        return result

    # ── model curves ──────────────────────────────────────────────
    if app_state.show_model_curves:
        curves: list[tuple[np.ndarray, np.ndarray, str, dict[str, Any]]] = []
        try:
            t_vals = np.linspace(0, 4500, 500)
            mc = geochemistry.calculate_modelcurve(t_vals, params=params)
            if actual_algorithm in ("PB_EVOL_76", "PLUMBOTECTONICS_76"):
                x_col, y_col = "Pb206_204", "Pb207_204"
            else:
                x_col, y_col = "Pb206_204", "Pb208_204"
            x_vals = np.asarray(mc[x_col])
            y_vals = np.asarray(mc[y_col])
            if x_vals is not None and y_vals is not None:
                model_name = str(params.get("model_name", "Model"))
                curves.append((
                    x_vals, y_vals,
                    model_name,
                    {"color": "#64748b", "width": 1.2,
                     "equation": f"Pb evolution curve — {model_name}"},
                ))
        except Exception as err:
            logger.warning("Failed to compute model curves for Origin export: %s", err)
        if curves:
            result["model_curves"] = curves

    # ── paleoisochrons ────────────────────────────────────────────
    if app_state.show_paleoisochrons:
        equations: list[tuple[np.ndarray, np.ndarray, str, dict[str, Any]]] = []
        ages = app_state.paleoisochron_ages
        age_step = getattr(app_state, "paleoisochron_age_step", 1000)
        if not ages and age_step > 0:
            ages = list(range(0, 4501, age_step))
        try:
            for age in ages:
                line_info = geochemistry.calculate_paleoisochron_line(
                    age, params=params, algorithm=actual_algorithm,
                )
                if not line_info:
                    continue
                slope, intercept = line_info
                xs = np.linspace(xlim[0], xlim[1], 200)
                ys = slope * xs + intercept
                label = f"{float(age):.0f} Ma (y={slope:.4f}x+{intercept:.4f})"
                equations.append((
                    xs, ys, label,
                    {"color": "#94a3b8", "width": 0.9,
                     "slope": slope, "intercept": intercept,
                     "equation": f"Paleoisochron {float(age):.0f} Ma: y = {slope:.6f}x + {intercept:.6f}"},
                ))
        except Exception as err:
            logger.warning("Failed to compute paleoisochrons for Origin export: %s", err)
        if equations:
            result["paleoisochrons"] = equations

    return result


# ── TASK 3: Plumbotectonics curve extraction ─────────────────────────

def _extract_plumbotectonics_curves(
    algorithm: str,
) -> dict[str, list[tuple[np.ndarray, np.ndarray, str, dict[str, Any]]]]:
    """Extract plumbotectonics model curves from ``PLUMBOTECTONICS_SECTIONS``.

    Returns a dict keyed by ``"plumbotectonics_curves"`` containing
    (x, y, name, style) tuples, one per tectonic group in the active
    model section.
    """
    result: dict[str, list[tuple[np.ndarray, np.ndarray, str, dict[str, Any]]]] = {}

    try:
        from data.plumbotectonics_data import PLUMBOTECTONICS_SECTIONS
        from visualization.plotting.geochem.plumbotectonics_metadata import (
            _select_plumbotectonics_section,
            get_plumbotectonics_group_entries,
        )
        from visualization.plotting.geochem.plumbotectonics_curves import (
            _fit_plumbotectonics_curve,
        )
    except ImportError as err:
        logger.debug("_extract_plumbotectonics_curves: imports failed: %s", err)
        return result

    sections = PLUMBOTECTONICS_SECTIONS
    section = _select_plumbotectonics_section(sections)
    if not section:
        return result

    variant_label = section.get("label", "Plumbotectonics")
    y_key = "pb207" if str(algorithm).endswith("_76") else "pb208"

    group_entries = get_plumbotectonics_group_entries(section=section)
    curves: list[tuple[np.ndarray, np.ndarray, str, dict[str, Any]]] = []

    for group, meta in zip(section.get("groups", []), group_entries):
        name = meta["name"]
        x_vals = group.get("pb206", [])
        y_vals = group.get(y_key, [])
        x_fit, y_fit = _fit_plumbotectonics_curve(x_vals, y_vals)
        if len(x_fit) < 2:
            continue

        curves.append((
            x_fit, y_fit,
            f"{name} ({variant_label})",
            {
                "color": "#3b82f6",
                "width": 1.2,
                "equation": f"Plumbotectonics curve: {name} — model {variant_label}",
            },
        ))

    if curves:
        result["plumbotectonics_curves"] = curves
    return result


# ── Equation overlay extraction ──────────────────────────────────────

def _extract_equation_overlays(
    ax: Any, x_min: float = 0.0, x_max: float = 45.0,
) -> list[dict[str, Any]]:
    """Extract user-defined equation overlays from ``app_state.overlay``.

    Each equation overlay contains an *expression* (e.g. ``"1.0049*x+20.259"``),
    *label*, *color*, *linewidth*, *linestyle*, *alpha*, and *enabled* flag.
    Returns a list of dicts with *x*, *y*, *label*, and *equation*.
    """
    eqs = app_state.equation_overlays
    if eqs is None:
        overlay_state = app_state.overlay
        if overlay_state is not None:
            eqs = getattr(overlay_state, "equation_overlays", [])
        else:
            eqs = []

    if not eqs:
        return []

    xs = np.linspace(x_min, x_max, 200)
    lines: list[dict[str, Any]] = []

    try:
        from visualization.plotting.geochem.equation_overlays import _safe_eval_expression
    except ImportError:
        _safe_eval_expression = None

    for eq in eqs:
        if not eq.get("enabled", True):
            continue

        expression = eq.get("expression", "")
        label = eq.get("label", expression)
        color = eq.get("color", "#ef4444")
        width = eq.get("linewidth", 1.0)

        if _safe_eval_expression is not None:
            try:
                ys = _safe_eval_expression(expression, xs)
                ys = np.asarray(ys, dtype=float)
            except Exception as err:
                logger.debug("Failed to eval equation %r: %s", expression, err)
                continue
        else:
            slope = eq.get("slope")
            intercept = eq.get("intercept")
            if slope is None or intercept is None:
                continue
            ys = float(slope) * xs + float(intercept)

        lines.append({
            "x": xs.tolist(),
            "y": ys.tolist(),
            "label": label,
            "color": color,
            "width": width,
            "equation": f"Equation overlay: {expression}",
        })

    return lines


# ═══════════════════════════════════════════════════════════════════════
#  Sheet name helpers
# ═══════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════
#  Origin-ready data export (works without originpro/COM automation)
# ═══════════════════════════════════════════════════════════════════════

#: Guard against pathological views producing hundreds of worksheets.
_MAX_ORIGIN_SHEETS = 60


def _origin_frame_columns(axis_labels: dict[str, str]) -> tuple[str, str, str]:
    """Column headers for scatter sheets, avoiding duplicates."""
    x_name = str(axis_labels.get("x") or "X").strip() or "X"
    y_name = str(axis_labels.get("y") or "Y").strip() or "Y"
    z_name = str(axis_labels.get("z") or "Z").strip() or "Z"
    if x_name == y_name:
        x_name, y_name = "X", "Y"
    return x_name, y_name, z_name


def _origin_group_frame(
    group: dict[str, Any], is_ternary: bool, axis_labels: dict[str, str]
) -> "Any":
    """Build one worksheet frame for a scatter group."""
    import pandas as pd

    if is_ternary:
        # Same 0-100 scale and headers as the Origin project path.
        columns = _ternary_column_names(axis_labels.get("ternary_cols") or group.get("ternary_cols"))
        return pd.DataFrame(
            {
                columns[0]: _ternary_percent(group.get("t", [])),
                columns[1]: _ternary_percent(group.get("l", [])),
                columns[2]: _ternary_percent(group.get("r", [])),
            }
        )

    x_name, y_name, z_name = _origin_frame_columns(axis_labels)
    frame = pd.DataFrame({x_name: group.get("x", []), y_name: group.get("y", [])})
    if group.get("z") is not None and len(group.get("z") or []) == len(frame):
        frame[z_name] = group["z"]
    return frame


def _origin_info_frame(data: dict[str, Any]) -> "Any":
    """Worksheet describing the exported view and how to import it."""
    import pandas as pd
    from datetime import datetime

    rows = [
        ("Export", "IsotopesAnalyse - Origin-ready data"),
        ("Exported at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ("Render mode", data["mode"]),
        ("Plot title", data["title"]),
        ("X label", data["axis_labels"].get("x", "")),
        ("Y label", data["axis_labels"].get("y", "")),
        ("Scatter series", len(data["scatter_groups"])),
        ("Overlay series", sum(len(v) for v in data["overlay_data"].values())),
        ("Isochron series", len(data["isochron_lines"])),
        ("Equation overlays", len(data["equation_lines"])),
        (
            "How to import",
            "Origin: File > Import > Excel, then select the X/Y columns and plot. "
            "Each sheet is one series; the Info sheet is for reference only.",
        ),
    ]
    return pd.DataFrame(rows, columns=["Item", "Value"])


def export_origin_ready_data(file_path: str) -> bool:
    """Write the current view as an Origin-importable Excel workbook.

    Used when ``originpro`` (COM automation) is unavailable: one worksheet per
    series with the current axis labels as column headers, plus an Info sheet.
    """
    import pandas as pd

    ax = app_state.ax
    if ax is None:
        logger.warning("Origin-ready data export requested without axes.")
        return False

    try:
        data = collect_origin_export_data(ax)
    except Exception as err:
        logger.warning("Origin-ready data export failed during extraction: %s", err)
        return False

    if not data["scatter_groups"]:
        logger.warning("No scatter data available for Origin-ready data export.")
        return False

    used: set[str] = set()
    is_ternary = bool(data["is_ternary"])
    try:
        with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
            _origin_info_frame(data).to_excel(writer, sheet_name="Info", index=False)
            used.add("Info")

            for group in data["scatter_groups"]:
                name = _origin_sheet_name(str(group.get("label") or "group"), "", used)
                _origin_group_frame(group, is_ternary, data["axis_labels"]).to_excel(
                    writer, sheet_name=name, index=False
                )

            overlay_sheets = 0
            for curves in data["overlay_data"].values():
                for x_arr, y_arr, curve_label, _style in curves:
                    if len(used) >= _MAX_ORIGIN_SHEETS:
                        logger.warning("Origin-ready export: sheet limit reached.")
                        break
                    name = _origin_sheet_name(str(curve_label), "OV_", used)
                    pd.DataFrame({"X": x_arr, "Y": y_arr}).to_excel(
                        writer, sheet_name=name, index=False
                    )
                    overlay_sheets += 1

            for iso in data["isochron_lines"]:
                if len(used) >= _MAX_ORIGIN_SHEETS:
                    break
                name = _origin_sheet_name(str(iso.get("label") or "isochron"), "ISO_", used)
                pd.DataFrame({"X": iso["x"], "Y": iso["y"]}).to_excel(
                    writer, sheet_name=name, index=False
                )

            for eq in data["equation_lines"]:
                if len(used) >= _MAX_ORIGIN_SHEETS:
                    break
                name = _origin_sheet_name(str(eq.get("label") or "equation"), "EQ_", used)
                pd.DataFrame({"X": eq["x"], "Y": eq["y"]}).to_excel(
                    writer, sheet_name=name, index=False
                )
    except Exception as err:
        logger.warning("Origin-ready data export failed while writing: %s", err)
        return False

    logger.info(
        "Origin-ready data exported to %s (%d sheets, %d overlay series)",
        file_path,
        len(used),
        overlay_sheets,
    )
    return True


def _origin_sheet_name(label: str, prefix: str, used: set[str], max_len: int = 28) -> str:
    """Generate a unique, Origin-safe sheet name from *label* with prefix."""
    # Origin forbids [] * ? \ in sheet names; strip them along with
    # whitespace and punctuation that confuse worksheet naming.
    base = "".join(
        ch for ch in str(label).replace("/", "_").replace(":", "_").replace(" ", "_")
        if ch not in "[]*?\\"
    )[:max_len]
    base = base or "Sheet"
    name = f"{prefix}{base}"
    suffix = 1
    while name in used:
        name = f"{prefix}{base}_{suffix}"
        suffix += 1
    used.add(name)
    return name


# ═══════════════════════════════════════════════════════════════════════
#  Origin project builder
# ═══════════════════════════════════════════════════════════════════════

def _build_origin_project(
    file_path: str,
    scatter_groups: list[dict[str, Any]],
    axis_labels: dict[str, str],
    overlay_data: dict[str, list[tuple[np.ndarray, np.ndarray, str, dict[str, Any]]]],
    isochron_lines: list[dict[str, Any]] | None = None,
    equation_lines: list[dict[str, Any]] | None = None,
    is_ternary: bool = False,
    title: str | None = None,
    notes: list[str] | None = None,
) -> bool:
    """Create an Origin project with worksheets and a multi-layer graph,
    then export the graph as a PNG image alongside the project.

    Parameters
    ----------
    is_ternary : bool
        If *True*, scatter groups use ``["t", "l", "r"]`` ternary columns
        instead of ``["x", "y"]``.
    """
    op = _lazy_import_originpro()
    if op is None:
        return False

    if notes is None:
        notes = []

    try:
        wb = op.new_book("w", "IsotopesAnalyse_Data")
        sheet_names: set[str] = set()
        wks_map: dict[str, Any] = {}

        # ── scatter worksheets ────────────────────────────────────
        for group in scatter_groups:
            name = _origin_sheet_name(
                group["label"],
                "TER_" if is_ternary else "",
                sheet_names,
            )
            try:
                wks = wb.add_sheet(name)
                if is_ternary:
                    # Origin's ternary template works on a 0-100 scale; the
                    # extractor produces fractions, so scale them here.
                    components = [
                        _ternary_percent(group.get("t", [])),
                        _ternary_percent(group.get("l", [])),
                        _ternary_percent(group.get("r", [])),
                    ]
                    column_names = _ternary_column_names(group.get("ternary_cols"))
                    for index, (values, column_name) in enumerate(zip(components, column_names)):
                        wks.from_list(index, values, column_name)
                    # Designate columns as XYZ for ternary mapping
                    _safe_sheet_call(notes, "ternary column designation", wks.cols_axis, 'xyz')
                    for index, column_name in enumerate(column_names):
                        _set_column_long_name(notes, wks, index, column_name)
                elif group.get("z"):
                    wks.from_list(0, group["x"], "X")
                    wks.from_list(1, group["y"], "Y")
                    wks.from_list(2, group["z"], "Z")
                    _safe_sheet_call(notes, "3D column designation", wks.cols_axis, 'xyz')
                    for index, column_name in enumerate(("X", "Y", "Z")):
                        _set_column_long_name(notes, wks, index, column_name)
                else:
                    x_name, y_name, _z_name = _origin_frame_columns(axis_labels)
                    wks.from_list(0, group["x"], x_name)
                    wks.from_list(1, group["y"], y_name)
                    _safe_sheet_call(notes, "XY column designation", wks.cols_axis, 'xy')
                    _set_column_long_name(notes, wks, 0, x_name)
                    _set_column_long_name(notes, wks, 1, y_name)
                wks_map[group["label"]] = (wks, name)
            except Exception as err:
                logger.warning("Failed to create sheet for %s: %s", name, err)

        if not wks_map:
            logger.warning("No worksheets created for scatter data.")
            return False

        # ── graph ─────────────────────────────────────────────────
        if is_ternary:
            try:
                gp = op.new_graph(template="ternary")
                notes.append("ternary graph template")
            except Exception as err:
                # Origin builds without the ternary app still get the data as an
                # XYZ scatter instead of failing outright.
                logger.warning("Ternary template unavailable (%s); using scatter.", err)
                notes.append("ternary template unavailable - exported as XYZ scatter")
                gp = op.new_graph(template="scatter")
        else:
            gp = op.new_graph(template="scatter")
        gl = gp[0]

        legend_entries: list[str] = []
        plot_idx = 0

        for group in scatter_groups:
            entry = wks_map.get(group["label"])
            if entry is None:
                continue
            wks, sheet_name = entry
            try:
                if is_ternary:
                    # Ternary plots need all three components: X (top),
                    # Y (left), Z (right).
                    plot = gl.add_plot(wks, coly=1, colx=0, colz=2, type="s")
                elif group.get("z"):
                    plot = gl.add_plot(wks, coly=1, colx=0, colz=2, type="s")
                else:
                    plot = gl.add_plot(wks, coly=1, colx=0, type="s")
                # Count the layer immediately: a later style failure must not
                # shift the legend indices (%(n,@WS) refers to the layer).
                plot_idx += 1
                plot.color = group.get("color", "#333333")
                plot.symbol_kind = group.get("marker", 1)
                plot.symbol_size = _export_symbol_size()
                legend_entries.append(
                    f"\\l({plot_idx}) %({plot_idx},@WS)"
                )
            except Exception as err:
                logger.warning("_build_origin_project failed: %s", err)

        gl.group()
        gl.rescale()  # Let Origin handle axis ranges (ternary geometry is coupled)

        # ── overlay layers ────────────────────────────────────────
        def _add_overlay_worksheets(
            curves_list: list[tuple[np.ndarray, np.ndarray, str, dict[str, Any]]],
            prefix: str = "OV_",
        ) -> None:
            nonlocal plot_idx
            for x_arr, y_arr, curve_label, style in curves_list:
                name = _origin_sheet_name(curve_label, prefix, sheet_names)
                try:
                    owks = wb.add_sheet(name)
                    owks.from_list(0, x_arr.tolist(), "X")
                    owks.from_list(1, y_arr.tolist(), "Y")

                    # add equation/description comment
                    eq_text = style.get("equation", curve_label)
                    slope = style.get("slope")
                    intercept = style.get("intercept")
                    if slope is not None and intercept is not None and not eq_text.startswith("y ="):
                        eq_text = f"y = {slope:.6f} * x + {intercept:.6f}"

                    try:
                        owks.cols = 3
                        owks.set_cell(0, 2, eq_text)
                    except Exception as err:
                        logger.warning("_add_overlay_worksheets failed: %s", err)

                    line = gl.add_plot(owks, coly=1, colx=0, type="l")
                    plot_idx += 1  # count the layer immediately (legend index)
                    line.color = style.get("color", "#000000")
                    if style.get("width"):
                        line.width = style["width"]
                    legend_entries.append(f"\\l({plot_idx}) %({plot_idx},@WS)")
                except Exception as err:
                    logger.warning("_add_overlay_worksheets failed: %s", err)

        for curves_list in overlay_data.values():
            _add_overlay_worksheets(curves_list, prefix="OV_")

        # ── TASK 2: isochron line overlay sheets ─────────────────
        if isochron_lines:
            for iso in isochron_lines:
                try:
                    age_val = iso.get("age")
                    if age_val is not None:
                        try:
                            age_str = f"{float(age_val):.0f}Ma"
                        except (TypeError, ValueError):
                            age_str = str(age_val)
                    else:
                        age_str = str(iso.get("group", "iso"))
                except Exception:
                    age_str = "iso"
                name = _origin_sheet_name(f"{age_str}", "ISO_", sheet_names)
                try:
                    owks = wb.add_sheet(name)
                    owks.from_list(0, iso["x"], "X")
                    owks.from_list(1, iso["y"], "Y")

                    eq_text = iso.get("equation", iso["label"])
                    try:
                        owks.cols = 3
                        owks.set_cell(0, 2, eq_text)
                    except Exception as err:
                        logger.warning("_build_origin_project failed: %s", err)

                    line = gl.add_plot(owks, coly=1, colx=0, type="l")
                    plot_idx += 1  # count the layer immediately (legend index)
                    line.color = iso.get("color", "#ef4444")
                    line.width = iso.get("width", 1.5)
                    legend_entries.append(f"\\l({plot_idx}) %({plot_idx},@WS)")
                except Exception as err:
                    logger.warning("_build_origin_project failed: %s", err)

        # ── equation overlay sheets ──────────────────────────────
        if equation_lines:
            for eq in equation_lines:
                name = _origin_sheet_name(eq.get("label", "Eq"), "OV_", sheet_names)
                try:
                    owks = wb.add_sheet(name)
                    owks.from_list(0, eq["x"], "X")
                    owks.from_list(1, eq["y"], "Y")

                    eq_text = eq.get("equation", eq["label"])
                    try:
                        owks.cols = 3
                        owks.set_cell(0, 2, eq_text)
                    except Exception as err:
                        logger.warning("_build_origin_project failed: %s", err)

                    line = gl.add_plot(owks, coly=1, colx=0, type="l")
                    plot_idx += 1  # count the layer immediately (legend index)
                    line.color = eq.get("color", "#ef4444")
                    line.width = eq.get("width", 1.0)
                    legend_entries.append(f"\\l({plot_idx}) %({plot_idx},@WS)")
                except Exception as err:
                    logger.warning("_build_origin_project failed: %s", err)

        # ── legend ────────────────────────────────────────────────
        if legend_entries:
            try:
                lgnd = gl.label("Legend")
                lgnd.set_int("fsize", 10)
                lgnd.set_int("showframe", 0)
                lgnd.text = "\n".join(legend_entries)
            except Exception as err:
                logger.warning("_build_origin_project failed: %s", err)

        # ── axis labels, ranges and title ─────────────────────────
        if is_ternary:
            ternary_cols = axis_labels.get("ternary_cols", ["Top", "Left", "Right"])
            # Origin ternary uses axis names "x", "y", "z" for top/left/right
            for axis_name, label in zip(["x", "y", "z"], ternary_cols):
                try:
                    gl.axis(axis_name).title = label
                except Exception as err:
                    logger.warning("_build_origin_project failed: %s", err)
            # Percent data needs the template's 0-100 scale on all three axes.
            _apply_axis_range(notes, op, gl, "x", 0.0, 100.0)
            _apply_axis_range(notes, op, gl, "y", 0.0, 100.0)
            _apply_axis_range(notes, op, gl, "z", 0.0, 100.0)
        else:
            if axis_labels.get("x"):
                gl.axis("x").title = axis_labels["x"]
            if axis_labels.get("y"):
                gl.axis("y").title = axis_labels["y"]
            if axis_labels.get("x_range"):
                _apply_axis_range(notes, op, gl, "x", *axis_labels["x_range"])
            if axis_labels.get("y_range"):
                _apply_axis_range(notes, op, gl, "y", *axis_labels["y_range"])
        if title:
            try:
                gl.set_str("title", title)
            except Exception as err:
                logger.warning("_build_origin_project failed: %s", err)

        # ── save project (.opju) ──────────────────────────────────
        op.save(file_path)
        logger.info("Origin project saved to %s", file_path)

        # ── companion PNG ─────────────────────────────────────────
        img_path = file_path.rsplit(".", 1)[0] + ".png"
        try:
            res = gp.save_fig(img_path, width=1600)
            if res:
                logger.info("Origin graph image saved to %s", img_path)
        except Exception as err:
            logger.warning("Failed to export Origin graph image: %s", err)

        return True
    except Exception as err:
        logger.warning("Failed to build Origin project: %s", err)
        return False


# ═══════════════════════════════════════════════════════════════════════
#  TASK 4: Main entry point — dispatch by render mode
# ═══════════════════════════════════════════════════════════════════════

def export_to_origin(file_path: str) -> bool:
    """Export the current plot to an Origin project (.opju) and companion PNG.

    Returns True on success. Use :func:`export_to_origin_detailed` when the
    caller wants to show *why* an export failed.
    """
    ok, _reason, _notes = export_to_origin_detailed(file_path)
    return ok


def export_to_origin_detailed(file_path: str) -> tuple[bool, str, list[str]]:
    """Export to Origin and return ``(ok, reason, notes)``.

    *reason* is empty on success; *notes* lists the Origin capabilities that were
    applied or skipped (ternary template, column metadata, axis ranges...).
    """
    op = _lazy_import_originpro()
    if op is None:
        logger.warning("Origin export requested but originpro is not installed.")
        return False, "originpro is not installed", []

    ax = app_state.ax
    if ax is None:
        logger.warning("No axes available for Origin export.")
        return False, "no axes to export", []

    try:
        data = collect_origin_export_data(ax)
    except Exception as err:
        logger.warning("Origin export failed during extraction: %s", err)
        return False, f"data extraction failed: {err}", []

    if not data["scatter_groups"]:
        logger.warning("No scatter data extracted from axes for Origin export.")
        return False, "no scatter data in the current view", []

    notes: list[str] = []
    try:
        ok = _build_origin_project(
            file_path,
            data["scatter_groups"],
            data["axis_labels"],
            data["overlay_data"],
            isochron_lines=data["isochron_lines"],
            equation_lines=data["equation_lines"],
            is_ternary=data["is_ternary"],
            title=data["title"],
            notes=notes,
        )
    except Exception as err:
        logger.warning("Origin export failed while building the project: %s", err)
        return False, f"Origin automation failed: {err}", notes

    if not ok:
        return False, "Origin refused to build the project (is Origin running?)", notes
    logger.info("Origin export capabilities: %s", notes)
    return True, "", notes


def collect_origin_export_data(ax: Any, mode: str | None = None) -> dict[str, Any]:
    """Collect every series of the current view for Origin export.

    Pure matplotlib/app_state extraction - no ``originpro`` required - so the same
    data feeds both the ``.opju`` project builder and the Excel fallback.
    """
    render_mode = str(mode if mode is not None else app_state.render_mode).upper()
    logger.info("Origin export: render_mode=%s", render_mode)

    # ── scatter data ──────────────────────────────────────────────
    scatter_groups: list[dict[str, Any]] = []
    is_ternary = False

    if render_mode == "3D":
        scatter_groups = _extract_scatter_groups_3d(ax)
    elif render_mode == "TERNARY":
        scatter_groups = _extract_ternary_data(ax)
        is_ternary = True
    else:
        # 2D axes for: UMAP, tSNE, PCA, RobustPCA, V1V2, 2D,
        # PB_EVOL_76, PB_EVOL_86, PLUMBOTECTONICS_76,
        # PLUMBOTECTONICS_86, PB_MU_AGE, PB_KAPPA_AGE
        scatter_groups = _extract_scatter_groups(ax)

    logger.info(
        "Origin export: extracted %d scatter groups (%d collections on axes)",
        len(scatter_groups),
        len(getattr(ax, "collections", [])),
    )

    # ── axis labels ───────────────────────────────────────────────
    axis_labels = {
        "x": str(ax.get_xlabel() or ""),
        "y": str(ax.get_ylabel() or ""),
    }
    try:
        x_limits = ax.get_xlim()
        y_limits = ax.get_ylim()
        axis_labels["x_range"] = (float(x_limits[0]), float(x_limits[1]))
        axis_labels["y_range"] = (float(y_limits[0]), float(y_limits[1]))
    except Exception as err:
        logger.warning("collect_origin_export_data failed: %s", err)
    if is_ternary:
        # Merge, do not overwrite: the ternary branch above set the user's
        # ternary column names and they must reach the project builder.
        axis_labels["ternary_cols"] = getattr(
            app_state, "selected_ternary_cols", ["Top", "Left", "Right"]
        )

    # ── overlay data ──────────────────────────────────────────────
    overlay_data: dict[str, list[tuple[np.ndarray, np.ndarray, str, dict[str, Any]]]] = {}
    isochron_lines: list[dict[str, Any]] = []
    equation_lines: list[dict[str, Any]] = []

    # Modes that include geochemistry model curves + paleoisochrons
    _pb_geo_modes = {"PB_EVOL_76", "PB_EVOL_86"}

    # Modes that include plumbotectonics curves
    _plumbo_modes = {"PLUMBOTECTONICS_76", "PLUMBOTECTONICS_86"}

    def _x_limits() -> tuple[float, float]:
        try:
            xlim = ax.get_xlim()
            return float(xlim[0]), float(xlim[1])
        except Exception:
            return 0.0, 45.0

    if render_mode in _pb_geo_modes:
        overlay_data.update(_extract_pb_evolution_overlay_data(render_mode, _x_limits()))
        logger.info(
            "Origin export: Pb-evolution overlays - categories=%s, entries=%d",
            list(overlay_data.keys()),
            sum(len(v) for v in overlay_data.values()),
        )
        if app_state.show_isochrons:
            isochron_lines = _extract_isochron_lines(ax)
            logger.info("Origin export: %d isochron lines extracted", len(isochron_lines))
        if app_state.show_equation_overlays:
            equation_lines = _extract_equation_overlays(ax, *_x_limits())

    if render_mode in _plumbo_modes:
        overlay_data.update(_extract_plumbotectonics_curves(render_mode))
        logger.info(
            "Origin export: plumbotectonics overlays - categories=%s, entries=%d",
            list(overlay_data.keys()),
            sum(len(v) for v in overlay_data.values()),
        )
        if app_state.show_equation_overlays:
            equation_lines = _extract_equation_overlays(ax, *_x_limits())

    return {
        "mode": render_mode,
        "is_ternary": is_ternary,
        "scatter_groups": scatter_groups,
        "axis_labels": axis_labels,
        "overlay_data": overlay_data,
        "isochron_lines": isochron_lines,
        "equation_lines": equation_lines,
        "title": str(getattr(app_state, "current_plot_title", "") or ""),
    }


def _extract_and_build_origin_project(file_path: str, ax: Any) -> bool:
    """Extract plot data for the current render mode and build the project."""
    data = collect_origin_export_data(ax)
    if not data["scatter_groups"]:
        logger.warning("No scatter data extracted from axes for Origin export.")
        return False

    return _build_origin_project(
        file_path,
        data["scatter_groups"],
        data["axis_labels"],
        data["overlay_data"],
        isochron_lines=data["isochron_lines"],
        equation_lines=data["equation_lines"],
        is_ternary=data["is_ternary"],
        title=data["title"],
    )
