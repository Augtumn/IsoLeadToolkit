"""Tests for embedding plotting dataframe preparation helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import cast

from core import app_state
from visualization.plotting.rendering.embedding import dataframe as dataframe_helpers


def test_prepare_plot_dataframe_filters_to_visible_groups(monkeypatch) -> None:
    df = pd.DataFrame({"group": ["A", "B"], "value": [1.0, 2.0]})
    embedding = np.array([[0.0, 0.1], [1.0, 1.1]], dtype=float)

    captured: dict[str, object] = {"set_visible_calls": []}
    monkeypatch.setattr(dataframe_helpers, "_df_global", lambda: df)
    monkeypatch.setattr(dataframe_helpers, "_active_subset_indices", lambda: None)
    monkeypatch.setattr(
        dataframe_helpers.state_gateway,
        "sync_available_and_visible_groups",
        lambda groups: captured.update({"synced_groups": list(groups)}),
    )
    monkeypatch.setattr(
        dataframe_helpers.state_gateway,
        "set_visible_groups",
        lambda value: cast(list[object], captured["set_visible_calls"]).append(value),
    )

    original_visible_groups = getattr(app_state, "visible_groups", None)
    try:
        setattr(app_state, "visible_groups", {"A"})

        result = dataframe_helpers.prepare_plot_dataframe("group", "UMAP", embedding)

        assert result is not None
        df_plot, unique_cats = result
        assert list(df_plot["group"]) == ["A"]
        assert unique_cats == ["A"]
        assert captured["synced_groups"] == ["A", "B"]
        assert captured["set_visible_calls"] == []
    finally:
        setattr(app_state, "visible_groups", original_visible_groups)


def test_prepare_plot_dataframe_resets_invalid_visible_filter(monkeypatch) -> None:
    df = pd.DataFrame({"group": ["A", "B"], "value": [1.0, 2.0]})
    embedding = np.array([[0.0, 0.1], [1.0, 1.1]], dtype=float)

    captured: dict[str, object] = {"set_visible_calls": []}
    monkeypatch.setattr(dataframe_helpers, "_df_global", lambda: df)
    monkeypatch.setattr(dataframe_helpers, "_active_subset_indices", lambda: None)
    monkeypatch.setattr(dataframe_helpers.state_gateway, "sync_available_and_visible_groups", lambda _groups: None)
    monkeypatch.setattr(
        dataframe_helpers.state_gateway,
        "set_visible_groups",
        lambda value: cast(list[object], captured["set_visible_calls"]).append(value),
    )

    original_visible_groups = getattr(app_state, "visible_groups", None)
    try:
        setattr(app_state, "visible_groups", {"Z"})

        result = dataframe_helpers.prepare_plot_dataframe("group", "UMAP", embedding)

        assert result is not None
        df_plot, unique_cats = result
        assert sorted(list(df_plot["group"])) == ["A", "B"]
        assert unique_cats == ["A", "B"]
        assert captured["set_visible_calls"] == [None]
    finally:
        setattr(app_state, "visible_groups", original_visible_groups)
