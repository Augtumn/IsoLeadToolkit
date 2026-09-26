"""Regression test for the export preview dialog's control builder.

The full dialog cannot be built offscreen (constructing it crashes the interpreter),
so this drives the builder directly with the real profile parameters. It is the
test that would have caught the shipped bug in isotopes_analyse.error.log:

    ExportPreviewControlsMixin._build_preview_controls() takes 10 positional
    arguments but 11 were given

(the helper had lost its ``self`` parameter, so the dialog only logged
"Failed to generate export preview" and never opened).
"""
from __future__ import annotations

import pytest

pytest.importorskip("PyQt5")

from PyQt5.QtWidgets import QApplication, QVBoxLayout, QWidget  # noqa: E402

from ui.panels import ExportPanel  # noqa: E402

_APP = QApplication.instance() or QApplication([])


@pytest.fixture()
def panel() -> ExportPanel:
    instance = ExportPanel(callback=lambda: None, parent=None)
    instance.reset_state()
    instance._built_widget = instance.build()
    return instance


def test_preview_controls_build_with_real_profile(panel) -> None:
    profile = panel._image_export_profile("science_single")
    params = dict(panel._profile_default_params(profile))

    parent = QWidget()
    layout = QVBoxLayout(parent)
    controls = panel._build_preview_controls(
        parent,
        layout,
        str(params.get("image_ext", "png")),
        int(round(float((profile.get("legend", {}) or {}).get("fontsize", 8.0)))),
        int(round(float((profile.get("legend", {}) or {}).get("fontsize", 8.0))) + 2.0),
        params,
        int(profile.get("point_size", 60)),
        "science_single",
        int(round(float((profile.get("legend", {}) or {}).get("fontsize", 8.0))) - 0.5),
        int(round(float((profile.get("legend", {}) or {}).get("fontsize", 8.0))) + 3.0),
    )

    # every control the dialog's closures read must come back from the builder
    for name in (
        "preset_combo", "format_combo", "dpi_slider", "dpi_spin",
        "ps_slider", "ps_spin", "ls_slider", "ls_spin",
        "lms_slider", "lms_spin", "lab_slider", "lab_spin",
        "tit_slider", "tit_spin", "tck_slider", "tck_spin",
        "tight_bbox_check", "pad_spin", "transparent_check",
    ):
        assert getattr(controls, name) is not None, name

    assert controls.dpi_slider.value() >= 72
    assert controls.format_combo.currentData()
    assert controls.preset_combo.currentData() == "science_single"
