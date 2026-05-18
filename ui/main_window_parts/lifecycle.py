"""Lifecycle and application actions mixin for main window."""
from __future__ import annotations

import logging

from PyQt5.QtCore import QSettings, Qt
from PyQt5.QtWidgets import QDockWidget

from core import app_state, state_gateway, translate

logger = logging.getLogger(__name__)


class MainWindowLifecycleMixin:
    """Window lifecycle methods and action callbacks."""

    def _refresh_plot(self):
        self._apply_legend_panel_layout()
        try:
            from visualization.events import on_slider_change

            on_slider_change()
        except Exception:
            pass

    def _restore_state(self):
        """恢复窗口状态"""
        settings = QSettings("IsotopesAnalyse", "MainWindow")
        if settings.contains("geometry"):
            self.restoreGeometry(settings.value("geometry"))
        if settings.contains("state"):
            self.restoreState(settings.value("state"))

    def save_state(self):
        """保存窗口状态"""
        settings = QSettings("IsotopesAnalyse", "MainWindow")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("state", self.saveState())

    def closeEvent(self, event):
        """关闭事件处理"""
        self.save_state()

        from core import save_session_params

        try:
            save_session_params(
                algorithm=app_state.algorithm,
                umap_params=app_state.umap_params,
                tsne_params=app_state.tsne_params,
                point_size=app_state.point_size,
                group_col=app_state.last_group_col or "Province",
                group_cols=app_state.group_cols,
                data_cols=app_state.data_cols,
                file_path=app_state.file_path,
                sheet_name=app_state.sheet_name,
                render_mode=app_state.render_mode,
                selected_2d_cols=getattr(app_state, "selected_2d_cols", []),
                selected_3d_cols=app_state.selected_3d_cols,
                language=app_state.language,
                tooltip_columns=getattr(app_state, "tooltip_columns", None),
                ui_theme=getattr(app_state, "ui_theme", "Modern Light"),
            )
        except Exception as e:
            logger.warning("Failed to save session: %s", e)

        event.accept()

    def add_dock_widget(self, area, widget, title, allowed_areas=Qt.AllDockWidgetAreas):
        """添加停靠窗口"""
        dock = QDockWidget(title, self)
        dock.setObjectName(title.replace(" ", ""))
        dock.setWidget(widget)
        dock.setAllowedAreas(allowed_areas)
        self.addDockWidget(area, dock)
        self.dock_widgets.append(dock)
        return dock

    def _reload_data(self):
        """重新加载数据"""
        from application.use_cases import load_dataset

        if load_dataset(show_file_dialog=True, show_config_dialog=True):
            self.statusBar().showMessage(translate("Data reloaded successfully"), 3000)
            self._refresh_status_info()
            if not app_state.last_group_col and app_state.group_cols:
                state_gateway.set_last_group_col(app_state.group_cols[0])
            if hasattr(self, "on_data_reload"):
                self.on_data_reload()
            else:
                try:
                    from visualization.events import on_slider_change

                    on_slider_change()
                except Exception as exc:
                    logger.warning("Failed to refresh plot after reload: %s", exc)
        else:
            self.statusBar().showMessage(translate("Failed to reload data"), 3000)

    def _show_section_dialog(self, section_key):
        """打开指定分区对话框"""
        if not hasattr(self, "_section_dialogs"):
            self._section_dialogs = {}

        dialog = self._section_dialogs.get(section_key)
        if dialog is None:
            from ui.control_panel import create_section_dialog
            from visualization.events import on_slider_change

            dialog = create_section_dialog(section_key, on_slider_change, parent=self)
            if dialog is None:
                return
            self._section_dialogs[section_key] = dialog

        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _connect_event_handlers(self, canvas):
        """连接事件处理器"""
        from visualization.events import on_click, on_hover, on_legend_click

        canvas.mpl_connect("motion_notify_event", on_hover)
        canvas.mpl_connect("button_press_event", on_click)
        canvas.mpl_connect("button_press_event", on_legend_click)

        logger.info("Event handlers connected successfully")
