"""Guard: every snapshot field is either registry-driven or a documented exception.

The declarative registry (core/state/fields.py) covers the fields whose three call sites
share the common shape. The rest stay explicit in store.py / _normalizers.py and are
listed here with the reason, so a new field cannot quietly skip the registry - it either
gets registered or added to this list on purpose.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.persistence.schema import SESSION_FIELDS, UI_STATE_FIELDS  # noqa: E402
from core.state.fields import SIMPLE_FIELDS  # noqa: E402

REGISTERED = {field.name for field in SIMPLE_FIELDS}
PERSISTED = set(SESSION_FIELDS) | set(UI_STATE_FIELDS)

#: Fields that stay explicit. transient = runtime bookkeeping, never persisted;
#: derived = rebuilt from data or the render pipeline; pending = persisted and regular
#: enough to migrate, but not present in all three call sites yet.
EXPLICIT_FIELDS: dict[str, set[str]] = {
    # Runtime bookkeeping: never persisted, so it stays out of the registry.
    "transient": {
        "active_subset_indices",
        "adjust_text_in_progress",
        "available_groups",
        "current_feature_names",
        "current_plot_title",
        "data_version",
        "df_global",
        "embedding_task_running",
        "embedding_task_token",
        "initial_render_done",
        "isochron_results",
        "last_2d_cols",
        "last_embedding",
        "last_embedding_type",
        "last_pca_components",
        "last_pca_variance",
        "legend_last_handles",
        "legend_last_labels",
        "legend_last_title",
        "marginal_axes",
        "ml_last_model_meta",
        "ml_last_result",
        "model_curve_models",
        "overlay_artists",
        "overlay_curve_label_data",
        "overlay_label_refreshing",
        "paleo_label_refreshing",
        "paleoisochron_label_data",
        "plumbotectonics_isoage_label_data",
        "plumbotectonics_label_data",
        "preserve_import_render_mode",
        "saved_themes",
        "selected_2d_confirmed",
        "selected_3d_confirmed",
        "selected_indices",
        "selected_isochron_data",
        "selected_ternary_cols",
        "selected_ternary_confirmed",
        "selection_mode",
        "selection_tool",
    },
    # Persisted fields without an entry in the store's initial snapshot: they are
    # set at runtime, so registering them needs the registry to skip the initial
    # snapshot for them (otherwise the key would appear earlier than before).
    "pending": {
        "algorithm",
        "current_palette",
        "custom_palettes",
        "custom_shape_sets",
        "data_cols",
        "equation_overlays",
        "file_path",
        "group_cols",
        "group_marker_map",
        "hidden_groups",
        "isochron_error_mode",
        "isochron_label_options",
        "isochron_rxy_col",
        "isochron_sx_col",
        "isochron_sy_col",
        "kde_bw_adjust",
        "kde_bw_method",
        "kde_clip_max",
        "kde_clip_min",
        "kde_common_norm",
        "kde_gridsize",
        "kde_thresh",
        "kde_warn_singular",
        "last_group_col",
        "legend_item_order",
        "legend_location",
        "legend_offset",
        "legend_position",
        "line_styles",
        "marginal_kde_clip_max",
        "marginal_kde_clip_min",
        "marginal_kde_cumulative",
        "mixing_endmembers",
        "mixing_mixtures",
        "mu_kappa_age_col",
        "paleoisochron_ages",
        "param_presets",
        "parent_groups",
        "parent_shape_map",
        "plumbotectonics_group_visibility",
        "recent_files",
        "render_mode",
        "selected_2d_cols",
        "selected_3d_cols",
        "sheet_name",
        "ternary_ranges",
        "tooltip_columns",
    },
}


def snapshot_keys() -> set[str]:
    keys: set[str] = set()
    source = (ROOT / "core/state/store.py").read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Dict) and len(node.keys) >= 40:
            keys |= {
                key.value
                for key in node.keys
                if isinstance(key, ast.Constant) and isinstance(key.value, str)
            }
    return keys


def main() -> int:
    documented = {name for names in EXPLICIT_FIELDS.values() for name in names}
    problems: list[str] = []

    explicit = snapshot_keys() - REGISTERED
    undocumented = sorted(explicit - documented)
    for name in undocumented:
        reason = "not persisted" if name not in PERSISTED else "persisted"
        problems.append(f"{name} ({reason}): neither in the registry nor in EXPLICIT_FIELDS")

    stale = sorted(documented & REGISTERED)
    for name in stale:
        problems.append(f"{name}: registered already, remove it from EXPLICIT_FIELDS")

    unused = sorted(documented - snapshot_keys())
    for name in unused:
        problems.append(f"{name}: listed but not in the snapshot any more")

    if problems:
        print(f"TOTAL={len(problems)}")
        for problem in problems:
            print(f"1\t{problem}")
        return 1

    print(f"# registry: {len(REGISTERED)} | explicit: {len(explicit)} (documented)")
    print("TOTAL=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
