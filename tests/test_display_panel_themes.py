"""Display-panel regression tests against the real panel.

These replace the earlier "universal stub" tests: ``_Panel(themes.DisplayThemeMixin)``
with ``__getattr__`` returning ``None`` for every unknown attribute made the missing
widget attributes look fine, so theme save really raised AttributeError and theme load
aborted half way - both inside a Qt slot, which aborts the process instead of raising.
The panel is built offscreen here and the theme round trip goes through its own widgets.
"""
from __future__ import annotations

import json

import matplotlib
import numpy as np
import pandas as pd
import pytest

pytest.importorskip("PyQt5")

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from PyQt5.QtWidgets import QApplication, QMessageBox, QSpinBox  # noqa: E402

from core import app_state, state_gateway, translate  # noqa: E402
from ui.panels import DisplayPanel  # noqa: E402

_APP = QApplication.instance() or QApplication([])


# The static message boxes are modal: clicking through them is not possible here and
# offscreen they abort the process, so every path that reports to the user is stubbed.
@pytest.fixture(autouse=True)
def _quiet_message_boxes(monkeypatch):
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: QMessageBox.Ok))
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: QMessageBox.Ok))
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.Yes))


@pytest.fixture()
def panel():
    instance = DisplayPanel(callback=lambda: None, parent=None)
    instance.reset_state()
    instance._built_widget = instance.build()  # keep the widget tree alive
    return instance


@pytest.fixture()
def user_themes_file():
    """The on-disk theme store, restored afterwards.

    ``_refresh_theme_list`` reloads the themes from ``user_themes.json`` and overwrites
    whatever the state holds, so a theme staged in memory never reaches the combo.
    """
    from core import CONFIG

    path = CONFIG["temp_dir"] / "user_themes.json"
    existing = path.read_text(encoding="utf-8") if path.exists() else None
    try:
        yield path
    finally:
        if existing is None:
            path.unlink(missing_ok=True)
        else:
            path.write_text(existing, encoding="utf-8")


def _stage_theme(path, name, fields) -> None:
    stored = {}
    if path.exists():
        stored = json.loads(path.read_text(encoding="utf-8")) or {}
    stored[name] = fields
    path.write_text(json.dumps(stored, ensure_ascii=False, indent=2), encoding="utf-8")


@pytest.fixture(autouse=True)
def _restore_display_state():
    """Snapshot and restore the display state these tests move around."""
    snapshot = {
        "saved_themes": dict(app_state.saved_themes or {}),
        "line_styles": {key: dict(value or {}) for key, value in (app_state.line_styles or {}).items()},
        "widths": (
            app_state.model_curve_width,
            app_state.paleoisochron_width,
            app_state.model_age_line_width,
            app_state.isochron_line_width,
        ),
        "legend_frame_on": app_state.legend_frame_on,
        "legend_frame_alpha": app_state.legend_frame_alpha,
        "plot_dpi": app_state.plot_dpi,
        "plot_marker_size": app_state.plot_marker_size,
        "kde_bw_method": app_state.kde_bw_method,
        "marginal_kde_gridsize": app_state.marginal_kde_gridsize,
        "ui_theme": app_state.ui_theme,
    }
    yield
    state_gateway.set_saved_themes(snapshot["saved_themes"])
    state_gateway.set_line_styles(snapshot["line_styles"])
    (
        model_curve_width,
        paleoisochron_width,
        model_age_line_width,
        isochron_line_width,
    ) = snapshot["widths"]
    state_gateway.set_model_curve_width(model_curve_width)
    state_gateway.set_paleoisochron_width(paleoisochron_width)
    state_gateway.set_model_age_line_width(model_age_line_width)
    state_gateway.set_isochron_line_width(isochron_line_width)
    state_gateway.set_legend_frame_on(snapshot["legend_frame_on"])
    state_gateway.set_legend_frame_alpha(snapshot["legend_frame_alpha"])
    state_gateway.set_plot_dpi(snapshot["plot_dpi"])
    state_gateway.set_point_size(snapshot["plot_marker_size"])
    state_gateway.set_kde_compute_options(bw_method=snapshot["kde_bw_method"])
    state_gateway.set_marginal_kde_compute_options(gridsize=snapshot["marginal_kde_gridsize"])
    state_gateway.set_ui_theme(snapshot["ui_theme"])


