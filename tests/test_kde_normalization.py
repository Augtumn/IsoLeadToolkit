"""KDE normalization and seaborn common_norm regression tests.

Extreme (tightly-spiked) data used to flatten other groups' curves:
- marginal KDEs shared one y-scale, so a huge density spike dominated
- seaborn's default common_norm=True scaled every group by the global
  maximum density, shrinking all other groups' contours
"""

from __future__ import annotations

import numpy as np

from core import app_state
from visualization.plotting import kde as kde_utils
from visualization.plotting.rendering import kde as kde_helpers
from visualization.plotting.rendering.raw import plot2d


def test_normalize_density_curve_peaks_at_one() -> None:
    curve = np.array([0.0, 2.0, 5.0, 2.0, 0.0])
    out = kde_utils._normalize_density_curve(curve)
    assert np.max(out) == 1.0
    assert np.allclose(out, curve / 5.0)


def test_normalize_density_curve_handles_degenerate_input() -> None:
    assert kde_utils._normalize_density_curve(None) is None
    empty = np.array([])
    assert kde_utils._normalize_density_curve(empty).size == 0
    zeros = np.zeros(4)
    assert np.array_equal(kde_utils._normalize_density_curve(zeros), zeros)
    nan_curve = np.array([np.nan, 1.0])
    out = kde_utils._normalize_density_curve(nan_curve)
    assert out[1] == 1.0  # finite values scaled, NaN preserved


def test_normalize_density_curve_is_idempotent() -> None:
    curve = np.array([0.1, 0.8, 1.0, 0.3])
    once = kde_utils._normalize_density_curve(curve)
    twice = kde_utils._normalize_density_curve(once)
    assert np.allclose(once, twice)


def test_embedding_kde_uses_common_norm_false(monkeypatch) -> None:
    """Groups must be normalized independently (no global-max flattening)."""
    captured: dict = {}

    def _fake_kdeplot(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(kde_helpers, "_resolve_kde_style", lambda target="kde": {
        "color": None, "linewidth": 1.0, "linestyle": "-",
        "alpha": 0.6, "fill": False, "levels": 8,
    })
    monkeypatch.setattr(kde_utils, "sns", type("SNS", (), {"kdeplot": staticmethod(_fake_kdeplot)})())
    monkeypatch.setattr(kde_utils, "lazy_import_seaborn", lambda: None)

    monkeypatch.setattr(app_state, "show_kde", True)
    monkeypatch.setattr(kde_helpers, "ensure_line_style", lambda _s, _k, fb: fb)
    monkeypatch.setattr(app_state, "ax", type("Ax", (), {})())

    from types import SimpleNamespace

    class _FakeSeries:
        def to_numpy(self, dtype=None, copy=False):
            return np.array([1.0, 2.0, 3.0])

    df_plot = SimpleNamespace(
        __getitem__=lambda self, key: _FakeSeries(),
    )

    kde_helpers._render_kde_overlay("UMAP", df_plot, "g", ["A"], {"A": "#ff0000"})

    assert captured.get("common_norm") is False, captured.keys()


def test_2d_kde_uses_common_norm_false(monkeypatch) -> None:
    captured: dict = {}

    def _fake_kdeplot(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(kde_utils, "sns", type("SNS", (), {"kdeplot": staticmethod(_fake_kdeplot)})())
    monkeypatch.setattr(kde_utils, "lazy_import_seaborn", lambda: None)
    monkeypatch.setattr(plot2d.kde_utils, "sns", type("SNS", (), {"kdeplot": staticmethod(_fake_kdeplot)})())
    monkeypatch.setattr(plot2d.kde_utils, "lazy_import_seaborn", lambda: None)
    monkeypatch.setattr(plot2d, "_resolve_kde_style", lambda target="kde": {
        "color": None, "linewidth": 1.0, "linestyle": "-",
        "alpha": 0.6, "fill": False, "levels": 8,
    })

    from types import SimpleNamespace

    df_plot = SimpleNamespace()
    monkeypatch.setattr(app_state, "current_palette", {"A": "#ff0000"})
    monkeypatch.setattr(app_state, "ax", type("Ax", (), {})())

    plot2d._render_2d_kde(df_plot, "g", ["Pb206", "Pb207"])

    assert captured.get("common_norm") is False, captured.keys()
