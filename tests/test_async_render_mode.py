"""The mode a render is asked for travels with the request, all the way to the worker.

With several panels, the panel being drawn is not the panel the state calls current. Reading the state
deep in the render path started another panel's algorithm and drew its embedding into this panel - so
the mode is passed along instead.
"""
from __future__ import annotations

from core import app_state, state_gateway
from application.use_cases.render_plot import RenderPlotUseCase


def _case(calls: list[tuple[str, str]]) -> RenderPlotUseCase:
    case = RenderPlotUseCase.__new__(RenderPlotUseCase)
    case._state = app_state
    case._state_write = state_gateway
    case._df_global = lambda: None
    case._data_cols = lambda: []
    case._group_cols = lambda: []
    case._cancel_embedding_task = lambda reason: None
    case._disable_rectangle_selector = lambda: None
    case._refresh_selection_overlay = lambda: None
    case._sync_selection_tools = lambda: None
    case._plot_2d_data = lambda *args, **kwargs: True
    case._plot_3d_data = lambda *args, **kwargs: True
    case._plot_embedding = lambda *args, **kwargs: True

    def _start(group_col: str, mode: str):
        calls.append((group_col, mode))
        return True, True

    case._start_async_embedding_render = _start
    return case


def test_an_async_mode_is_started_for_the_mode_the_render_asked_for(qapp) -> None:
    calls: list[tuple[str, str]] = []
    case = _case(calls)

    state_gateway.set_render_mode("2D")
    ok, pending = case._dispatch_render("Site", ["a", "b"], ["a", "b", "c"], mode="UMAP")

    assert calls == [("Site", "UMAP")], f"the requested mode, not the state's, got {calls}"
    assert (ok, pending) == (True, True)


def test_each_panel_starts_its_own_algorithm(qapp) -> None:
    calls: list[tuple[str, str]] = []
    case = _case(calls)

    state_gateway.set_render_mode("PCA")
    case._dispatch_render("Site", ["a", "b"], ["a", "b", "c"], mode="tSNE")
    case._dispatch_render("Site", ["a", "b"], ["a", "b", "c"], mode="UMAP")

    assert calls == [("Site", "tSNE"), ("Site", "UMAP")], f"one per panel, got {calls}"


def test_a_mode_that_is_not_asynchronous_is_not_started_async(qapp) -> None:
    calls: list[tuple[str, str]] = []
    case = _case(calls)

    state_gateway.set_render_mode("UMAP")
    # A synchronous mode is drawn in place; the async path is not used for it even when the state says
    # the current mode is an asynchronous one.
    case._dispatch_render("Site", ["a", "b"], ["a", "b", "c"], mode="2D")

    assert calls == [], f"2D is not an embedding, got {calls}"