# ---- A1 / A2: theme save and load on the real panel ------------------------

def test_theme_save_writes_every_field_the_panel_persists(panel) -> None:
    """A1: saving raised AttributeError on six attributes the panel never built."""
    state_gateway.set_model_curve_width(2.25)
    state_gateway.set_legend_frame_alpha(0.5)
    panel.theme_name_edit.setText("round_trip")

    panel._save_theme()

    saved = app_state.saved_themes.get("round_trip")
    assert saved is not None, "the theme was not stored"
    assert saved["model_curve_width"] == pytest.approx(2.25)
    assert saved["legend_frame_alpha"] == pytest.approx(0.5)
    for key in (
        "model_curve_width",
        "paleoisochron_width",
        "model_age_line_width",
        "isochron_line_width",
        "legend_frame_on",
        "legend_frame_alpha",
    ):
        assert key in saved, f"{key} missing from the saved theme"


def test_theme_load_applies_the_saved_values_to_state(panel, user_themes_file) -> None:
    """A2: loading raised on the same six attributes after a partial apply."""
    _stage_theme(user_themes_file, "load_me", {
        "model_curve_width": 3.5,
        "paleoisochron_width": 1.25,
        "model_age_line_width": 2.0,
        "isochron_line_width": 0.75,
        "legend_frame_on": False,
        "legend_frame_alpha": 0.4,
    })
    panel._refresh_theme_list()

    panel.theme_load_combo.setCurrentText("load_me")
    assert panel.theme_load_combo.currentText() == "load_me", "the theme was not selected"
    panel._load_theme()

    assert app_state.model_curve_width == pytest.approx(3.5)
    assert app_state.paleoisochron_width == pytest.approx(1.25)
    assert app_state.model_age_line_width == pytest.approx(2.0)
    assert app_state.isochron_line_width == pytest.approx(0.75)
    assert app_state.legend_frame_on is False
    assert app_state.legend_frame_alpha == pytest.approx(0.4)
    assert app_state.saved_themes["load_me"]["model_curve_width"] == pytest.approx(3.5)


def test_theme_round_trip_restores_the_saved_values(panel) -> None:
    """Save then load must move the live state, not only the stored dictionary."""
    state_gateway.set_model_curve_width(1.75)
    state_gateway.set_paleoisochron_width(1.1)
    panel.theme_name_edit.setText("round_trip_state")
    panel._save_theme()

    state_gateway.set_model_curve_width(0.3)
    state_gateway.set_paleoisochron_width(0.3)
    panel.theme_load_combo.setCurrentText("round_trip_state")
    panel._load_theme()

    assert app_state.model_curve_width == pytest.approx(1.75)
    assert app_state.paleoisochron_width == pytest.approx(1.1)


def test_theme_load_still_reaches_the_final_style_change(panel, user_themes_file, monkeypatch) -> None:
    """A2: the trailing ``_on_style_change()`` must still run after a load."""
    calls: list[str] = []
    monkeypatch.setattr(panel, "_on_style_change", lambda *a, **k: calls.append("style"))

    _stage_theme(user_themes_file, "final_style", {"grid": True})
    panel._refresh_theme_list()
    # Selecting the entry fires _load_theme through the combo signal; record only the
    # explicit call so the assertion is about the load path itself.
    panel.theme_load_combo.blockSignals(True)
    panel.theme_load_combo.setCurrentText("final_style")
    panel.theme_load_combo.blockSignals(False)
    calls.clear()

    panel._load_theme()

    assert calls == ["style"], "the load path returned before the final style commit"

    assert calls == ["style"], "the load path returned before the final style commit"


