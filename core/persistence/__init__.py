"""Unified persistence facade (see docs/persistence_plan.md).

One entry point for everything the app persists:

- ``save_all``   — atomic snapshot of session + UI state to disk
- ``load_all``   — read both files back (session keeps its migration/version cap)
- ``install_autosave`` — debounced dispatch hook so state is never more than
  ``interval`` (default 30 s) old, plus immediate saves for rare key actions
- ``mark_clean_exit`` / ``consume_exit_marker`` — crash detection: the exit
  marker is only written on a clean shutdown, so a missing marker on the next
  startup means the previous run died mid-flight.

The facade is deliberately thin: schemas live in ``schema.py``, atomic I/O in
``atomic.py``, paths in ``paths.py``.
"""
from __future__ import annotations

import json
import logging
import os
import time
import zipfile
from pathlib import Path
from typing import Any

from ..config import CONFIG
from ..session.io import load_session_params
from .atomic import atomic_write_json, read_json_isolated
from .paths import EXIT_OK_FILE, SESSION_FILE, UI_STATE_FILE
from .schema import SESSION_FIELDS, UI_STATE_FIELDS, build_payload

logger = logging.getLogger(__name__)

#: Session archive format tag and version (export/import feature).
SESSION_ARCHIVE_FORMAT = "isotopes-session"
SESSION_ARCHIVE_VERSION = 1

#: Default debounce: save at most once per interval while state keeps changing.
DEFAULT_AUTOSAVE_INTERVAL = 30.0
#: Safety net: also save after this many dispatches even inside one interval.
DEFAULT_AUTOSAVE_DISPATCHES = 20
#: Rare, high-value actions that flush to disk immediately.
IMMEDIATE_SAVE_ACTIONS: frozenset[str] = frozenset({
    "SET_PARENT_GROUPS",
    "SET_PARENT_SHAPE_MAP",
    "SET_PARAM_PRESETS",
    "SET_SAVED_THEMES",
    "SAVE_THEME",
    "DELETE_THEME",
    "SET_RECENT_FILES",
    "SET_LEGEND_ITEM_ORDER",
    "SET_VISIBLE_GROUPS",
    "SET_CUSTOM_PALETTES",
    "SET_CUSTOM_SHAPE_SETS",
    "SET_LANGUAGE",
    "SET_UI_THEME",
})


def _json_safe(payload: dict[str, Any]) -> dict[str, Any]:
    """Convert snapshot values to JSON-serializable form.

    Sets and tuples appear in several snapshot fields (hidden_groups,
    legend_offset, adjust_text_*); they round-trip through ``_sync_state``
    normalizers on restore, so plain lists are lossless here.
    """
    out: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, set):
            out[key] = sorted(value)
        elif isinstance(value, tuple):
            out[key] = list(value)
        else:
            out[key] = value
    return out


