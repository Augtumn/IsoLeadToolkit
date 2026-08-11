"""Shared state access helpers for rendering modules."""
from __future__ import annotations

from typing import Any

from core import app_state


def _data_state() -> Any:
    return getattr(app_state, 'data', app_state)


def _df_global() -> Any:
    return getattr(_data_state(), 'df_global', app_state.df_global)


def _data_cols() -> list[str]:
    return getattr(_data_state(), 'data_cols', app_state.data_cols)


def _active_subset_indices() -> Any:
    return getattr(_data_state(), 'active_subset_indices', app_state.active_subset_indices)


def _group_cols() -> list[str]:
    return getattr(_data_state(), 'group_cols', app_state.group_cols)
