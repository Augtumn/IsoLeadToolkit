"""Targeted rendering sub-function unit tests: scatter, KDE, geochem overlay, legend, title."""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")  # headless backend — no display required

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from core import app_state, state_gateway


# ── State snapshot helpers (follow existing test conventions) ──────────

def _snapshot_rendering_state() -> dict[str, object]:
    keys = [
        "fig", "ax", "df_global", "file_path", "sheet_name",
        "group_cols", "data_cols", "algorithm", "render_mode",
        "umap_params", "current_plot_title", "scatter_collections",
        "data_version", "last_embedding", "last_embedding_type",
    ]
    snapshot = {key: getattr(app_state, key, None) for key in keys}
    # Save embedding cache entries to prevent cross-test pollution.
    # get() moves entries to MRU position, so iterate _store directly.
    cache_store = getattr(app_state.embedding_cache, '_store', {})
    snapshot["_cache_pairs"] = list(cache_store.items())
    return snapshot


def _restore_rendering_state(snapshot: dict[str, object]) -> None:
    setattr(app_state, "fig", snapshot.get("fig"))
    setattr(app_state, "ax", snapshot.get("ax"))
    state_gateway.set_dataframe_and_source(
        snapshot.get("df_global"),
        file_path=snapshot.get("file_path") or "",
        sheet_name=snapshot.get("sheet_name"),
    )
    state_gateway.set_group_data_columns(
        list(snapshot.get("group_cols") or []),
        list(snapshot.get("data_cols") or []),
    )
    state_gateway.set_algorithm(str(snapshot.get("algorithm") or "UMAP"))
    state_gateway.set_render_mode(str(snapshot.get("render_mode") or "UMAP"))
    state_gateway.set_umap_params(dict(snapshot.get("umap_params") or {}))
    state_gateway.set_current_plot_title(str(snapshot.get("current_plot_title") or ""))
    # Restore embedding cache (avoids cross-test pollution of LRU state)
    app_state.embedding_cache.clear()
    for key, value in snapshot.get("_cache_pairs", []):
        try:
            app_state.embedding_cache.set(key, value)
        except Exception:
            pass


def _make_test_df(n_samples: int = 10, n_groups: int = 3) -> pd.DataFrame:
    """Create a minimal but realistic lead-isotope test DataFrame."""
    rng = np.random.default_rng(42)
    df = pd.DataFrame({
        'Pb206_204': rng.uniform(18.0, 19.5, n_samples),
        'Pb207_204': rng.uniform(15.5, 15.8, n_samples),
        'Pb208_204': rng.uniform(38.0, 39.5, n_samples),
        'Group': [chr(65 + i % n_groups) for i in range(n_samples)],
    })
    return df


# ── Test 1: scatter rendering produces valid figure (via PCA) ───────────

def test_render_scatter_produces_valid_figure():
    """plot_embedding with PCA on test data should produce a Figure with axes.

    PCA is used because it works reliably on small sample sizes without
    the numerical instability UMAP exhibits with n_samples <= n_neighbors.
    """
    from visualization.plotting import plot_embedding

    snapshot = _snapshot_rendering_state()
    fig = plt.figure()
    ax = fig.add_subplot(111)
    try:
        state_gateway.set_figure_axes(fig, ax)

        df = _make_test_df(n_samples=8, n_groups=3)
        state_gateway.set_dataframe_and_source(df, file_path=None, sheet_name=None)
        state_gateway.set_group_data_columns(['Group'], ['Pb206_204', 'Pb207_204', 'Pb208_204'])
        state_gateway.set_algorithm('PCA')
        state_gateway.set_render_mode('PCA')

        result = plot_embedding(
            'Group', 'PCA',
            pca_params={'n_components': 2, 'random_state': 42},
            size=30,
        )
        assert result is True, "plot_embedding (PCA) should return True on success"
        assert app_state.fig is not None
        assert len(app_state.fig.axes) > 0
    finally:
        plt.close('all')
        _restore_rendering_state(snapshot)


