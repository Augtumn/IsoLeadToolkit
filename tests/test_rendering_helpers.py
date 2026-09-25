"""Unit tests for rendering helpers (geo layers, KDE, legend, scatter, titles, rollback)."""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from core import app_state, state_gateway
from visualization.plotting.rendering import geo_layers, kde as kde_helpers
from visualization.plotting.rendering.common import (
    legend as legend_helpers,
    title as title_helpers,
)
from visualization.plotting.rendering.common.scatter import _render_scatter_groups


class _FakeGeochemistry:
    class engine:
        @staticmethod
        def get_parameters():
            return {"x": 1}


def _snapshot_geo_state() -> dict[str, object]:
    keys = [
        "ax",
        "show_model_curves",
        "show_isochrons",
        "selected_isochron_data",
        "show_paleoisochrons",
        "paleoisochron_ages",
        "show_model_age_lines",
        "show_plumbotectonics_curves",
    ]
    return {key: getattr(app_state, key, None) for key in keys}


def _restore_geo_state(snapshot: dict[str, object]) -> None:
    for key, value in snapshot.items():
        setattr(app_state, key, value)


def test_render_geo_overlays_plumbotectonics_dispatch(monkeypatch) -> None:
    snapshot = _snapshot_geo_state()
    fig, ax = plt.subplots()
    calls: list[str] = []
    try:
        setattr(app_state, "ax", ax)
        setattr(app_state, "show_paleoisochrons", True)
        setattr(app_state, "show_plumbotectonics_curves", True)

        monkeypatch.setattr(geo_layers, "_draw_plumbotectonics_isoage_lines", lambda _ax, _alg: calls.append("isoage"))
        monkeypatch.setattr(geo_layers, "_draw_plumbotectonics_curves", lambda _ax, _alg: calls.append("curves"))
        monkeypatch.setattr(geo_layers, "_draw_equation_overlays", lambda _ax: calls.append("equation"))

        geo_layers._render_geo_overlays(
            actual_algorithm="PLUMBOTECTONICS_76",
            prev_ax=ax,
            prev_embedding_type="PLUMBOTECTONICS_76",
            prev_xlim=ax.get_xlim(),
            prev_ylim=ax.get_ylim(),
        )

        assert calls == ["isoage", "curves", "equation"]
    finally:
        plt.close(fig)
        _restore_geo_state(snapshot)


def test_render_geo_overlays_pb_mu_age_dispatch(monkeypatch) -> None:
    snapshot = _snapshot_geo_state()
    fig, ax = plt.subplots()
    calls: list[str] = []
    try:
        setattr(app_state, "ax", ax)
        setattr(app_state, "show_paleoisochrons", True)
        setattr(app_state, "paleoisochron_ages", [100, 200])

        monkeypatch.setattr(geo_layers, "_lazy_import_geochemistry", lambda: (_FakeGeochemistry(), None))
        monkeypatch.setattr(geo_layers, "_draw_mu_kappa_paleoisochrons", lambda _ax, ages: calls.append(f"mu_kappa:{ages}"))
        monkeypatch.setattr(geo_layers, "_draw_equation_overlays", lambda _ax: calls.append("equation"))

        geo_layers._render_geo_overlays(
            actual_algorithm="PB_MU_AGE",
            prev_ax=ax,
            prev_embedding_type="PB_MU_AGE",
            prev_xlim=ax.get_xlim(),
            prev_ylim=ax.get_ylim(),
        )

        assert calls == ["mu_kappa:[100, 200]", "equation"]
    finally:
        plt.close(fig)
        _restore_geo_state(snapshot)


def test_resolve_kde_style_uses_kde_defaults(monkeypatch) -> None:
    monkeypatch.setattr(kde_helpers, "ensure_line_style", lambda _state, _key, fallback: fallback)

    style = kde_helpers._resolve_kde_style("kde")

    assert style["linewidth"] == 1.0
    assert style["alpha"] == 0.6
    assert style["fill"] is True
    assert style["levels"] == 10
    assert style["linestyle"] == "-"


def test_resolve_kde_style_builds_marginal_defaults(monkeypatch) -> None:
    monkeypatch.setattr(kde_helpers, "ensure_line_style", lambda _state, _key, fallback: fallback)

    style = kde_helpers._resolve_kde_style("marginal")

    assert style["linewidth"] == 1.0
    assert style["alpha"] == 0.25
    assert style["fill"] is True
    assert "levels" not in style


def test_build_legend_proxies_uses_patch_when_any_handle_is_patch(monkeypatch) -> None:
    monkeypatch.setattr(
        legend_helpers,
        "group_legend_items",
        lambda all_groups: [
            {"marker": "o", "color": "#111111"},
            {"marker": "s", "color": "#222222"},
        ],
    )

    handles = [Patch(facecolor="#aaaaaa")]
    labels = ["A", "B"]

    proxies = legend_helpers._build_legend_proxies(handles, labels)

    assert len(proxies) == 2
    assert all(isinstance(item, Patch) for item in proxies)


