"""Application use cases for image export configuration and saving."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

SUPPORTED_IMAGE_FORMATS = {"png", "tiff", "pdf", "svg", "eps"}
DEFAULT_EXPORT_HEIGHT_RATIO = 0.72
MIN_EXPORT_DPI = 72


def build_image_export_profile(preset_key: str) -> dict:
    """Return export profile for a journal preset."""
    profiles = {
        "science_single": {
            "styles": ["science", "no-latex"],
            "width_mm": 85.0,
            "height_ratio": DEFAULT_EXPORT_HEIGHT_RATIO,
            "dpi": 300,
            "point_size": 48,
            "legend": {
                "fontsize": 7.0,
                "title_fontsize": 7.5,
                "markerscale": 0.82,
                "handlelength": 1.05,
                "handletextpad": 0.30,
                "labelspacing": 0.10,
                "borderpad": 0.15,
                "columnspacing": 0.45,
            },
        },
        "ieee_single": {
            "styles": ["science", "ieee", "no-latex"],
            "width_mm": 88.0,
            "height_ratio": DEFAULT_EXPORT_HEIGHT_RATIO,
            "dpi": 300,
            "point_size": 46,
            "legend": {
                "fontsize": 7.0,
                "title_fontsize": 7.5,
                "markerscale": 0.80,
                "handlelength": 1.00,
                "handletextpad": 0.28,
                "labelspacing": 0.10,
                "borderpad": 0.14,
                "columnspacing": 0.40,
            },
        },
        "nature_double": {
            "styles": ["science", "nature", "no-latex"],
            "width_mm": 180.0,
            "height_ratio": 0.55,
            "dpi": 300,
            "point_size": 50,
            "legend": {
                "fontsize": 8.0,
                "title_fontsize": 8.5,
                "markerscale": 0.90,
                "handlelength": 1.10,
                "handletextpad": 0.34,
                "labelspacing": 0.12,
                "borderpad": 0.18,
                "columnspacing": 0.50,
            },
        },
        "presentation": {
            "styles": ["science", "no-latex"],
            "width_mm": 240.0,
            "height_ratio": 0.55,
            "dpi": 220,
            "point_size": 60,
            "legend": {
                "fontsize": 10.0,
                "title_fontsize": 11.0,
                "markerscale": 1.00,
                "handlelength": 1.15,
                "handletextpad": 0.38,
                "labelspacing": 0.14,
                "borderpad": 0.20,
                "columnspacing": 0.55,
            },
        },
    }

    profile = dict(profiles.get(preset_key, profiles["science_single"]))
    width_in = mm_to_inch(float(profile["width_mm"]))
    height_in = max(2.0, width_in * float(profile.get("height_ratio", DEFAULT_EXPORT_HEIGHT_RATIO)))
    profile["figsize"] = (width_in, height_in)
    return profile


def mm_to_inch(mm_value: float) -> float:
    """Convert millimeter to inch."""
    return float(mm_value) / 25.4


def normalize_export_target(file_path: str, preferred_ext: str) -> tuple[str, str]:
    """Normalize output path and extension using supported export formats."""
    normalized_ext = str(preferred_ext or "png").lower().strip(".")
    if normalized_ext not in SUPPORTED_IMAGE_FORMATS:
        normalized_ext = "png"

    target_path = Path(file_path)
    suffix = target_path.suffix.lower().strip(".")
    if suffix in SUPPORTED_IMAGE_FORMATS:
        return str(target_path), suffix

    if target_path.suffix:
        target_path = target_path.with_suffix(f".{normalized_ext}")
    else:
        target_path = Path(f"{file_path}.{normalized_ext}")
    return str(target_path), normalized_ext


def resolve_image_save_options(
    *,
    profile: Mapping[str, object],
    dpi_override: int | None,
    bbox_tight: bool,
    transparent: bool,
    pad_inches: float,
    default_dpi: int,
) -> dict[str, object]:
    """Resolve save options from profile defaults and UI overrides."""
    profile_dpi = int(profile.get("dpi", default_dpi))
    dpi_value = int(dpi_override) if dpi_override is not None else profile_dpi
    return {
        "dpi": max(MIN_EXPORT_DPI, dpi_value),
        "bbox_tight": bool(bbox_tight),
        "pad_inches": max(0.0, float(pad_inches)),
        "transparent": bool(transparent),
    }


def fallback_export_rc(
    profile: Mapping[str, object],
    *,
    label_fontsize: int | None = None,
    title_fontsize: int | None = None,
    tick_fontsize: int | None = None,
) -> dict[str, object]:
    """Build fallback rcParams when SciencePlots is unavailable.

    Args:
        profile: Export profile dict.
        label_fontsize: Override for axes label font size. Defaults to computed from base font.
        title_fontsize: Override for axes title font size. Defaults to computed from base font.
        tick_fontsize: Override for tick label font size. Defaults to computed from base font.
    """
    legend_style = dict((profile.get("legend", {}) or {}))
    base_font_size = float(legend_style.get("fontsize", 8.0))
    return {
        "font.size": base_font_size + 0.5,
        "axes.titlesize": title_fontsize if title_fontsize is not None else base_font_size + 1.8,
        "axes.labelsize": label_fontsize if label_fontsize is not None else base_font_size + 1.0,
        "xtick.labelsize": tick_fontsize if tick_fontsize is not None else base_font_size,
        "ytick.labelsize": tick_fontsize if tick_fontsize is not None else base_font_size,
        "legend.fontsize": base_font_size,
        "axes.grid": True,
        "grid.alpha": 0.22,
        "grid.linestyle": "--",
        "axes.linewidth": 0.8,
        "lines.linewidth": 1.15,
    }


def save_export_figure(
    export_fig: Any,
    file_path: str,
    image_ext: str,
    *,
    export_dpi: int,
    bbox_tight: bool,
    pad_inches: float,
    transparent: bool,
) -> None:
    """Save figure using normalized options."""
    save_kwargs = {
        "format": image_ext,
        "dpi": int(export_dpi),
        "bbox_inches": "tight" if bbox_tight else None,
        "transparent": bool(transparent),
    }
    if bbox_tight:
        save_kwargs["pad_inches"] = float(max(0.0, pad_inches))

    # EPS backend does not preserve alpha channels reliably.
    if image_ext == "eps" and save_kwargs["transparent"]:
        save_kwargs["transparent"] = False

    export_fig.savefig(file_path, **save_kwargs)
