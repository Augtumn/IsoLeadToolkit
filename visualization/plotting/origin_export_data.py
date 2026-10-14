"""Origin export data extraction - the presentation half of the Origin export.

Reads the current matplotlib axes and ``app_state`` and returns one plain dict of series; the
use case in :mod:`application.use_cases.export_origin` turns that dict into an ``.opju`` project
or an Origin-importable workbook.  The split keeps the use case free of plotting imports
(docs/dev_conventions.md §18.1: presentation -> application, never the other way).
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from core import app_state

logger = logging.getLogger(__name__)

__all__ = ["collect_origin_export_data"]

_MARKER_TO_ORIGIN: dict[str, int] = {
    "o": 1,  "s": 0,  "^": 2,  "v": 3,  "D": 4,  "d": 4,
    "*": 7,  "+": 5,  "x": 6,  "p": 8,  "h": 9,  "H": 10,
    ".": 11, "<": 12, ">": 13, "1": 2,  "2": 3,  "3": 12,
    "4": 13, "8": 4,  "P": 8,  "X": 6,  "|": 14, "_": 15,
}


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
                     "equation": (
                        f"Paleoisochron {float(age):.0f} Ma: "
                        f"y = {slope:.6f}x + {intercept:.6f}"
                    ),},
                ))
        except Exception as err:
            logger.warning("Failed to compute paleoisochrons for Origin export: %s", err)
        if equations:
            result["paleoisochrons"] = equations

    return result


def _extract_plumbotectonics_curves(
    algorithm: str,
) -> dict[str, list[tuple[np.ndarray, np.ndarray, str, dict[str, Any]]]]:
    """Extract plumbotectonics model curves from ``PLUMBOTECTONICS_SECTIONS``.

    Returns a dict keyed by ``"plumbotectonics_curves"`` containing
    (x, y, name, style) tuples, one per tectonic group in the active
    model section.
    """
    result: dict[str, list[tuple[np.ndarray, np.ndarray, str, dict[str, Any]]]] = {}

    from data.plumbotectonics_data import PLUMBOTECTONICS_SECTIONS
    from visualization.plotting.geochem.plumbotectonics_metadata import (
        _select_plumbotectonics_section,
        get_plumbotectonics_group_entries,
    )
    from visualization.plotting.geochem.plumbotectonics_curves import (
        _fit_plumbotectonics_curve,
    )

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

    from visualization.plotting.geochem.equation_overlays import _safe_eval_expression

    for eq in eqs:
        if not eq.get("enabled", True):
            continue

        expression = eq.get("expression", "")
        label = eq.get("label", expression)
        color = eq.get("color", "#ef4444")
        width = eq.get("linewidth", 1.0)

        try:
            ys = _safe_eval_expression(expression, xs)
            ys = np.asarray(ys, dtype=float)
        except Exception as err:
            logger.warning("Skipping equation overlay %r: cannot evaluate it: %s", expression, err)
            continue

        lines.append({
            "x": xs.tolist(),
            "y": ys.tolist(),
            "label": label,
            "color": color,
            "width": width,
            "equation": f"Equation overlay: {expression}",
        })

    return lines


def collect_origin_export_data(ax: Any, mode: str | None = None) -> dict[str, Any]:
    """Collect every series of the current view for Origin export.

    Pure matplotlib/app_state extraction - no ``originpro`` required - so the same
    data feeds both the ``.opju`` project builder and the Excel fallback.

    Raises:
        ValueError: no axes to read (the caller exports a view that was never drawn).
    """
    if ax is None:
        raise ValueError("no axes to export: draw the plot before exporting it")

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
        axis_labels["ternary_cols"] = app_state.selected_ternary_cols

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