def test_build_overlay_legend_entries_translates_and_applies_style(monkeypatch) -> None:
    monkeypatch.setattr(
        legend_helpers,
        "overlay_legend_items",
        lambda actual_algorithm: [
            {
                "style_key": "model_curve",
                "fallback": {},
                "default_color": "#333333",
                "label_key": "Model Curve",
            }
        ],
    )
    monkeypatch.setattr(
        legend_helpers,
        "resolve_line_style",
        lambda _state, _key, _fallback: {
            "color": "#ff0000",
            "linewidth": 2.0,
            "linestyle": "--",
            "alpha": 0.5,
        },
    )
    monkeypatch.setattr(legend_helpers, "translate", lambda text: f"T:{text}")

    entries = legend_helpers._build_overlay_legend_entries("PB_EVOL_76")

    assert len(entries) == 1
    handle, label = entries[0]
    assert isinstance(handle, Line2D)
    assert handle.get_color() == "#ff0000"
    assert handle.get_linewidth() == 2.0
    assert handle.get_linestyle() == "--"
    assert handle.get_alpha() == 0.5
    assert label == "T:Model Curve"


def test_async_render_stale_token_ignored():
    """Stale embedding task token should not modify worker state."""
    from core import app_state, state_gateway

    state_gateway.set_embedding_worker("mock_worker", running=True, task_token=999)

    from visualization.events import _on_embedding_task_finished

    _on_embedding_task_finished(
        task_token=1,
        payload={"algorithm": "UMAP", "embedding": np.zeros((3, 2))},
        group_col="Group",
    )

    assert app_state.embedding_task_token == 999
    assert app_state.embedding_task_running is True
    assert app_state.embedding_worker == "mock_worker"


def test_embedding_task_failed_clears_worker(monkeypatch: pytest.MonkeyPatch):
    """Matching token failure should clear worker state.

    The failure path shows a modal QMessageBox; stub it out so the
    offscreen test environment does not block on an unclickable dialog.
    """
    import PyQt5.QtWidgets as QtWidgets

    monkeypatch.setattr(
        QtWidgets.QMessageBox, "warning", staticmethod(lambda *a, **k: None))

    from core import app_state, state_gateway

    state_gateway.set_embedding_worker("mock_worker", running=True, task_token=42)

    from visualization.events import _on_embedding_task_failed

    _on_embedding_task_failed(task_token=42, error_message="Test failure")

    assert app_state.embedding_worker is None
    assert not app_state.embedding_task_running


def test_failed_stale_token_ignored():
    """Failed embedding with stale token should not modify state."""
    from core import app_state, state_gateway

    state_gateway.set_embedding_worker("mock_worker", running=True, task_token=999)

    from visualization.events import _on_embedding_task_failed

    _on_embedding_task_failed(task_token=1, error_message="Old failure")

    assert app_state.embedding_task_token == 999
    assert app_state.embedding_task_running is True


def _snapshot_scatter_state() -> dict[str, object]:
    return {
        "fig": getattr(app_state, "fig", None),
        "ax": getattr(app_state, "ax", None),
        "scatter_collections": list(getattr(app_state, "scatter_collections", []) or []),
        "group_to_scatter": dict(getattr(app_state, "group_to_scatter", {}) or {}),
        "sample_index_map": dict(getattr(app_state, "sample_index_map", {}) or {}),
        "sample_coordinates": dict(getattr(app_state, "sample_coordinates", {}) or {}),
        "artist_to_sample": dict(getattr(app_state, "artist_to_sample", {}) or {}),
        "show_kde": getattr(app_state, "show_kde", False),
        "group_marker_map": dict(getattr(app_state, "group_marker_map", {}) or {}),
    }


def _restore_scatter_state(snapshot: dict[str, object]) -> None:
    setattr(app_state, "fig", snapshot.get("fig"))
    setattr(app_state, "ax", snapshot.get("ax"))
    setattr(app_state, "scatter_collections", list(snapshot.get("scatter_collections", []) or []))
    setattr(app_state, "group_to_scatter", dict(snapshot.get("group_to_scatter", {}) or {}))
    setattr(app_state, "sample_index_map", dict(snapshot.get("sample_index_map", {}) or {}))
    setattr(app_state, "sample_coordinates", dict(snapshot.get("sample_coordinates", {}) or {}))
    setattr(app_state, "artist_to_sample", dict(snapshot.get("artist_to_sample", {}) or {}))
    setattr(app_state, "show_kde", bool(snapshot.get("show_kde", False)))
    setattr(app_state, "group_marker_map", dict(snapshot.get("group_marker_map", {}) or {}))


