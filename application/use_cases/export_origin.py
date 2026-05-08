"""Origin project export use case.

Extracts plot data from the current matplotlib axes and app_state,
constructs an Origin project (.opju) with worksheets and graphs that
replicate the current view.  Also exports a companion image via
Origin's save_fig when requested.
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


def _extract_scatter_groups(ax: Any) -> list[dict[str, Any]]:
    """Extract per-group (x, y) data from matplotlib scatter collections."""
    if ax is None:
        return []

    groups: list[dict[str, Any]] = []
    marker_map = getattr(app_state, "group_marker_map", {}) or {}
    seen = set()

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
    marker_map = getattr(app_state, "group_marker_map", {}) or {}
    seen = set()

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


def _extract_pb_evolution_overlay_data(
    actual_algorithm: str,
) -> dict[str, list[tuple[np.ndarray, np.ndarray, str, dict[str, Any]]]]:
    """Recompute overlay curves for Pb evolution plots via the geochemistry engine."""
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

    xlim = (0, 45)

    # --- model curves ---
    if getattr(app_state, "show_model_curves", True):
        curves: list[tuple[np.ndarray, np.ndarray, str, dict[str, Any]]] = []
        try:
            t_vals = np.linspace(0, 4500, 300)
            x_vals, y_vals = geochemistry.calculate_modelcurve(
                t_vals, params=params, algorithm=actual_algorithm,
            )
            if x_vals is not None and y_vals is not None:
                curves.append((
                    np.asarray(x_vals), np.asarray(y_vals),
                    str(params.get("model_name", "Model")),
                    {"color": "#64748b", "width": 1.2},
                ))
        except Exception as err:
            logger.warning("Failed to compute model curves for Origin export: %s", err)
        if curves:
            result["model_curves"] = curves

    # --- paleoisochrons (export as equation lines: y = slope*x + intercept) ---
    if getattr(app_state, "show_paleoisochrons", True):
        equations: list[tuple[np.ndarray, np.ndarray, str, dict[str, Any]]] = []
        ages = getattr(app_state, "paleoisochron_ages", [3000, 2000, 1000, 0])
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
                    {"color": "#94a3b8", "width": 0.9, "slope": slope, "intercept": intercept},
                ))
        except Exception as err:
            logger.warning("Failed to compute paleoisochrons for Origin export: %s", err)
        if equations:
            result["paleoisochrons"] = equations

    return result


# ---------------------------------------------------------------------------
# Origin project builder
# ---------------------------------------------------------------------------


def _origin_sheet_name(label: str, prefix: str, used: set[str]) -> str:
    """Generate a unique sheet name from *label*."""
    base = str(label).replace("/", "_").replace(" ", "_").replace(":", "_")[:28]
    name = f"{prefix}{base}"
    suffix = 1
    while name in used:
        name = f"{prefix}{base}_{suffix}"
        suffix += 1
    used.add(name)
    return name


def _build_origin_project(
    file_path: str,
    scatter_groups: list[dict[str, Any]],
    axis_labels: dict[str, str],
    overlay_data: dict[str, list[tuple[np.ndarray, np.ndarray, str, dict[str, Any]]]],
    title: str | None,
) -> bool:
    """Create an Origin project with worksheets and a multi-layer graph,
    then export the graph as a PNG image alongside the project."""
    op = _lazy_import_originpro()
    if op is None:
        return False

    try:
        wb = op.new_book("w", "IsotopesAnalyse_Data")
        sheet_names: set[str] = set()
        wks_map: dict[str, Any] = {}

        # ---- scatter worksheets ----
        for group in scatter_groups:
            name = _origin_sheet_name(group["label"], "", sheet_names)
            try:
                wks = wb.add_sheet(name)
                wks.from_list(0, group["x"], "X")
                wks.from_list(1, group["y"], "Y")
                wks_map[group["label"]] = (wks, name)
            except Exception as err:
                logger.warning("Failed to create sheet for %s: %s", name, err)

        if not wks_map:
            logger.warning("No worksheets created for scatter data.")
            return False

        # ---- graph ----
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
                if group.get("z"):
                    plot = gl.add_plot(wks, coly=1, colx=0, colz=2, type="s")
                else:
                    plot = gl.add_plot(wks, coly=1, colx=0, type="s")
                plot.color = group.get("color", "#333333")
                plot.symbol_kind = group.get("marker", 1)
                plot.symbol_size = 8
                plot_idx += 1
                # Use @WS substitution so the legend shows the worksheet name.
                legend_entries.append(
                    f"\\l({plot_idx}) %({plot_idx},@WS)"
                )
            except Exception as err:
                logger.debug("Skipping scatter %s: %s", group.get("label"), err)

        gl.group()
        gl.rescale()

        # ---- overlay layers ----
        for overlay_name, curves in overlay_data.items():
            for x_arr, y_arr, curve_label, style in curves:
                name = _origin_sheet_name(curve_label, "OV_", sheet_names)
                try:
                    owks = wb.add_sheet(name)
                    owks.from_list(0, x_arr.tolist(), "X")
                    owks.from_list(1, y_arr.tolist(), "Y")
                    line = gl.add_plot(owks, coly=1, colx=0, type="l")
                    line.color = style.get("color", "#000000")
                    if style.get("width"):
                        line.width = style["width"]
                    plot_idx += 1
                    legend_entries.append(
                        f"\\l({plot_idx}) %({plot_idx},@WS)"
                    )
                except Exception as err:
                    logger.debug("Skipping overlay %s: %s", curve_label, err)

        # ---- legend ----
        if legend_entries:
            try:
                lgnd = gl.label("Legend")
                lgnd.set_int("fsize", 10)
                lgnd.set_int("showframe", 0)
                lgnd.text = "\n".join(legend_entries)
            except Exception as err:
                logger.debug("Failed to set custom legend: %s", err)

        # ---- axis labels and title ----
        if axis_labels.get("x"):
            gl.axis("x").title = axis_labels["x"]
        if axis_labels.get("y"):
            gl.axis("y").title = axis_labels["y"]
        if title:
            try:
                gl.set_str("title", title)
            except Exception:
                pass

        # ---- save project (.opju) ----
        op.save(file_path)
        logger.info("Origin project saved to %s", file_path)

        # ---- also export a companion PNG at ~300 dpi ----
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


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def export_to_origin(file_path: str) -> bool:
    """Export the current plot to an Origin project (.opju) and companion PNG.

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
    logger.info("Origin export: render_mode=%s", mode)

    # ---- scatter data ----
    ax_name = getattr(ax, "name", "")
    if ax_name == "3d":
        scatter_groups = _extract_scatter_groups_3d(ax)
    else:
        scatter_groups = _extract_scatter_groups(ax)

    logger.info(
        "Origin export: extracted %d scatter groups (%d collections on axes)",
        len(scatter_groups),
        len(getattr(ax, "collections", [])),
    )

    if not scatter_groups:
        logger.warning("No scatter data extracted from axes for Origin export.")
        return False

    # ---- axis labels ----
    axis_labels = {
        "x": str(ax.get_xlabel() or ""),
        "y": str(ax.get_ylabel() or ""),
    }

    # ---- overlay data (Pb evolution modes) ----
    overlay_data: dict[str, list[tuple[np.ndarray, np.ndarray, str, dict[str, Any]]]] = {}
    if mode in ("PB_EVOL_76", "PB_EVOL_86"):
        overlay_data = _extract_pb_evolution_overlay_data(mode)
        logger.info(
            "Origin export: overlay categories=%s, entries=%d",
            list(overlay_data.keys()),
            sum(len(v) for v in overlay_data.values()),
        )

    # ---- title ----
    title = str(getattr(app_state, "current_plot_title", "") or "")

    return _build_origin_project(file_path, scatter_groups, axis_labels, overlay_data, title)
