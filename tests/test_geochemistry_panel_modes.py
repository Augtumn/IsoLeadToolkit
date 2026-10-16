"""The geochemistry controls follow the render mode while the panel is open."""
from __future__ import annotations

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


def test_the_plumbotectonics_model_offers_all_three(qapp) -> None:
    """The three datasets are what the panel is for; the control has to offer them."""
    panel, _widget = _panel()
    try:
        state_gateway.set_render_mode("PLUMBOTECTONICS_76")
        texts = [
            panel.plumbotectonics_model_combo.itemText(index)
            for index in range(panel.plumbotectonics_model_combo.count())
        ]
        assert len(texts) >= 3, f"three models, got {texts}"
        assert not any("No plumbotectonics data" in text for text in texts), f"got {texts}"
    finally:
        app_state.unregister_render_mode_listener(panel._on_render_mode_changed)
