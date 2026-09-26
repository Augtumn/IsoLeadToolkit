"""End-to-end tests for the KDE style dialog's computation options.

The dialog is opened with ``QDialog.exec_`` replaced by a driver that sets the new
controls and clicks Save, so the whole path (control -> gateway -> state -> style)
is exercised without blocking on a modal dialog.
"""
from __future__ import annotations

from typing import Callable

import pytest

pytest.importorskip("PyQt5")

from PyQt5.QtWidgets import (  # noqa: E402
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QMessageBox,
    QPushButton,
    QSpinBox,
)

from core import app_state, state_gateway, translate  # noqa: E402
from ui.panels import DisplayPanel  # noqa: E402

_APP = QApplication.instance() or QApplication([])


@pytest.fixture()
def panel() -> DisplayPanel:
    instance = DisplayPanel(callback=lambda: None, parent=None)
    instance.reset_state()
    instance._built_widget = instance.build()  # keep the widget tree alive
    return instance


@pytest.fixture(autouse=True)
def _restore_kde_state():
    """Snapshot and restore all KDE options so tests cannot leak into each other."""
    snapshot = {
        "bw_adjust": app_state.kde_bw_adjust,
        "bw_method": app_state.kde_bw_method,
        "gridsize": app_state.kde_gridsize,
        "thresh": app_state.kde_thresh,
        "clip_min": app_state.kde_clip_min,
        "clip_max": app_state.kde_clip_max,
        "common_norm": app_state.kde_common_norm,
        "warn_singular": app_state.kde_warn_singular,
        "marginal_clip_min": app_state.marginal_kde_clip_min,
        "marginal_clip_max": app_state.marginal_kde_clip_max,
        "marginal_cumulative": app_state.marginal_kde_cumulative,
        "styles": dict(app_state.line_styles or {}),
    }
    yield
    state_gateway.set_kde_compute_options(
        bw_adjust=snapshot["bw_adjust"], bw_method=snapshot["bw_method"],
        gridsize=snapshot["gridsize"], thresh=snapshot["thresh"],
        common_norm=snapshot["common_norm"], warn_singular=snapshot["warn_singular"],
    )
    if snapshot["clip_min"] is None and snapshot["clip_max"] is None:
        state_gateway.set_kde_compute_options(clear_clip=True)
    else:
        state_gateway.set_kde_compute_options(
            clip_min=snapshot["clip_min"], clip_max=snapshot["clip_max"]
        )
    state_gateway.set_marginal_kde_compute_options(
        cumulative=snapshot["marginal_cumulative"]
    )
    if snapshot["marginal_clip_min"] is None and snapshot["marginal_clip_max"] is None:
        state_gateway.set_marginal_kde_compute_options(clear_clip=True)
    else:
        state_gateway.set_marginal_kde_compute_options(
            clip_min=snapshot["marginal_clip_min"], clip_max=snapshot["marginal_clip_max"]
        )
    state_gateway.set_line_styles(snapshot["styles"])


def _drive_dialog(panel: DisplayPanel, target: str, monkeypatch, configure: Callable) -> dict:
    """Open the style dialog, run *configure* on it, then press Save."""
    seen: dict = {}

    def _fake_exec(self):  # noqa: ANN001 - Qt signature
        seen["dialog"] = self
        configure(self)
        save = next(
            button
            for button in self.findChildren(QPushButton)
            if button.text() == translate("Save")
        )
        save.click()
        return 0

    monkeypatch.setattr(QDialog, "exec_", _fake_exec)
    panel._open_kde_style_dialog(target, None)
    return seen["dialog"]


