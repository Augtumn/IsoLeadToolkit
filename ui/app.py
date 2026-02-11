"""
Qt5 应用程序类
管理应用初始化、生命周期和资源清理
"""
import sys
import warnings
import traceback
from PyQt5.QtWidgets import QApplication, QMessageBox, QWidget, QStyleFactory
from PyQt5.QtCore import Qt, QSettings, QTranslator, QLocale, QObject, QEvent
from PyQt5.QtGui import QFont, QIcon

from core import (CONFIG, app_state, load_session_params, save_session_params,
                  translate, set_language, validate_language)
from ui.main_window import Qt5MainWindow


def _clear_widget_styles(widget):
    if widget is None:
        return

    def _clear(target):
        if not isinstance(target, QWidget):
            return
        if target.property("keepStyle"):
            return
        if target.styleSheet():
            target.setStyleSheet("")

    _clear(widget)
    for child in widget.findChildren(QWidget):
        _clear(child)


class _NativeStyleFilter(QObject):
    """Clear per-widget stylesheets on show to keep native Qt styling."""

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Show:
            _clear_widget_styles(obj)
        return False


def _configure_matplotlib_fonts():
    """配置 Matplotlib 字体"""
    import matplotlib
    from matplotlib import font_manager

    preferred_fonts = CONFIG.get('preferred_plot_fonts', [])
    available_fonts = {f.name for f in font_manager.fontManager.ttflist}
    chosen_font = None

    for name in preferred_fonts:
        if name in available_fonts:
            chosen_font = name
            break

    if chosen_font:
        matplotlib.rcParams['font.family'] = 'sans-serif'
        matplotlib.rcParams['font.sans-serif'] = [chosen_font, 'Arial', 'sans-serif']
        print(f"[INFO] Using plot font: {chosen_font}", flush=True)
    else:
        print("[WARN] Preferred plot fonts not found; falling back to default sans-serif font.", flush=True)

    matplotlib.rcParams['axes.unicode_minus'] = False
    dpi_value = CONFIG.get('figure_dpi')
    if dpi_value:
        matplotlib.rcParams['figure.dpi'] = dpi_value
        matplotlib.rcParams['savefig.dpi'] = dpi_value


def _configure_matplotlib():
    """配置 matplotlib 后端和字体"""
    import matplotlib

    # 配置警告
    warnings.filterwarnings("ignore", message=".*n_jobs value.*overridden.*random_state.*")

    # 配置 matplotlib 后端为 Qt5Agg
    try:
        matplotlib.use('Qt5Agg')
        print("[INFO] Using Qt5Agg backend", flush=True)
    except Exception:
        print("[WARN] Qt5Agg backend not available, using Agg", flush=True)
        matplotlib.use('Agg')

    _configure_matplotlib_fonts()


