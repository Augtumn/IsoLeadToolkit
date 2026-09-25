"""Geochemistry overlay helpers (model curves, isochrons, equations, plumbotectonics)."""

import matplotlib.pyplot as plt
import numpy as np
import pytest

from core import app_state, state_gateway
from core.legend_state import DEFAULT_LEGEND_FRAME_ALPHA, LegendState
from core.overlay_state import OverlayState
from visualization.plotting.geochem import (
    isochron_fits,
    model_age_lines,
    model_overlays,
    overlay_common,
    paleoisochron_overlays,
    plumbotectonics_isoage,
    plumbotectonics_metadata as metadata,
    selected_isochron_overlay,
)
from visualization.plotting.geochem.equation_overlays import _safe_eval_expression
from visualization.plotting.geochem.isochron_labels import _build_isochron_label
from visualization.plotting.geochem.plumbotectonics_curves import (
    _fit_plumbotectonics_curve,
)
from visualization.plotting.styling.overlays import (
    refresh_overlay_styles,
    refresh_overlay_visibility,
)


def test_safe_eval_expression_supports_basic_arithmetic_and_where() -> None:
    x_vals = np.array([-2.0, -1.0, 0.0, 1.0, 2.0], dtype=float)

    linear = _safe_eval_expression("x * 2 + 1", x_vals)
    conditional = _safe_eval_expression("where(x > 0, x, -x)", x_vals)

    np.testing.assert_allclose(linear, np.array([-3.0, -1.0, 1.0, 3.0, 5.0], dtype=float), rtol=0.0, atol=1e-12)
    np.testing.assert_allclose(conditional, np.array([2.0, 1.0, -0.0, 1.0, 2.0], dtype=float), rtol=0.0, atol=1e-12)


def test_safe_eval_expression_rejects_unknown_symbols() -> None:
    x_vals = np.array([1.0, 2.0], dtype=float)

    with pytest.raises(ValueError):
        _safe_eval_expression("y + 1", x_vals)

    with pytest.raises(ValueError):
        _safe_eval_expression("__import__('os').system('echo bad')", x_vals)


class _FakeModelGeochemistry:
    class engine:
        @staticmethod
        def get_parameters() -> dict[str, float]:
            return {"Tsec": 0.0, "T2": 1_000_000.0}

    @staticmethod
    def calculate_modelcurve(_t_vals, params=None, T1=None):
        _ = params, T1
        return {
            "Pb206_204": np.array([1.0, 2.0, 3.0], dtype=float),
            "Pb207_204": np.array([4.0, 5.0, 6.0], dtype=float),
            "Pb208_204": np.array([7.0, 8.0, 9.0], dtype=float),
        }


class _FakePaleoGeochemistry:
    @staticmethod
    def calculate_paleoisochron_line(_age, params=None, algorithm=None):
        _ = params, algorithm
        return (0.5, 1.0)


def _snapshot_state() -> dict[str, object]:
    keys = [
        "selected_isochron_data",
        "overlay_curve_label_data",
        "paleoisochron_label_data",
        "plumbotectonics_isoage_label_data",
        "line_styles",
    ]
    return {key: getattr(app_state, key, None) for key in keys}


def _restore_state(snapshot: dict[str, object]) -> None:
    for key, value in snapshot.items():
        setattr(app_state, key, value)


def test_draw_isochron_overlays_no_geochemistry_is_noop(monkeypatch) -> None:
    fig, ax = plt.subplots()
    try:
        monkeypatch.setattr(isochron_fits, "_lazy_import_geochemistry", lambda: (None, None))

        isochron_fits._draw_isochron_overlays(ax, "PB_EVOL_76")

        assert len(ax.lines) == 0
    finally:
        plt.close(fig)


def test_draw_model_curves_renders_curve_line(monkeypatch) -> None:
    snapshot = _snapshot_state()
    fig, ax = plt.subplots()
    try:
        setattr(app_state, "overlay_curve_label_data", [])
        monkeypatch.setattr(model_overlays, "_lazy_import_geochemistry", lambda: (_FakeModelGeochemistry(), None))
        monkeypatch.setattr(model_overlays, "position_curve_label", lambda *args, **kwargs: None)

        model_overlays._draw_model_curves(ax, "PB_EVOL_76", [{"Tsec": 0.0, "T2": 1_000_000.0}])

        assert len(ax.lines) >= 1
    finally:
        plt.close(fig)
        _restore_state(snapshot)


