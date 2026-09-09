"""Embedding cache utilities."""
from __future__ import annotations

import json
from collections import OrderedDict
from typing import Any, Hashable, Iterable, Tuple

#: Memoized data signatures keyed by (id(df), data_version, row count).
#: ``build_data_signature`` recomputes per-column means on every call and is
#: called twice per render; this keeps that off the hot path.
_SIGNATURE_CACHE: dict[Tuple[int, int, int], Tuple[Any, ...]] = {}


def _normalize_params(params: Any) -> str:
    try:
        return json.dumps(params, sort_keys=True, default=str)
    except Exception:
        return str(params)


def build_data_signature(app_state: Any) -> Tuple[Any, ...]:
    df = getattr(app_state, 'df_global', None)
    shape = (len(df), len(df.columns)) if df is not None else (0, 0)
    data_version = int(getattr(app_state, 'data_version', 0) or 0)
    cache_key = (id(df), data_version, int(shape[0]))
    cached = _SIGNATURE_CACHE.get(cache_key)
    if cached is not None:
        return cached

    file_path = getattr(app_state, 'file_path', '') or ''
    sheet_name = getattr(app_state, 'sheet_name', '') or ''
    data_cols = tuple(getattr(app_state, 'data_cols', []) or [])
    group_cols = tuple(getattr(app_state, 'group_cols', []) or [])
    # Lightweight content probe: column names plus per-column means. This
    # catches same-shape files whose values changed without a version bump.
    content_probe: Tuple[Any, ...] = ()
    if df is not None and len(df) > 0:
        try:
            columns = tuple(str(c) for c in df.columns)
            numeric = df.select_dtypes(include='number')
            means = tuple(
                round(float(v), 6) for v in numeric.mean(numeric_only=True)
            ) if numeric.shape[1] else ()
            content_probe = (columns, means)
        except Exception:
            content_probe = ()
    # NOTE: data_version is deliberately NOT part of the signature. It is
    # session-local (reset to 0 on every start), which made the persisted
    # embedding cache unusable across sessions; the content probe already
    # covers in-place data changes.
    signature = (file_path, sheet_name, shape, data_cols, group_cols, content_probe)

    _SIGNATURE_CACHE.clear()  # datasets are not hot-swapped often
    _SIGNATURE_CACHE[cache_key] = signature
    return signature


def build_embedding_cache_key(app_state: Any, algorithm: str, params: Any, subset_key: Hashable) -> Tuple[Any, ...]:
    signature = build_data_signature(app_state)
    return (
        'embed',
        str(algorithm),
        _normalize_params(params),
        subset_key,
        signature,
    )


class EmbeddingCache:
    """Simple LRU cache for embeddings."""

    def __init__(self, max_entries: int = 8) -> None:
        self.max_entries = max_entries
        self._store: OrderedDict[Hashable, Any] = OrderedDict()

    def get(self, key: Hashable) -> Any:
        if key not in self._store:
            return None
        value = self._store.pop(key)
        self._store[key] = value
        return value

    def set(self, key: Hashable, value: Any) -> None:
        if key in self._store:
            self._store.pop(key)
        self._store[key] = value
        self._trim()

    def clear(self) -> None:
        self._store.clear()

    def _trim(self) -> None:
        while len(self._store) > self.max_entries:
            self._store.popitem(last=False)

    def __len__(self) -> int:
        return len(self._store)

    def keys(self) -> Iterable[Hashable]:
        return list(self._store.keys())
