"""Lifecycle and application actions mixin for main window."""
from __future__ import annotations

import logging

from PyQt5.QtCore import QSettings, Qt
from PyQt5.QtWidgets import QDockWidget, QFileDialog, QMessageBox

from core import app_state, state_gateway, translate

logger = logging.getLogger(__name__)


class MainWindowLifecycleMixin:
    """Window lifecycle methods and action callbacks."""

    def _session_archive_filter(self) -> str:
        return translate("Isotope Session Archive (*.zip)")

    def _export_session(self) -> None:
        """Export the current session (config + loaded data) to a ZIP archive."""
        default_path = f"{app_state.file_path or 'session'}.session.zip"
        path, _ = QFileDialog.getSaveFileName(
            self,
            translate("Export Session..."),
            default_path,
            self._session_archive_filter(),
        )
        if not path:
            return
        if not path.lower().endswith(".zip"):
            path += ".zip"
        try:
            from application.use_cases import export_session

            if export_session(path):
                logger.info("Session exported to %s", path)
                self.statusBar().showMessage(
                    translate("Session exported to {path}").format(path=path),
                    5000,
                )
            else:
                QMessageBox.warning(
                    self,
                    translate("Export Session..."),
                    translate("Failed to export session: {error}").format(
                        error=translate("Unknown error")
                    ),
                )
        except Exception as exc:
            logger.exception("Session export failed")
            QMessageBox.warning(
                self,
                translate("Export Session..."),
                translate("Failed to export session: {error}").format(error=exc),
            )

    def _import_session(self) -> None:
        """Import a session archive (config + optional data) into the app."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            translate("Import Session..."),
            "",
            self._session_archive_filter(),
        )
        if not path:
            return
        reply = QMessageBox.question(
            self,
            translate("Import Session"),
            translate("Importing a session will replace current settings. Continue?"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            from application.use_cases import import_session

            ok, flag = import_session(path)
        except Exception as exc:
            logger.exception("Session import failed")
            QMessageBox.warning(
                self,
                translate("Import Session"),
                translate("Failed to import session: {error}").format(error=exc),
            )
            return

        if not ok:
            QMessageBox.warning(
                self,
                translate("Import Session"),
                translate(
                    "The session file is not valid or was created by a newer version."
                ),
            )
            return

        # Refresh the plot with the imported data/settings.
        self._refresh_plot()
        try:
            from core import save_all

            save_all(state_gateway)
        except Exception:
            pass
        # restore_snapshot bypasses dispatch, so refresh the mode label here.
        try:
            self._refresh_status_info()
        except Exception:
            pass

        if flag == "data_failed":
            QMessageBox.warning(
                self,
                translate("Import Session"),
                translate(
                    "Session settings were imported, but the saved data could "
                    "not be restored."
                ),
            )
        else:
            QMessageBox.information(
                self,
                translate("Import Session"),
                translate("Session imported successfully."),
            )

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

        # Stop background embedding work before the event loop exits so a
        # still-running QThread is not destroyed while running.
        try:
            from visualization.events import shutdown_embedding_worker

            shutdown_embedding_worker()
        except Exception as exc:
            logger.warning("Failed to stop embedding worker: %s", exc)

        from core import mark_clean_exit, save_all

        try:
            if save_all(state_gateway):
                logger.info("Session + UI state saved on exit")
            else:
                logger.warning("Failed to save state on exit")
        except Exception as e:
            logger.warning("Failed to save session: %s", e)
        finally:
            # A user-initiated close is a clean exit even when the save
            # itself failed; without the marker the next startup would
            # wrongly report a crash.
            mark_clean_exit()

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
            # Ensure legend callback is connected after data reload
            state_gateway.set_legend_update_callback(self._update_legend_panel)
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