def test_draw_mu_kappa_paleoisochrons_ignores_invalid_ages() -> None:
    fig, ax = plt.subplots()
    try:
        model_overlays._draw_mu_kappa_paleoisochrons(ax, [100.0, "invalid", np.nan])

        assert len(ax.lines) == 1
    finally:
        plt.close(fig)


def test_draw_paleoisochrons_draws_line_and_label_data(monkeypatch) -> None:
    snapshot = _snapshot_state()
    fig, ax = plt.subplots()
    try:
        monkeypatch.setattr(paleoisochron_overlays, "_lazy_import_geochemistry", lambda: (_FakePaleoGeochemistry(), None))
        monkeypatch.setattr(paleoisochron_overlays, "position_curve_label", lambda *args, **kwargs: None)

        paleoisochron_overlays._draw_paleoisochrons(ax, "PB_EVOL_76", [100.0], {"Tsec": 0.0})

        assert len(ax.lines) == 1
        assert len(getattr(app_state, "paleoisochron_label_data", [])) == 1
    finally:
        plt.close(fig)
        _restore_state(snapshot)


def test_draw_plumbotectonics_isoage_lines_draws_multiple_lines(monkeypatch) -> None:
    snapshot = _snapshot_state()
    fig, ax = plt.subplots()
    try:
        section = {
            "groups": [
                {"t": [0.1, 0.2], "pb206": [1.0, 2.0], "pb207": [3.0, 4.0]},
                {"t": [0.1, 0.2], "pb206": [1.5, 2.5], "pb207": [3.5, 4.5]},
            ]
        }
        monkeypatch.setattr(plumbotectonics_isoage, "_load_plumbotectonics_data", lambda: {"stub": section})
        monkeypatch.setattr(plumbotectonics_isoage, "_select_plumbotectonics_section", lambda _sections: section)
        monkeypatch.setattr(plumbotectonics_isoage, "position_curve_label", lambda *args, **kwargs: None)

        plumbotectonics_isoage._draw_plumbotectonics_isoage_lines(ax, "PLUMBOTECTONICS_76")

        assert len(ax.lines) == 2
        assert len(getattr(app_state, "plumbotectonics_isoage_label_data", [])) == 2
    finally:
        plt.close(fig)
        _restore_state(snapshot)


def test_draw_selected_isochron_renders_highlight() -> None:
    snapshot = _snapshot_state()
    fig, ax = plt.subplots()
    try:
        setattr(
            app_state,
            "selected_isochron_data",
            {
                "x_range": [1.0, 2.0],
                "y_range": [3.0, 4.0],
                "age_ma": 120.0,
                "age_err_2sigma": 8.0,
                "mswd": 1.1,
            },
        )

        selected_isochron_overlay._draw_selected_isochron(ax)

        assert len(ax.lines) == 1
    finally:
        plt.close(fig)
        _restore_state(snapshot)


def test_build_isochron_label_uses_default_age_and_n_points() -> None:
    original_options = dict(getattr(app_state, "isochron_label_options", {}) or {})
    try:
        state_gateway.set_isochron_label_options({})

        label = _build_isochron_label(
            {
                "age": 123.4,
                "n_points": 9,
                "mswd": 1.23,
                "r_squared": 0.98,
            }
        )

        assert label == "123 Ma, n=9"
    finally:
        state_gateway.set_isochron_label_options(original_options)


def test_build_isochron_label_respects_extended_options() -> None:
    original_options = dict(getattr(app_state, "isochron_label_options", {}) or {})
    try:
        state_gateway.set_isochron_label_options(
            {
                "show_age": False,
                "show_n_points": False,
                "show_mswd": True,
                "show_r_squared": True,
                "show_slope": True,
                "show_intercept": True,
            }
        )

        label = _build_isochron_label(
            {
                "age": 500.0,
                "n_points": 12,
                "mswd": 1.234,
                "r_squared": 0.9876,
                "slope": 0.01234,
                "intercept": 15.6789,
            }
        )

        assert label == "MSWD=1.23, R²=0.988, m=0.0123, b=15.6789"
    finally:
        state_gateway.set_isochron_label_options(original_options)


