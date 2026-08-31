"""UI setup mixin for main window."""
from __future__ import annotations

import logging
import os

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QAction,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QProgressBar,
    QPushButton,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from core import app_state, available_languages, set_language, state_gateway, translate

logger = logging.getLogger(__name__)
QT_DEBUG_MODE = os.environ.get("ISOTOPES_QT_DEBUG", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


class LegendListWidget(QListWidget):
    """Legend list widget with lightweight debug tracing for drag/drop.

    Drops are delegated to the main window handlers:
    - ``_legend_drop_handler`` — merge groups into parents / nest parents;
    - ``_legend_reorder_handler`` — plain reordering via legend_item_order.
    Qt's default InternalMove drop is bypassed so rows can never stack
    ("OnItem" ambiguity).
    """

    def startDrag(self, actions):
        # Remember which rows started the drag: during an internal move the
        # selection can change before dropEvent is delivered.
        self._dragging_items = list(self.selectedItems())
        super().startDrag(actions)

    def dropEvent(self, event):
        if QT_DEBUG_MODE:
            logger.debug("Legend dropEvent begin: count=%d", self.count())
        handler = getattr(self, "_legend_drop_handler", None)
        if handler is not None and handler(self, event):
            if QT_DEBUG_MODE:
                logger.debug("Legend dropEvent handled by parent-group handler")
            event.acceptProposedAction()
            return
        reorder = getattr(self, "_legend_reorder_handler", None)
        if reorder is not None and reorder(self, event):
            if QT_DEBUG_MODE:
                logger.debug("Legend dropEvent handled by reorder handler")
            event.acceptProposedAction()
            return
        super().dropEvent(event)
        if QT_DEBUG_MODE:
            logger.debug("Legend dropEvent end: count=%d", self.count())


class MainWindowSetupMixin:
    """Setup methods for main window widgets and menus."""

    def _setup_ui(self):
        """设置 UI 基本属性"""
        self.setWindowTitle("Isotopes Analyse")
        self.resize(1200, 800)
        self.setMinimumSize(800, 600)

        # 中央部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # 主布局
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Matplotlib 画布区域
        self.canvas_widget = QWidget()
        self.canvas_root_layout = QVBoxLayout(self.canvas_widget)
        self.canvas_root_layout.setContentsMargins(0, 0, 0, 0)
        self.canvas_root_layout.setSpacing(0)

        self.plot_container = QWidget()
        self.canvas_layout = QVBoxLayout(self.plot_container)
        self.canvas_layout.setContentsMargins(0, 0, 0, 0)
        self.canvas_layout.setSpacing(0)

        self.legend_panel = QWidget()
        legend_layout = QVBoxLayout(self.legend_panel)
        legend_layout.setContentsMargins(8, 8, 8, 8)
        legend_layout.setSpacing(6)
        legend_title = QLabel(translate("Legend"))
        legend_title.setProperty("keepStyle", True)  # survive _NativeStyleFilter
        legend_title.setStyleSheet("font-weight: bold;")
        legend_layout.addWidget(legend_title)

        # Legend settings entry (parents are created via context menu or by
        # dragging a parent row onto another parent row to nest it).
        settings_row = QWidget()
        settings_layout = QHBoxLayout(settings_row)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        settings_layout.setSpacing(4)
        self.legend_settings_btn = QPushButton(translate("Legend Settings..."))
        self.legend_settings_btn.setToolTip(translate("Open the full legend settings dialog"))
        self.legend_settings_btn.clicked.connect(self._open_legend_settings)
        settings_layout.addWidget(self.legend_settings_btn, 1)
        legend_layout.addWidget(settings_row)

        legend_list = LegendListWidget()
        legend_list.setSelectionMode(QAbstractItemView.SingleSelection)
        legend_list.setUniformItemSizes(False)
        legend_list.setIconSize(QSize(14, 14))
        legend_list.setDragDropMode(QAbstractItemView.InternalMove)
        legend_list.setDragDropOverwriteMode(False)
        legend_list.setDefaultDropAction(Qt.MoveAction)
        legend_list.setDragEnabled(True)
        legend_list.setAcceptDrops(True)
        legend_list.setDropIndicatorShown(True)
        legend_list.itemDoubleClicked.connect(self._on_legend_item_double_clicked)
        legend_list.setContextMenuPolicy(Qt.CustomContextMenu)
        legend_list.customContextMenuRequested.connect(self._show_legend_context_menu)
        legend_layout.addWidget(legend_list, 1)
        self.legend_panel.setMinimumWidth(160)
        self._legend_title_label = legend_title
        self._legend_list = legend_list
        legend_list._legend_drop_handler = self._handle_legend_drop
        legend_list._legend_reorder_handler = self._handle_legend_reorder
        try:
            legend_list.model().rowsMoved.connect(self._on_legend_rows_moved)
        except Exception as exc:
            logger.warning("Failed to connect legend rowsMoved signal: %s", exc)

        self.legend_splitter = QSplitter(Qt.Horizontal)
        self.legend_splitter.setChildrenCollapsible(False)
        self.legend_splitter.setOpaqueResize(False)
        self.legend_splitter.addWidget(self.legend_panel)
        self.legend_splitter.addWidget(self.plot_container)
        self.canvas_root_layout.addWidget(self.legend_splitter)
        self._apply_legend_panel_layout()

        self.main_layout.addWidget(self.canvas_widget)

        # 浮动dock区域
        self.dock_widgets = []

    def _setup_menubar(self):
        """设置菜单栏"""
        menubar = self.menuBar()
        self.menubar = menubar

        # 文件菜单
        self.file_menu = menubar.addMenu(translate("File"))

        reload_action = QAction(translate("Reload Data"), self)
        reload_action.setShortcut(QKeySequence("Ctrl+R"))
        reload_action.triggered.connect(self._reload_data)
        self.file_menu.addAction(reload_action)

        self.file_menu.addSeparator()

        export_session_action = QAction(translate("Export Session..."), self)
        export_session_action.triggered.connect(self._export_session)
        self.file_menu.addAction(export_session_action)

        import_session_action = QAction(translate("Import Session..."), self)
        import_session_action.triggered.connect(self._import_session)
        self.file_menu.addAction(import_session_action)

        self.file_menu.addSeparator()

        exit_action = QAction(translate("Exit"), self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        self.file_menu.addAction(exit_action)

        self.file_menu.addSeparator()

        log_action = QAction(translate("View Log..."), self)
        log_action.triggered.connect(self._show_log_viewer)
        self.file_menu.addAction(log_action)

        self._menu_actions = {
            "reload": reload_action,
            "exit": exit_action,
            "log": log_action,
            "export_session": export_session_action,
            "import_session": import_session_action,
        }

        panels_menu = menubar.addMenu(translate("Panels"))
        self.panels_menu = panels_menu

        for label, key, shortcut in [
            ("Data", "data", "Ctrl+D"),
            ("Display", "display", "Ctrl+Shift+D"),
            ("Analysis", "analysis", "Ctrl+Shift+A"),
            ("Export", "export", "Ctrl+E"),
            ("Legend", "legend", "Ctrl+L"),
            ("Geochemistry", "geochemistry", "Ctrl+G"),
        ]:
            action = QAction(translate(label), self)
            action.setShortcut(QKeySequence(shortcut))
            action.triggered.connect(lambda checked, k=key: self._show_section_dialog(k))
            panels_menu.addAction(action)
            self._menu_actions[key] = action

        menubar.addSeparator()

        self.lang_menu = menubar.addMenu(translate("Language"))
        for code, label in dict(available_languages()).items():
            lang_action = QAction(label, self)
            lang_action.triggered.connect(lambda checked, c=code: set_language(c))
            self.lang_menu.addAction(lang_action)

        try:
            app_state.register_language_listener(self._refresh_language)
        except Exception:
            pass

    def _show_log_viewer(self) -> None:
        """Open the in-app log viewer dialog."""
        try:
            from ui.dialogs.log_viewer import show_log_viewer

            show_log_viewer(self)
        except Exception as err:
            logger.warning("Failed to open log viewer: %s", err)

    def _setup_toolbar(self):
        """设置工具栏"""
        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(QSize(20, 20))
        self.toolbar.setObjectName("MainToolbar")
        self.addToolBar(self.toolbar)

    def _setup_statusbar(self):
        """设置状态栏，含异步嵌入计算进度条"""
        status_bar = self.statusBar()
        status_bar.showMessage(translate("Ready"))

        self._embedding_progress_bar = QProgressBar()
        self._embedding_progress_bar.setRange(0, 100)
        self._embedding_progress_bar.setValue(0)
        self._embedding_progress_bar.setTextVisible(True)
        self._embedding_progress_bar.setMaximumWidth(300)
        self._embedding_progress_bar.setMaximumHeight(18)
        self._embedding_progress_bar.hide()

        self._status_info_label = QLabel()
        self._status_info_label.setContentsMargins(4, 0, 8, 0)
        status_bar.addPermanentWidget(self._status_info_label)

        status_bar.addPermanentWidget(self._embedding_progress_bar)

        self._refresh_status_info()

        def _on_embedding_progress(percent: int, stage: str) -> None:
            bar = getattr(self, "_embedding_progress_bar", None)
            if bar is None:
                return
            if percent >= 100 or stage == "done":
                bar.hide()
                status_bar.showMessage(translate("Ready"))
                return
            stage_names = {
                "prepare": translate("Preparing..."),
                "umap_init": translate("UMAP Initializing..."),
                "umap_fit": translate("UMAP Computing..."),
                "tsne_init": translate("t-SNE Initializing..."),
                "tsne_fit": translate("t-SNE Computing..."),
                "pca_scale": translate("PCA Scaling..."),
                "pca_fit": translate("PCA Computing..."),
                "robust_scale": translate("Robust PCA Scaling..."),
                "robust_mcd_fit": translate("Robust PCA Computing..."),
                "robust_fallback_pca_fit": translate("Robust PCA Computing..."),
            }
            label = stage_names.get(stage, stage)
            bar.setFormat(f"{label}  %p%")
            bar.setValue(percent)
            bar.show()

        state_gateway.set_embedding_progress_callback(_on_embedding_progress)

    def _refresh_status_info(self) -> None:
        """Update status bar info label with current app state summary."""
        df = getattr(app_state, "df_global", None)
        if df is not None and len(df) > 0:
            n = len(df)
            # Show the user-friendly mode name (e.g. "Pb Evolution 206-207"
            # for the internal "PB_EVOL_76" code) via the locale table.
            mode = translate(str(getattr(app_state, "render_mode", "?")))
            group_cols = getattr(app_state, "group_cols", []) or []
            g = len(group_cols)
            text = translate(
                "Samples: {n} | Mode: {mode} | Groups: {g}",
                n=n, mode=mode, g=g,
            )
        else:
            text = translate("No data loaded")
        self._status_info_label.setText(text)

    def _apply_legend_panel_layout(self):
        try:
            location_key = getattr(app_state, "legend_location", None)
            if location_key not in {"outside_left", "outside_right"}:
                location_key = None
            is_outside = bool(location_key)
            if not hasattr(self, "legend_splitter"):
                return

            layout_state = (location_key, is_outside)
            if getattr(self, "_legend_layout_state", None) == layout_state:
                return

            self.legend_panel.setVisible(is_outside)
            if not is_outside:
                if hasattr(self, "_legend_list") and self._legend_list is not None:
                    self._legend_list.clear()
                self.legend_splitter.setSizes([0, 1])
                return

            if self.legend_splitter.orientation() != Qt.Horizontal:
                self.legend_splitter.setOrientation(Qt.Horizontal)
            first = self.legend_panel if location_key == "outside_left" else self.plot_container
            second = self.plot_container if location_key == "outside_left" else self.legend_panel

            if self.legend_splitter.indexOf(first) != 0:
                self.legend_splitter.insertWidget(0, first)
            if self.legend_splitter.indexOf(second) != 1:
                self.legend_splitter.insertWidget(1, second)

            self.legend_splitter.setStretchFactor(0, 0)
            self.legend_splitter.setStretchFactor(1, 1)

            sizes = self.legend_splitter.sizes()
            if len(sizes) >= 2 and min(sizes) == 0:
                self.legend_splitter.setSizes([200, 800])

            self._legend_layout_state = layout_state
        except Exception as exc:
            import traceback

            logger.error("Legend splitter layout failed: %s", exc)
            traceback.print_exc()

    def _refresh_language(self):
        """刷新菜单与状态栏语言"""
        if hasattr(self, "file_menu"):
            self.file_menu.setTitle(translate("File"))
        actions = getattr(self, "_menu_actions", {})
        if "reload" in actions:
            actions["reload"].setText(translate("Reload Data"))
        if "exit" in actions:
            actions["exit"].setText(translate("Exit"))
        if "log" in actions:
            actions["log"].setText(translate("View Log..."))
        if "export_session" in actions:
            actions["export_session"].setText(translate("Export Session..."))
        if "import_session" in actions:
            actions["import_session"].setText(translate("Import Session..."))
        if hasattr(self, "legend_settings_btn") and self.legend_settings_btn is not None:
            self.legend_settings_btn.setText(translate("Legend Settings..."))
        if "data" in actions:
            actions["data"].setText(translate("Data"))
        if "display" in actions:
            actions["display"].setText(translate("Display"))
        if "analysis" in actions:
            actions["analysis"].setText(translate("Analysis"))
        if "export" in actions:
            actions["export"].setText(translate("Export"))
        if "legend" in actions:
            actions["legend"].setText(translate("Legend"))
        if "geochemistry" in actions:
            actions["geochemistry"].setText(translate("Geochemistry"))
        if hasattr(self, "lang_menu"):
            self.lang_menu.setTitle(translate("Language"))
        if hasattr(self, "panels_menu"):
            self.panels_menu.setTitle(translate("Panels"))
        if self.statusBar() is not None:
            self.statusBar().showMessage(translate("Ready"))

        self._refresh_status_info()

        if hasattr(self, "_legend_title_label") and self._legend_title_label is not None:
            last_title = getattr(app_state, "legend_last_title", None)
            if last_title:
                self._legend_title_label.setText(str(last_title))
            else:
                self._legend_title_label.setText(translate("Legend"))
