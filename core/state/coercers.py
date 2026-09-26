"""Coercion helpers for the state fields.

Every helper takes a value from the live state or from the snapshot and returns the
canonical form. They live here so that the field registry (core/state/fields.py) and the
normalizers can both use them without an import cycle; core/state/_normalizers.py
re-exports them for the dispatch handlers and the store.
"""
from __future__ import annotations

from collections.abc import Iterable

import logging

import math
from typing import Any

try:  # numpy is a hard dependency of the plotting stack, but the coercers must not
    import numpy as np  # pragma: no cover - import guard
except Exception:  # pragma: no cover
    np = None  # type: ignore[assignment]


logger = logging.getLogger(__name__)
DEFAULT_EXPORT_IMAGE_OPTIONS = {
    "preset_key": "science_single",
    "image_ext": "png",
    "dpi": 400,
    "bbox_tight": True,
    "pad_inches": 0.02,
    "transparent": False,
    "point_size": None,
    "legend_size": None,
    "embed_fonts": True,
    "white_background": True,
}
DEFAULT_PLOT_FONT_SIZES = {
    "title": 14,
    "label": 12,
    "tick": 10,
    "legend": 10,
}
MIN_EXPORT_DPI = 72
DEFAULT_LEGEND_FRAME_ALPHA = 0.95
DEFAULT_CONFIDENCE_LEVEL = 0.95
MARGINAL_KDE_DEFAULT_KERNEL = "gaussian"
MARGINAL_KDE_ALLOWED_KERNELS = (
    "gaussian",
    "tophat",
    "epanechnikov",
    "exponential",
    "linear",
    "cosine",
)
_KDE_THRESH_DEFAULT = 0.05
_KDE_THRESH_MIN = 0.001
_KDE_THRESH_MAX = 1.0
MARGINAL_KDE_DEFAULT_AUTO_BANDWIDTH_METHOD = "scott"
MARGINAL_KDE_ALLOWED_AUTO_BANDWIDTH_METHODS = ("scott", "silverman")


def _normalize_export_options(options: Any) -> dict[str, Any]:
    merged = dict(DEFAULT_EXPORT_IMAGE_OPTIONS)
    if isinstance(options, dict):
        merged.update(options)

    merged["preset_key"] = str(merged.get("preset_key") or "science_single")
    merged["image_ext"] = str(merged.get("image_ext") or "png").lower().strip(".")
    merged["dpi"] = max(MIN_EXPORT_DPI, int(merged.get("dpi", 400)))
    merged["bbox_tight"] = bool(merged.get("bbox_tight", True))
    merged["pad_inches"] = max(0.0, float(merged.get("pad_inches", 0.02)))
    merged["transparent"] = bool(merged.get("transparent", False))
    merged["embed_fonts"] = bool(merged.get("embed_fonts", True))
    merged["white_background"] = bool(merged.get("white_background", True))

    point_size = merged.get("point_size")
    legend_size = merged.get("legend_size")
    merged["point_size"] = int(point_size) if point_size is not None else None
    merged["legend_size"] = int(legend_size) if legend_size is not None else None
    return merged


def _normalize_visible_groups(groups: Any) -> list[str] | None:
    if groups is None:
        return None
    if isinstance(groups, Iterable) and not isinstance(groups, (str, bytes)):
        out = [str(group) for group in groups]
        return out if out else None
    return [str(groups)]


def _normalize_active_subset_indices(indices: Any) -> set[int] | None:
    if indices is None:
        return None
    if isinstance(indices, Iterable) and not isinstance(indices, (str, bytes)):
        normalized = {int(v) for v in indices}
        return normalized if normalized else set()
    return {int(indices)}


def _normalize_algorithm_params(params: Any) -> dict[str, Any]:
    if isinstance(params, dict):
        return dict(params)
    if params is None:
        return {}
    try:
        return dict(params)
    except Exception:
        return {}


def _normalize_plot_marker_size(value: Any) -> int:
    return max(1, min(int(value), 2000))


def _normalize_plot_marker_alpha(value: Any) -> float:
    return max(0.0, min(float(value), 1.0))


def _normalize_plot_dpi(value: Any) -> int:
    return max(MIN_EXPORT_DPI, min(int(value), 1200))


def _normalize_font_name(value: Any) -> str:
    return str(value or "").strip()


def _normalize_plot_font_sizes(sizes: Any) -> dict[str, int]:
    merged = dict(DEFAULT_PLOT_FONT_SIZES)
    if isinstance(sizes, dict):
        for key in merged:
            if key not in sizes or sizes.get(key) is None:
                continue
            merged[key] = max(6, min(int(sizes[key]), 72))
    return merged


def _normalize_color(value: Any, default: str) -> str:
    text = str(value or "").strip()
    return text if text else default


def _normalize_style_linewidth(value: Any, *, default: float) -> float:
    return max(0.0, min(float(value if value is not None else default), 10.0))


def _normalize_unit_interval(value: Any, *, default: float) -> float:
    return max(0.0, min(float(value if value is not None else default), 1.0))


def _normalize_grid_linestyle(value: Any) -> str:
    text = str(value or "--").strip()
    return text if text in ("-", "--", "-.", ":") else "--"


def _normalize_tick_direction(value: Any) -> str:
    text = str(value or "out").strip().lower()
    return text if text in ("in", "out", "inout") else "out"


def _normalize_tick_length(value: Any, *, default: float) -> float:
    return max(0.0, min(float(value if value is not None else default), 20.0))


def _normalize_text_weight(value: Any, *, default: str) -> str:
    text = str(value or default).strip().lower()
    return text if text in ("normal", "bold") else default


def _normalize_text_pad(value: Any, *, default: float, max_value: float) -> float:
    return max(0.0, min(float(value if value is not None else default), max_value))


