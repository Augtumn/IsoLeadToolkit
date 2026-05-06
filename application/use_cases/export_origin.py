"""Origin project export use case.

Extracts plot data from the current matplotlib axes and app_state,
constructs an Origin project (.opju) with worksheets and graphs that
replicate the current view.
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
    "o": 1,
    "s": 0,
    "^": 2,
    "v": 3,
    "D": 4,
    "d": 4,
    "*": 7,
    "+": 5,
    "x": 6,
    "p": 8,
    "h": 9,
    "H": 10,
    ".": 11,
    "<": 12,
    ">": 13,
    "1": 2,
    "2": 3,
    "3": 12,
    "4": 13,
    "8": 4,
    "P": 8,
    "X": 6,
    "|": 14,
    "_": 15,
}


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


# ---------------------------------------------------------------------------
# Data extraction helpers
# ---------------------------------------------------------------------------


def _hex_color(color: Any) -> str:
    """Convert a matplotlib color spec to a hex string."""
    import matplotlib.colors as mcolors

    try:
        return mcolors.to_hex(color)
    except Exception:
        return "#333333"


def _origin_marker(matplotlib_marker: str) -> int:
    """Map a matplotlib marker string to an Origin symbol index."""
    return _MARKER_TO_ORIGIN.get(str(matplotlib_marker), 1)


def extract_scatter_data_from_axes(ax: Any, group_col: str) -> list[dict[str, Any]]:
    """Extract per-group (x, y) data from matplotlib scatter collections."""
    if ax is None:
        return []

    groups: list[dict[str, Any]] = []
    for coll in getattr(ax, "collections", []):
        try:
            label = str(coll.get_label() or "")
        except Exception:
            label = ""
        if not label or label.startswith("_"):
            continue

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

        marker_map = getattr(app_state, "group_marker_map", {}) or {}
        marker = _origin_marker(marker_map.get(label, "o"))

        groups.append(
            {
                "label": label,
                "x": offsets[:, 0].tolist(),
                "y": offsets[:, 1].tolist(),
                "color": color,
                "marker": marker,
            }
        )

    return groups


def extract_3d_data_from_axes(ax: Any, group_col: str) -> list[dict[str, Any]]:
    """Extract per-group (x, y, z) data from 3D scatter collections."""
    if ax is None:
        return []

    groups: list[dict[str, Any]] = []
    for coll in getattr(ax, "collections", []):
        try:
            label = str(coll.get_label() or "")
        except Exception:
            label = ""
        if not label or label.startswith("_"):
            continue

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

        marker_map = getattr(app_state, "group_marker_map", {}) or {}
        marker = _origin_marker(marker_map.get(label, "o"))

        groups.append(
            {
                "label": label,
                "x": np.asarray(xs).tolist(),
                "y": np.asarray(ys).tolist(),
                "z": np.asarray(zs).tolist(),
                "color": color,
                "marker": marker,
            }
        )

    return groups


def _extract_pb_evolution_overlay_data(
    actual_algorithm: str,
) -> dict[str, list[tuple[np.ndarray, np.ndarray, str, dict[str, Any]]]]:
    """Recompute overlay curves for Pb evolution plots via the geochemistry engine."""
    result: dict[str, list[tuple[np.ndarray, np.ndarray, str, dict[str, Any]]]] = {}

    try:
        from visualization.plotting.data import _lazy_import_geochemistry

        geochemistry, _ = _lazy_import_geochemistry()
        if geochemistry is None:
            return result

        params = geochemistry.engine.get_parameters()
        xlim = (0, 45)
    except Exception as err:
        logger.warning("Failed to load geochemistry engine: %s", err)
        return result

    # --- model curves ---
    if getattr(app_state, "show_model_curves", True):
        curves: list[tuple[np.ndarray, np.ndarray, str, dict[str, Any]]] = []
        try:
            for model_params in [params]:
                t_vals = np.linspace(0, 4500, 300)
                x_vals, y_vals = geochemistry.calculate_modelcurve(
                    t_vals, params=model_params, algorithm=actual_algorithm
                )
                if x_vals is not None and y_vals is not None:
                    curves.append(
                        (
                            np.asarray(x_vals),
                            np.asarray(y_vals),
                            str(model_params.get("model_name", "Model")),
                            {"color": "#64748b", "width": 1.2},
                        )
                    )
        except Exception as err:
            logger.warning("Failed to compute model curves for Origin export: %s", err)
        if curves:
            result["model_curves"] = curves

    # --- paleoisochrons ---
    if getattr(app_state, "show_paleoisochrons", True):
        lines: list[tuple[np.ndarray, np.ndarray, str, dict[str, Any]]] = []
        ages = getattr(app_state, "paleoisochron_ages", [3000, 2000, 1000, 0])
        try:
            for age in ages:
                line = geochemistry.calculate_paleoisochron_line(
                    age, params=params, algorithm=actual_algorithm
                )
                if not line:
                    continue
                slope, intercept = line
                xs = np.linspace(xlim[0], xlim[1], 200)
                ys = slope * xs + intercept
                lines.append(
                    (
                        xs,
                        ys,
                        f"{float(age):.0f} Ma",
                        {"color": "#94a3b8", "width": 0.9, "style": "--"},
                    )
                )
        except Exception as err:
            logger.warning("Failed to compute paleoisochrons for Origin export: %s", err)
        if lines:
            result["paleoisochrons"] = lines

    # --- model age lines ---
    if getattr(app_state, "show_model_age_lines", True):
        age_lines: list[tuple[np.ndarray, np.ndarray, str, dict[str, Any]]] = []
        try:
            df_global = getattr(app_state, "df_global", None)
            if df_global is not None:
                col_206 = "206Pb/204Pb"
                col_207 = "207Pb/204Pb"
                if col_206 in df_global.columns and col_207 in df_global.columns:
                    pb206 = df_global[col_206].dropna().values[:200]
                    pb207 = df_global[col_207].dropna().values[:200]
                    n = min(len(pb206), len(pb207))
                    for i in range(0, n, max(1, n // 10)):
                        try:
                            model_age = geochemistry.calculate_model_age(
                                pb206[i], pb207[i], params=params
                            )
                            xs_line = np.linspace(xlim[0], xlim[1], 50)
                            slope_line = (
                                (model_age - params.get("initial_207_204", 10.0))
                                / (pb206[i] - params.get("initial_206_204", 9.0))
                            )
                            intercept_line = model_age - slope_line * pb206[i]
                            ys_line = slope_line * xs_line + intercept_line
                            age_lines.append(
                                (
                                    xs_line,
                                    ys_line,
                                    f"{float(model_age):.0f} Ma",
                                    {"color": "#cbd5e1", "width": 0.7, "style": ":"},
                                )
                            )
                        except Exception:
                            continue
        except Exception as err:
            logger.warning("Failed to compute model age lines for Origin export: %s", err)
        if age_lines:
            result["model_age_lines"] = age_lines

    return result


# ---------------------------------------------------------------------------
# Origin project builder
# ---------------------------------------------------------------------------


def _build_origin_project(
    file_path: str,
    scatter_groups: list[dict[str, Any]],
    mode: str,
    axis_labels: dict[str, str],
    overlay_data: dict[str, list[tuple[np.ndarray, np.ndarray, str, dict[str, Any]]]],
    title: str | None,
) -> bool:
    """Create an Origin project with worksheets and a multi-layer graph."""
    op = _lazy_import_originpro()
    if op is None:
        return False

    try:
        wb = op.new_book("w", "IsotopesAnalyse_Data")
        gp = op.new_graph(template="scatter")
        gl = gp[0]

        # ---- scatter layer ----
        for group in scatter_groups:
            try:
                safe_label = str(group["label"]).replace("/", "_")[:30]
                wks = wb.add_sheet(f"G_{safe_label}")
                wks.from_list(0, group["x"], "X")
                wks.from_list(1, group["y"], "Y")
                plot = gl.add_plot(wks, coly=1, colx=0, type="s")
                plot.color = group.get("color", "#333333")
                plot.symbol_kind = group.get("marker", 1)
                plot.symbol_size = 8
            except Exception as err:
                logger.debug("Skipping group %s: %s", group.get("label"), err)

        gl.group()
        gl.rescale()

        # ---- overlay layers ----
        for _category, curves in overlay_data.items():
            for x_arr, y_arr, curve_label, style in curves:
                try:
                    safe_label = str(curve_label).replace("/", "_")[:30]
                    owks = wb.add_sheet(f"OL_{safe_label}")
                    owks.from_list(0, x_arr.tolist(), "X")
                    owks.from_list(1, y_arr.tolist(), "Y")
                    line = gl.add_plot(owks, coly=1, colx=0, type="l")
                    line.color = style.get("color", "#000000")
                except Exception as err:
                    logger.debug("Skipping overlay %s: %s", curve_label, err)

        # ---- axis labels and title ----
        gl.axis("x").title = axis_labels.get("x", "")
        gl.axis("y").title = axis_labels.get("y", "")
        if title:
            try:
                gl.set_str("title", title)
            except Exception:
                pass

        # ---- save project ----
        op.save(file_path)
        return True
    except Exception as err:
        logger.warning("Failed to build Origin project: %s", err)
        return False


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def export_to_origin(file_path: str) -> bool:
    """Export the current plot to an Origin project (.opju).

    Returns True on success, False on failure.
    """
    op = _lazy_import_originpro()
    if op is None:
        logger.warning("Origin export requested but originpro is not installed.")
        return False

    ax = getattr(app_state, "ax", None)
    if ax is None:
        logger.warning("No axes available for Origin export.")
        return False

    mode = str(getattr(app_state, "render_mode", "UMAP"))
    group_col = str(getattr(app_state, "last_group_col", ""))

    # ---- scatter data ----
    ax_name = getattr(ax, "name", "")
    if ax_name == "3d":
        scatter_groups = extract_3d_data_from_axes(ax, group_col)
    else:
        scatter_groups = extract_scatter_data_from_axes(ax, group_col)

    if not scatter_groups:
        logger.warning("No scatter data extracted from axes for Origin export.")
        return False

    # ---- axis labels ----
    axis_labels = {
        "x": str(ax.get_xlabel() or ""),
        "y": str(ax.get_ylabel() or ""),
    }

    # ---- overlay data (Pb evolution modes) ----
    overlay_data: dict[
        str, list[tuple[np.ndarray, np.ndarray, str, dict[str, Any]]]
    ] = {}
    if mode in ("PB_EVOL_76", "PB_EVOL_86"):
        overlay_data = _extract_pb_evolution_overlay_data(mode)

    # ---- title ----
    title = str(getattr(app_state, "current_plot_title", "") or "")

    return _build_origin_project(
        file_path, scatter_groups, mode, axis_labels, overlay_data, title
    )