class _FakeGeochemistry:
    @staticmethod
    def calculate_two_stage_age(_pb206, _pb207, params=None):
        return np.array([100.0, np.nan], dtype=float)

    @staticmethod
    def calculate_single_stage_age(_pb206, _pb207, params=None):
        return np.array([200.0, 300.0], dtype=float)


def test_resolve_model_age_single_stage_uses_cdt_and_t2(monkeypatch) -> None:
    monkeypatch.setattr(model_age_lines, "_lazy_import_geochemistry", lambda: (_FakeGeochemistry(), None))

    t_model, t1_override = model_age_lines._resolve_model_age(
        pb206=np.array([1.0, 2.0], dtype=float),
        pb207=np.array([3.0, 4.0], dtype=float),
        params={"Tsec": 0.0, "T2": 4_500_000_000.0, "T1": 4_430_000_000.0},
    )

    np.testing.assert_allclose(t_model, np.array([200.0, 300.0], dtype=float), rtol=0.0, atol=1e-12)
    assert t1_override == 4_500_000_000.0


def test_resolve_model_age_two_stage_prefers_finite_sk_age(monkeypatch) -> None:
    monkeypatch.setattr(model_age_lines, "_lazy_import_geochemistry", lambda: (_FakeGeochemistry(), None))

    t_model, t1_override = model_age_lines._resolve_model_age(
        pb206=np.array([1.0, 2.0], dtype=float),
        pb207=np.array([3.0, 4.0], dtype=float),
        params={"Tsec": 3_700_000_000.0, "T2": 4_500_000_000.0, "T1": 4_430_000_000.0},
    )

    np.testing.assert_allclose(t_model, np.array([100.0, 300.0], dtype=float), rtol=0.0, atol=1e-12)
    assert t1_override == 3_700_000_000.0


def test_format_label_text_supports_age_and_fallback() -> None:
    assert overlay_common._format_label_text("Age={age:.1f}", age=12.34) == "Age=12.3"
    assert overlay_common._format_label_text("Name={name}", name="A") == "Name=A"
    assert overlay_common._format_label_text("Missing={missing}") == "Missing={missing}"
    assert overlay_common._format_label_text(None) is None


def test_label_bbox_uses_defaults_and_custom_edge() -> None:
    assert overlay_common._label_bbox({"label_background": False}) is None

    bbox = overlay_common._label_bbox(
        {
            "label_background": True,
            "label_bg_color": "#ffeecc",
            "label_bg_alpha": 0.6,
        },
        edgecolor="#333333",
    )

    assert bbox == {
        "boxstyle": "round,pad=0.25",
        "facecolor": "#ffeecc",
        "edgecolor": "#333333",
        "alpha": 0.6,
    }


def test_resolve_label_options_ignores_empty_or_none_values() -> None:
    original_line_styles = dict(getattr(app_state, "line_styles", {}) or {})
    try:
        state_gateway.set_line_styles(
            {
                "model_curve": {
                    "label_background": True,
                    "label_bg_alpha": 0.7,
                    "label_bg_color": "",
                    "label_template": None,
                }
            }
        )

        resolved = overlay_common._resolve_label_options(
            "model_curve",
            {
                "label_background": False,
                "label_bg_alpha": 0.5,
                "label_bg_color": "#ffffff",
                "label_template": "Age={age}",
            },
        )

        assert resolved["label_background"] is True
        assert resolved["label_bg_alpha"] == 0.7
        assert resolved["label_bg_color"] == "#ffffff"
        assert resolved["label_template"] == "Age={age}"
    finally:
        state_gateway.set_line_styles(original_line_styles)


def test_overlay_state_clear_artists_resets_runtime_tracking() -> None:
    overlay = OverlayState()
    overlay.overlay_artists = {"curves": ["line_1"]}
    overlay.overlay_curve_label_data = [{"text": "curve"}]
    overlay.paleoisochron_label_data = [{"text": "paleo"}]
    overlay.plumbotectonics_label_data = [{"text": "plumbo"}]
    overlay.plumbotectonics_isoage_label_data = [{"text": "isoage"}]

    overlay.clear_artists()

    assert overlay.overlay_artists == {}
    assert overlay.overlay_curve_label_data == []
    assert overlay.paleoisochron_label_data == []
    assert overlay.plumbotectonics_label_data == []
    assert overlay.plumbotectonics_isoage_label_data == []


