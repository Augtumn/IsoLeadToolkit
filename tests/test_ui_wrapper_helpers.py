"""Tests for UI helper wrapper functions and lightweight startup helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

pytest.importorskip("PyQt5")


def test_configure_matplotlib_uses_agg_fallback_and_calls_font_setup(monkeypatch) -> None:
    import matplotlib
    from ui import app as ui_app

    backends: list[str] = []
    called = {"fonts": False}

    def _fake_use(backend: str) -> None:
        backends.append(backend)
        if backend == "Qt5Agg":
            raise RuntimeError("backend unavailable")

    monkeypatch.setattr(matplotlib, "use", _fake_use)
    monkeypatch.setattr(ui_app, "_configure_matplotlib_fonts", lambda: called.__setitem__("fonts", True))

    ui_app._configure_matplotlib()

    assert backends == ["Qt5Agg", "Agg"]
    assert called["fonts"] is True


def test_configure_matplotlib_fonts_applies_preferred_font_and_dpi(monkeypatch) -> None:
    import matplotlib
    from matplotlib import font_manager
    from ui import app as ui_app

    family_before = matplotlib.rcParams.get("font.family")
    sans_before = matplotlib.rcParams.get("font.sans-serif")
    unicode_minus_before = matplotlib.rcParams.get("axes.unicode_minus")
    figure_dpi_before = matplotlib.rcParams.get("figure.dpi")
    savefig_dpi_before = matplotlib.rcParams.get("savefig.dpi")

    preferred_before = ui_app.CONFIG.get("preferred_plot_fonts")
    figure_cfg_before = ui_app.CONFIG.get("figure_dpi")
    savefig_cfg_before = ui_app.CONFIG.get("savefig_dpi")

    try:
        monkeypatch.setattr(font_manager.fontManager, "ttflist", [SimpleNamespace(name="MockPreferred")])
        monkeypatch.setitem(ui_app.CONFIG, "preferred_plot_fonts", ["MockPreferred", "Other"])
        monkeypatch.setitem(ui_app.CONFIG, "figure_dpi", 111)
        monkeypatch.setitem(ui_app.CONFIG, "savefig_dpi", 222)

        ui_app._configure_matplotlib_fonts()

        assert "MockPreferred" in matplotlib.rcParams["font.sans-serif"]
        assert matplotlib.rcParams["figure.dpi"] == 111
        assert matplotlib.rcParams["savefig.dpi"] == 222
        assert matplotlib.rcParams["axes.unicode_minus"] is False
    finally:
        matplotlib.rcParams["font.family"] = family_before
        matplotlib.rcParams["font.sans-serif"] = sans_before
        matplotlib.rcParams["axes.unicode_minus"] = unicode_minus_before
        matplotlib.rcParams["figure.dpi"] = figure_dpi_before
        matplotlib.rcParams["savefig.dpi"] = savefig_dpi_before

        if preferred_before is None:
            ui_app.CONFIG.pop("preferred_plot_fonts", None)
        else:
            ui_app.CONFIG["preferred_plot_fonts"] = preferred_before
        if figure_cfg_before is None:
            ui_app.CONFIG.pop("figure_dpi", None)
        else:
            ui_app.CONFIG["figure_dpi"] = figure_cfg_before
        if savefig_cfg_before is None:
            ui_app.CONFIG.pop("savefig_dpi", None)
        else:
            ui_app.CONFIG["savefig_dpi"] = savefig_cfg_before


def test_create_control_panel_delegates_constructor(monkeypatch) -> None:
    from ui import control_panel

    class _FakePanel:
        def __init__(self, callback):
            self.callback = callback

    monkeypatch.setattr(control_panel, "Qt5ControlPanel", _FakePanel)
    callback = lambda: None

    panel = control_panel.create_control_panel(callback)

    assert isinstance(panel, _FakePanel)
    assert panel.callback is callback


def test_create_section_dialog_invalid_key_returns_none() -> None:
    from ui import control_panel

    result = control_panel.create_section_dialog("unknown", callback=lambda: None)

    assert result is None


def test_get_data_configuration_returns_result_when_accepted(monkeypatch) -> None:
    from ui.dialogs import data_config

    class _FakeDialog:
        Accepted = 1

        def __init__(self, *_args, **_kwargs):
            self.result = {"group_cols": ["grp"], "data_cols": ["x", "y"]}

        def exec_(self):
            return self.Accepted

    monkeypatch.setattr(data_config, "Qt5DataConfigDialog", _FakeDialog)

    result = data_config.get_data_configuration(df=object(), default_group_cols=["grp"], default_data_cols=["x"])

    assert result == {"group_cols": ["grp"], "data_cols": ["x", "y"]}


def test_get_file_sheet_selection_returns_none_when_rejected(monkeypatch) -> None:
    from ui.dialogs import file_dialog

    class _FakeDialog:
        Accepted = 1

        def __init__(self, *_args, **_kwargs):
            self.result = {"file": "D:/x.csv"}

        def exec_(self):
            return 0

    monkeypatch.setattr(file_dialog, "Qt5FileDialog", _FakeDialog)

    assert file_dialog.get_file_sheet_selection("D:/x.csv") is None


def test_get_isochron_error_settings_returns_settings_when_accepted(monkeypatch) -> None:
    from ui.dialogs import isochron_dialog

    class _FakeDialog:
        def __init__(self, *_args, **_kwargs):
            pass

        def exec_(self):
            return isochron_dialog.QDialog.Accepted

        def get_settings(self):
            return {"mode": "fixed", "sx": 0.01}

    monkeypatch.setattr(isochron_dialog, "IsochronErrorConfigDialog", _FakeDialog)

    result = isochron_dialog.get_isochron_error_settings()

    assert result == {"mode": "fixed", "sx": 0.01}


def test_get_sheet_selection_returns_selected_sheet(monkeypatch) -> None:
    from ui.dialogs import sheet_dialog

    class _FakeDialog:
        Accepted = 1

        def __init__(self, *_args, **_kwargs):
            self.result = "Sheet1"

        def exec_(self):
            return self.Accepted

    monkeypatch.setattr(sheet_dialog, "Qt5SheetDialog", _FakeDialog)

    assert sheet_dialog.get_sheet_selection("D:/x.xlsx", default_sheet="Sheet0") == "Sheet1"


def test_get_ternary_column_selection_returns_result(monkeypatch) -> None:
    from ui.dialogs import ternary_dialog

    class _FakeDialog:
        Accepted = 1

        def __init__(self, *_args, **_kwargs):
            self.result = {"columns": ["a", "b", "c"], "stretch": False, "factors": [1.0, 1.0, 1.0]}

        def exec_(self):
            return self.Accepted

    monkeypatch.setattr(ternary_dialog, "Qt5TernaryDialog", _FakeDialog)

    assert ternary_dialog.get_ternary_column_selection() == {
        "columns": ["a", "b", "c"],
        "stretch": False,
        "factors": [1.0, 1.0, 1.0],
    }


def test_get_3d_and_2d_selection_wrappers(monkeypatch) -> None:
    from ui.dialogs import three_d_dialog, two_d_dialog

    class _Fake3DDialog:
        Accepted = 1

        def __init__(self, *_args, **_kwargs):
            self.result = ["x", "y", "z"]

        def exec_(self):
            return self.Accepted

    class _Fake2DDialog:
        Accepted = 1

        def __init__(self, *_args, **_kwargs):
            self.result = ["x", "y"]

        def exec_(self):
            return self.Accepted

    monkeypatch.setattr(three_d_dialog, "Qt5ThreeDDialog", _Fake3DDialog)
    monkeypatch.setattr(two_d_dialog, "Qt5TwoDDialog", _Fake2DDialog)

    assert three_d_dialog.get_3d_column_selection() == ["x", "y", "z"]
    assert two_d_dialog.get_2d_column_selection() == ["x", "y"]


def test_get_tooltip_configuration_returns_selected_columns(monkeypatch) -> None:
    from ui.dialogs import tooltip_dialog

    class _FakeDialog:
        def __init__(self, *_args, **_kwargs):
            pass

        def exec_(self):
            return tooltip_dialog.QDialog.Accepted

        def get_selected_columns(self):
            return ["sample", "value"]

    monkeypatch.setattr(tooltip_dialog, "TooltipConfigDialog", _FakeDialog)

    assert tooltip_dialog.get_tooltip_configuration() == ["sample", "value"]


def test_show_dialog_wrappers_execute_dialog(monkeypatch) -> None:
    from ui.dialogs import endmember_dialog, mixing_dialog, provenance_ml_dialog

    calls: list[str] = []

    class _ExecDialog:
        def __init__(self, *_args, **_kwargs):
            self.name = _kwargs.get("name", "dialog")

        def exec_(self):
            calls.append(self.name)

    monkeypatch.setattr(endmember_dialog, "EndmemberAnalysisDialog", lambda *_a, **_k: SimpleNamespace(exec_=lambda: calls.append("endmember")))
    monkeypatch.setattr(mixing_dialog, "MixingCalculatorDialog", lambda *_a, **_k: SimpleNamespace(exec_=lambda: calls.append("mixing")))
    monkeypatch.setattr(provenance_ml_dialog, "ProvenanceMLDialog", lambda *_a, **_k: SimpleNamespace(exec_=lambda: calls.append("provenance")))

    endmember_dialog.show_endmember_analysis()
    mixing_dialog.show_mixing_calculator()
    provenance_ml_dialog.show_provenance_ml()

    assert calls == ["endmember", "mixing", "provenance"]


def test_clear_widget_styles_skips_keep_style_children(monkeypatch) -> None:
    from ui.app_parts import styles

    class _FakeWidget:
        def __init__(self, style: str = "", keep: bool = False, children: list["_FakeWidget"] | None = None):
            self._style = style
            self._keep = keep
            self._children = children or []

        def property(self, name: str):
            if name == "keepStyle":
                return self._keep
            return None

        def styleSheet(self) -> str:
            return self._style

        def setStyleSheet(self, value: str) -> None:
            self._style = value

        def findChildren(self, _cls):
            return list(self._children)

    monkeypatch.setattr(styles, "QWidget", _FakeWidget)

    child_cleared = _FakeWidget(style="child")
    child_kept = _FakeWidget(style="keep", keep=True)
    root = _FakeWidget(style="root", children=[child_cleared, child_kept])

    styles._clear_widget_styles(root)

    assert root.styleSheet() == ""
    assert child_cleared.styleSheet() == ""
    assert child_kept.styleSheet() == "keep"


def test_display_theme_auto_layout_delegates_to_layout_helper(monkeypatch) -> None:
    from ui.panels.display import themes

    calls: dict[str, object] = {"fig": None, "draw_called": False}

    class _Canvas:
        def draw_idle(self) -> None:
            calls["draw_called"] = True

    fake_fig = SimpleNamespace(canvas=_Canvas())
    monkeypatch.setattr(themes, "app_state", SimpleNamespace(fig=fake_fig))
    monkeypatch.setattr(
        themes,
        "configure_constrained_layout",
        lambda fig: calls.__setitem__("fig", fig),
    )

    class _Panel(themes.DisplayThemeMixin):
        pass

    _Panel()._apply_auto_layout()

    assert calls["fig"] is fake_fig
    assert calls["draw_called"] is True
