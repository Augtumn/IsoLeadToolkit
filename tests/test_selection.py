"""Selection overlay, tooltip and confidence-ellipse tests."""

import matplotlib.pyplot as plt
import numpy as np
import pytest

from application.use_cases.selection_interaction import SelectionInteractionUseCase
from application.use_cases.tooltip_content import TooltipContentUseCase
from visualization import selection_overlay
from visualization.selection_overlay import draw_confidence_ellipse


def test_draw_confidence_ellipse_filters_nonfinite_points() -> None:
    fig, ax = plt.subplots()
    try:
        ellipse = draw_confidence_ellipse(
            np.array([0.0, 1.0, np.nan, 2.0, 3.0], dtype=float),
            np.array([1.0, 2.0, 3.0, np.inf, 4.0], dtype=float),
            ax,
            edgecolor="#f97316",
        )

        assert ellipse is not None
        assert ellipse in ax.patches
    finally:
        plt.close(fig)


def test_draw_confidence_ellipse_returns_none_for_mismatched_sizes() -> None:
    fig, ax = plt.subplots()
    try:
        ellipse = draw_confidence_ellipse(
            np.array([0.0, 1.0, 2.0], dtype=float),
            np.array([1.0, 2.0], dtype=float),
            ax,
        )

        assert ellipse is None
    finally:
        plt.close(fig)


def test_draw_confidence_ellipse_returns_none_for_zero_variance() -> None:
    fig, ax = plt.subplots()
    try:
        ellipse = draw_confidence_ellipse(
            np.array([1.0, 1.0, 1.0], dtype=float),
            np.array([2.0, 3.0, 4.0], dtype=float),
            ax,
        )

        assert ellipse is None
    finally:
        plt.close(fig)


def test_draw_confidence_ellipse_default_confidence_uses_named_constant(monkeypatch) -> None:
    seen: list[float] = []

    def _fake_ppf(confidence: float, df: int) -> float:
        seen.append(float(confidence))
        return 1.0

    monkeypatch.setattr(selection_overlay.scipy.stats.chi2, "ppf", _fake_ppf)

    fig, ax = plt.subplots()
    try:
        ellipse = draw_confidence_ellipse(
            np.array([0.0, 1.0, 2.0], dtype=float),
            np.array([1.0, 2.0, 3.0], dtype=float),
            ax,
        )

        assert ellipse is not None
        assert seen == [selection_overlay._DEFAULT_ELLIPSE_CONFIDENCE]
    finally:
        plt.close(fig)


def test_selection_rectangle_and_toggle_plan() -> None:
    use_case = SelectionInteractionUseCase()
    coordinates = {
        1: (0.0, 0.0),
        2: (1.0, 1.0),
        3: (3.0, 3.0),
    }

    selected = use_case.rectangle_indices(
        coordinates,
        x_min=-0.1,
        x_max=1.5,
        y_min=-0.1,
        y_max=1.5,
    )
    plan = use_case.plan_toggle({1}, selected)

    assert selected == [1, 2]
    assert plan.action == "add"
    assert plan.indices == [1, 2]


def test_selection_lasso_handles_near_horizontal_edge() -> None:
    use_case = SelectionInteractionUseCase()
    coordinates = {
        1: (0.9, 5e-17),
        2: (3.0, 1.0),
    }
    vertices = [
        (0.0, 0.0),
        (2.0, 1e-16),
        (2.0, 2.0),
        (0.0, 2.0),
    ]

    selected = use_case.lasso_indices(coordinates, vertices)

    # With _RAY_CAST_EPSILON, the near-horizontal edge (dy ≈ 1e-16) is treated
    # as horizontal, so the barely-above point at y=5e-17 is correctly outside.
    assert selected == []


def test_tooltip_content_fallback_to_id() -> None:
    use_case = TooltipContentUseCase()
    row = {"Name": "Demo"}

    text = use_case.build_text(
        row=row,
        df_columns=["Name"],
        sample_idx=42,
        tooltip_columns=["MissingColumn"],
        selected=True,
        selected_status_label="Selected",
    )

    assert "ID: 42" in text
    assert "Selected" in text


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
            )
        finally:
            selection_overlay.draw_confidence_ellipse = original_draw
        assert captured.get("confidence") == pytest.approx(0.99)
    finally:
        state_gateway.set_confidence_level(original)


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