def test_overlay_state_init_equation_styles_creates_style_key_entry() -> None:
    overlay = OverlayState()
    overlay.equation_overlays = [
        {
            "id": "eq_custom",
            "label": "y=2x+1",
            "expression": "2*x+1",
            "color": "#0ea5e9",
            "linewidth": 1.6,
            "linestyle": "-.",
            "alpha": 0.72,
        }
    ]

    overlay._init_equation_styles()

    style_key = overlay.equation_overlays[0].get("style_key")
    assert style_key == "equation:eq_custom"
    assert style_key in overlay.line_styles
    assert overlay.line_styles[style_key]["color"] == "#0ea5e9"
    assert overlay.line_styles[style_key]["linewidth"] == 1.6
    assert overlay.line_styles[style_key]["linestyle"] == "-."
    assert overlay.line_styles[style_key]["alpha"] == 0.72


def test_legend_state_defaults_are_stable() -> None:
    legend = LegendState()

    assert legend.legend_position is None
    assert legend.legend_columns == 0
    assert legend.legend_offset == (0.0, 0.0)
    assert legend.legend_location == "outside_left"
    assert legend.legend_display_mode == "inline"
    assert legend.legend_frame_alpha == DEFAULT_LEGEND_FRAME_ALPHA
    assert legend.hidden_groups == set()
    assert legend.legend_to_scatter == {}
    assert legend.legend_update_callback is None


class _DummyArtist:
    def __init__(self) -> None:
        self.color = None
        self.linewidth = None
        self.linestyle = None
        self.alpha = None
        self.visible = True

    def set_color(self, value):
        self.color = value

    def set_linewidth(self, value):
        self.linewidth = value

    def set_linestyle(self, value):
        self.linestyle = value

    def set_alpha(self, value):
        self.alpha = value

    def set_visible(self, value):
        self.visible = bool(value)


class _DummyCanvas:
    def __init__(self) -> None:
        self.draw_calls = 0

    def draw_idle(self) -> None:
        self.draw_calls += 1


class _DummyFigure:
    def __init__(self) -> None:
        self.canvas = _DummyCanvas()


def test_refresh_overlay_styles_updates_artist_properties(monkeypatch) -> None:
    fig = _DummyFigure()
    artist = _DummyArtist()
    group_artist = _DummyArtist()

    monkeypatch.setattr(app_state, "fig", fig, raising=False)
    monkeypatch.setattr(app_state, "ax", object(), raising=False)
    # Registration shape: singular style keys mapped to artist lists, with
    # per-group suffixes for plumbotectonics curves.
    monkeypatch.setattr(
        app_state,
        "overlay_artists",
        {
            "model_curve": [artist],
            "plumbotectonics_curve:grp": {"grp": [group_artist]},
        },
        raising=False,
    )
    monkeypatch.setattr(
        app_state,
        "line_styles",
        {
            "model_curve": {
                "color": "#112233",
                "linewidth": 2.5,
                "linestyle": "--",
                "alpha": 0.4,
            },
            "plumbotectonics_curve": {
                "color": "#445566",
                "linewidth": 3.0,
                "linestyle": ":",
                "alpha": 0.6,
            },
        },
        raising=False,
    )

    refresh_overlay_styles()

    assert artist.color == "#112233"
    assert artist.linewidth == 2.5
    assert artist.linestyle == "--"
    assert artist.alpha == 0.4
    # Per-group style key falls back to the base style entry.
    assert group_artist.color == "#445566"
    assert group_artist.linewidth == 3.0
    assert group_artist.linestyle == ":"
    assert group_artist.alpha == 0.6
    assert fig.canvas.draw_calls == 1


def test_refresh_overlay_visibility_applies_toggle_and_group_visibility(monkeypatch) -> None:
    fig = _DummyFigure()
    model_artist = _DummyArtist()
    group_artist = _DummyArtist()
    label_artist = _DummyArtist()

    monkeypatch.setattr(app_state, "fig", fig, raising=False)
    monkeypatch.setattr(app_state, "ax", object(), raising=False)
    monkeypatch.setattr(
        app_state,
        "overlay_artists",
        {
            "model_curve": [model_artist],
            "plumbotectonics_curve:grp": [group_artist],
        },
        raising=False,
    )
    monkeypatch.setattr(app_state, "show_model_curves", False, raising=False)
    monkeypatch.setattr(app_state, "show_plumbotectonics_curves", True, raising=False)
    monkeypatch.setattr(
        app_state,
        "plumbotectonics_group_visibility",
        {"plumbotectonics_curve:grp": False},
        raising=False,
    )
    monkeypatch.setattr(
        app_state,
        "overlay_curve_label_data",
        [{"text": label_artist, "style_key": "model_curve"}],
        raising=False,
    )
    monkeypatch.setattr(app_state, "paleoisochron_label_data", [], raising=False)
    monkeypatch.setattr(app_state, "plumbotectonics_label_data", [], raising=False)
    monkeypatch.setattr(app_state, "plumbotectonics_isoage_label_data", [], raising=False)

    refresh_overlay_visibility()

    assert model_artist.visible is False
    assert group_artist.visible is False
    assert label_artist.visible is False
    assert fig.canvas.draw_calls == 1


