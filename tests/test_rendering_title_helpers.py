"""Tests for rendering common title/axis label helper."""

from __future__ import annotations

import matplotlib.pyplot as plt

from core import app_state, state_gateway
from visualization.plotting.rendering.common import title as title_helpers


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