def test_render_scatter_groups_2d_builds_point_mappings() -> None:
    snapshot = _snapshot_scatter_state()
    fig, ax = plt.subplots()
    try:
        setattr(app_state, "fig", fig)
        setattr(app_state, "ax", ax)
        setattr(app_state, "scatter_collections", [])
        setattr(app_state, "group_to_scatter", {})
        setattr(app_state, "sample_index_map", {})
        setattr(app_state, "sample_coordinates", {})
        setattr(app_state, "artist_to_sample", {})
        setattr(app_state, "show_kde", False)
        setattr(app_state, "group_marker_map", {})

        df_plot = pd.DataFrame(
            {
                "group": ["A", "A"],
                "_emb_x": [1.0, 2.0],
                "_emb_y": [3.0, 4.0],
            },
            index=[10, 11],
        )

        scatters = _render_scatter_groups(
            actual_algorithm="UMAP",
            df_plot=df_plot,
            group_col="group",
            unique_cats=["A"],
            size=30.0,
            palette={"A": "#ff0000"},
        )

        assert scatters is not None
        assert len(scatters) == 1
        assert len(getattr(app_state, "scatter_collections", [])) == 1
        assert "A" in getattr(app_state, "group_to_scatter", {})
        assert getattr(app_state, "sample_coordinates", {}).get(10) == (1.0, 3.0)
        assert getattr(app_state, "sample_coordinates", {}).get(11) == (2.0, 4.0)
        assert len(getattr(app_state, "artist_to_sample", {})) == 2
    finally:
        plt.close(fig)
        _restore_scatter_state(snapshot)


def _snapshot_title_state() -> dict[str, object]:
    return {
        "fig": getattr(app_state, "fig", None),
        "ax": getattr(app_state, "ax", None),
        "show_plot_title": getattr(app_state, "show_plot_title", True),
        "pca_component_indices": getattr(app_state, "pca_component_indices", (0, 1)),
        "title_pad": getattr(app_state, "title_pad", 20.0),
    }


def _restore_title_state(snapshot: dict[str, object]) -> None:
    setattr(app_state, "fig", snapshot.get("fig"))
    setattr(app_state, "ax", snapshot.get("ax"))
    state_gateway.set_show_plot_title(bool(snapshot.get("show_plot_title", True)))
    state_gateway.set_pca_component_indices(snapshot.get("pca_component_indices", (0, 1)))
    setattr(app_state, "title_pad", snapshot.get("title_pad", 20.0))


def test_render_title_labels_sets_pca_axis_labels(monkeypatch) -> None:
    snapshot = _snapshot_title_state()
    fig, ax = plt.subplots()
    try:
        setattr(app_state, "fig", fig)
        setattr(app_state, "ax", ax)
        state_gateway.set_show_plot_title(True)
        state_gateway.set_pca_component_indices((0, 2))
        monkeypatch.setattr(title_helpers, "_active_subset_indices", lambda: None)
        monkeypatch.setattr(title_helpers, "_apply_axis_text_style", lambda _ax: None)

        title_helpers._render_title_labels(
            actual_algorithm="PCA",
            group_col="Group",
            umap_params={"n_neighbors": 15, "min_dist": 0.1},
            tsne_params={"perplexity": 30, "learning_rate": 200},
            pca_params={"n_components": 3},
            robust_pca_params={"n_components": 2},
        )

        assert "Embedding - PCA" in getattr(app_state, "current_plot_title", "")
        assert ax.get_xlabel() == "PC1"
        assert ax.get_ylabel() == "PC3"
    finally:
        plt.close(fig)
        _restore_title_state(snapshot)


def test_render_title_labels_includes_subset_tag_for_geochem_mode(monkeypatch) -> None:
    snapshot = _snapshot_title_state()
    fig, ax = plt.subplots()
    try:
        setattr(app_state, "fig", fig)
        setattr(app_state, "ax", ax)
        state_gateway.set_show_plot_title(True)
        monkeypatch.setattr(title_helpers, "_active_subset_indices", lambda: {0, 1})
        monkeypatch.setattr(title_helpers, "_apply_axis_text_style", lambda _ax: None)

        title_helpers._render_title_labels(
            actual_algorithm="PB_EVOL_76",
            group_col="Group",
            umap_params={"n_neighbors": 15, "min_dist": 0.1},
            tsne_params={"perplexity": 30, "learning_rate": 200},
            pca_params={"n_components": 2},
            robust_pca_params={"n_components": 2},
        )

        assert "(Subset)" in getattr(app_state, "current_plot_title", "")
        assert ax.get_xlabel() == "206Pb/204Pb"
        assert ax.get_ylabel() == "207Pb/204Pb"
    finally:
        plt.close(fig)
        _restore_title_state(snapshot)
