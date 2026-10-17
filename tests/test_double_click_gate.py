"""The double click serves the tooltip and the selection, and is off with both.

Reported: the double click highlight was always on. It reveals a group and marks a sample, which belongs to
the tooltip and the selection features; with both switched off it did that anyway.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pytest  # noqa: E402
from types import SimpleNamespace  # noqa: E402

from core import app_state, state_gateway  # noqa: E402
from visualization.event_handlers import pointer_events  # noqa: E402


@pytest.fixture()
def canvas(qapp):
    fig, ax = plt.subplots()
    ax.scatter([1, 2], [3, 4])
    state_gateway.set_figure(fig)
    state_gateway.set_axis(ax)
    yield fig, ax
    plt.close(fig)


def _double_click(ax, fig):
    return SimpleNamespace(inaxes=ax, button=1, dblclick=True, xdata=1.0, ydata=3.0, canvas=fig.canvas)


def test_a_double_click_does_nothing_with_both_features_off(canvas, monkeypatch) -> None:
    fig, ax = canvas
    state_gateway.set_show_tooltip(False)
    state_gateway.disable_selection_mode()
    resolved: list = []
    revealed: list = []
    monkeypatch.setattr(pointer_events, "_resolve_sample_index", lambda event: resolved.append(event) or 0)
    monkeypatch.setattr(app_state, "group_reveal_callback", lambda group: revealed.append(group), raising=False)

    pointer_events.on_click(_double_click(ax, fig))

    assert resolved == [], "the sample is not resolved when nothing asked for it"
    assert revealed == [], "and no group is revealed either"


def test_a_double_click_acts_when_the_tooltip_is_on(canvas, monkeypatch) -> None:
    fig, ax = canvas
    state_gateway.set_show_tooltip(True)
    resolved: list = []
    monkeypatch.setattr(pointer_events, "_resolve_sample_index", lambda event: resolved.append(event) or 0)

    pointer_events.on_click(_double_click(ax, fig))

    assert resolved, "the sample is resolved, because a feature that uses it is on"