def test_fit_plumbotectonics_curve_handles_duplicates_and_invalid_values() -> None:
    x_vals = [1.0, 2.0, 2.0, np.nan, 4.0]
    y_vals = [10.0, 20.0, 22.0, 30.0, np.inf]

    x_fit, y_fit = _fit_plumbotectonics_curve(x_vals, y_vals, n_points=50)

    assert len(x_fit) == 50
    assert len(y_fit) == 50
    assert np.isfinite(x_fit).all()
    assert np.isfinite(y_fit).all()
    assert np.all(np.diff(x_fit) >= 0)


def test_fit_plumbotectonics_curve_returns_raw_when_insufficient_points() -> None:
    x_fit, y_fit = _fit_plumbotectonics_curve([1.0, np.nan], [2.0, 3.0])

    np.testing.assert_allclose(x_fit, np.array([1.0], dtype=float), rtol=0.0, atol=1e-12)
    np.testing.assert_allclose(y_fit, np.array([2.0], dtype=float), rtol=0.0, atol=1e-12)


def test_get_plumbotectonics_variants_uses_label_and_fallback(monkeypatch) -> None:
    sections = [
        {"label": "Variant A"},
        {"label": ""},
        {},
    ]
    monkeypatch.setattr(metadata, "_load_plumbotectonics_data", lambda: sections)

    assert metadata.get_plumbotectonics_variants() == [
        ("0", "Variant A"),
        ("1", "Model 2"),
        ("2", "Model 3"),
    ]


def test_get_plumbotectonics_group_entries_builds_unique_keys() -> None:
    section = {
        "groups": [
            {"name": "Mantle Arc"},
            {"name": "Mantle Arc"},
            {"name": ""},
        ]
    }

    entries = metadata.get_plumbotectonics_group_entries(section=section)

    assert [item["key"] for item in entries] == ["mantle_arc", "mantle_arc_2", "group_3"]
    assert [item["style_key"] for item in entries] == [
        "plumbotectonics_curve:mantle_arc",
        "plumbotectonics_curve:mantle_arc_2",
        "plumbotectonics_curve:group_3",
    ]


def test_get_plumbotectonics_group_palette_cycles_colors(monkeypatch) -> None:
    section = {
        "groups": [
            {"name": "G1"},
            {"name": "G2"},
            {"name": "G3"},
        ]
    }
    monkeypatch.setattr(metadata, "_overlay_palette", lambda: ["#111111", "#222222"])

    palette = metadata.get_plumbotectonics_group_palette(section=section)

    assert palette == {
        "plumbotectonics_curve:g1": "#111111",
        "plumbotectonics_curve:g2": "#222222",
        "plumbotectonics_curve:g3": "#111111",
    }


def test_get_overlay_default_color_uses_index_map(monkeypatch) -> None:
    monkeypatch.setattr(metadata, "_overlay_palette", lambda: ["#111111", "#222222"])

    assert metadata.get_overlay_default_color("model_curve") == "#111111"
    assert metadata.get_overlay_default_color("paleoisochron") == "#222222"
    assert metadata.get_overlay_default_color("model_age_line") == "#111111"
    assert metadata.get_overlay_default_color("unknown") == "#111111"


def test_plumbotectonics_marker_keyword_mapping() -> None:
    assert metadata._plumbotectonics_marker("Mantle") == "o"
    assert metadata._plumbotectonics_marker("下地壳") == "s"
    assert metadata._plumbotectonics_marker("Upper Crust") == "^"
    assert metadata._plumbotectonics_marker("Orogene belt") == "D"
    assert metadata._plumbotectonics_marker("Other") == "o"
