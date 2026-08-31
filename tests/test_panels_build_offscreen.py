"""All six section panels must build without exceptions (offscreen Qt).

Regression guard: display/build.py once used ``Qt.AlignRight`` without
importing Qt, crashing the Display dialog on open (see error log
2026-08-31 16:57:57, NameError: name 'Qt' is not defined).
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PyQt5")

from PyQt5.QtWidgets import QApplication

from core import app_state

_APP: QApplication | None = None


@pytest.fixture(scope="module", autouse=True)
def _qapp():
    global _APP
    if _APP is None:
        _APP = QApplication.instance() or QApplication([])
    yield _APP


PANEL_SPECS = [
    ("data", "DataPanel"),
    ("display", "DisplayPanel"),
    ("analysis", "AnalysisPanel"),
    ("export", "ExportPanel"),
    ("legend", "LegendPanel"),
    ("geo", "GeoPanel"),
]


@pytest.mark.parametrize("module_name,class_name", PANEL_SPECS)
def test_panel_builds_offscreen(module_name: str, class_name: str) -> None:
    module = __import__(f"ui.panels.{module_name}_panel", fromlist=[class_name])
    panel_cls = getattr(module, class_name)
    panel = panel_cls(callback=lambda: None, parent=None)
    panel.reset_state()
    widget = panel.build()
    assert widget is not None
    widget.deleteLater()
    assert app_state is not None
