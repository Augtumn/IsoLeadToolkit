"""Pytest bootstrap: workspace-local imports and headless test environment.

The Agg backend and the offscreen Qt platform are configured here once so no
test module needs its own ``matplotlib.use`` / ``QT_QPA_PLATFORM`` line; this
runs before any test module is imported.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
project_root_str = str(PROJECT_ROOT)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import matplotlib  # noqa: E402  (must follow the Qt platform setup)

matplotlib.use("Agg")


# ── UI fixtures (composition root) ──────────────────────────────────────

@pytest.fixture(scope="session")
def qapp():
    """A single offscreen QApplication for the whole session."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture()
def main_window(qapp):
    """The real main window, built through the composition root.

    Widget behaviour must be tested against the actual window instead of ad-hoc host
    objects that fake the mixin attributes.
    """
    from ui.factory import build_main_window

    window = build_main_window()
    try:
        yield window
    finally:
        window.close()
        window.deleteLater()
        qapp.processEvents()
