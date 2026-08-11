"""Tests for V1V2 embedding computation with missing-data handling."""

from __future__ import annotations

import numpy as np
import pandas as pd

from core import app_state, state_gateway
from visualization.plotting.rendering.embedding.compute_geochem import (
    compute_v1v2_embedding,
)
from visualization.plotting.rendering.embedding.dataframe import (
    prepare_plot_dataframe,
)


def _setup_df_with_nan(n_nan_rows: int = 1) -> pd.DataFrame:
    """Build a df_global with isotope columns, group column and NaN rows."""
    n = 8
    rng = np.random.default_rng(7)
    df = pd.DataFrame(
        {
            "206Pb/204Pb": rng.uniform(17.0, 19.0, n),
            "207Pb/204Pb": rng.uniform(15.3, 15.7, n),
            "208Pb/204Pb": rng.uniform(37.5, 39.5, n),
        }
    )
    df["Group"] = [f"G{i % 2}" for i in range(n)]
    for i in range(n_nan_rows):
        df.loc[i, "207Pb/204Pb"] = np.nan
        df.loc[i, "208Pb/204Pb"] = np.nan
    return df


def test_compute_v1v2_embedding_preserves_nan_rows() -> None:
    """NaN rows must stay NaN (not imputed to 0), valid rows must be finite."""
    df = _setup_df_with_nan(n_nan_rows=1)
    state_gateway.set_dataframe_and_source(df, file_path="", sheet_name=None)
    state_gateway.set_group_data_columns(
        ["Group"], ["206Pb/204Pb", "207Pb/204Pb", "208Pb/204Pb"]
    )
    state_gateway.set_last_group_col("Group")

    emb = compute_v1v2_embedding()
    assert emb is not None
    assert emb.shape == (len(df), 2)

    # Row 0 (NaN input) -> NaN embedding; remaining rows finite
    assert np.isnan(emb[0]).all()
    valid = emb[1:]
    assert np.isfinite(valid).all(), "Valid rows must produce finite V1/V2"


def test_v1v2_plot_dataframe_keeps_valid_points_when_nan_present() -> None:
    """prepare_plot_dataframe must keep row alignment so valid points render."""
    df = _setup_df_with_nan(n_nan_rows=2)
    state_gateway.set_dataframe_and_source(df, file_path="", sheet_name=None)
    state_gateway.set_group_data_columns(
        ["Group"], ["206Pb/204Pb", "207Pb/204Pb", "208Pb/204Pb"]
    )
    state_gateway.set_last_group_col("Group")

    emb = compute_v1v2_embedding()
    assert emb is not None

    prepared = prepare_plot_dataframe("Group", "V1V2", emb)
    assert prepared is not None, "Plot dataframe must align embedding with source data"
    df_plot, cats = prepared
    assert len(df_plot) == len(df)
    assert df_plot["_emb_x"].isna().sum() == 2
    assert df_plot["_emb_x"].notna().sum() == len(df) - 2
    assert cats == ["G0", "G1"]


def test_v1v2_embedding_all_valid_no_nan() -> None:
    """Fully valid data produces finite embedding with no NaN."""
    df = _setup_df_with_nan(n_nan_rows=0)
    state_gateway.set_dataframe_and_source(df, file_path="", sheet_name=None)
    state_gateway.set_group_data_columns(
        ["Group"], ["206Pb/204Pb", "207Pb/204Pb", "208Pb/204Pb"]
    )
    state_gateway.set_last_group_col("Group")

    emb = compute_v1v2_embedding()
    assert emb is not None
    assert emb.shape == (len(df), 2)
    assert np.isfinite(emb).all()


def test_v1v2_embedding_missing_isotope_column_returns_none() -> None:
    """Without all three isotope columns the embedding must be None, not crash."""
    df = pd.DataFrame(
        {
            "206Pb/204Pb": [18.5, 18.6],
            "207Pb/204Pb": [15.5, 15.6],
            "Group": ["G0", "G1"],
        }
    )
    state_gateway.set_dataframe_and_source(df, file_path="", sheet_name=None)
    state_gateway.set_group_data_columns(
        ["Group"], ["206Pb/204Pb", "207Pb/204Pb"]
    )
    state_gateway.set_last_group_col("Group")

    emb = compute_v1v2_embedding()
    assert emb is None


def test_v1v2_embedding_accepts_abbreviated_column_names() -> None:
    """Real-world datasets use '206/204' style names; they must be recognized."""
    rng = np.random.default_rng(11)
    n = 20
    df = pd.DataFrame(
        {
            "206/204": rng.uniform(17.0, 19.0, n),
            "207/204": rng.uniform(15.3, 15.7, n),
            "208/204": rng.uniform(37.5, 39.5, n),
        }
    )
    df["Group"] = [f"G{i % 2}" for i in range(n)]
    state_gateway.set_dataframe_and_source(df, file_path="", sheet_name=None)
    state_gateway.set_group_data_columns(
        ["Group"], ["206/204", "207/204", "208/204"]
    )
    state_gateway.set_last_group_col("Group")

    emb = compute_v1v2_embedding()
    assert emb is not None
    assert emb.shape == (n, 2)
    assert np.isfinite(emb).all()

    prepared = prepare_plot_dataframe("Group", "V1V2", emb)
    assert prepared is not None
    df_plot, cats = prepared
    assert len(df_plot) == n
    assert df_plot["_emb_x"].notna().sum() == n
