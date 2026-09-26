"""Data panel build mixin."""
from __future__ import annotations

import logging

from PyQt5.QtWidgets import (
    QToolBox,
    QVBoxLayout,
    QWidget,
)

from .coloring_build import DataPanelColoringBuildMixin
from .projection_build import DataPanelProjectionBuildMixin
from .render_build import DataPanelRenderBuildMixin
from core import translate

#: Methods this class expects from the classes it is composed with
#: (explicit interface, UI review item I).
REQUIRES_DataPanelBuildMixin = (
    "_build_axis_selection",
    "_build_coloring_grouping",
    "_build_projection_params",
    "_build_render_controls",
    "_build_v1v2_params",
    "_restore_toolbox_state",
    "_set_combo_value",
    "_update_algorithm_visibility",
)

logger = logging.getLogger(__name__)


class DataPanelBuildMixin(
    DataPanelColoringBuildMixin,
    DataPanelProjectionBuildMixin,
    DataPanelRenderBuildMixin,
):
    """Construct and initialize the data panel UI."""
    ternary_limit_mode_combo = None

    # Declared by the class that uses them, so no probe is needed for widgets
    # that build() creates later (UI review item B).

    def __init__(self, callback=None, parent=None):
        super().__init__(callback, parent)
        self.legend_panel = None

    def reset_state(self):
        super().reset_state()
        self.group_radio_group = None
        self.group_radio_layout = None
        self.group_placeholder_label = None
        self.tooltip_check = None
        self.render_combo = None
        self.algo_combo = None
        self.algo_group = None
        self.umap_group = None
        self.tsne_group = None
        self.pca_group = None
        self.robust_pca_group = None
        self.ternary_group = None
        self.ternary_auto_zoom_check = None
        self.ternary_limit_mode_combo = None
        self.ternary_manual_limits_check = None
        self.ternary_limit_spins = {}
        self.ternary_render_margin_spin = None
        self.spinboxes = {}
        self.v1v2_group = None
        self.v1v2_t1_spin = None
        self.v1v2_t2_spin = None
        self.twod_group = None
        self.xaxis_combo = None
        self.yaxis_combo = None
        self.pca_x_spin = None
        self.pca_y_spin = None
        self.rpca_x_spin = None
        self.rpca_y_spin = None
        self.metric_combo = None
        self.plumbotectonics_model_keys = []

    def _update_translations(self, root: QWidget | None = None) -> None:
        """Refresh translated widget text and ternary mode combo options."""
        super()._update_translations(root)

        combo = self.ternary_limit_mode_combo
        if combo is not None:
            current_mode = str(combo.currentData()).strip().lower() if combo.currentData() is not None else "min"
            if current_mode not in ("min", "max", "both"):
                current_mode = "min"

            combo.blockSignals(True)
            combo.clear()
            combo.addItem(translate("Minimum Only"), "min")
            combo.addItem(translate("Maximum Only"), "max")
            combo.addItem(translate("Both Ends"), "both")
            self._set_combo_value(combo, current_mode)
            combo.blockSignals(False)

    def build(self) -> QWidget:
        widget = self._build_data_section()
        self._is_initialized = True
        return widget

    def _build_data_section(self):
        """Construct data tab content."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        section_toolbox = QToolBox()
        section_toolbox.setObjectName("data_section_toolbox")

        basics_page = QWidget()
        basics_layout = QVBoxLayout(basics_page)
        basics_layout.setContentsMargins(6, 6, 6, 6)
        basics_layout.setSpacing(8)

        self._build_coloring_grouping(basics_layout)

        projection_widget = self._build_projection_section()
        section_toolbox.addItem(basics_page, translate("Coloring / Grouping"))
        section_toolbox.addItem(projection_widget, translate("Render Mode"))

        self._restore_toolbox_state(section_toolbox, 'data')
        layout.addWidget(section_toolbox)
        layout.addStretch()
        return widget

    def _build_projection_section(self):
        """Construct projection controls."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)

        self._build_render_controls(layout)
        self._build_projection_params(layout)
        self._build_v1v2_params(layout)
        self._build_axis_selection(layout)

        self._update_algorithm_visibility()

        layout.addStretch()
        return widget


