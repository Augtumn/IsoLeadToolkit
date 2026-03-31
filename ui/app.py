"""Qt5 应用程序类。

管理应用初始化、生命周期和资源清理。
"""
import logging
import sys
import warnings
import traceback

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication

from core import (
    CONFIG,
    app_state,
    state_gateway,
)
from ui.app_parts import Qt5AppPlottingMixin, Qt5AppSessionMixin, Qt5AppStyleMixin
from ui.main_window import Qt5MainWindow

logger = logging.getLogger(__name__)

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
        logger.info("Using plot font: %s", chosen_font)
    else:
        logger.warning("Preferred plot fonts not found; falling back to default sans-serif font.")

    matplotlib.rcParams['axes.unicode_minus'] = False
    dpi_value = CONFIG.get('figure_dpi')
    savefig_dpi_value = CONFIG.get('savefig_dpi', 300)
    if dpi_value:
        matplotlib.rcParams['figure.dpi'] = dpi_value
    matplotlib.rcParams['savefig.dpi'] = savefig_dpi_value


def _configure_matplotlib():
    """配置 matplotlib 后端和字体"""
    import matplotlib

    # 配置警告
    warnings.filterwarnings("ignore", message=".*n_jobs value.*overridden.*random_state.*")

    # 配置 matplotlib 后端为 Qt5Agg
    try:
        matplotlib.use('Qt5Agg')
        logger.info("Using Qt5Agg backend")
    except Exception:
        logger.warning("Qt5Agg backend not available, using Agg")
        matplotlib.use('Agg')

    _configure_matplotlib_fonts()


class Qt5Application(Qt5AppStyleMixin, Qt5AppSessionMixin, Qt5AppPlottingMixin):
    """Qt5 应用程序类"""

    def __init__(self):
        self.app = None
        self.main_window = None
        self.translator = None
        self.control_panel = None
        self._style_filter = None

    def run(self):
        """运行应用程序"""
        logger.info("Initializing Qt5 application...")

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
                state_gateway.set_attrs(
                    {
                        'file_path': session_data.get('file_path') or app_state.file_path,
                        'sheet_name': session_data.get('sheet_name') or app_state.sheet_name,
                        'group_cols': session_data.get('group_cols') or [],
                        'data_cols': session_data.get('data_cols') or [],
                    }
                )

            # 加载数据
            logger.info("Loading data...")
            from application.use_cases import load_dataset
            if not load_dataset(show_file_dialog=True, show_config_dialog=True):
                logger.error("Failed to load data. Exiting.")
                return False

            logger.info("Data loaded successfully.")

            # 确保 last_group_col 已设置
            if not app_state.last_group_col and app_state.group_cols:
                state_gateway.set_last_group_col(app_state.group_cols[0])
                logger.info("Set default group column: %s", app_state.last_group_col)

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
            logger.info("Showing windows...")
            self.main_window.show()

            # 事件循环
            result = self.app.exec_()

            logger.info("Application closed normally.")
            return result == 0

        except Exception as e:
            logger.error("Application error: %s", e)
            traceback.print_exc()
            return False
        finally:
            logger.info("Cleanup complete.")
