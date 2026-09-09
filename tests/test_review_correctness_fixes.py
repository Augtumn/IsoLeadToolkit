"""Regression tests for the correctness fixes from the project review."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# ---------------------------------------------------------------- ellipse
def test_confidence_ellipse_axes_match_covariance_eigenvalues() -> None:
    """Semi-axes must be sqrt(eigenvalue)*n_std, not the 2*sqrt(1±rho) recipe.

    With var_x != var_y the old formula mis-sized both axes badly. The
    covariance must stay non-singular: a singular matrix has a theoretical
    minor axis of 0, so the sample estimate is pure BLAS noise (~1e-8) and a
    relative tolerance degenerates into pytest's absolute 1e-12 floor.
    """
    import scipy.stats

    from visualization.selection_overlay import draw_confidence_ellipse

    rng = np.random.default_rng(0)
    cov = np.array([[4.0, 2.0], [2.0, 1.5]])  # anisotropic, det > 0
    samples = rng.multivariate_normal([0.0, 0.0], cov, size=4000)

    fig, ax = plt.subplots()
    try:
        ellipse = draw_confidence_ellipse(samples[:, 0], samples[:, 1], ax)
        assert ellipse is not None

        n_std = np.sqrt(scipy.stats.chi2.ppf(0.95, df=2))
        eigenvalues = np.sort(np.linalg.eigvalsh(cov))[::-1]
        expected_major = 2.0 * np.sqrt(eigenvalues[0]) * n_std
        expected_minor = 2.0 * np.sqrt(eigenvalues[1]) * n_std

        assert ellipse.width == pytest.approx(expected_major, rel=0.05)
        assert ellipse.height == pytest.approx(expected_minor, rel=0.05)
        # Orientation follows the major eigenvector (mod 180 degrees).
        evals, evecs = np.linalg.eigh(cov)
        major = evecs[:, int(np.argmax(evals))]
        expected_angle = np.degrees(np.arctan2(major[1], major[0]))
        delta = (ellipse.angle - expected_angle + 90.0) % 180.0 - 90.0
        assert abs(delta) < 5.0, (ellipse.angle, expected_angle)
    finally:
        plt.close(fig)


def test_confidence_ellipse_handles_singular_covariance() -> None:
    """Collinear samples (singular covariance) must degrade gracefully:
    no crash, no negative semi-axes."""
    from visualization.selection_overlay import draw_confidence_ellipse

    x = np.linspace(-1.0, 1.0, 50)
    y = 2.0 * x

    fig, ax = plt.subplots()
    try:
        ellipse = draw_confidence_ellipse(x, y, ax)
        assert ellipse is not None
        assert ellipse.width > 0.0
        assert ellipse.height >= 0.0
    finally:
        plt.close(fig)


# ------------------------------------------------------------- export 208Pb
def test_geochem_export_skips_when_208pb_missing(monkeypatch, caplog) -> None:
    """Missing 208Pb must skip the derived columns, never fabricate a constant."""
    import logging

    from application.use_cases import export_data as export_module

    df = pd.DataFrame({
        "206Pb/204Pb": [18.5, 18.6],
        "207Pb/204Pb": [15.6, 15.7],
    })

    with caplog.at_level(logging.WARNING, logger=export_module.__name__):
        result = export_module._compute_geochem_params(df, "PB_EVOL_86")

    assert result == {}
    assert "missing columns" in caplog.text
    assert "208Pb/204Pb" in caplog.text


def test_geochem_export_uses_real_208pb_when_present(monkeypatch) -> None:
    from application.use_cases import export_data as export_module

    df = pd.DataFrame({
        "206Pb/204Pb": [18.5, 18.6],
        "207Pb/204Pb": [15.6, 15.7],
        "208Pb/204Pb": [38.5, 38.6],
    })

    captured: dict = {}

    def _fake_calc(pb206, pb207, pb208, **kwargs):
        captured["pb208"] = np.asarray(pb208, dtype=float)
        captured["kwargs"] = kwargs
        return {"kappa_model": np.full_like(pb206, 1.0)}

    monkeypatch.setattr("data.geochemistry.calculate_all_parameters", _fake_calc)
    result = export_module._compute_geochem_params(df, "PB_KAPPA_AGE")

    assert "kappa_model" in result
    assert np.allclose(captured["pb208"], [38.5, 38.6])


# ---------------------------------------------------------- PCA diagnostics
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


# ------------------------------------------------------------ legend groups
def test_legend_toggle_uses_available_groups() -> None:
    """Hide/show must operate on the rendered group universe, not current_groups."""
    from core import app_state, state_gateway
    from application.use_cases import selection_interaction

    original_visible = getattr(app_state, "visible_groups", None)
    original_available = list(getattr(app_state, "available_groups", []) or [])
    try:
        state_gateway.sync_available_and_visible_groups(["A", "B", "C"])
        # Hiding A from the full universe keeps B and C visible.
        next_groups = selection_interaction.SelectionInteractionUseCase().next_visible_groups(
            current_visible_groups=None,
            all_groups=list(app_state.available_groups),
            target_group="A",
            target_visible=False,
        )
        assert next_groups == ["B", "C"]
    finally:
        state_gateway.set_visible_groups(original_visible)
        state_gateway.sync_available_and_visible_groups(original_available)



# ------------------------------------------------------- state layer (batch 4)
def test_immediate_save_actions_are_real_actions() -> None:
    """Every immediate-save action name must exist as a dispatch action."""
    import re
    from pathlib import Path

    from core.persistence import IMMEDIATE_SAVE_ACTIONS

    repo_root = Path(__file__).resolve().parents[1]
    handlers = (repo_root / "core" / "state" / "_dispatch_handlers.py").read_text(encoding="utf-8")
    gateway = (repo_root / "core" / "state" / "gateway.py").read_text(encoding="utf-8")
    known = set(re.findall(r'action_type == "([A-Z_]+)"', handlers))
    known |= set(re.findall(r'_dispatch\("([A-Z_]+)"', gateway))
    assert IMMEDIATE_SAVE_ACTIONS <= known, sorted(IMMEDIATE_SAVE_ACTIONS - known)


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


def test_disable_selection_mode_clears_tool() -> None:
    from core import app_state, state_gateway

    original_tool = getattr(app_state, "selection_tool", None)
    try:
        state_gateway.set_selection_mode(True)
        state_gateway.set_selection_tool("rect")
        state_gateway.disable_selection_mode()
        assert app_state.selection_mode is False
        assert app_state.selection_tool is None
    finally:
        state_gateway.set_selection_tool(original_tool)


def test_restore_snapshot_rolls_back_on_bad_value(caplog) -> None:
    """A wrong-typed persisted value must not crash or corrupt the snapshot."""
    import logging

    from core import app_state

    store = app_state.state_store
    before = store.snapshot()
    with caplog.at_level(logging.ERROR, logger="core.state.store"):
        ok = store.restore_snapshot({"plot_dpi": "not-a-number"})
    assert ok is False
    assert "Failed to apply restored snapshot" in caplog.text
    after = store.snapshot()
    assert after["plot_dpi"] == before["plot_dpi"]


def test_confidence_ellipse_uses_tracked_confidence_level() -> None:
    """The 68/95/99% radios write confidence_level; the overlay must read it."""
    import types

    from core import app_state, state_gateway
    from visualization import selection_overlay

    original = float(getattr(app_state, "confidence_level", 0.95))
    captured: dict = {}

    class _Canvas:
        @staticmethod
        def draw_idle():
            return None

    class _StateWrite:
        @staticmethod
        def set_selection_ellipse(_ellipse):
            pass

        @staticmethod
        def set_selection_overlay(_overlay):
            pass

    class _Ax:
        @staticmethod
        def scatter(*_a, **_k):
            return None

        @staticmethod
        def get_xlim():
            return (0.0, 1.0)

        @staticmethod
        def get_ylim():
            return (0.0, 1.0)

        @staticmethod
        def set_xlim(*_a):
            pass

        @staticmethod
        def set_ylim(*_a):
            pass

        @staticmethod
        def add_patch(patch):
            return patch

    def _fake_draw(x, y, ax, confidence=0.95, **kwargs):
        captured["confidence"] = confidence
        return None

    try:
        state_gateway.set_confidence_level(0.99)
        state = types.SimpleNamespace(
            fig=types.SimpleNamespace(canvas=_Canvas()),
            ax=_Ax(),
            render_mode="UMAP",
            selection_overlay=None,
            selection_ellipse=None,
            selected_indices={0, 1, 2, 3},
            sample_coordinates={0: (0.0, 0.0), 1: (1.0, 1.0), 2: (0.5, 0.8), 3: (0.2, 0.3)},
            selection_tool=None,
            show_ellipses=True,
            draw_selection_ellipse=True,
            confidence_level=app_state.confidence_level,
            ellipse_confidence=0.95,
            plot_marker_size=60,
            point_size=60,
        )
        original_draw = selection_overlay.draw_confidence_ellipse
        selection_overlay.draw_confidence_ellipse = _fake_draw
        try:
            selection_overlay.refresh_selection_overlay_state(
                state=state,
                state_write=_StateWrite(),
                notify_selection_ui=lambda: None,
            )
        finally:
            selection_overlay.draw_confidence_ellipse = original_draw
        assert captured.get("confidence") == pytest.approx(0.99)
    finally:
        state_gateway.set_confidence_level(original)
