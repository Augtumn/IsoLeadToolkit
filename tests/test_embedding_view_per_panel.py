"""A panel's view survives a refresh, whichever mode its neighbours are drawn in."""
from __future__ import annotations

import pandas as pd
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from core import app_state, state_gateway
from ui.main_window_parts.mdi_panels import PanelWindows, create_mdi_area


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Site": ["A", "A", "B", "B", "C", "C"],
            "206Pb/204Pb": [18.1, 18.3, 18.5, 18.7, 19.0, 19.2],
            "207Pb/204Pb": [15.5, 15.55, 15.6, 15.62, 15.65, 15.7],
            "208Pb/204Pb": [38.2, 38.3, 38.4, 38.5, 38.6, 38.7],
        }
    )


def _render(mode: str, record) -> bool:
    from visualization.plotting.rendering.embedding_plot import plot_embedding

    state_gateway.set_figure(record["figure"])
    state_gateway.set_axis(record["axes"])
    return plot_embedding("Site", mode)


def test_a_panel_keeps_its_view_when_a_neighbour_renders_another_mode(qapp) -> None:
    """Reported: ticking a group under the Pb evolution plot reset the zoom.

    The renderer decided whether to restore the view by asking what the application drew last - a
    single value. With several panels that value belongs to whichever panel rendered before, so the
    panel whose mode had not changed was not recognised and its view was dropped.
    """
    state_gateway.set_dataframe_and_source(_frame(), file_path="x", sheet_name="s")
    state_gateway.set_group_data_columns(
        ["Site"], ["206Pb/204Pb", "207Pb/204Pb", "208Pb/204Pb"]
    )
    state_gateway.set_last_group_col("Site")
    state_gateway.set_visible_groups(None)

    area = create_mdi_area(None)
    area.resize(1000, 700)
    area.show()
    panels = PanelWindows(area)
    try:
        records = panels.sync(["PB_EVOL_86", "PB_EVOL_76"])
        app_state.plot_panel_windows[:] = records

        assert _render("PB_EVOL_86", records[0]) is True
        assert _render("PB_EVOL_76", records[1]) is True

        records[0]["axes"].set_xlim(17.0, 19.0)
        records[1]["axes"].set_xlim(18.0, 20.0)

        # What ticking a legend group does: every panel is rendered again, in order.
        _render("PB_EVOL_86", records[0])
        _render("PB_EVOL_76", records[1])

        assert tuple(round(float(value), 2) for value in records[0]["axes"].get_xlim()) == (
            17.0,
            19.0,
        ), "the first panel keeps the view the user gave it"
        assert tuple(round(float(value), 2) for value in records[1]["axes"].get_xlim()) == (
            18.0,
            20.0,
        ), "and so does the second, whose mode is its own"
    finally:
        app_state.plot_panel_windows[:] = []
        area.close()
