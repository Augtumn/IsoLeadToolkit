"""Lifecycle and application actions mixin for main window."""
from __future__ import annotations
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLineEdit, QPlainTextEdit, QTextEdit

import logging

from PyQt5.QtCore import QSettings, Qt
from PyQt5.QtWidgets import QDockWidget, QFileDialog, QMessageBox

from core import app_state, state_gateway, translate

#: Methods this class expects from the classes it is composed with
#: (explicit interface, UI review item I).
REQUIRES_MainWindowLifecycleMixin = (
    "_apply_legend_panel_layout",
    "_refresh_status_info",
    "_sync_selection_tool_actions",
)

logger = logging.getLogger(__name__)


class MainWindowLifecycleMixin:
    """Window lifecycle methods and action callbacks."""

    legend_search_edit = None

    def keyPressEvent(self, event):
        """Keyboard interaction for the plot window.

        Escape cancels the active selection tool (and then the selection itself), Delete
        removes the selected samples, Ctrl+F jumps to the legend search box. Keys are never
        stolen from a text field the user is typing in - there Escape only clears the field.
        """
        import logging

        from core import app_state, state_gateway

        key = event.key()
        modifiers = event.modifiers()
        focus = self.focusWidget()
        typing = isinstance(focus, (QLineEdit, QPlainTextEdit, QTextEdit))

        if key == Qt.Key_F and modifiers & Qt.ControlModifier:
            search = self.legend_search_edit
            if search is not None:
                search.setFocus(Qt.ShortcutFocusReason)
                search.selectAll()
                event.accept()
                return

        if typing:
            if key == Qt.Key_Escape:
                focus.clear()
                event.accept()
                return
            super().keyPressEvent(event)
            return

        if key == Qt.Key_Escape:
            if app_state.selection_tool:
                state_gateway.set_selection_tool(None)
                self._sync_selection_tool_actions()
                logging.getLogger(__name__).info("Selection tool cancelled with Escape.")
                event.accept()
                return
            if app_state.selected_indices:
                state_gateway.clear_selected_indices()
                event.accept()
                return

        if key in (Qt.Key_Delete, Qt.Key_Backspace):
            indices = list(app_state.selected_indices or [])
            if indices:
                state_gateway.remove_selected_indices(indices)
                logging.getLogger(__name__).info("Removed %d selected sample(s).", len(indices))
                event.accept()
                return

        super().keyPressEvent(event)

    _section_dialogs = None

    # Declared by the class that uses them, so no probe is needed for widgets
    # that build() creates later (UI review item B).

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
        except Exception as err:
            logger.warning("_import_session failed: %s", err)
        # restore_snapshot bypasses dispatch, so refresh the mode label here.
        self._refresh_status_info()

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
        except Exception as err:
            logger.warning("_refresh_plot failed: %s", err)

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
            state_gateway.set_group_reveal_callback(self._reveal_group_in_legend)
            try:
                from visualization.events import on_slider_change

                on_slider_change()
            except Exception as exc:
                logger.warning("Failed to refresh plot after reload: %s", exc)
        else:
            self.statusBar().showMessage(translate("Failed to reload data"), 3000)

    def _show_section_dialog(self, section_key):
        """打开指定分区对话框"""
        if not self._section_dialogs is not None:
            self._section_dialogs = {}

        dialog = self._section_dialogs.get(section_key)
        if dialog is None:
            from ui.sections import create_section_dialog
            from visualization.events import on_slider_change

            dialog = create_section_dialog(section_key, on_slider_change, parent=self)
            if dialog is None:
                return
            self._section_dialogs[section_key] = dialog

        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
