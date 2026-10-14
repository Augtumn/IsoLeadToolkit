"""Rendering pipeline behaviour tests (dispatch, rollback, embedding diagnostics, event sync)."""

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from core import app_state, state_gateway
from visualization import events


# ── State snapshot helpers (follow existing test conventions) ──────────


def _snapshot_rendering_state() -> dict[str, object]:
    keys = [
        "fig", "ax", "df_global", "file_path", "sheet_name",
        "group_cols", "data_cols", "algorithm", "render_mode",
        "umap_params", "current_plot_title", "scatter_collections",
        "data_version", "last_embedding", "last_embedding_type",
    ]
    snapshot = {key: getattr(app_state, key, None) for key in keys}
    # The legend's visibility selection is state the render paths read; leaving it out of
    # the snapshot let one test's selection leak into the next.
    snapshot["visible_groups"] = getattr(app_state, "visible_groups", None)
    snapshot["available_groups"] = list(getattr(app_state, "available_groups", None) or [])
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
    state_gateway.sync_available_and_visible_groups(list(snapshot.get("available_groups") or []))
    state_gateway.set_visible_groups(snapshot.get("visible_groups"))
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


def test_sync_render_mode_updates_state() -> None:
    original_mode = getattr(app_state, "render_mode", "2D")
    try:
        state_gateway.set_render_mode("2D")

        events._sync_render_mode("PCA")

        assert app_state.render_mode == "PCA"
    finally:
        state_gateway.set_render_mode(str(original_mode))


def test_sync_render_mode_noop_when_mode_unchanged() -> None:
    original_mode = getattr(app_state, "render_mode", "2D")
    try:
        state_gateway.set_render_mode("2D")

        events._sync_render_mode("2D")

        assert app_state.render_mode == "2D"
    finally:
        state_gateway.set_render_mode(str(original_mode))


def test_precomputed_embedding_with_empty_meta_keeps_pca_diagnostics() -> None:
    """Cache-hit renders must not wipe last_pca_variance/components."""
    from core import app_state, state_gateway
    from visualization.plotting.rendering.embedding import compute_ml

    original = (
        getattr(app_state, "last_pca_variance", None),
        getattr(app_state, "last_pca_components", None),
        list(getattr(app_state, "current_feature_names", []) or []),
    )
    try:
        state_gateway.set_pca_diagnostics(
            last_pca_variance=[0.5, 0.3],
            last_pca_components=[[1.0, 0.0], [0.0, 1.0]],
            current_feature_names=["a", "b"],
        )
        compute_ml.apply_precomputed_embedding(
            "PCA", np.array([[0.0, 0.0], [1.0, 1.0]]), {}
        )
        assert list(app_state.last_pca_variance) == [0.5, 0.3]
        assert list(app_state.current_feature_names) == ["a", "b"]
    finally:
        state_gateway.set_pca_diagnostics(
            last_pca_variance=original[0],
            last_pca_components=original[1],
            current_feature_names=original[2],
        )


def test_precomputed_embedding_with_meta_updates_diagnostics() -> None:
    from core import app_state, state_gateway
    from visualization.plotting.rendering.embedding import compute_ml

    original = (
        getattr(app_state, "last_pca_variance", None),
        getattr(app_state, "last_pca_components", None),
        list(getattr(app_state, "current_feature_names", []) or []),
    )
    try:
        compute_ml.apply_precomputed_embedding(
            "PCA",
            np.array([[0.0, 0.0], [1.0, 1.0]]),
            {"last_pca_variance": [0.9, 0.1]},
        )
        assert list(app_state.last_pca_variance) == [0.9, 0.1]
    finally:
        state_gateway.set_pca_diagnostics(
            last_pca_variance=original[0],
            last_pca_components=original[1],
            current_feature_names=original[2],
        )


def test_set_algorithm_updates_render_mode() -> None:
    """set_algorithm must not be a silent no-op in embedding modes."""
    from core import app_state, state_gateway

    original = (
        state_gateway.snapshot()["render_mode"],
        state_gateway.snapshot()["algorithm"],
    )
    try:
        state_gateway.set_algorithm("PCA")
        assert app_state.algorithm == "PCA"
        assert app_state.render_mode == "PCA"
        state_gateway.set_render_mode("UMAP")
        state_gateway.set_algorithm("tSNE")
        assert app_state.render_mode == "tSNE"
    finally:
        state_gateway.set_render_mode(original[0])


# ── legend visibility across render modes ────────────────────────────────
#
# Reported as "切换渲染模式后，不应该刷新图例可见性": the visibility selection belongs to
# the user, and a render (including the one a mode switch triggers) must neither rewrite it
# nor ignore it.


