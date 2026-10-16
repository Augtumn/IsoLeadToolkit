"""The geochemistry controls follow the render mode while the panel is open."""
from __future__ import annotations

import pandas as pd
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import QApplication

from core import app_state, state_gateway
from ui.panels.geochemistry.panel import GeoPanel


def _panel() -> tuple[GeoPanel, object]:
    """The panel and the widget it built, shown: isVisible() is false while an ancestor is hidden."""
    panel = GeoPanel(lambda *args, **kwargs: None)
    widget = panel.build()
    widget.show()
    QApplication.processEvents()
    return panel, widget


def test_the_controls_follow_the_mode_the_panel_was_not_built_in(qapp) -> None:
    """Reported: Plumbotectonics has three models and the panel had them all removed.

    Which controls apply depends on the render mode, and the panel only worked that out when it was
    built - so a Plumbotectonics mode reached from another one showed none of its controls.
    """
    panel, _widget = _panel()
    try:
        state_gateway.set_render_mode("UMAP")
        assert panel.geochem_plot_group.isVisible() is False, "not a geochemistry mode"

        state_gateway.set_render_mode("PLUMBOTECTONICS_76")
        assert panel.geochem_plot_group.isVisible() is True, "the mode now in force shows its controls"
        assert panel.plumbotectonics_model_combo.isVisible() is True

        state_gateway.set_render_mode("PLUMBOTECTONICS_86")
        assert panel.plumbotectonics_model_combo.isVisible() is True

        # A Pb evolution mode owns the same group but not the Plumbotectonics model choice.
        state_gateway.set_render_mode("PB_EVOL_86")
        assert panel.geochem_plot_group.isVisible() is True
        assert panel.plumbotectonics_model_combo.isVisible() is False

        state_gateway.set_render_mode("2D")
        assert panel.geochem_plot_group.isVisible() is False, "and it goes away outside them"
    finally:
        app_state.unregister_render_mode_listener(panel._on_render_mode_changed)


def test_every_plumbotectonics_mode_draws_its_curves(qapp) -> None:
    """The point of the panel: both modes, with every one of the three datasets."""
    from visualization.plotting.geochem.plumbotectonics_metadata import (
        get_plumbotectonics_variants,
    )
    from visualization.plotting.rendering.embedding_plot import plot_embedding

    frame = pd.DataFrame(
        {
            "Site": ["A", "A", "B", "B", "C", "C"],
            "206Pb/204Pb": [18.1, 18.3, 18.5, 18.7, 19.0, 19.2],
            "207Pb/204Pb": [15.5, 15.55, 15.6, 15.62, 15.65, 15.7],
            "208Pb/204Pb": [38.2, 38.3, 38.4, 38.5, 38.6, 38.7],
        }
    )
    state_gateway.set_dataframe_and_source(frame, file_path="x", sheet_name="s")
    state_gateway.set_group_data_columns(
        ["Site"], ["206Pb/204Pb", "207Pb/204Pb", "208Pb/204Pb"]
    )
    state_gateway.set_last_group_col("Site")
    state_gateway.set_visible_groups(None)
    state_gateway.set_show_plumbotectonics_curves(True)

    variants = get_plumbotectonics_variants()
    assert len(variants) >= 3, f"the three datasets, got {variants}"

    for mode in ("PLUMBOTECTONICS_76", "PLUMBOTECTONICS_86"):
        for key, _label in variants:
            figure = Figure()
            canvas = FigureCanvas(figure)
            canvas.resize(500, 400)
            state_gateway.set_figure(figure)
            state_gateway.set_render_mode(mode)
            state_gateway.set_plumbotectonics_variant(key)

            assert plot_embedding("Site", mode) is True, f"{mode} renders"
            assert app_state.ax.lines, f"{mode} with variant {key} drew its curves"
            assert app_state.scatter_collections, f"{mode} drew the data too"