def _normalize_adjust_text_pair(
    value: Any,
    *,
    default: tuple[float, float],
    min_value: float,
    max_value: float,
) -> tuple[float, float]:
    values: list[float] = []
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        for item in value:
            try:
                values.append(float(item))
            except Exception:
                values.append(0.0)
            if len(values) >= 2:
                break
    if not values:
        values = [default[0], default[1]]
    elif len(values) == 1:
        values = [values[0], default[1]]
    return (
        max(min_value, min(values[0], max_value)),
        max(min_value, min(values[1], max_value)),
    )


def _normalize_adjust_text_iter_lim(value: Any) -> int:
    return max(_ADJUST_TEXT_ITER_MIN, min(int(value), _ADJUST_TEXT_ITER_MAX))


def _normalize_adjust_text_time_lim(value: Any) -> float:
    return max(_ADJUST_TEXT_TIME_MIN, min(float(value), _ADJUST_TEXT_TIME_MAX))


def _normalize_marginal_size(value: Any) -> float:
    return max(_MARGINAL_SIZE_MIN, min(float(value), _MARGINAL_SIZE_MAX))


def _normalize_max_points(value: Any) -> int:
    return max(_MAX_POINTS_MIN, min(int(value), _MAX_POINTS_MAX))


def _normalize_bw_adjust(value: Any) -> float:
    return max(_BW_ADJUST_MIN, min(float(value), _BW_ADJUST_MAX))


def _normalize_kde_bandwidth(value: Any) -> float:
    if value is None:
        return _KDE_BW_MIN
    return max(_KDE_BW_MIN, min(float(value), _KDE_BW_MAX))


def _normalize_kde_kernel(value: Any) -> str:
    text = str(value or MARGINAL_KDE_DEFAULT_KERNEL).strip().lower()
    return text if text in MARGINAL_KDE_ALLOWED_KERNELS else MARGINAL_KDE_DEFAULT_KERNEL


def _normalize_kde_auto_bandwidth_method(value: Any) -> str:
    text = str(value or MARGINAL_KDE_DEFAULT_AUTO_BANDWIDTH_METHOD).strip().lower()
    return (
        text
        if text in MARGINAL_KDE_ALLOWED_AUTO_BANDWIDTH_METHODS
        else MARGINAL_KDE_DEFAULT_AUTO_BANDWIDTH_METHOD
    )


def _normalize_gridsize(value: Any) -> int:
    return max(32, min(int(value), 1024))


def _normalize_kde_thresh(value: Any) -> float:
    """Iso-proportion threshold: seaborn rejects values outside (0, 1]."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return _KDE_THRESH_DEFAULT
    return max(_KDE_THRESH_MIN, min(number, _KDE_THRESH_MAX))


def _normalize_clip_bound(value: Any) -> float | None:
    """Clip bound for KDE data/grids; ``None`` means unbounded."""
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number and abs(number) != float("inf") else None


def _normalize_cut(value: Any) -> float:
    return max(0.0, min(float(value), 5.0))


def _normalize_pca_component_indices(indices: Any) -> list[int]:
    if indices is None:
        return [0, 1]
    if isinstance(indices, Iterable) and not isinstance(indices, (str, bytes)):
        values = [int(v) for v in indices]
    else:
        values = [int(indices)]
    if len(values) < 2:
        values = (values + [1])[:2]
    return [max(0, values[0]), max(0, values[1])]


def _normalize_ternary_limit_mode(mode: Any) -> str:
    text = str(mode or "min").strip().lower()
    return text if text in ("min", "max", "both") else "min"


def _normalize_ternary_limit_anchor(anchor: Any) -> str:
    text = str(anchor or "min").strip().lower()
    return text if text in ("min", "max") else "min"

_ADJUST_TEXT_ITER_MIN: int = 10

_ADJUST_TEXT_ITER_MAX: int = 1000

_ADJUST_TEXT_TIME_MIN: float = 0.05

_ADJUST_TEXT_TIME_MAX: float = 2.0

_MARGINAL_SIZE_MIN: float = 5.0

_MARGINAL_SIZE_MAX: float = 40.0

_MAX_POINTS_MIN: int = 200

_MAX_POINTS_MAX: int = 50000

_BW_ADJUST_MIN: float = 0.05

_BW_ADJUST_MAX: float = 5.0

_KDE_BW_MIN: float = 0.0

_KDE_BW_MAX: float = 10.0


def _normalize_ternary_boundary_percent(percent: Any) -> float:
    return max(0.0, min(float(percent if percent is not None else 5.0), 30.0))


def _normalize_ternary_manual_limits(limits: Any) -> dict[str, float]:
    defaults = {
        "tmin": 0.0,
        "tmax": 1.0,
        "lmin": 0.0,
        "lmax": 1.0,
        "rmin": 0.0,
        "rmax": 1.0,
    }
    merged = dict(defaults)
    if isinstance(limits, dict):
        for key, value in limits.items():
            if key in merged and value is not None:
                merged[key] = max(0.0, min(float(value), 1.0))
    return merged


def _normalize_ternary_render_margin(margin: Any) -> float:
    return max(0.0, min(float(margin if margin is not None else 0.002), 0.05))


# ── small shape helpers used by the registry declarations ───────────────

def _as_bool(value: Any) -> bool:
    return bool(value)


def _as_float(value: Any) -> float:
    return float(value)


def _as_str(value: Any) -> str:
    return str(value)


def _as_list(value: Any) -> list:
    return list(value) if value else []


def _as_stretch_mode(value: Any) -> str:
    return str(value or "power")


def _as_factors(value: Any) -> list:
    return list(value or [1.0, 1.0, 1.0])
