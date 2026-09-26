"""Guard: every persisted state field must be written back to the app state.

IsotopesAnalyse keeps a snapshot in StateStore; sync_state_store_to_app() copies it
back onto app_state. A field that is missing there keeps its old value and makes every
later dispatch log "modified outside the gateway" - exactly the ternary_render_margin
bug. This guard compares the snapshot with the live state at runtime, which also
covers nested holders (app_state.legend.*) and helper-based assignments that a static
check would miss.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import logging

from core import app_state  # noqa: E402
from core.state._normalizers import sync_state_store_to_app  # noqa: E402

#: Snapshot entries that are runtime objects (or are written by other code paths),
#: with the reason they cannot be compared here.
RUNTIME_FIELDS = {
    "active_subset_indices": "derived from the current selection",
    "annotation": "matplotlib artist",
    "artist_to_sample": "matplotlib artist -> sample map",
    "ax": "matplotlib axes",
    "current_groups": "derived from the data",
    "current_plot_title": "derived from the render",
    "data_version": "counter",
    "df_global": "pandas frame",
    "embedding_task_running": "runtime flag",
    "embedding_task_token": "runtime token",
    "equation_overlays": "matplotlib artists",
    "fig": "matplotlib figure",
    "group_to_scatter": "matplotlib artists",
    "language_labels": "resolved at load time",
    "language_listeners": "runtime callbacks",
    "last_2d_cols": "derived from the export dialog",
    "last_embedding_type": "derived from the last render",
    "model_curve_models": "matplotlib artists",
    "overlay_artists": "matplotlib artists",
    "overlay_curve_label_data": "matplotlib artists",
    "paleoisochron_ages": "derived from the controls",
    "paleoisochron_label_data": "matplotlib artists",
    "plumbotectonics_isoage_label_data": "matplotlib artists",
    "plumbotectonics_label_data": "matplotlib artists",
    "saved_themes": "theme storage",
    "scatter_collections": "matplotlib artists",
    "selected_2d_confirmed": "dialog state",
    "selected_3d_confirmed": "dialog state",
    "selected_isochron_data": "matplotlib artists",
    "selected_ternary_cols": "dialog state",
    "selected_ternary_confirmed": "dialog state",
    "state_store": "the store itself",
    "ternary_factors": "normalised by the renderer",
}

_MISSING = object()


def _live_value(name: str):
    """The live value of a snapshot field, looking into app_state.legend as well."""
    value = getattr(app_state, name, _MISSING)
    if value is not _MISSING:
        return value
    legend = getattr(app_state, "legend", None)
    if legend is not None:
        return getattr(legend, name, _MISSING)
    return _MISSING


#: A value that no snapshot field can legitimately hold, used to ensure the sync
#: actually writes the field back (otherwise an already-correct value would hide a
#: missing assignment).
_PROBE = "__isotopes_sync_probe__"


def _perturb(value):
    """A different value of a comparable type, or _MISSING when not comparable."""
    if isinstance(value, bool):
        return not value
    if isinstance(value, (int, float)):
        return value + 1
    if isinstance(value, str):
        return _PROBE
    if value is None:
        return _PROBE
    if isinstance(value, list):
        return [] if value else [_PROBE]
    if isinstance(value, dict):
        return {} if value else {"probe": _PROBE}
    if isinstance(value, tuple):
        return () if value else (_PROBE,)
    return _MISSING


def _set_live(name: str, value) -> bool:
    if hasattr(app_state, name):
        setattr(app_state, name, value)
        return True
    legend = getattr(app_state, "legend", None)
    if legend is not None and hasattr(legend, name):
        setattr(legend, name, value)
        return True
    return False


def main() -> int:
    # The deliberate perturbation below writes straight to the state, which the
    # store reports; that noise is expected here.
    logging.getLogger("core.state.store").setLevel(logging.CRITICAL)

    snapshot = app_state.state_store.snapshot()

    problems: list[str] = []
    probed = 0
    for name, expected in snapshot.items():
        if name in RUNTIME_FIELDS or name.startswith("_"):
            continue
        if _live_value(name) is _MISSING:
            problems.append(f"{name}: in the snapshot but no such attribute on the state")
            continue
        probe = _perturb(expected)
        if probe is _MISSING or not _set_live(name, probe):
            continue
        probed += 1

    # One sync must restore every probed field to its snapshot value.
    sync_state_store_to_app(app_state, snapshot)
    for name, expected in snapshot.items():
        if name in RUNTIME_FIELDS or name.startswith("_"):
            continue
        live = _live_value(name)
        if live is _MISSING:
            continue
        try:
            same = bool(live == expected)
        except Exception:
            same = live is expected
        if not same:
            problems.append(
                f"{name}: not restored by sync_state_store_to_app (state={live!r}, snapshot={expected!r})"
            )

    print(f"# probed {probed} fields")
    if problems:
        print(f"TOTAL={len(problems)}")
        for problem in problems:
            print(f"1\t{problem}")
        return 1
    print("TOTAL=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
