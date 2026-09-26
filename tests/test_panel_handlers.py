"""Regression tests for the panel regressions reported in isotopes_analyse.error.log.

The KDE checkbox and the geochemistry overlay swatch are handler paths that the
offscreen panel-build test never touches: they run only on user interaction, so
the AttributeErrors they raised (missing helpers after the panel reshuffle) went
unnoticed until the app was clicked. These tests call those handlers directly.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

pytest.importorskip("PyQt5")

from PyQt5.QtCore import Qt  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

from ui.panels import DisplayPanel  # noqa: E402

#: Module-level application: dropping the last reference destroys the QWidgets
#: created by the tests ("wrapped C/C++ object ... has been deleted").
_APP = QApplication.instance() or QApplication([])


def _build(cls):
    panel = cls(callback=lambda: None, parent=None)
    panel.reset_state()
    # keep the built widget tree alive: without a parent (or this reference) the
    # top-level widget and its children are collected and the handlers then touch
    # deleted C++ objects
    panel._built_widget = panel.build()
    return panel


def test_display_panel_kde_toggle_handler_runs(monkeypatch) -> None:
    """`_on_kde_change` used to raise AttributeError: no _sync_toggle_widgets."""
    panel = _build(DisplayPanel)
    calls: list[object] = []
    monkeypatch.setattr(panel, "_on_change", lambda: calls.append("change"))

    panel._on_kde_change(Qt.Checked)
    panel._on_kde_change(Qt.Unchecked)

    assert calls, "the KDE toggle handler did not refresh the plot"


def test_display_panel_marginal_kde_toggle_handler_runs(monkeypatch) -> None:
    panel = _build(DisplayPanel)
    monkeypatch.setattr(panel, "_on_change", lambda: None)

    panel._on_marginal_kde_change(Qt.Checked)
    panel._on_marginal_kde_change(Qt.Unchecked)

    assert panel.tools_marginal_kde_check is not None


def test_panels_can_open_the_line_style_dialog(monkeypatch) -> None:
    """The geochem overlay swatches call _open_line_style_dialog from GeoPanel."""
    from ui.panels import GeoPanel
    from ui.panels.display.dialogs import line_style_dialog

    opened: list[tuple[str, object]] = []

    def _fake_open(parent, style_key, swatch=None, on_applied=None):
        opened.append((style_key, swatch))
        return None

    monkeypatch.setattr(line_style_dialog, "open_line_style_dialog", _fake_open)

    panel = _build(GeoPanel)
    swatch = object()
    panel._open_line_style_dialog("model_curve", swatch)

    assert opened == [("model_curve", swatch)]


def test_every_panel_inherits_the_shared_helpers() -> None:
    from ui.panels import AnalysisPanel, DataPanel, ExportPanel, GeoPanel, LegendPanel

    for cls in (AnalysisPanel, DataPanel, DisplayPanel, ExportPanel, GeoPanel, LegendPanel):
        assert hasattr(cls, "_sync_toggle_widgets"), cls.__name__
        assert hasattr(cls, "_open_line_style_dialog"), cls.__name__
