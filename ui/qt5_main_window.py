"""
Qt5 主窗口基类
提供标准的应用程序窗口框架
"""
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout,
                              QHBoxLayout, QDockWidget, QToolBar,
                              QStatusBar, QMenuBar, QAction)
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

        self.main_layout.addWidget(self.canvas_widget)

        # 浮动dock区域
        self.dock_widgets = []

    def _setup_menubar(self):
        """设置菜单栏"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu(translate("File"))

        reload_action = QAction(translate("Reload Data"), self)
        reload_action.setShortcut(QKeySequence("Ctrl+R"))
        reload_action.triggered.connect(self._reload_data)
        file_menu.addAction(reload_action)

        file_menu.addSeparator()

        exit_action = QAction(translate("Exit"), self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 视图菜单
        view_menu = menubar.addMenu(translate("View"))

        control_panel_action = QAction(translate("Control Panel"), self)
        control_panel_action.setShortcut(QKeySequence("Ctrl+P"))
        control_panel_action.triggered.connect(self._show_control_panel)
        view_menu.addAction(control_panel_action)

    def _setup_toolbar(self):
        """设置工具栏"""
        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(DEFAULT_TOOLBAR_ICON_SIZE)
        self.addToolBar(self.toolbar)

        # 控制面板按钮
        control_panel_action = QAction(translate("Control Panel"), self)
        control_panel_action.triggered.connect(self._show_control_panel)
        self.toolbar.addAction(control_panel_action)

    def _setup_statusbar(self):
        """设置状态栏"""
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

        # 添加到布局
        self.canvas_layout.addWidget(toolbar)
        self.canvas_layout.addWidget(canvas)

        # 保存引用
        app_state.fig = fig
        app_state.canvas = canvas

        # 连接事件处理器
        self._connect_event_handlers(canvas)

    def _reload_data(self):
        """重新加载数据"""
        from data.qt5_loader import load_data
        if load_data(show_file_dialog=True, show_config_dialog=True):
            self.statusBar().showMessage(translate("Data reloaded successfully"), 3000)
            # 触发重绘
            if hasattr(self, 'on_data_reload'):
                self.on_data_reload()
        else:
            self.statusBar().showMessage(translate("Failed to reload data"), 3000)

    def _show_control_panel(self):
        """显示控制面板"""
        if self.control_panel:
            self.control_panel.show()
            self.control_panel.raise_()
            self.control_panel.activateWindow()

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
