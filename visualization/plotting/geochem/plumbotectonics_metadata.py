"""Plumbotectonics metadata, grouping, and palette helpers."""
from __future__ import annotations

import re
from typing import Any

from core import app_state
from data.plumbotectonics_data import PLUMBOTECTONICS_SECTIONS


def _load_plumbotectonics_data() -> list[dict[str, Any]]:
    return PLUMBOTECTONICS_SECTIONS


def _plumbotectonics_section_name(section: dict[str, Any], index: int) -> str:
    label = (section.get('label') or '').strip()
    if label:
        return label
    return f"Model {index + 1}"


def get_plumbotectonics_variants() -> list[tuple[str, str]]:
    """Return available plumbotectonics model variants."""
    sections = _load_plumbotectonics_data()
    if not sections:
        return []
    variants = []
    for idx, section in enumerate(sections):
        variants.append((str(idx), _plumbotectonics_section_name(section, idx)))
    return variants


def _select_plumbotectonics_section(sections: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not sections:
        return None
    variant = getattr(app_state, 'plumbotectonics_variant', None)
    try:
        idx = int(variant)
    except Exception:
        idx = None
    if idx is not None and 0 <= idx < len(sections):
        return sections[idx]
    return sections[0]


def _normalize_plumbotectonics_group_key(name: str) -> str:
    value = str(name or '').strip().lower()
    value = re.sub(r'[^a-z0-9]+', '_', value)
    return value.strip('_')


def _plumbotectonics_group_visible(style_key: str) -> bool:
    visibility = getattr(app_state, 'plumbotectonics_group_visibility', {}) or {}
    return bool(visibility.get(style_key, True))


def get_plumbotectonics_group_entries(
    section: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Return plumbotectonics group metadata for the active model."""
    sections = _load_plumbotectonics_data()
    if section is None:
        section = _select_plumbotectonics_section(sections)
    if not section:
        return []

    used = set()
    entries = []
    for idx, group in enumerate(section.get('groups', [])):
        name = str(group.get('name') or '').strip() or f"Group {idx + 1}"
        base_key = _normalize_plumbotectonics_group_key(name) or f"group_{idx + 1}"
        key = base_key
        if key in used:
            key = f"{base_key}_{idx + 1}"
        used.add(key)
        entries.append({
            'name': name,
            'key': key,
            'style_key': f"plumbotectonics_curve:{key}",
        })
    return entries


def _overlay_palette() -> list[str]:
    palette = []
    try:
        from visualization.style_manager import style_manager_instance
        scheme = getattr(app_state, 'color_scheme', None)
        if scheme and scheme in style_manager_instance.palettes:
            palette = list(style_manager_instance.palettes.get(scheme, []))
    except Exception:
        palette = []
    if not palette:
        try:
            import matplotlib.pyplot as plt
            prop_cycle = plt.rcParams.get('axes.prop_cycle', None)
            if prop_cycle is not None:
                palette = list(prop_cycle.by_key().get('color', []))
        except Exception:
            palette = []
    return palette


def get_plumbotectonics_group_palette(section: dict[str, Any] | None = None) -> dict[str, str]:
    entries = get_plumbotectonics_group_entries(section=section)
    colors = _overlay_palette()
    if not colors:
        return {}
    palette = {}
    for idx, entry in enumerate(entries):
        palette[entry['style_key']] = colors[idx % len(colors)]
    return palette


def get_overlay_default_color(style_key: str) -> str | None:
    colors = _overlay_palette()
    if not colors:
        return None
    index_map = {
        'model_curve': 0,
        'paleoisochron': 1,
        'model_age_line': 2,
    }
    idx = index_map.get(style_key, 0)
    return colors[idx % len(colors)]


def _plumbotectonics_marker(name: str) -> str:
    key = str(name).lower()
    if 'mantle' in key or '地幔' in key:
        return 'o'
    if 'lower' in key or '下地壳' in key:
        return 's'
    if 'upper' in key or '上地壳' in key:
        return '^'
    if 'orogene' in key or 'orogen' in key:
        return 'D'
    return 'o'