# ---- A3: findChildren must stay callable ----------------------------------

def test_find_children_stays_callable_on_the_panel(panel) -> None:
    """A3: declaring ``findChildren`` on the mixin shadowed QWidget.findChildren."""
    assert callable(panel.findChildren)
    assert DisplayPanel.findChildren is not None, "the mixin shadowed QWidget.findChildren"
    assert panel._built_widget.findChildren(QSpinBox), "the widget tree came back empty"


def test_update_translations_returns_for_the_real_panel(panel) -> None:
    """A3: the TypeError here aborted the main window's per-panel translation loop."""
    panel._update_translations()


# ---- A4: the restored UI theme is applied at build time -------------------

def test_build_applies_the_restored_ui_theme(panel, monkeypatch) -> None:
    """A4: setStyleSheet / plt.style.use were reachable only from the combo signal."""
    from ui.panels.display import themes

    applied: list[str] = []
    original = themes.DisplayThemeMixin._apply_ui_theme

    mpl_flags: list[bool] = []

    def _record(self, theme_name, refresh=True, apply_mpl=True):
        applied.append(theme_name)
        mpl_flags.append(apply_mpl)
        return original(self, theme_name, refresh=refresh, apply_mpl=apply_mpl)

    monkeypatch.setattr(themes.DisplayThemeMixin, "_apply_ui_theme", _record)
    state_gateway.set_ui_theme("Modern Dark")

    fresh = DisplayPanel(callback=lambda: None, parent=None)
    fresh.reset_state()
    fresh._built_widget = fresh.build()

    assert applied == ["Modern Dark"], f"build did not apply the restored theme: {applied}"
    assert fresh.ui_theme_combo.currentText() == "Modern Dark"
    # The Qt stylesheet belongs at build time; plt.style.use does not. It resets matplotlib's global
    # rcParams, and doing that while the window is assembled stretched the ternary triangle and gave
    # it a grid, so the build-time call must opt out of it.
    assert mpl_flags == [False], f"build must not reset matplotlib's global style: {mpl_flags}"


def test_apply_ui_theme_installs_the_stylesheet(panel) -> None:
    """The application itself, not only the combo text: QSS and the mpl style change.

    ``_apply_ui_theme`` is the only place in the suite that drives the real theme application, and
    it writes two globals: the app stylesheet and, through ``plt.style.use``, matplotlib's rcParams.
    Both are restored here, because anything this test leaves behind leaks into every later test in
    the session.  "Modern Dark" carries ``dark_background``: a white ``axes.edgecolor``/``text.color``
    on a white figure renders no dark pixel at all, so ``tests/test_ternary_rendered_geometry.py``
    used to read "the ternary figure drew nothing" in a combined run where it passed alone.
    ``rc_context`` snapshots all of rcParams and puts it back on exit; the stylesheet and the state
    theme are restored by hand.
    """
    previous_qss = _APP.styleSheet()
    previous_theme = app_state.ui_theme
    ambient_edgecolor = matplotlib.rcParams["axes.edgecolor"]
    ambient_text_color = matplotlib.rcParams["text.color"]

    try:
        with matplotlib.rc_context():
            state_gateway.set_ui_theme("Modern Light")
            panel._apply_ui_theme("Modern Light")
            light_qss = _APP.styleSheet()
            light_edgecolor = matplotlib.rcParams["axes.edgecolor"]

            panel._apply_ui_theme("Modern Dark")

            dark_qss = _APP.styleSheet()
            assert dark_qss and dark_qss != light_qss, "no app stylesheet was installed"
            assert "#111827" in dark_qss, "the dark theme palette was not used"
            assert matplotlib.rcParams["axes.edgecolor"] != light_edgecolor, (
                "the matplotlib style did not go through rcParams, so there was nothing to leak"
            )
    finally:
        # A failing assertion above must not leave the dark stylesheet behind for the next test.
        _APP.setStyleSheet(previous_qss)
        state_gateway.set_ui_theme(previous_theme)

    assert _APP.styleSheet() == previous_qss, "the app stylesheet was left on the dark theme"
    assert app_state.ui_theme == previous_theme, "the state theme was left on the dark theme"
    assert matplotlib.rcParams["axes.edgecolor"] == ambient_edgecolor, (
        "rcParams leaked the theme's edge colour into the rest of the session"
    )
    assert matplotlib.rcParams["text.color"] == ambient_text_color, (
        "rcParams leaked the theme's text colour into the rest of the session"
    )


