"""
Qt5 主窗口基类
提供标准的应用程序窗口框架
"""
from pathlib import Path

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout,
                              QHBoxLayout, QDockWidget, QToolBar,
                              QStatusBar, QMenuBar, QAction, QStyle,
                              QSplitter)
from PyQt5.QtCore import Qt, QSize, QSettings
from PyQt5.QtGui import QIcon, QFont, QKeySequence

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt

from core import app_state, translate

# 默认图标尺寸
DEFAULT_TOOLBAR_ICON_SIZE = QSize(24, 24)


class Qt5MainWindow(QMainWindow):
    """Qt5 主窗口基类"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.control_panel = None
        self._setup_ui()
        self._setup_menubar()
        self._setup_toolbar()
        self._setup_statusbar()
        self._restore_state()

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
        self.canvas_layout = QVBoxLayout(self.canvas_widget)
        self.canvas_layout.setContentsMargins(0, 0, 0, 0)
        self.canvas_layout.setSpacing(0)

        self.panel_container = QWidget()
        self.panel_layout = QVBoxLayout(self.panel_container)
        self.panel_layout.setContentsMargins(0, 0, 0, 0)
        self.panel_layout.setSpacing(0)
        self.panel_container.setVisible(False)

        self.main_splitter = QSplitter(Qt.Vertical)
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.addWidget(self.panel_container)
        self.main_splitter.addWidget(self.canvas_widget)
        self.main_layout.addWidget(self.main_splitter)

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

        exit_action = QAction(translate("Exit"), self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        self.file_menu.addAction(exit_action)

        data_action = QAction(translate("Data"), self)
        data_action.triggered.connect(lambda: self._show_section_dialog('data'))
        menubar.addAction(data_action)

        display_action = QAction(translate("Display"), self)
        display_action.triggered.connect(lambda: self._show_section_dialog('display'))
        menubar.addAction(display_action)

        analysis_action = QAction(translate("Analysis"), self)
        analysis_action.triggered.connect(lambda: self._show_section_dialog('analysis'))
        menubar.addAction(analysis_action)

        export_action = QAction(translate("Export"), self)
        export_action.triggered.connect(lambda: self._show_section_dialog('export'))
        menubar.addAction(export_action)

        legend_action = QAction(translate("Legend"), self)
        legend_action.triggered.connect(lambda: self._show_section_dialog('legend'))
        menubar.addAction(legend_action)

        geo_action = QAction(translate("Geochemistry"), self)
        geo_action.triggered.connect(lambda: self._show_section_dialog('geochemistry'))
        menubar.addAction(geo_action)

        self._menu_actions = {
            'reload': reload_action,
            'exit': exit_action,
            'data': data_action,
            'display': display_action,
            'analysis': analysis_action,
            'export': export_action,
            'legend': legend_action,
            'geochemistry': geo_action,
        }

        try:
            app_state.register_language_listener(self._refresh_language)
        except Exception:
            pass

    def _setup_toolbar(self):
        """设置工具栏"""
        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(DEFAULT_TOOLBAR_ICON_SIZE)
        self.toolbar.setObjectName("MainToolbar")
        self.addToolBar(self.toolbar)

        # 控制面板按钮已弃用

    def _setup_statusbar(self):
        """设置状态栏"""
        self.statusBar().showMessage(translate("Ready"))

    def _refresh_language(self):
        """刷新菜单与状态栏语言"""
        if hasattr(self, 'file_menu'):
            self.file_menu.setTitle(translate("File"))
        actions = getattr(self, '_menu_actions', {})
        if 'reload' in actions:
            actions['reload'].setText(translate("Reload Data"))
        if 'exit' in actions:
            actions['exit'].setText(translate("Exit"))
        if 'data' in actions:
            actions['data'].setText(translate("Data"))
        if 'display' in actions:
            actions['display'].setText(translate("Display"))
        if 'analysis' in actions:
            actions['analysis'].setText(translate("Analysis"))
        if 'export' in actions:
            actions['export'].setText(translate("Export"))
        if 'legend' in actions:
            actions['legend'].setText(translate("Legend"))
        if 'geochemistry' in actions:
            actions['geochemistry'].setText(translate("Geochemistry"))
        if self.statusBar() is not None:
            self.statusBar().showMessage(translate("Ready"))

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

        # 保存会话参数
        from core import save_session_params
        try:
            save_session_params(
                algorithm=app_state.algorithm,
                umap_params=app_state.umap_params,
                tsne_params=app_state.tsne_params,
                point_size=app_state.point_size,
                group_col=app_state.last_group_col or 'Province',
                group_cols=app_state.group_cols,
                data_cols=app_state.data_cols,
                file_path=app_state.file_path,
                sheet_name=app_state.sheet_name,
                render_mode=app_state.render_mode,
                selected_2d_cols=getattr(app_state, 'selected_2d_cols', []),
                selected_3d_cols=app_state.selected_3d_cols,
                language=app_state.language,
                tooltip_columns=getattr(app_state, 'tooltip_columns', None),
                ui_theme=getattr(app_state, 'ui_theme', 'Modern Light')
            )
        except Exception as e:
            print(f"[WARN] Failed to save session: {e}", flush=True)

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

    def set_matplotlib_figure(self, fig):
        """设置 matplotlib 图形"""
        # 清除旧的画布
        for i in reversed(range(self.canvas_layout.count())):
            widget = self.canvas_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        # 创建新画布
        canvas = FigureCanvas(fig)
        toolbar = NavigationToolbar(canvas, self)
        toolbar.setVisible(False)
        zoom_out_action = QAction(self._get_zoom_out_icon(), translate("Zoom Out"), self)
        zoom_out_action.setToolTip(translate("Zoom Out"))
        zoom_out_action.triggered.connect(self._zoom_out_view)

        zoom_action = None
        actions = toolbar.actions()
        for action in actions:
            if 'zoom' in (action.text() or '').lower():
                zoom_action = action
                break

        if zoom_action is not None:
            zoom_index = actions.index(zoom_action)
            if zoom_index + 1 < len(actions):
                toolbar.insertAction(actions[zoom_index + 1], zoom_out_action)
            else:
                toolbar.addAction(zoom_out_action)
        else:
            toolbar.addAction(zoom_out_action)

        rect_select_action = QAction(self._get_selection_icon("selection_rect.svg"), translate("Box Select"), self)
        rect_select_action.setToolTip(translate("Box Select"))
        rect_select_action.setCheckable(True)
        rect_select_action.triggered.connect(lambda: self._toggle_selection_tool('export'))

        lasso_select_action = QAction(self._get_selection_icon("selection_polygon.svg"), translate("Lasso Select"), self)
        lasso_select_action.setToolTip(translate("Lasso Select"))
        lasso_select_action.setCheckable(True)
        lasso_select_action.triggered.connect(lambda: self._toggle_selection_tool('lasso'))

        toolbar.addSeparator()
        toolbar.addAction(rect_select_action)
        toolbar.addAction(lasso_select_action)

        self._selection_tool_actions = {
            'rect': rect_select_action,
            'lasso': lasso_select_action,
        }
        self._sync_selection_tool_actions()

        self._attach_matplotlib_toolbar_actions(toolbar)
        self.canvas_layout.addWidget(canvas)
        self.canvas_layout.addWidget(canvas)

        # 保存引用
        app_state.fig = fig
        app_state.canvas = canvas

        # 连接事件处理器
        self._connect_event_handlers(canvas)

    def set_control_panel(self, panel_widget):
        """Attach the control panel widget above the canvas."""
        for i in reversed(range(self.panel_layout.count())):
            widget = self.panel_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        if panel_widget is None:
            self.panel_container.setVisible(False)
            return

        self.panel_layout.addWidget(panel_widget)
        self.panel_container.setVisible(True)
        try:
            self.main_splitter.setSizes([320, 560])
        except Exception:
            pass

    def _attach_matplotlib_toolbar_actions(self, toolbar):
        self._clear_matplotlib_toolbar_actions()
        self._mpl_toolbar = toolbar
        actions = list(toolbar.actions())
        if not actions:
            return
        filtered = []
        for action in actions:
            if action is None:
                continue
            if action.isSeparator():
                filtered.append(action)
                continue
            text = (action.text() or '').strip()
            tooltip = (action.toolTip() or '').strip()
            has_icon = action.icon() is not None and not action.icon().isNull()
            if not text and not tooltip and not has_icon:
                continue
            filtered.append(action)

        for action in filtered:
            self.toolbar.addAction(action)
        self._mpl_toolbar_actions = filtered

    def _clear_matplotlib_toolbar_actions(self):
        actions = getattr(self, '_mpl_toolbar_actions', [])
        if not actions:
            return
        for action in actions:
            try:
                self.toolbar.removeAction(action)
            except Exception:
                pass
        self._mpl_toolbar_actions = []

    def _get_zoom_out_icon(self):
        """Resolve a zoom-out icon, falling back to a standard icon."""
        base_dir = Path(__file__).resolve().parent.parent
        svg_path = base_dir / "assets" / "icons" / "zoom_out.svg"
        if svg_path.exists():
            icon = QIcon(str(svg_path))
            if not icon.isNull():
                return icon
        for name in ("zoom-out", "view-zoom-out", "magnifier-zoom-out"):
            icon = QIcon.fromTheme(name)
            if not icon.isNull():
                return icon
        return self.style().standardIcon(QStyle.SP_TitleBarMinButton)

    def _get_selection_icon(self, filename):
        """Resolve selection tool icon from assets."""
        base_dir = Path(__file__).resolve().parent.parent
        svg_path = base_dir / "assets" / "icons" / filename
        if svg_path.exists():
            icon = QIcon(str(svg_path))
            if not icon.isNull():
                return icon
        return self.style().standardIcon(QStyle.SP_ArrowCursor)

    def _toggle_selection_tool(self, tool_type):
        try:
            from visualization.events import toggle_selection_mode
            toggle_selection_mode(tool_type)
        except Exception as exc:
            print(f"[WARN] Failed to toggle selection tool: {exc}", flush=True)
        self._sync_selection_tool_actions()

    def _sync_selection_tool_actions(self):
        actions = getattr(self, '_selection_tool_actions', None)
        if not actions:
            return
        current_tool = getattr(app_state, 'selection_tool', None)
        rect_checked = current_tool == 'export'
        lasso_checked = current_tool == 'lasso'
        actions['rect'].blockSignals(True)
        actions['lasso'].blockSignals(True)
        actions['rect'].setChecked(rect_checked)
        actions['lasso'].setChecked(lasso_checked)
        actions['rect'].blockSignals(False)
        actions['lasso'].blockSignals(False)

    def _zoom_out_view(self):
        """Zoom out the current axes view."""
        ax = getattr(app_state, 'ax', None)
        if ax is None:
            return
        try:
            xlim = ax.get_xlim()
            ylim = ax.get_ylim()
            x_range = xlim[1] - xlim[0]
            y_range = ylim[1] - ylim[0]
            if x_range == 0 or y_range == 0:
                return
            ax.set_xlim([xlim[0] - x_range * 0.25, xlim[1] + x_range * 0.25])
            ax.set_ylim([ylim[0] - y_range * 0.25, ylim[1] + y_range * 0.25])
            if app_state.fig is not None and app_state.fig.canvas is not None:
                app_state.fig.canvas.draw_idle()
        except Exception:
            pass

    def _reload_data(self):
        """重新加载数据"""
        from data.loader import load_data
        if load_data(show_file_dialog=True, show_config_dialog=True):
            self.statusBar().showMessage(translate("Data reloaded successfully"), 3000)
            if not app_state.last_group_col and app_state.group_cols:
                app_state.last_group_col = app_state.group_cols[0]
            # 触发重绘
            if hasattr(self, 'on_data_reload'):
                self.on_data_reload()
            else:
                try:
                    from visualization.events import on_slider_change
                    on_slider_change()
                except Exception as exc:
                    print(f"[WARN] Failed to refresh plot after reload: {exc}", flush=True)
        else:
            self.statusBar().showMessage(translate("Failed to reload data"), 3000)

    def _show_section_dialog(self, section_key):
        """打开指定分区对话框"""
        if not hasattr(self, '_section_dialogs'):
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
        from visualization.events import on_hover, on_click, on_legend_click

        # 连接 hover 事件
        canvas.mpl_connect('motion_notify_event', on_hover)

        # 连接 click 事件
        canvas.mpl_connect('button_press_event', on_click)

        # 连接 legend click 事件
        canvas.mpl_connect('button_press_event', on_legend_click)

        print("[INFO] Event handlers connected successfully", flush=True)
