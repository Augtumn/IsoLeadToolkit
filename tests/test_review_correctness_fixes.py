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

    With var_x != var_y the old formula mis-sized both axes badly.
    """
    import scipy.stats

    from visualization.selection_overlay import draw_confidence_ellipse

    rng = np.random.default_rng(0)
    cov = np.array([[4.0, 2.0], [2.0, 1.0]])  # highly anisotropic
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

    def _fake_calc(pb206, pb207, pb208):
        captured["pb208"] = np.asarray(pb208, dtype=float)
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