# ---- A5: settings search reaches more than QLabel/QGroupBox ---------------

def test_settings_search_finds_a_checkbox_row(panel) -> None:
    """A5: the search only indexed QLabel/QGroupBox text."""
    toolbox = panel._section_toolbox
    assert toolbox.count() == 4

    panel._on_search_changed(translate("Minor Ticks"))
    kept = [toolbox.itemText(i) for i in range(toolbox.count())]

    assert panel._search_match_label.text() == translate("{n} matches").format(n=1)
    assert len(kept) == 1, f"the checkbox row was not indexed: {kept}"

    panel._on_search_changed("")
    assert toolbox.count() == 4, "clearing the search did not restore the pages"


def test_settings_search_finds_a_combo_item(panel) -> None:
    """A5: combo item texts and button texts are searchable too."""
    toolbox = panel._section_toolbox

    panel._on_search_changed("Scientific Blue")
    assert panel._search_match_label.text() == translate("{n} matches").format(n=1)

    panel._on_search_changed(translate("Save"))
    assert panel._search_match_label.text() == translate("{n} matches").format(n=1)

    panel._on_search_changed("")


def test_settings_search_no_match_hides_and_restores_the_pages(panel) -> None:
    """A5: the current page stayed visible next to "No matches"."""
    toolbox = panel._section_toolbox
    original_titles = [toolbox.itemText(i) for i in range(toolbox.count())]

    panel._on_search_changed("zzzz-no-such-setting")

    assert panel._search_match_label.text() == translate("No matches")
    assert toolbox.count() == 0, "a non-matching page stayed visible"

    panel._on_search_changed("")

    assert toolbox.count() == len(original_titles)
    assert [toolbox.itemText(i) for i in range(toolbox.count())] == original_titles


# ---- A6: the marginal bandwidth rule reaches the estimator ----------------

def test_the_marginal_bandwidth_rule_reaches_the_estimator(panel, monkeypatch) -> None:
    """A6: the style seed made ``_resolve_marginal_bandwidth_method`` unreachable."""
    from visualization.plotting import kde as plotting_kde

    captured: list[dict] = []

    def _capture(values, **kwargs):
        captured.append(kwargs)
        grid = np.linspace(float(np.min(values)), float(np.max(values)), 64)
        return grid, np.exp(-((grid - grid.mean()) ** 2))

    monkeypatch.setattr(plotting_kde, "_estimate_density_curve", _capture)
    state_gateway.set_line_styles(
        {key: dict(value or {}) for key, value in (app_state.line_styles or {}).items()
         if key != "marginal_kde_curve"}
    )
    state_gateway.set_kde_compute_options(bw_method="silverman")
    state_gateway.set_marginal_kde_compute_options(gridsize=320)

    rng = np.random.default_rng(0)
    values = rng.lognormal(0.0, 1.0, 80)
    df_plot = pd.DataFrame(
        {
            "group": ["A"] * values.size,
            "_emb_x": values,
            "_emb_y": values * 0.5 + rng.normal(0.0, 0.3, values.size),
        }
    )

    fig, ax = plt.subplots()
    try:
        plotting_kde.draw_marginal_kde(
            ax=ax,
            df_plot=df_plot,
            group_col="group",
            palette={"A": "#1f77b4"},
            unique_cats=["A"],
        )
    finally:
        plotting_kde.clear_marginal_axes(ax)
        plt.close(fig)

    assert captured, "the marginal curves were never estimated"
    assert {call["auto_bandwidth_method"] for call in captured} == {"silverman"}
    assert {call["gridsize"] for call in captured} == {320}