def test_kde_style_dialog_applies_compute_options(panel, monkeypatch) -> None:
    state_gateway.set_kde_compute_options(
        bw_adjust=1.0, bw_method="scott", gridsize=200, thresh=0.05,
        common_norm=False, warn_singular=False, clear_clip=True,
    )

    def configure(dialog):
        assert dialog.findChild(QDoubleSpinBox, "kde_bw_adjust_spin").value() == 1.0
        assert dialog.findChild(QComboBox, "kde_bw_method_combo").currentData() == "scott"
        assert dialog.findChild(QSpinBox, "kde_gridsize_spin").value() == 200
        assert dialog.findChild(QDoubleSpinBox, "kde_thresh_spin").value() == 0.05
        assert dialog.findChild(QCheckBox, "kde_common_norm_check").isChecked() is False
        assert dialog.findChild(QCheckBox, "kde_warn_singular_check").isChecked() is False

        dialog.findChild(QDoubleSpinBox, "kde_bw_adjust_spin").setValue(2.25)
        dialog.findChild(QComboBox, "kde_bw_method_combo").setCurrentIndex(
            dialog.findChild(QComboBox, "kde_bw_method_combo").findData("silverman")
        )
        dialog.findChild(QSpinBox, "kde_gridsize_spin").setValue(64)
        dialog.findChild(QDoubleSpinBox, "kde_thresh_spin").setValue(0.2)
        dialog.findChild(QCheckBox, "kde_common_norm_check").setChecked(True)
        dialog.findChild(QCheckBox, "kde_warn_singular_check").setChecked(True)
        dialog.findChild(QCheckBox, "kde_clip_check").setChecked(True)
        dialog.findChild(QDoubleSpinBox, "kde_clip_min_spin").setValue(-4.0)
        dialog.findChild(QDoubleSpinBox, "kde_clip_max_spin").setValue(7.5)

    _drive_dialog(panel, "kde", monkeypatch, configure)

    assert app_state.kde_bw_adjust == pytest.approx(2.25)
    assert app_state.kde_bw_method == "silverman"
    assert app_state.kde_gridsize == 64
    assert app_state.kde_thresh == pytest.approx(0.2)
    assert app_state.kde_common_norm is True
    assert app_state.kde_warn_singular is True
    assert (app_state.kde_clip_min, app_state.kde_clip_max) == (-4.0, 7.5)


def test_kde_style_dialog_clears_clip_when_unchecked(panel, monkeypatch) -> None:
    state_gateway.set_kde_compute_options(clip_min=-1.0, clip_max=1.0)

    def configure(dialog):
        assert dialog.findChild(QCheckBox, "kde_clip_check").isChecked() is True
        dialog.findChild(QCheckBox, "kde_clip_check").setChecked(False)

    _drive_dialog(panel, "kde", monkeypatch, configure)

    assert app_state.kde_clip_min is None and app_state.kde_clip_max is None


def test_kde_style_dialog_rejects_inverted_clip(panel, monkeypatch) -> None:
    warnings: list[tuple] = []
    monkeypatch.setattr(
        QMessageBox, "warning", staticmethod(lambda *args, **kwargs: warnings.append(args))
    )
    state_gateway.set_kde_compute_options(clear_clip=True)
    state_gateway.set_kde_compute_options(bw_adjust=1.5)

    def configure(dialog):
        dialog.findChild(QCheckBox, "kde_clip_check").setChecked(True)
        dialog.findChild(QDoubleSpinBox, "kde_clip_min_spin").setValue(10.0)
        dialog.findChild(QDoubleSpinBox, "kde_clip_max_spin").setValue(5.0)

    _drive_dialog(panel, "kde", monkeypatch, configure)

    assert warnings, "an inverted clip range must warn instead of being applied"
    assert app_state.kde_clip_min is None and app_state.kde_clip_max is None
    assert app_state.kde_bw_adjust == pytest.approx(1.5), "rejected apply must change nothing"


def test_marginal_kde_dialog_applies_clip_and_cumulative(panel, monkeypatch) -> None:
    state_gateway.set_marginal_kde_compute_options(cumulative=False, clear_clip=True)

    def configure(dialog):
        assert dialog.findChild(QCheckBox, "marginal_cumulative_check").isChecked() is False
        dialog.findChild(QCheckBox, "marginal_clip_check").setChecked(True)
        dialog.findChild(QDoubleSpinBox, "marginal_clip_min_spin").setValue(1.0)
        dialog.findChild(QDoubleSpinBox, "marginal_clip_max_spin").setValue(9.0)
        dialog.findChild(QCheckBox, "marginal_cumulative_check").setChecked(True)

    _drive_dialog(panel, "marginal_kde", monkeypatch, configure)

    assert (app_state.marginal_kde_clip_min, app_state.marginal_kde_clip_max) == (1.0, 9.0)
    assert app_state.marginal_kde_cumulative is True
    style = (app_state.line_styles or {}).get("marginal_kde_curve", {})
    assert style.get("clip_min") == 1.0 and style.get("clip_max") == 9.0
    assert style.get("cumulative") is True
