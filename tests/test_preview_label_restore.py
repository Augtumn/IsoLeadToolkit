"""The preview label refresh puts the live label state back, whatever fails on the way.

Reported by the same sweep that found the export restore: the finally block restored three pieces of state with no
protection around them, so a failing restore skipped the rest - and the one that matters most is the label state,
which left pointing at the preview draws the preview labels on the live plot.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

from matplotlib.figure import Figure  # noqa: E402

from core import state_gateway  # noqa: E402
from ui.panels.export.export_legends import ExportPanelLegendMixin  # noqa: E402

_KEYS = (
    "paleoisochron_label_data",
    "plumbotectonics_label_data",
    "plumbotectonics_isoage_label_data",
    "overlay_curve_label_data",
)


class _Host(ExportPanelLegendMixin):
    pass


def test_the_other_restores_still_run_when_one_fails(qapp, monkeypatch) -> None:
    figure = Figure()
    axes = figure.add_subplot(111)
    figure._overlay_label_state = {key: ["preview"] for key in _KEYS}

    calls = []
    real_figure_axes = state_gateway.set_figure_axes
    count = {"n": 0}

    def flaky(value=1):
        count["n"] += 1
        if count["n"] >= 2:  # the restore, not the swap
            raise RuntimeError("restore failed")
        return real_figure_axes(figure, axes)

    monkeypatch.setattr(state_gateway, "set_figure_axes", flaky)
    monkeypatch.setattr(
        state_gateway, "set_overlay_label_flags", lambda **kwargs: calls.append(("flags", kwargs))
    )
    monkeypatch.setattr(
        state_gateway, "set_overlay_label_state", lambda mapping: calls.append(("state", mapping))
    )
    monkeypatch.setattr(
        "visualization.plotting.refresh_paleoisochron_labels", lambda: None
    )

    _Host()._refresh_preview_overlay_labels(figure, axes)

    kinds = [kind for kind, _payload in calls]
    assert ("state" in kinds), "the label state is restored even though the figure restore failed"
    assert ("flags" in kinds), "and so are the flags"
