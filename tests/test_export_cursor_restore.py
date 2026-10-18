"""The export preview puts the application back even when putting it back fails.

Reported by review: the preview swaps several pieces of global state for the duration of the offscreen render. The
restore was in a finally, but its own steps were unprotected - a step that raised skipped the rest and, worse,
skipped the cursor restore. A wait cursor left behind makes the application look frozen.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

from PyQt5.QtWidgets import QApplication  # noqa: E402

from core import app_state, state_gateway  # noqa: E402
from ui.panels.export.export_prep import ExportPanelPrepMixin  # noqa: E402


class _Host(ExportPanelPrepMixin):
    """The mixin with everything the render needs stubbed to the simplest answer."""

    def _capture_axis_view(self, ax):
        return None

    def _palette_from_axis_collections(self, ax, fallback_palette):
        return dict(fallback_palette)

    def _is_scienceplots_available(self):
        return False

    def _fallback_export_rc(self, profile, **kwargs):
        return {}

    def _render_current_mode_sync(self, point_size=None):
        return True

    def _apply_axis_view(self, ax, view):
        return None

    def _normalize_export_legends(self, figure, profile, **kwargs):
        return None

    def _attach_preview_label_state(self, figure):
        return None


def test_the_wait_cursor_is_restored_when_a_restore_step_fails(qapp, monkeypatch) -> None:
    host = _Host()
    profile = {"figsize": (3.0, 2.0), "dpi": 100, "styles": ["default"]}

    original = (app_state.fig, app_state.ax)
    real_marker_size = state_gateway.set_plot_marker_size
    calls = {"render": 0}

    def failing_marker_size(value):
        calls["render"] += 1
        if calls["render"] >= 2:  # the restore call, not the export override
            raise RuntimeError("restore failed")
        return real_marker_size(value)

    monkeypatch.setattr(state_gateway, "set_plot_marker_size", failing_marker_size)
    assert QApplication.overrideCursor() is None, "the test starts with no override cursor"

    try:
        figure = host._create_export_figure(profile, point_size_for_export=9)

        assert figure is not None, "the figure is still returned: the restore failure is not the caller problem"
        assert QApplication.overrideCursor() is None, "the wait cursor is not left behind"
    finally:
        state_gateway.set_figure_axes(*original)


def test_the_cursor_is_restored_on_the_happy_path(qapp) -> None:
    host = _Host()
    profile = {"figsize": (3.0, 2.0), "dpi": 100, "styles": ["default"]}
    original = (app_state.fig, app_state.ax)
    try:
        assert host._create_export_figure(profile, point_size_for_export=9) is not None
    finally:
        state_gateway.set_figure_axes(*original)
    assert QApplication.overrideCursor() is None