def test_the_marginal_rule_changes_the_bandwidth_it_hands_to_the_estimator(panel) -> None:
    """The rule is not a label: it selects the scipy factor for the marginal data."""
    from visualization.plotting.kde import (
        _estimate_density_curve,
        _resolve_auto_bandwidth_method,
        _resolve_marginal_bandwidth_method,
    )

    rng = np.random.default_rng(0)
    values = rng.lognormal(0.0, 1.0, 80)
    std = float(np.nanstd(values))
    count = values.size
    scott = std * count ** (-1.0 / 5.0)
    silverman = std * (count * 3.0 / 4.0) ** (-1.0 / 5.0)
    assert silverman != scott

    state_gateway.set_kde_compute_options(bw_method="silverman")
    rule = _resolve_marginal_bandwidth_method()

    assert rule == "silverman", "the marginal did not follow the joint rule"
    assert _resolve_auto_bandwidth_method(rule) != "scott"

    estimate = _estimate_density_curve(
        values,
        bw_adjust=1.0,
        bandwidth=0.0,
        kernel="gaussian",
        auto_bandwidth_method=rule,
        gridsize=256,
        cut=1.0,
        log_transform=False,
    )
    assert estimate is not None


# ---- A7 / A8: widget bounds agree with the state clamps -------------------

def test_figure_dpi_widget_range_matches_the_state_clamp(panel) -> None:
    """A7: setRange(50, 600) offered values the state clamp rejects (MIN_EXPORT_DPI)."""
    from core.state.coercers import MIN_EXPORT_DPI

    spin = panel.figure_dpi_spin
    assert spin.minimum() == MIN_EXPORT_DPI
    assert spin.maximum() == 600

    state_gateway.set_plot_dpi(MIN_EXPORT_DPI - 10)
    assert app_state.plot_dpi == MIN_EXPORT_DPI

    spin.setValue(MIN_EXPORT_DPI + 5)
    assert spin.value() == app_state.plot_dpi == MIN_EXPORT_DPI + 5


def test_marker_size_range_tooltip_and_normalizer_share_one_constant(panel) -> None:
    """A8: widget 1-500, tooltip 1-2000, normalizer 2000."""
    from core.state.coercers import (
        MAX_PLOT_MARKER_SIZE,
        MIN_PLOT_MARKER_SIZE,
        _normalize_plot_marker_size,
    )
    from ui.panels.display import build_pages

    assert build_pages.MARKER_SIZE_MIN == MIN_PLOT_MARKER_SIZE == 1
    assert build_pages.MARKER_SIZE_MAX == MAX_PLOT_MARKER_SIZE == 2000

    spin = panel.marker_size_spin
    assert (spin.minimum(), spin.maximum()) == (MIN_PLOT_MARKER_SIZE, MAX_PLOT_MARKER_SIZE)
    assert spin.toolTip() == translate("Point size in square points, from {min} to {max}. The same size is used for every group.").format(
        min=MIN_PLOT_MARKER_SIZE, max=MAX_PLOT_MARKER_SIZE
    )
    assert _normalize_plot_marker_size(MAX_PLOT_MARKER_SIZE * 10) == MAX_PLOT_MARKER_SIZE


# ---- A9 / A10: no duplicated texts or tab keys ----------------------------

def test_show_grid_label_is_not_duplicated(panel) -> None:
    """A9: the QCheckBox text and the add_row label were both "Show Grid"."""
    from PyQt5.QtWidgets import QCheckBox, QLabel

    assert panel.grid_check.text() == "", "the checkbox carries a second copy of its label"
    labels = [label.text() for label in panel._built_widget.findChildren(QLabel)]
    assert labels.count(translate("Show Grid")) == 1