class Qt5Application:
    """Qt5 应用程序类"""

    def __init__(self):
        self.app = None
        self.main_window = None
        self.translator = None
        self.control_panel = None

    def _configure_fonts(self):
        """配置应用字体"""
        default_font = QFont("Microsoft YaHei UI", 9)
        QApplication.setFont(default_font)

    def _configure_native_style(self):
        """Use native Qt style and clear custom stylesheets."""
        preferred = None
        for name in ("WindowsVista", "Windows", "Fusion"):
            style = QStyleFactory.create(name)
            if style is not None:
                preferred = style
                break
        if preferred is not None:
            self.app.setStyle(preferred)
        self.app.setStyleSheet("")
        self.app.installEventFilter(_NativeStyleFilter())

    def _install_debug_handlers(self):
        """Capture Qt and Python errors to log files for crash diagnostics."""
        try:
            from PyQt5.QtCore import qInstallMessageHandler
        except Exception:
            return

        try:
            qt_log = open("isotopes_qt.log", "a", encoding="utf-8", buffering=1)
        except Exception:
            qt_log = None

        def _qt_handler(msg_type, context, message):
            if qt_log is None:
                return
            try:
                qt_log.write(f"[QT] {message}\n")
            except Exception:
                pass

        qInstallMessageHandler(_qt_handler)

        def _excepthook(exc_type, exc, tb):
            try:
                with open("isotopes_py.log", "a", encoding="utf-8") as handle:
                    handle.write("[PY] Unhandled exception\n")
                    traceback.print_exception(exc_type, exc, tb, file=handle)
            except Exception:
                pass
            sys.__excepthook__(exc_type, exc, tb)

        sys.excepthook = _excepthook

    def _setup_translator(self, language):
        """设置翻译"""
        if self.translator:
            QApplication.removeTranslator(self.translator)

        self.translator = QTranslator()
        translations_dir = "locales"

        if self.translator.load(QLocale(language), "qt", "_", translations_dir):
            QApplication.installTranslator(self.translator)

    def _load_session(self):
        """加载会话参数"""
        print("[INFO] Loading session parameters...", flush=True)
        session_data = load_session_params()

        requested_language = None
        if session_data:
            requested_language = session_data.get('language')
        if not requested_language:
            requested_language = app_state.language or CONFIG.get('default_language')
        if not validate_language(requested_language):
            requested_language = CONFIG.get('default_language', 'en')
        set_language(requested_language)

        return session_data

    def _restore_session_state(self, session_data):
        """恢复会话状态"""
        if not session_data:
            app_state.algorithm = 'UMAP'
            app_state.render_mode = 'UMAP'
            print(f"[INFO] No session data, using default algorithm: UMAP", flush=True)
            return

        # 算法参数
        app_state.algorithm = session_data.get('algorithm', 'UMAP')
        print(f"[INFO] Algorithm from session: {app_state.algorithm}", flush=True)

        app_state.umap_params.update(session_data.get('umap_params', {}))
        app_state.tsne_params.update(session_data.get('tsne_params', {}))
        app_state.point_size = session_data.get('point_size', app_state.point_size)

        render_mode = session_data.get('render_mode')
        if not render_mode:
            legacy_mode = session_data.get('plot_mode')
            if legacy_mode == '3D':
                render_mode = '3D'
            elif legacy_mode == '2D':
                render_mode = '2D'
            else:
                render_mode = app_state.algorithm

        app_state.render_mode = render_mode or 'UMAP'
        app_state.selected_2d_cols = session_data.get('selected_2d_cols', [])
        app_state.selected_3d_cols = session_data.get('selected_3d_cols', [])

        # 恢复 tooltip 列
        saved_cols = session_data.get('tooltip_columns')
        if saved_cols is not None:
            app_state.tooltip_columns = saved_cols
            print(f"[DEBUG] Restored tooltip columns from session: {saved_cols}", flush=True)
        else:
            print(f"[DEBUG] No tooltip columns in session, using default: {app_state.tooltip_columns}", flush=True)

        # 恢复 UI 主题
        app_state.ui_theme = session_data.get('ui_theme') or 'Modern Light'
        print(f"[INFO] Restored UI theme: {app_state.ui_theme}", flush=True)

        # 分组列：从会话恢复
        session_group_col = session_data.get('group_col')
        if session_group_col and session_group_col in app_state.group_cols:
            app_state.last_group_col = session_group_col
            print(f"[INFO] Group column restored from session: {app_state.last_group_col}", flush=True)

    def _validate_render_mode(self):
        """验证并调整渲染模式"""
        num_numeric_cols = len(app_state.data_cols)

        if app_state.render_mode == '3D' and num_numeric_cols < 3:
            if num_numeric_cols >= 2:
                print("[INFO] Not enough numeric columns for 3D; switching to 2D scatter.", flush=True)
                app_state.render_mode = '2D'
            else:
                print("[INFO] Not enough numeric columns for 3D; switching to UMAP.", flush=True)
                app_state.render_mode = 'UMAP'

        if app_state.render_mode == '2D' and num_numeric_cols < 2:
            print("[INFO] Not enough numeric columns for 2D; switching to UMAP.", flush=True)
            app_state.render_mode = 'UMAP'

        if app_state.render_mode == '3D':
            if num_numeric_cols == 3:
                app_state.selected_3d_cols = app_state.data_cols[:3]
            else:
                valid_cols = [col for col in app_state.selected_3d_cols if col in app_state.data_cols][:3]
                if len(valid_cols) == 3:
                    app_state.selected_3d_cols = valid_cols
                else:
                    app_state.selected_3d_cols = []
                    print("[INFO] Stored 3D column selection invalid or incomplete; will prompt user on demand.", flush=True)

        if app_state.render_mode == '2D':
            if num_numeric_cols == 2:
                app_state.selected_2d_cols = app_state.data_cols[:2]
            else:
                valid_2d = [col for col in app_state.selected_2d_cols if col in app_state.data_cols][:2]
                if len(valid_2d) == 2:
                    app_state.selected_2d_cols = valid_2d
                else:
                    app_state.selected_2d_cols = []
                    print("[INFO] Stored 2D column selection invalid or incomplete; will prompt user on demand.", flush=True)

        if app_state.render_mode in ('UMAP', 'tSNE'):
            app_state.algorithm = 'UMAP' if app_state.render_mode == 'UMAP' else 'tSNE'

    def _create_plot_figure(self):
        """创建主绘图图形"""
        import matplotlib.pyplot as plt
        print("[INFO] Creating plot figure...", flush=True)

        # 使用 constrained_layout 进行自适应布局
        app_state.fig, app_state.ax = plt.subplots(figsize=CONFIG['figure_size'], constrained_layout=True)
        try:
            app_state.fig.set_constrained_layout_pads(w_pad=0.02, h_pad=0.02, wspace=0.02, hspace=0.02)
        except Exception:
            pass

        # 自动调整布局以避免裁剪
        def _on_resize(event):
            try:
                if app_state.fig is None:
                    return
                app_state.fig.set_constrained_layout(True)
                try:
                    app_state.fig.set_constrained_layout_pads(w_pad=0.02, h_pad=0.02, wspace=0.02, hspace=0.02)
                except Exception:
                    pass
                app_state.fig.canvas.draw_idle()
            except Exception:
                pass

        try:
            app_state.fig.canvas.mpl_connect('resize_event', _on_resize)

            def _on_draw(event):
                try:
                    if getattr(app_state, 'paleo_label_refreshing', False):
                        app_state.paleo_label_refreshing = False
                        return
                    from visualization.plotting import refresh_paleoisochron_labels
                    refresh_paleoisochron_labels()
                    if app_state.fig is not None and app_state.fig.canvas is not None:
                        app_state.paleo_label_refreshing = True
                        app_state.fig.canvas.draw_idle()
                except Exception:
                    app_state.paleo_label_refreshing = False

            app_state.fig.canvas.mpl_connect('draw_event', _on_draw)

            def _on_view_change(event):
                try:
                    from visualization.plotting import refresh_paleoisochron_labels
                    refresh_paleoisochron_labels()
                    if app_state.fig is not None and app_state.fig.canvas is not None:
                        app_state.fig.canvas.draw_idle()
                except Exception:
                    pass

            app_state.fig.canvas.mpl_connect('button_release_event', _on_view_change)
            app_state.fig.canvas.mpl_connect('scroll_event', _on_view_change)
        except Exception:
            pass

        print("[INFO] Plot figure created.", flush=True)
        plt.ion()

    def _setup_control_panel(self):
        """创建并设置控制面板"""
        print("[INFO] Control panel disabled; using top menu dialogs.", flush=True)
        self.control_panel = None
        import core.state as state
        state.control_panel = None
        app_state.control_panel_ref = None

    def _connect_event_handlers(self):
        """连接事件处理器"""
        from visualization.events import on_hover, on_click, on_legend_click
        print("[INFO] Connecting event handlers...", flush=True)
        app_state.fig.canvas.mpl_connect('motion_notify_event', on_hover)
        app_state.fig.canvas.mpl_connect('button_press_event', on_click)
        app_state.fig.canvas.mpl_connect('button_press_event', on_legend_click)
        print("[INFO] Event handlers connected.", flush=True)

    def _render_initial_plot(self):
        """渲染初始绘图"""
        from visualization.events import on_slider_change
        print("[INFO] Rendering initial plot...", flush=True)
        on_slider_change()
        print("[INFO] Plot ready.", flush=True)

    def _print_instructions(self):
        """打印应用使用说明"""
        print("[INFO] Application Controls:", flush=True)
        print("  * Use the Control Panel window to adjust parameters", flush=True)
        print("  * Algorithm selector -> Choose UMAP or t-SNE", flush=True)
        print("  * Point size -> Adjust marker size", flush=True)
        print("  * Hover over points -> View Lab No. / Site / Period", flush=True)
        print("  * Left click point -> Export sample to CSV", flush=True)
        print("  * Click legend item -> Bring group to front", flush=True)
        print("[INFO] Application started. Close the windows to exit.", flush=True)

    def run(self):
        """运行应用程序"""
        print("[INFO] Initializing Qt5 application...", flush=True)

        try:
            # 高 DPI 设置
            QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
            QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

            # 创建应用
            self.app = QApplication(sys.argv)
            self._install_debug_handlers()
            self._configure_fonts()
            self._configure_native_style()

            try:
                from pathlib import Path
                icon_path = Path(__file__).resolve().parent.parent / "assets" / "icons" / "logo.png"
                if icon_path.exists():
                    app_icon = QIcon(str(icon_path))
                    if not app_icon.isNull():
                        self.app.setWindowIcon(app_icon)
            except Exception:
                pass

            # 加载会话
            session_data = self._load_session()
            if session_data:
                app_state.file_path = session_data.get('file_path') or app_state.file_path
                app_state.sheet_name = session_data.get('sheet_name') or app_state.sheet_name
                app_state.group_cols = session_data.get('group_cols') or []
                app_state.data_cols = session_data.get('data_cols') or []

            # 加载数据
            print("[INFO] Loading data...", flush=True)
            from data.loader import load_data
            if not load_data(show_file_dialog=True, show_config_dialog=True):
                print("[ERROR] Failed to load data. Exiting.", flush=True)
                return False

            print("[INFO] Data loaded successfully.", flush=True)

            # 确保 last_group_col 已设置
            if not app_state.last_group_col and app_state.group_cols:
                app_state.last_group_col = app_state.group_cols[0]
                print(f"[INFO] Set default group column: {app_state.last_group_col}", flush=True)

            # 恢复会话参数
            self._restore_session_state(session_data)

            # 验证渲染模式
            self._validate_render_mode()

            # 配置 matplotlib
            _configure_matplotlib()

            # 创建绘图图形
            self._create_plot_figure()

            # 创建主窗口
            self.main_window = Qt5MainWindow()
            try:
                if self.app is not None:
                    self.main_window.setWindowIcon(self.app.windowIcon())
            except Exception:
                pass
            self.main_window.set_matplotlib_figure(app_state.fig)

            # 设置控制面板
            self._setup_control_panel()

            # 连接事件处理器
            self._connect_event_handlers()

            # 渲染初始绘图
            self._render_initial_plot()

            # 打印说明
            self._print_instructions()

            # 显示窗口
            print("[INFO] Showing windows...", flush=True)
            self.main_window.show()

            # 事件循环
            result = self.app.exec_()

            print("[INFO] Application closed normally.", flush=True)
            return result == 0

        except Exception as e:
            print(f"[ERROR] Application error: {e}", flush=True)
            traceback.print_exc()
            return False
        finally:
            print("[INFO] Cleanup complete.", flush=True)
