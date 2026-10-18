"""StateStore for managed AppState domains."""

from __future__ import annotations

import logging
from typing import Any, Callable

from ._dispatch_handlers import dispatch_action
from .fields import snapshot_from_state, snapshot_from_store
from ._normalizers import (
    _normalize_active_subset_indices,
    _normalize_visible_groups,
    sync_state_store_to_app,
)

logger = logging.getLogger(__name__)


def dispatch_or_apply(owner: Any, action: dict[str, Any], apply: Callable[[], None]) -> None:
    """Route a state mutation through *owner*'s StateStore.

    Property setters run both before the store exists (during AppState
    construction) and after it is attached; before that point the mutation is
    the plain attribute write in *apply*.
    """
    store = getattr(owner, 'state_store', None)
    if store is not None:
        store.dispatch(action)
        return
    apply()

# Runtime-only snapshot fields that the rendering pipeline legitimately
# writes directly (rebuilt every render / transient artist state); they are
# exempt from the direct-mutation warning below.
_DIFF_WARN_EXCLUDED = frozenset({
    "overlay_artists",
    "overlay_curve_label_data",
    "paleoisochron_label_data",
    "plumbotectonics_label_data",
    "plumbotectonics_isoage_label_data",
    "marginal_axes",
    "legend_last_title",
    "legend_last_handles",
    "legend_last_labels",
    "df_global",
    "last_embedding",
})


def _warn_direct_mutations(state: Any, snapshot: dict[str, Any]) -> None:
    """Warn when snapshot-managed state diverged from the store snapshot.

    Any divergence on a non-exempt field means someone bypassed the gateway;
    the next sync will silently roll that change back. Runtime-only fields
    (render maps, matplotlib objects) are exempt.
    """
    import numpy as np

    for key, snap_value in snapshot.items():
        if key in _DIFF_WARN_EXCLUDED:
            continue
        current = getattr(state, key, None)
        try:
            if isinstance(snap_value, np.ndarray) or isinstance(current, np.ndarray):
                equal = bool(np.array_equal(current, snap_value, equal_nan=True))
            else:
                equal = current == snap_value
        except Exception:
            continue
        if not equal:
            logger.warning(
                "State field '%s' was modified outside the gateway and will "
                "be rolled back on the next sync",
                key,
            )


def _copied(value):
    """A copy of *value* when it is an array-like that callers may mutate in place."""
    copier = getattr(value, "copy", None)
    return copier() if callable(copier) else value