def test_toolbox_tab_keys_match_the_pages(panel) -> None:
    """A10: add_group_page appended a fifth key for four pages (duplicated KDE tab)."""
    toolbox = panel._section_toolbox
    keys = json.loads(toolbox.property("toolbox_tab_keys"))

    assert len(keys) == toolbox.count(), f"{len(keys)} keys for {toolbox.count()} pages"
    assert len(set(keys)) == len(keys), f"duplicate tab keys: {keys}"
    assert keys[-1] == "Kernel Density"


# ---- A11 / A12 / A13 / A14 ------------------------------------------------

def test_kde_style_entry_points_are_labelled_buttons(panel, monkeypatch) -> None:
    """A11: the only entry point was an unlabelled 16x16 swatch."""
    from PyQt5.QtWidgets import QPushButton

    opened: list[str] = []
    monkeypatch.setattr(
        panel, "_open_kde_style_dialog", lambda target, swatch: opened.append(target)
    )

    buttons = {
        button.text(): button
        for button in panel._built_widget.findChildren(QPushButton)
        if button.text() in (translate("KDE Style"), translate("Marginal KDE Style"))
    }
    assert set(buttons) == {translate("KDE Style"), translate("Marginal KDE Style")}
    for button in buttons.values():
        assert button.toolTip(), "the style entry point has no tooltip"

    buttons[translate("KDE Style")].click()
    buttons[translate("Marginal KDE Style")].click()

    assert opened == ["kde", "marginal_kde"]


def test_kde_style_module_annotates_with_an_imported_type() -> None:
    """A12: ``dict[str, Any]`` used Any without importing it."""
    from ui.panels.display import kde_style

    assert kde_style.Any is not None
    source = (kde_style.__file__ or "")
    text = open(source, encoding="utf-8").read()
    assert "\nimport ast\n" not in text
    assert "\nimport uuid\n" not in text


def test_unnormalised_combo_values_fall_back_to_the_first_item() -> None:
    """A13: ``list.index`` raised ValueError before ``max(0, ...)`` could help."""
    from PyQt5.QtWidgets import QComboBox

    from ui.panels.display.build_pages_axes import DisplayBuildAxesMixin

    combo = QComboBox()
    combo.addItems(["-", "--", "-.", ":"])

    assert DisplayBuildAxesMixin._initial_combo_index(combo, "--") == 1
    assert DisplayBuildAxesMixin._initial_combo_index(combo, "not-a-linestyle") == 0
    assert combo.currentText() == "-"


def test_the_axes_page_combos_never_raise_for_a_bad_state_value(monkeypatch) -> None:
    """The build path itself must survive a value that is not in the list.

    ``app_state`` normalises its own fields, so the absent-value branch is driven through
    the helper the page now uses rather than by planting an invalid state value.
    """
    from PyQt5.QtWidgets import QComboBox

    from ui.panels.display.build_pages_axes import DisplayBuildAxesMixin

    for value in ("!!bogus!!", "", None, "inout"):
        combo = QComboBox()
        combo.addItems(["out", "in", "inout"])
        index = DisplayBuildAxesMixin._initial_combo_index(combo, value)
        assert 0 <= index < combo.count()
        assert not combo.signalsBlocked(), "the initial assignment left the combo muted"


def test_the_dead_legend_position_helper_is_gone() -> None:
    """A14: ``legend_panel`` was permanently None, so the helper could never act."""
    from ui.panels.display.helpers import DisplayControlHelperMixin

    assert not hasattr(DisplayControlHelperMixin, "_set_legend_position_button")
    assert not hasattr(DisplayPanel, "_set_legend_position_button")
    assert not hasattr(DisplayPanel, "legend_panel")