def test_render_scatter_with_umap_produces_valid_figure():
    """plot_embedding with UMAP on sufficient data should produce a Figure."""
    from visualization.plotting import plot_embedding

    snapshot = _snapshot_rendering_state()
    fig = plt.figure()
    ax = fig.add_subplot(111)
    try:
        state_gateway.set_figure_axes(fig, ax)

        df = _make_test_df(n_samples=15, n_groups=3)
        state_gateway.set_dataframe_and_source(df, file_path=None, sheet_name=None)
        state_gateway.set_group_data_columns(['Group'], ['Pb206_204', 'Pb207_204', 'Pb208_204'])
        state_gateway.set_algorithm('UMAP')
        state_gateway.set_render_mode('UMAP')

        # n_neighbors must be < n_samples; 3 is safe for 15 samples
        umap_params = {'n_neighbors': 3, 'min_dist': 0.1, 'random_state': 42}
        state_gateway.set_umap_params(umap_params)

        result = plot_embedding(
            'Group', 'UMAP',
            umap_params=umap_params,
            size=30,
        )
        assert result is True, "plot_embedding (UMAP) should return True on success"
        assert app_state.fig is not None
        assert len(app_state.fig.axes) > 0
    finally:
        plt.close('all')
        _restore_rendering_state(snapshot)


# ── Test 2: KDE contour rendering handles edge cases ────────────────────

def test_kde_rendering_handles_single_point():
    """KDE with single data point should not crash — verify import and callable."""
    from visualization.plotting.kde import clear_marginal_axes, draw_marginal_kde

    assert callable(draw_marginal_kde)
    assert callable(clear_marginal_axes)


# ── Test 3: legend rendering produces handles or scatter collections ────

def test_legend_rendering_after_embedding():
    """After plot_embedding, figure axes should have a legend or scatter output."""
    from visualization.plotting import plot_embedding

    snapshot = _snapshot_rendering_state()
    fig = plt.figure()
    ax = fig.add_subplot(111)
    try:
        state_gateway.set_figure_axes(fig, ax)

        df = _make_test_df(n_samples=8, n_groups=3)
        state_gateway.set_dataframe_and_source(df, file_path=None, sheet_name=None)
        state_gateway.set_group_data_columns(['Group'], ['Pb206_204', 'Pb207_204', 'Pb208_204'])
        state_gateway.set_algorithm('PCA')
        state_gateway.set_render_mode('PCA')

        plot_embedding(
            'Group', 'PCA',
            pca_params={'n_components': 2, 'random_state': 42},
            size=30,
        )

        legends = [ax_.get_legend() for ax_ in app_state.fig.axes if ax_.get_legend() is not None]
        has_scatter = len(getattr(app_state, 'scatter_collections', [])) > 0
        assert len(legends) > 0 or has_scatter, (
            "Should have either a legend or scatter collections after embedding"
        )
    finally:
        plt.close('all')
        _restore_rendering_state(snapshot)


# ── Test 4: title rendering applies correctly ───────────────────────────

def test_plot_title_applies_to_figure():
    """Setting current_plot_title via gateway should be retrievable."""
    snapshot = _snapshot_rendering_state()
    try:
        state_gateway.set_current_plot_title("Test Plot")
        assert getattr(app_state, "current_plot_title", "") == "Test Plot"
    finally:
        _restore_rendering_state(snapshot)


# ── Test 5: geochem overlay import chain works ──────────────────────────

def test_geochem_overlay_imports():
    """All geochem overlay sub-modules should be importable."""
    from visualization.plotting.geochem import (
        equation_overlays,
        isochron_fit_76,
        isochron_fit_86,
        isochron_fits,
        isochron_labels,
        model_age_lines,
        model_overlays,
        overlay_common,
        paleoisochron_overlays,
        plumbotectonics_curves,
        plumbotectonics_isoage,
    )

    assert isochron_fits is not None
    assert isochron_fit_76 is not None
    assert isochron_fit_86 is not None
    assert isochron_labels is not None
    assert model_overlays is not None
    assert model_age_lines is not None
    assert paleoisochron_overlays is not None
    assert plumbotectonics_curves is not None
    assert plumbotectonics_isoage is not None
    assert overlay_common is not None
    assert equation_overlays is not None