def test_the_3d_render_honours_the_legend_visibility_filter() -> None:
    """3D used to ignore ``visible_groups``, so switching to it redrew hidden groups."""
    from visualization.plotting import plot_3d_data

    snapshot = _snapshot_rendering_state()
    fig = plt.figure()
    ax = fig.add_subplot(111)
    try:
        state_gateway.set_figure_axes(fig, ax)
        state_gateway.set_dataframe_and_source(
            _make_test_df(n_samples=12, n_groups=3), file_path=None, sheet_name=None
        )
        state_gateway.set_group_data_columns(
            ["Group"], ["Pb206_204", "Pb207_204", "Pb208_204"]
        )
        state_gateway.set_last_group_col("Group")
        state_gateway.set_visible_groups(["A"])

        assert plot_3d_data(
            "Group", ["Pb206_204", "Pb207_204", "Pb208_204"], size=30
        ) is True

        drawn = {scatter.get_label() for scatter in app_state.scatter_collections}
        assert drawn == {"A"}, f"3D drew {sorted(drawn)} although only A is visible"
        assert app_state.visible_groups == ["A"]
    finally:
        plt.close("all")
        _restore_rendering_state(snapshot)


def test_a_2d_render_keeps_a_visibility_selection_it_cannot_draw() -> None:
    """The renderer filters by the selection; it never rewrites it.

    Group ``A`` has no complete row in the two plotted columns, so the 2D projection cannot
    draw it. The old behaviour re-ticked every group in the legend (``visible_groups`` ->
    None) and, when the failure path ran, silently fell back to UMAP - so one mode switch
    changed both the plot and the legend. Now the frame stays empty and the selection stays.
    """
    from visualization.plotting import plot_2d_data

    snapshot = _snapshot_rendering_state()
    fig = plt.figure()
    ax = fig.add_subplot(111)
    try:
        state_gateway.set_figure_axes(fig, ax)
        frame = pd.DataFrame(
            {
                "Pb206_204": [18.1, 18.2, 18.3, 18.4],
                "Pb207_204": [np.nan, np.nan, 15.6, 15.7],
                "Group": ["A", "A", "B", "B"],
            }
        )
        state_gateway.set_dataframe_and_source(frame, file_path=None, sheet_name=None)
        state_gateway.set_group_data_columns(["Group"], ["Pb206_204", "Pb207_204"])
        state_gateway.set_last_group_col("Group")
        state_gateway.set_render_mode("2D")
        state_gateway.set_visible_groups(["A"])

        assert plot_2d_data("Group", ["Pb206_204", "Pb207_204"], size=30) is True

        assert not app_state.scatter_collections, "nothing visible must draw nothing"
        assert app_state.visible_groups == ["A"], "the selection must survive the render"
        assert app_state.render_mode == "2D", "no silent fall back to another mode"
    finally:
        plt.close("all")
        _restore_rendering_state(snapshot)


def test_an_empty_visibility_selection_draws_nothing_and_stays_empty() -> None:
    """Unticking every group is allowed: the frame is empty and no group is re-ticked.

    An empty selection used to normalise to "no filter", so the state could not express it
    and the plot showed everything again. It is now a real state - the legend can reach it,
    and the render answers with an empty frame instead of resurrecting the groups.
    """
    from visualization.plotting import plot_2d_data

    snapshot = _snapshot_rendering_state()
    fig = plt.figure()
    ax = fig.add_subplot(111)
    try:
        state_gateway.set_figure_axes(fig, ax)
        state_gateway.set_dataframe_and_source(
            _make_test_df(n_samples=9, n_groups=3), file_path=None, sheet_name=None
        )
        state_gateway.set_group_data_columns(["Group"], ["Pb206_204", "Pb207_204"])
        state_gateway.set_last_group_col("Group")
        # The render use case syncs the data's groups before rendering; do the same here so
        # the assertion does not depend on groups left behind by another test.
        state_gateway.sync_available_and_visible_groups(["A", "B", "C"])
        state_gateway.set_render_mode("2D")
        state_gateway.set_visible_groups([])

        assert plot_2d_data("Group", ["Pb206_204", "Pb207_204"], size=30) is True

        assert not app_state.scatter_collections, "nothing visible must draw nothing"
        assert app_state.visible_groups == [], "the empty selection must survive"
        assert app_state.available_groups, "the data's groups stay available to tick again"
        assert app_state.render_mode == "2D"
    finally:
        plt.close("all")
        _restore_rendering_state(snapshot)