class StateStore:
    """Manage selected AppState domains through action dispatch."""

    def __init__(self, state: Any) -> None:
        self._state = state
        self._dispatch_hook = None
        self._snapshot: dict[str, Any] = {
            "paleo_label_refreshing": bool(getattr(state, "paleo_label_refreshing", False)),
            "overlay_label_refreshing": bool(getattr(state, "overlay_label_refreshing", False)),
            "overlay_curve_label_data": list(getattr(state, "overlay_curve_label_data", []) or []),
            "paleoisochron_label_data": list(getattr(state, "paleoisochron_label_data", []) or []),
            "plumbotectonics_label_data": list(
                getattr(state, "plumbotectonics_label_data", []) or []
            ),
            "plumbotectonics_isoage_label_data": list(
                getattr(state, "plumbotectonics_isoage_label_data", []) or []
            ),
            "overlay_artists": dict(getattr(state, "overlay_artists", {}) or {}),
            "last_embedding": getattr(state, "last_embedding", None),
            "last_embedding_type": str(getattr(state, "last_embedding_type", "") or ""),
            "selected_isochron_data": getattr(state, "selected_isochron_data", None),
            "embedding_task_token": int(getattr(state, "embedding_task_token", 0)),
            "embedding_task_running": bool(getattr(state, "embedding_task_running", False)),
            "marginal_axes": getattr(state, "marginal_axes", None),
            # Copied, not referenced: these are the only three projections that hand an internal object
            # out, and an in-place change then proved nothing - the direct-mutation detector compared the
            # object with itself and always found it equal.
            "last_pca_variance": _copied(getattr(state, "last_pca_variance", None)),
            "last_pca_components": _copied(getattr(state, "last_pca_components", None)),
            "current_feature_names": list(getattr(state, "current_feature_names", []) or []),
            "adjust_text_in_progress": bool(getattr(state, "adjust_text_in_progress", False)),
            "current_plot_title": str(getattr(state, "current_plot_title", "")),
            "last_2d_cols": (
                list(getattr(state, "last_2d_cols", []) or [])
                if getattr(state, "last_2d_cols", None) is not None
                else None
            ),
            "isochron_results": dict(getattr(state, "isochron_results", {}) or {}),
            "selected_indices": set(getattr(state, "selected_indices", set()) or set()),
            "active_subset_indices": _normalize_active_subset_indices(
                getattr(state, "active_subset_indices", None)
            ),
            "df_global": getattr(state, "df_global", None),
            "data_version": int(getattr(state, "data_version", 0)),
            "selection_mode": bool(getattr(state, "selection_mode", False)),
            "selection_tool": getattr(state, "selection_tool", None),
            "legend_last_title": getattr(state, "legend_last_title", None),
            "legend_last_handles": getattr(state, "legend_last_handles", None),
            "legend_last_labels": getattr(state, "legend_last_labels", None),
            "saved_themes": dict(getattr(state, "saved_themes", {}) or {}),
            "ml_last_result": getattr(state, "ml_last_result", None),
            "ml_last_model_meta": getattr(state, "ml_last_model_meta", None),
            "preserve_import_render_mode": bool(getattr(state, "preserve_import_render_mode", False)),
            "available_groups": list(getattr(state, "available_groups", []) or []),
            "selected_ternary_cols": list(getattr(state, "selected_ternary_cols", []) or []),
            "selected_2d_confirmed": bool(getattr(state, "selected_2d_confirmed", False)),
            "selected_3d_confirmed": bool(getattr(state, "selected_3d_confirmed", False)),
            "selected_ternary_confirmed": bool(getattr(state, "selected_ternary_confirmed", False)),
            "initial_render_done": bool(getattr(state, "initial_render_done", False)),
            **snapshot_from_state(state),
            "model_curve_models": (
                list(getattr(state, "model_curve_models", []) or [])
                if getattr(state, "model_curve_models", None) is not None
                else None
            ),
        }
        self._sync_state()

    def dispatch(self, action: dict[str, Any]) -> dict[str, Any]:
        """Dispatch an action and return a snapshot copy."""
        _warn_direct_mutations(self._state, self._snapshot)
        # An action is one transaction: a handler that raises halfway used to leave the snapshot partly
        # updated and the live state not updated at all, and the next dispatch then reported the store's own
        # leftovers as a direct mutation - the check's own noise. Roll back and bring the state back with it.
        before = dict(self._snapshot)
        try:
            dispatch_action(self, action)
            self._sync_state()
        except Exception:
            self._snapshot.clear()
            self._snapshot.update(before)
            self._sync_state()
            logger.exception("Action %r failed; the state was rolled back", action.get("type"))
            raise
        self._notify_render_mode_if_changed(action)
        hook = self._dispatch_hook
        if callable(hook):
            try:
                hook(str(action.get("type", "")))
            except Exception:
                logger.exception("Dispatch hook failed for action %s", action.get("type"))
        return self.snapshot()

    def _notify_render_mode_if_changed(self, action: dict[str, Any]) -> None:
        """Tell render-mode listeners when the mode actually changed.

        The status bar (and any other follower) refreshes through this
        listener; without it, the bottom-right mode label stays stale after
        switching modes from a panel dialog.
        """
        action_type = str(action.get("type", "")).upper().strip()
        if action_type != "SET_RENDER_MODE":
            return
        notify = getattr(self._state, "notify_render_mode_change", None)
        if callable(notify):
            try:
                notify(str(self._snapshot.get("render_mode", "")))
            except Exception:
                logger.exception("Render-mode listener failed")

    def restore_snapshot(self, payload: dict[str, Any]) -> bool:
        """Bulk-restore persisted fields without going through the gateway.

        Used by the persistence layer on startup (see docs/persistence.md
        §2). Only whitelisted, persisted fields are accepted so a hand-edited
        file can never smuggle junk into the live snapshot. Returns True when
        the payload was applied; a value that breaks the sync is rolled back
        and reported as False instead of raising.
        """
        from ..persistence.schema import SESSION_FIELDS, UI_STATE_FIELDS

        # Metadata keys carried by persisted session payloads that are not
        # snapshot fields; they are expected and silently ignored.
        _META_KEYS = frozenset({"session_version", "saved_at"})
        # Derived keys an archive written by an earlier version still carries. They are recomputed from the fields
        # they come from, so they are dropped without the "non-persisted key" warning.
        _DERIVED_KEYS = frozenset({"paleoisochron_ages"})

        allowed = SESSION_FIELDS | UI_STATE_FIELDS
        accepted = {key: value for key, value in payload.items() if key in allowed}
        skipped = sorted(set(payload) - allowed - _META_KEYS - _DERIVED_KEYS)
        if skipped:
            logger.warning(
                "Ignored %s non-persisted key(s) during snapshot restore: %s",
                len(skipped),
                ", ".join(skipped),
            )
        if not accepted:
            return False
        # JSON round-trips sets/tuples as lists; restore their native types
        # so the mutation-diff check does not flag a false divergence.
        for key in ("hidden_groups",):
            if key in accepted and accepted[key] is not None:
                accepted[key] = set(accepted[key])
        for key in (
            "legend_offset",
            "adjust_text_force_text",
            "adjust_text_force_static",
            "adjust_text_expand",
        ):
            if key in accepted and accepted[key] is not None:
                accepted[key] = tuple(accepted[key])
        # Values are not schema-validated: a hand-edited file can carry a
        # wrong type that only blows up inside _sync_state (e.g. plot_dpi
        # 'abc'). Apply defensively and roll back on failure so a bad file
        # cannot abort startup.
        previous = {key: self._snapshot.get(key) for key in accepted}
        self._snapshot.update(accepted)
        # The derived ages follow the three controls that were just restored, never the file's own copy of them.
        from ._dispatch_handlers import _recompute_paleoisochron_ages

        _recompute_paleoisochron_ages(self._snapshot)
        try:
            self._sync_state()
        except Exception as exc:
            logger.error(
                "Failed to apply restored snapshot (%s); rolling back", exc
            )
            self._snapshot.update(previous)
            try:
                self._sync_state()
            except Exception:
                logger.exception("Rollback after failed restore also failed")
            return False
        return True

    def snapshot(self) -> dict[str, Any]:
        """Return shallow-copied tracked domains."""
        return {
            "paleo_label_refreshing": bool(self._snapshot["paleo_label_refreshing"]),
            "overlay_label_refreshing": bool(self._snapshot["overlay_label_refreshing"]),
            "overlay_curve_label_data": list(self._snapshot["overlay_curve_label_data"]),
            "paleoisochron_label_data": list(self._snapshot["paleoisochron_label_data"]),
            "plumbotectonics_label_data": list(self._snapshot["plumbotectonics_label_data"]),
            "plumbotectonics_isoage_label_data": list(
                self._snapshot["plumbotectonics_isoage_label_data"]
            ),
            "overlay_artists": dict(self._snapshot["overlay_artists"]),
            "last_embedding": self._snapshot["last_embedding"],
            "last_embedding_type": str(self._snapshot["last_embedding_type"]),
            "selected_isochron_data": self._snapshot["selected_isochron_data"],
            "embedding_task_token": int(self._snapshot["embedding_task_token"]),
            "embedding_task_running": bool(self._snapshot["embedding_task_running"]),
            "marginal_axes": self._snapshot["marginal_axes"],
            "last_pca_variance": _copied(self._snapshot["last_pca_variance"]),
            "last_pca_components": _copied(self._snapshot["last_pca_components"]),
            "current_feature_names": list(self._snapshot["current_feature_names"] or []),
            "adjust_text_in_progress": bool(self._snapshot["adjust_text_in_progress"]),
            "current_plot_title": str(self._snapshot["current_plot_title"]),
            "last_2d_cols": (
                list(self._snapshot["last_2d_cols"])
                if self._snapshot["last_2d_cols"] is not None
                else None
            ),
            "isochron_results": dict(self._snapshot["isochron_results"]),
            "selected_indices": set(self._snapshot["selected_indices"]),
            "active_subset_indices": _normalize_active_subset_indices(
                self._snapshot["active_subset_indices"]
            ),
            "df_global": self._snapshot["df_global"],
            "data_version": int(self._snapshot["data_version"]),
            "selection_mode": bool(self._snapshot["selection_mode"]),
            "selection_tool": self._snapshot["selection_tool"],
            "legend_last_title": self._snapshot["legend_last_title"],
            "legend_last_handles": self._snapshot["legend_last_handles"],
            "legend_last_labels": self._snapshot["legend_last_labels"],
            "saved_themes": dict(self._snapshot["saved_themes"]),
            "ml_last_result": self._snapshot["ml_last_result"],
            "ml_last_model_meta": self._snapshot["ml_last_model_meta"],
            "preserve_import_render_mode": bool(self._snapshot["preserve_import_render_mode"]),
            "available_groups": list(self._snapshot["available_groups"]),
            "selected_ternary_cols": list(self._snapshot["selected_ternary_cols"]),
            "selected_2d_confirmed": bool(self._snapshot["selected_2d_confirmed"]),
            "selected_3d_confirmed": bool(self._snapshot["selected_3d_confirmed"]),
            "selected_ternary_confirmed": bool(self._snapshot["selected_ternary_confirmed"]),
            "initial_render_done": bool(self._snapshot["initial_render_done"]),
            **snapshot_from_store(self._snapshot),
            "model_curve_models": (
                list(self._snapshot["model_curve_models"])
                if self._snapshot["model_curve_models"] is not None
                else None
            ),
        }

    def _sync_state(self) -> None:
        sync_state_store_to_app(self._state, self._snapshot)



