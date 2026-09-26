"""Double click raises the clicked point's layer (unless selection mode is on)."""
from __future__ import annotations

import matplotlib
import pandas as pd
import pytest

matplotlib.use("Agg")

from matplotlib.backend_bases import MouseEvent  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

from core import app_state, state_gateway  # noqa: E402
from visualization.event_handlers import pointer_events  # noqa: E402


@pytest.fixture()
def scene(monkeypatch):
    """A current axes + group column, with the sample resolver stubbed."""
    figure = Figure(figsize=(3, 3))
    axes = figure.add_subplot(111)
    axes.scatter([1.0, 2.0], [1.0, 2.0], label="GroupA")
    figure.canvas.draw()
    state_gateway.set_figure_axes(figure, axes)

    original_mode = app_state.selection_mode
    # Mode first: a dispatch syncs the store and would roll back direct attributes.
    state_gateway.set_selection_mode(False)
    monkeypatch.setattr(app_state, "last_group_col", "Province/Lueague", raising=False)
    monkeypatch.setattr(
        pointer_events, "df_global",
        lambda: pd.DataFrame({"Province/Lueague": ["GroupA", "GroupB"]}),
    )
    monkeypatch.setattr(pointer_events, "_resolve_sample_index", lambda event: 0)

    calls: list[str] = []
    monkeypatch.setattr(app_state, "group_front_callback", calls.append, raising=False)
    yield figure, axes, calls, monkeypatch
    state_gateway.set_selection_mode(original_mode)


def _double_click(figure, axes, dblclick=True):
    x, y = axes.transData.transform((1.0, 1.0))
    return MouseEvent(
        "button_press_event", figure.canvas, x, y, button=1, dblclick=dblclick, key=None
    )


def test_double_click_raises_the_group_of_the_clicked_point(scene) -> None:
    figure, axes, calls, _mp = scene

    pointer_events.on_click(_double_click(figure, axes))

    assert calls == ["GroupA"], calls


def test_double_click_in_selection_mode_selects_instead(scene) -> None:
    """With the selection tool open the existing behaviour must stay untouched."""
    figure, axes, calls, monkeypatch = scene
    state_gateway.set_selection_mode(True)
    monkeypatch.setattr(app_state, "group_front_callback", calls.append, raising=False)

    pointer_events.on_click(_double_click(figure, axes))

    assert calls == [], "selection mode must not raise layers"


def test_a_single_click_never_raises_a_layer(scene) -> None:
    figure, axes, calls, _mp = scene

    pointer_events.on_click(_double_click(figure, axes, dblclick=False))

    assert calls == []


def test_clicks_outside_the_current_axis_are_ignored(scene) -> None:
    figure, axes, calls, _mp = scene
    other = figure.add_subplot(122)
    x, y = other.transData.transform((1.0, 1.0))

    pointer_events.on_click(
        MouseEvent("button_press_event", figure.canvas, x, y, button=1, dblclick=True, key=None)
    )

    assert calls == [], "only the current axes may raise a layer"


def test_missing_group_column_is_harmless(scene, monkeypatch) -> None:
    figure, axes, calls, _mp = scene
    monkeypatch.setattr(pointer_events, "df_global", lambda: None)

    pointer_events.on_click(_double_click(figure, axes))

    assert calls == []


def test_the_callback_is_registered_by_the_gateway() -> None:
    state_gateway.set_group_front_callback(None)
    assert getattr(app_state, "group_front_callback", "missing") is None
