"""Data panel grouping and utility behavior mixin."""
from __future__ import annotations

import logging

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)

from core import app_state, state_gateway, translate

logger = logging.getLogger(__name__)


class DataPanelGroupingMixin:
    """Grouping and tooltip handlers for data panel."""
    legend_panel = None

    # Declared by the class that uses them, so no probe is needed for widgets
    # that build() creates later (UI review item B).

    def _update_group_list(self):
        panel = self.legend_panel
        if panel is not None and hasattr(panel, "_update_group_list"):
            panel._update_group_list()

    def _sync_geochem_model_for_mode(self, mode):
        try:
            from application.use_cases import geochemistry as geochem_usecase
        except Exception:
            return

        target_model = None
        if mode == "V1V2":
            target_model = "V1V2 (Zhu 1993)"
        elif mode in ("PB_EVOL_76", "PB_EVOL_86", "PB_MU_AGE", "PB_KAPPA_AGE"):
            target_model = "Stacey & Kramers (2nd Stage)"

        if not target_model:
            return

        current_model = geochem_usecase.get_current_model_name()
        if current_model == target_model:
            return

        # In dialog mode, DataPanel and GeoPanel are opened separately,
        # so DataPanel may not hold a live geo_model_combo reference.
        available_models = geochem_usecase.get_available_models()
        if target_model not in available_models:
            return

        if geochem_usecase.load_preset(target_model):
            state_gateway.set_geo_model_name(target_model)

    def _refresh_group_column_radios(self):
        """Refresh grouping column radio buttons."""
        if self.group_radio_layout is None:
            return

        while self.group_radio_layout.count():
            item = self.group_radio_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)

        if self.group_radio_group is not None:
            for btn in list(self.group_radio_group.buttons()):
                self.group_radio_group.removeButton(btn)

        self.group_placeholder_label = None

        if app_state.group_cols:
            if app_state.last_group_col not in app_state.group_cols:
                state_gateway.set_last_group_col(app_state.group_cols[0])
                state_gateway.set_visible_groups(None)

            for col in app_state.group_cols:
                btn = QRadioButton(col)
                btn.setChecked(col == app_state.last_group_col)
                btn.setProperty("group_col", col)
                self.group_radio_group.addButton(btn)
                self.group_radio_layout.addWidget(btn)
        else:
            placeholder = QLabel(translate("Load data to unlock grouping options."))
            placeholder.setWordWrap(True)
            self.group_radio_layout.addWidget(placeholder)
            self.group_placeholder_label = placeholder

    def _on_group_col_selected(self, button):
        """Handle grouping column selection changes."""
        if button is None:
            return

        col = button.property("group_col") or button.text()
        if col and app_state.last_group_col != col:
            state_gateway.set_last_group_col(col)
            state_gateway.set_visible_groups(None)
            self._update_group_list()
            self._on_change()

    def _on_configure_group_columns(self):
        """Open group column selection dialog."""
        if app_state.df_global is None:
            QMessageBox.warning(self, translate("Warning"), translate("Please load data first."))
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(translate("Group Columns Configuration"))
        dialog.resize(420, 520)

        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(translate("Select columns to use for grouping:")))

        list_widget = QListWidget()
        list_widget.setSelectionMode(QListWidget.MultiSelection)
        layout.addWidget(list_widget, 1)

        current = set(app_state.group_cols or [])
        for col in list(app_state.df_global.columns):
            item = QListWidgetItem(str(col))
            item.setData(Qt.UserRole, col)
            if col in current:
                item.setSelected(True)
            list_widget.addItem(item)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton(translate("Cancel"))
        cancel_btn.clicked.connect(dialog.reject)
        btn_row.addWidget(cancel_btn)
        apply_btn = QPushButton(translate("Apply"))

        def _apply():
            selected = [item.data(Qt.UserRole) for item in list_widget.selectedItems()]
            if not selected:
                QMessageBox.warning(
                    self,
                    translate("Validation Error"),
                    translate("Please select at least one grouping column."),
                )
                return
            state_gateway.set_group_data_columns(selected, list(app_state.data_cols or []))
            if app_state.last_group_col not in app_state.group_cols:
                state_gateway.set_last_group_col(app_state.group_cols[0])
                state_gateway.set_visible_groups(None)

            self._refresh_group_column_radios()
            self._update_group_list()
            self._on_change()
            dialog.accept()

        apply_btn.clicked.connect(_apply)
        btn_row.addWidget(apply_btn)
        layout.addLayout(btn_row)

        dialog.exec_()

    def _normalize_algorithm(self, algorithm):
        """Normalize algorithm aliases."""
        if not algorithm:
            return "UMAP"
        value = str(algorithm)
        if value in ("t-SNE", "TSNE", "tSNE"):
            return "tSNE"
        return value

    def _on_tooltip_change(self, state):
        """Handle tooltip visibility change."""
        state_gateway.set_show_tooltip(state == Qt.Checked)
        self._on_change()

    def _on_configure_tooltip(self):
        """Open tooltip configuration dialog."""
        try:
            from ui.panels.data.dialogs.tooltip_dialog import get_tooltip_configuration

            result = get_tooltip_configuration(self)
            if result:
                state_gateway.set_tooltip_columns(result)
                logger.info("Tooltip columns configured: %s", result)
                self._on_change()
        except Exception as exc:
            logger.error("Failed to open tooltip configuration dialog: %s", exc)
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Failed to open tooltip configuration: {error}").format(error=str(exc)),
            )