def save_all(store: Any) -> bool:
    """Persist session + UI state atomically; return True on full success.

    ``store`` may be a StateStore or anything exposing ``snapshot()``
    (the AppStateGateway forwards to its store). The params.json payload
    keeps the ``session_version`` key so the legacy loader can still apply
    its version cap on the next start.
    """
    try:
        session_payload, ui_payload = _build_payloads(store)
        session_payload["saved_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        atomic_write_json(SESSION_FILE, _json_safe(session_payload))

        atomic_write_json(UI_STATE_FILE, _json_safe(ui_payload))
        return True
    except Exception as exc:
        logger.exception("Failed to persist state: %s", exc)
        return False


def load_ui_state() -> dict[str, Any] | None:
    """Read the UI-state payload only (corruption-isolated)."""
    return read_json_isolated(UI_STATE_FILE)


def extract_legacy_projection_presets() -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Split legacy projection presets out of the theme container.

    Before the persistence rework, projection parameter presets lived inside
    ``saved_themes["projection_presets"]`` in user_themes.json. Returns
    ``(themes_payload, presets_payload)`` with the presets key removed from
    the themes payload; either may be None when absent/unreadable. The theme
    file itself is left untouched here (it is rewritten on the next theme
    save, which then persists the clean container).
    """
    from .paths import THEMES_FILE

    themes = read_json_isolated(THEMES_FILE)
    if not themes:
        return None, None
    presets = themes.pop("projection_presets", None)
    presets_payload = (
        {str(k): dict(v or {}) for k, v in presets.items()}
        if isinstance(presets, dict)
        else None
    )
    return themes, presets_payload


def load_all() -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Load session + UI state payloads.

    Session payload goes through the legacy loader so version caps and
    legacy-file migration keep working. UI state is a fresh file read with
    corruption isolation. Returns ``(session_payload, ui_payload)``.
    """
    session_payload = load_session_params()
    ui_payload = read_json_isolated(UI_STATE_FILE)
    if ui_payload:
        logger.info("UI state loaded from %s", UI_STATE_FILE)
    else:
        logger.info("No UI state file found at %s; using defaults", UI_STATE_FILE)
    return session_payload, ui_payload


def install_autosave(store: Any, interval: float | None = None) -> None:
    """Attach a debounced save hook to *store*'s dispatch loop.

    The hook saves immediately for actions in ``IMMEDIATE_SAVE_ACTIONS`` and
    otherwise at most once per *interval* seconds (or every
    ``DEFAULT_AUTOSAVE_DISPATCHES`` dispatches). The final save on exit is
    still handled by the window ``closeEvent`` via ``save_all`` + ``mark_clean_exit``.
    """
    if interval is None:
        interval = float(CONFIG.get("autosave_interval", DEFAULT_AUTOSAVE_INTERVAL) or 0)
    dispatch_hook = getattr(store, "_dispatch_hook", None)
    if dispatch_hook is not None:
        logger.warning("Autosave hook already installed; replacing it")
    store._dispatch_hook = _make_autosave_hook(store, interval)


def _make_autosave_hook(store: Any, interval: float) -> Any:
    """Build the closure installed as the store dispatch hook."""
    last_save = time.monotonic()
    dispatches = 0
    last_result = True

    def hook(action_type: str) -> None:
        nonlocal last_save, dispatches, last_result
        dispatches += 1
        immediate = action_type in IMMEDIATE_SAVE_ACTIONS
        due = interval > 0 and time.monotonic() - last_save >= interval
        if immediate or due or dispatches >= DEFAULT_AUTOSAVE_DISPATCHES:
            dispatches = 0
            last_save = time.monotonic()
            if action_type in IMMEDIATE_SAVE_ACTIONS:
                logger.info("Immediate save after action %s", action_type)
            last_result = save_all(store)
            if not last_result:
                logger.error("Autosave failed; will retry on the next dispatch")
            _maybe_save_cache()

    def _maybe_save_cache() -> None:
        """Persist the embedding LRU cache when enabled (async, best-effort)."""
        if not CONFIG.get("cache_persist", False):
            return
        try:
            from ..cache import EmbeddingCache
            from ..state import app_state
            from .cache import save_cache_async
            from .paths import CACHE_FILE

            cache = getattr(app_state, "embedding_cache", None)
            if isinstance(cache, EmbeddingCache) and len(cache) > 0:
                save_cache_async(cache, CACHE_FILE)
        except Exception:
            logger.exception("Failed to schedule embedding cache persistence")

    return hook


def load_persistent_cache(state: Any) -> int:
    """Restore the persistent embedding cache into *state* (opt-in).

    Called once at startup after the dataset is loaded; entries whose data
    signature no longer matches the current dataset are dropped. Returns the
    number of restored entries.
    """
    if not CONFIG.get("cache_persist", False):
        return 0
    try:
        from ..cache import EmbeddingCache
        from .cache import load_cache
        from .paths import CACHE_FILE

        cache = getattr(state, "embedding_cache", None)
        if not isinstance(cache, EmbeddingCache):
            return 0
        return load_cache(cache, state, CACHE_FILE)
    except Exception:
        logger.exception("Failed to load persistent embedding cache")
        return 0


def mark_clean_exit() -> None:
    """Write the clean-exit marker (called from the window closeEvent)."""
    try:
        EXIT_OK_FILE.parent.mkdir(parents=True, exist_ok=True)
        EXIT_OK_FILE.write_text("ok", encoding="utf-8")
    except OSError:
        logger.exception("Failed to write clean-exit marker")


def consume_exit_marker() -> bool:
    """Return True if the previous run exited cleanly, then clear the marker.

    A missing marker implies a crash only when a previous session actually
    exists (params.json or ui_state.json); a brand-new install has no marker
    but is not a crash. Call this once at startup.
    """
    if EXIT_OK_FILE.exists():
        was_clean = True
    else:
        had_session = SESSION_FILE.exists() or UI_STATE_FILE.exists()
        was_clean = not had_session
    try:
        EXIT_OK_FILE.unlink(missing_ok=True)
    except OSError:
        logger.exception("Failed to remove clean-exit marker")
    return was_clean


def _build_payloads(store: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    """Extract the (session, ui_state) payload pair from a store snapshot."""
    snapshot = store.snapshot()
    session_payload = build_payload(snapshot, SESSION_FIELDS)
    session_payload["session_version"] = CONFIG.get("session_version", 1)
    ui_payload = build_payload(snapshot, UI_STATE_FIELDS)
    return session_payload, ui_payload


def export_session(store: Any, path: Any, *, include_data: bool = True) -> bool:
    """Export the current session (config + loaded data) as a ZIP archive.

    Archive layout (single portable file):
    - ``manifest.json``  — format tag, archive version, saved_at, has_data
    - ``session.json``   — SESSION_FIELDS payload (algorithm, params, ...)
    - ``ui_state.json``  — UI_STATE_FIELDS payload (styles, legend, presets)
    - ``data.csv``       — the loaded ``df_global`` (when present and
      ``include_data``), utf-8-sig compatible

    Writes are atomic (tmp + rename). Returns True on success.
    """
    try:
        session_payload, ui_payload = _build_payloads(store)
        snapshot = store.snapshot()
        df = snapshot.get("df_global")
        has_data = bool(include_data and df is not None and len(df) > 0)

        manifest = {
            "format": SESSION_ARCHIVE_FORMAT,
            "version": SESSION_ARCHIVE_VERSION,
            "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "has_data": has_data,
            "data_file": "data.csv" if has_data else None,
        }

        path = _as_path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = Path(str(path) + ".tmp")
        with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                "manifest.json",
                json.dumps(manifest, indent=2, ensure_ascii=False),
            )
            archive.writestr(
                "session.json",
                json.dumps(_json_safe(session_payload), indent=2, ensure_ascii=False),
            )
            archive.writestr(
                "ui_state.json",
                json.dumps(_json_safe(ui_payload), indent=2, ensure_ascii=False),
            )
            if has_data:
                archive.writestr("data.csv", df.to_csv(index=False))
        os.replace(tmp_path, path)
        logger.info(
            "Session exported to %s (data=%s)",
            path,
            "yes" if has_data else "no",
        )
        return True
    except Exception as exc:
        logger.exception("Failed to export session to %s: %s", path, exc)
        return False


def import_session(path: Any) -> dict[str, Any] | None:
    """Read and validate a session archive produced by ``export_session``.

    Returns a dict with keys ``session``, ``ui_state``, ``data_csv`` (raw CSV
    text or None) and ``has_data``; returns None when the file is missing,
    unreadable, not a session archive, or from a newer version. Nothing is
    applied to the live state here — the caller decides how to apply it.
    """
    try:
        path = _as_path(path)
        if not path.exists():
            logger.warning("Session archive not found: %s", path)
            return None
        with zipfile.ZipFile(path, "r") as archive:
            names = set(archive.namelist())
            if "manifest.json" not in names:
                logger.warning("Session archive %s has no manifest", path)
                return None
            manifest = json.loads(archive.read("manifest.json"))
            if manifest.get("format") != SESSION_ARCHIVE_FORMAT:
                logger.warning(
                    "File %s is not a %s archive (format=%r)",
                    path,
                    SESSION_ARCHIVE_FORMAT,
                    manifest.get("format"),
                )
                return None
            version = int(manifest.get("version", 1) or 1)
            if version > SESSION_ARCHIVE_VERSION:
                logger.warning(
                    "Session archive %s is version %s (supported: <=%s)",
                    path,
                    version,
                    SESSION_ARCHIVE_VERSION,
                )
                return None

            session_payload = (
                json.loads(archive.read("session.json"))
                if "session.json" in names
                else {}
            )
            ui_payload = (
                json.loads(archive.read("ui_state.json"))
                if "ui_state.json" in names
                else {}
            )
            data_csv = None
            has_data = bool(manifest.get("has_data") and "data.csv" in names)
            if has_data:
                data_csv = archive.read("data.csv").decode("utf-8-sig")
            logger.info(
                "Session archive %s loaded (version %s, data=%s)",
                path,
                version,
                "yes" if has_data else "no",
            )
            return {
                "session": session_payload,
                "ui_state": ui_payload,
                "data_csv": data_csv,
                "has_data": has_data,
            }
    except Exception as exc:
        logger.exception("Failed to import session from %s: %s", path, exc)
        return None


def _as_path(path: Any) -> Path:
    """Normalize a str/Path archive path."""
    return Path(str(path))
