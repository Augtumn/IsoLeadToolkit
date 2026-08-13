"""Persistent embedding cache (npz, per-entry signature validation).

Opt-in via config ``cache_persist`` (default off). Only the most recent
``CACHE_PERSIST_ENTRIES`` LRU entries are persisted, capped at
``CACHE_PERSIST_MAX_BYTES``. Every entry stores its cache key (which embeds
the data signature); on load each entry is validated against the *current*
data signature and silently dropped when the underlying dataset changed.

Writes are atomic (tmp + rename) and, through ``save_cache_async``, run on a
daemon thread so the UI thread never blocks on disk I/O.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any

import numpy as np

from ..cache import build_data_signature

logger = logging.getLogger(__name__)

#: How many LRU-most-recent entries to persist.
CACHE_PERSIST_ENTRIES = 4
#: Hard size cap for the persisted file (bytes).
CACHE_PERSIST_MAX_BYTES = 50 * 1024 * 1024
#: Cache file format version; a mismatch invalidates the whole file.
CACHE_SCHEMA_VERSION = 1


def _hashable(value: Any) -> Any:
    """Recursively convert JSON-decoded values into hashable ones.

    Cache keys contain a ``subset_key`` that may round-trip through JSON as
    a list; a list is unhashable and would break dict lookups after restore.
    Returns None when no hashable form exists.
    """
    if isinstance(value, list):
        items = [_hashable(item) for item in value]
        if any(item is None for item in items):
            return None
        return tuple(items)
    if isinstance(value, dict):
        try:
            return tuple(sorted((str(k), _hashable(v)) for k, v in value.items()))
        except TypeError:
            return None
    try:
        hash(value)
        return value
    except TypeError:
        return None


def save_cache(cache: Any, path: Path) -> bool:
    """Persist the most recent cache entries to *path*; return True if written.

    Only ``np.ndarray`` values are saved; other payload types are skipped.
    """
    try:
        entries = list(getattr(cache, "_store", {}).items())[-CACHE_PERSIST_ENTRIES:]
        arrays: dict[str, Any] = {}
        meta: list[dict[str, Any]] = []
        for idx, (key, value) in enumerate(entries):
            if not isinstance(value, np.ndarray):
                continue
            arr_name = f"arr_{idx}"
            arrays[arr_name] = value
            meta.append({"key": list(key), "name": arr_name})
        if not arrays:
            return False

        meta_json = [json.dumps(entry, ensure_ascii=False) for entry in meta]
        arrays["meta"] = np.array(meta_json)
        arrays["schema_version"] = np.array([CACHE_SCHEMA_VERSION])

        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = Path(str(path) + ".tmp")
        # numpy appends ".npz" to filenames that do not end in ".npz", so
        # write through a handle to keep the temp name under our control.
        with open(tmp_path, "wb") as handle:
            np.savez_compressed(handle, **arrays)
        if tmp_path.stat().st_size > CACHE_PERSIST_MAX_BYTES:
            logger.warning(
                "Embedding cache file exceeds %s bytes; not persisting",
                CACHE_PERSIST_MAX_BYTES,
            )
            tmp_path.unlink(missing_ok=True)
            return False
        os.replace(tmp_path, path)
        logger.info("Persisted %s embedding cache entries to %s", len(meta), path)
        return True
    except Exception:
        logger.exception("Failed to persist embedding cache to %s", path)
        return False


def load_cache(cache: Any, app_state: Any, path: Path) -> int:
    """Restore validated entries from *path* into *cache*; return restored count.

    An entry is only accepted when its stored data signature (embedded in the
    cache key) matches the current dataset, so a changed dataset never
    reuses stale embeddings.
    """
    if not path.exists():
        return 0
    try:
        current_signature = build_data_signature(app_state)
        restored = 0
        with np.load(path, allow_pickle=False) as data:
            if "schema_version" not in data:
                logger.warning("Embedding cache %s has no schema version; ignoring", path)
                return 0
            try:
                file_version = int(data["schema_version"].flat[0])
            except Exception:
                logger.warning("Embedding cache %s schema version unreadable; ignoring", path)
                return 0
            if file_version != CACHE_SCHEMA_VERSION:
                logger.warning(
                    "Embedding cache %s schema v%s != supported v%s; ignoring",
                    path,
                    file_version,
                    CACHE_SCHEMA_VERSION,
                )
                return 0
            if "meta" not in data:
                logger.warning("Embedding cache %s has no meta; ignoring", path)
                return 0
            try:
                metas = [json.loads(item) for item in data["meta"].tolist()]
            except Exception:
                logger.warning("Embedding cache meta unreadable in %s; ignoring", path)
                return 0
            for meta in metas:
                try:
                    raw_key = meta["key"]
                    name = meta["name"]
                except (KeyError, TypeError):
                    continue
                if name not in data:
                    continue
                try:
                    key = tuple(_hashable(item) for item in raw_key)
                except TypeError:
                    continue
                if not key or any(item is None for item in key):
                    continue
                if key[-1] != current_signature:
                    continue
                cache.set(key, data[name])
                restored += 1
        if restored:
            logger.info("Restored %s validated embedding cache entries", restored)
        else:
            logger.info("No valid embedding cache entries for the current dataset")
        return restored
    except Exception:
        logger.exception("Failed to load embedding cache from %s", path)
        return 0


def save_cache_async(cache: Any, path: Path) -> None:
    """Persist the cache on a daemon thread (fire-and-forget)."""
    try:
        thread = threading.Thread(
            target=save_cache,
            args=(cache, path),
            name="embedding-cache-save",
            daemon=True,
        )
        thread.start()
    except Exception:
        logger.exception("Failed to start embedding cache save thread")
