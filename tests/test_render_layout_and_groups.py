"""The marginal KDE keeps its layout, and a missing grouping column keeps the chosen groups.

Two defects the review of the rendering and application layers found:

* The 2D render re-enabled constrained layout in its decorate step, right after the marginal step had
  turned it off for the divider axes. The constraint is written down in kde.py; now it is enforced, and the
  renderer asks kde.py whether marginals are attached before touching the layout.
* Listing the groups of a render swallowed every exception and passed an empty list on, which the state
  handler turns into visible_groups=None: the user's "show only these groups" was cleared silently. A
  missing column now warns and leaves the selection alone.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import pandas as pd  # noqa: E402
import pytest  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

from core import app_state, state_gateway  # noqa: E402
from visualization.plotting.kde import marginal_axes_attached_to  # noqa: E402


@pytest.fixture()
def ready(qapp):
    frame = pd.DataFrame(
        {"Site": ["A", "A", "B", "B"], "x1": [1.0, 2.0, 3.0, 4.0], "x2": [2.0, 3.0, 4.0, 5.0]}
    )
    state_gateway.set_dataframe_and_source(frame, file_path="layout.csv", sheet_name="s")
    state_gateway.set_group_data_columns(["Site"], ["x1", "x2"])
    state_gateway.set_last_group_col("Site")
    state_gateway.set_visible_groups(None)
    state_gateway.set_selected_2d_columns(["x1", "x2"], confirmed=True)
    figure = Figure()
    state_gateway.set_figure(figure)
    state_gateway.set_axis(figure.add_subplot(111))
    yield frame
    # Leave the application as it was found: the render below attaches marginal axes and the marginal
    # state is global, so a later test in the same session would otherwise see them.
    state_gateway.set_show_marginal_kde(False)
    state_gateway.set_marginal_axes(None)
    state_gateway.set_visible_groups(None)
    figure = app_state.fig
    if figure is not None:
        figure.clear()


def test_a_2d_render_does_not_reenable_layout_while_marginals_are_attached(ready) -> None:
    from visualization.plotting.rendering.raw.plot2d import plot_2d_data

    state_gateway.set_figure(ready_figure := app_state.fig)
    ready_figure.set_layout_engine("constrained")
    state_gateway.set_show_marginal_kde(True)

    assert plot_2d_data("Site", ["x1", "x2"])
    figure = app_state.ax.figure

    assert marginal_axes_attached_to(figure), "the render attached the marginals"
    engine = figure.get_layout_engine()
    assert engine is None or "Constrained" not in type(engine).__name__, (
        "constrained layout collapses divider axes, so it must stay off while they are attached"
    )
    # And they really are laid out, not zero-sized.
    widths = [axes.get_position().width for axes in figure.axes[1:]]
    assert all(width > 0.01 for width in widths), f"marginal axes have a real size, got {widths}"


def test_a_missing_grouping_column_keeps_the_chosen_groups(ready, monkeypatch) -> None:
    """The failure used to be swallowed and the user's group selection cleared with it."""
    from application.use_cases.render_plot import RenderPlotUseCase

    state_gateway.set_visible_groups(["A"])
    use_case = RenderPlotUseCase.__new__(RenderPlotUseCase)
    use_case._df_global = lambda: ready
    written: list[list[str]] = []
    use_case._state_write = type(
        "Recorder", (), {"sync_available_and_visible_groups": staticmethod(lambda groups: written.append(list(groups)))}
    )()

    use_case._sync_visible_groups("NotAColumn")

    assert written == [], "nothing is written when the column is missing"
    assert app_state.visible_groups == ["A"], "the user's selection is untouched"
