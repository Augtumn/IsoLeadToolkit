"""Qt5 主窗口基类。

提供标准的应用程序窗口框架。
"""
import logging
from pathlib import Path

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout,
                              QHBoxLayout, QDockWidget, QToolBar,
                              QStatusBar, QMenuBar, QAction, QStyle,
                              QSplitter, QSizePolicy, QListWidget,
                              QListWidgetItem, QAbstractItemView, QLabel,
                              QPushButton, QCheckBox, QMenu)
from PyQt5.QtCore import Qt, QSize, QSettings, QTimer
from PyQt5.QtGui import QIcon, QKeySequence, QColor, QCursor

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

from core import app_state, translate
from visualization.plotting.legend_model import overlay_legend_items, normalize_render_mode, OVERLAY_TOGGLE_MAP
from utils.icons import build_marker_icon

logger = logging.getLogger(__name__)

# 默认图标尺寸
DEFAULT_TOOLBAR_ICON_SIZE = QSize(24, 24)


class LegendListWidget(QListWidget):
    """QListWidget that preserves item widgets after internal move."""
    def dropEvent(self, event):
        widgets = {self.item(i): self.itemWidget(self.item(i)) for i in range(self.count())}
        super().dropEvent(event)
        for item, widget in widgets.items():
            if widget is not None and self.itemWidget(item) is None:
                self.setItemWidget(item, widget)


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
        app_state.legend_update_callback = self._update_legend_panel

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
        legend_title.setStyleSheet("font-weight: bold;")
        legend_layout.addWidget(legend_title)
        legend_list = LegendListWidget()
        legend_list.setSelectionMode(QAbstractItemView.SingleSelection)
        legend_list.setUniformItemSizes(False)
        legend_list.setIconSize(QSize(14, 14))
        legend_list.setDragDropMode(QAbstractItemView.InternalMove)
        legend_list.setDefaultDropAction(Qt.MoveAction)
        legend_list.setDragEnabled(True)
        legend_list.setAcceptDrops(True)
        legend_list.setDropIndicatorShown(True)
        legend_list.itemDoubleClicked.connect(self._on_legend_item_double_clicked)
        legend_layout.addWidget(legend_list, 1)
        self.legend_panel.setMinimumWidth(160)
        self._legend_title_label = legend_title
        self._legend_list = legend_list
        try:
            legend_list.model().rowsMoved.connect(self._on_legend_rows_moved)
        except Exception:
            pass

        self.legend_splitter = QSplitter(Qt.Horizontal)
        self.legend_splitter.setChildrenCollapsible(False)
        self.legend_splitter.setOpaqueResize(False)
        self.legend_splitter.addWidget(self.legend_panel)
        self.legend_splitter.addWidget(self.plot_container)
        self.canvas_root_layout.addWidget(self.legend_splitter)
        self._apply_legend_panel_layout()

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
        data_action.setShortcut(QKeySequence("Ctrl+D"))
        data_action.triggered.connect(lambda: self._show_section_dialog('data'))
        menubar.addAction(data_action)

        display_action = QAction(translate("Display"), self)
        display_action.setShortcut(QKeySequence("Ctrl+Shift+D"))
        display_action.triggered.connect(lambda: self._show_section_dialog('display'))
        menubar.addAction(display_action)

        analysis_action = QAction(translate("Analysis"), self)
        analysis_action.setShortcut(QKeySequence("Ctrl+Shift+A"))
        analysis_action.triggered.connect(lambda: self._show_section_dialog('analysis'))
        menubar.addAction(analysis_action)

        export_action = QAction(translate("Export"), self)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.triggered.connect(lambda: self._show_section_dialog('export'))
        menubar.addAction(export_action)

        legend_action = QAction(translate("Legend"), self)
        legend_action.setShortcut(QKeySequence("Ctrl+L"))
        legend_action.triggered.connect(lambda: self._show_section_dialog('legend'))
        menubar.addAction(legend_action)

        geo_action = QAction(translate("Geochemistry"), self)
        geo_action.setShortcut(QKeySequence("Ctrl+G"))
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

    def _apply_legend_panel_layout(self):
        try:
            location_key = getattr(app_state, 'legend_location', None)
            if location_key not in {'outside_left', 'outside_right'}:
                location_key = None
            is_outside = bool(location_key)
            if not hasattr(self, 'legend_splitter'):
                return

            layout_state = (location_key, is_outside)
            if getattr(self, '_legend_layout_state', None) == layout_state:
                return

            self.legend_panel.setVisible(is_outside)
            if not is_outside:
                if hasattr(self, '_legend_list') and self._legend_list is not None:
                    self._legend_list.clear()
                self.legend_splitter.setSizes([0, 1])
                return

            if self.legend_splitter.orientation() != Qt.Horizontal:
                self.legend_splitter.setOrientation(Qt.Horizontal)
            first = self.legend_panel if location_key == 'outside_left' else self.plot_container
            second = self.plot_container if location_key == 'outside_left' else self.legend_panel

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

    def _build_marker_icon(self, color, marker, size=14):
        return build_marker_icon(color, marker, size)

    def _ensure_marker_shape_map(self):
        if not hasattr(self, '_marker_shape_map'):
            self._marker_shape_map = {
                translate("Point (.)"): '.',
                translate("Pixel (,)"): ',',
                translate("Circle (o)"): 'o',
                translate("Triangle Down (v)"): 'v',
                translate("Triangle Up (^)"): '^',
                translate("Triangle Left (<)"): '<',
                translate("Triangle Right (>)"): '>',
                translate("Tri Down (1)"): '1',
                translate("Tri Up (2)"): '2',
                translate("Tri Left (3)"): '3',
                translate("Tri Right (4)"): '4',
                translate("Octagon (8)"): '8',
                translate("Square (s)"): 's',
                translate("Pentagon (p)"): 'p',
                translate("Plus Filled (P)"): 'P',
                translate("Star (*)"): '*',
                translate("Hexagon 1 (h)"): 'h',
                translate("Hexagon 2 (H)"): 'H',
                translate("Diamond (D)"): 'D',
                translate("Plus (+)"): '+',
                translate("Cross (x)"): 'x',
                translate("X (X)"): 'X',
                translate("Thin Diamond (d)"): 'd',
                translate("Vline (|)"): '|',
                translate("Hline (_)"): '_',
            }

    def _overlay_entries_for_legend(self):
        mode = normalize_render_mode(getattr(app_state, 'render_mode', ''))
        return [
            (item['label_key'], item['style_key'])
            for item in overlay_legend_items(render_mode=mode, include_disabled=True)
        ]

    def _legend_order_key(self, entry_type, key):
        return f"{entry_type}:{key}"

    def _set_legend_item_meta(self, item, entry_type, key):
        if item is None:
            return
        item.setData(Qt.UserRole, {'type': entry_type, 'key': key})

    def _apply_legend_z_order(self):
        if not hasattr(self, '_legend_list') or self._legend_list is None:
            return
        ax = getattr(app_state, 'ax', None)
        if ax is None:
            return

        order = []
        for i in range(self._legend_list.count()):
            item = self._legend_list.item(i)
            meta = item.data(Qt.UserRole)
            if not meta:
                continue
            entry_type = meta.get('type')
            entry_key = meta.get('key')
            if entry_type and entry_key is not None:
                order.append((entry_type, entry_key))

        if not order:
            return

        max_z = 2
        try:
            for artist in ax.get_children():
                try:
                    max_z = max(max_z, artist.get_zorder())
                except Exception:
                    continue
        except Exception:
            pass

        target_z = max_z + len(order)
        overlay_map = getattr(app_state, 'overlay_artists', {}) or {}
        group_map = getattr(app_state, 'group_to_scatter', {}) or {}

        for entry_type, entry_key in order:
            if entry_type == 'group':
                artist = group_map.get(entry_key)
                if artist is not None:
                    try:
                        artist.set_zorder(target_z)
                    except Exception:
                        pass
            elif entry_type == 'overlay':
                artists = list(overlay_map.get(entry_key, []))
                if entry_key == 'isochron':
                    artists.extend(overlay_map.get('selected_isochron', []))
                for artist in artists:
                    try:
                        artist.set_zorder(target_z)
                    except Exception:
                        pass
            target_z -= 1

        app_state.legend_item_order = [
            self._legend_order_key(entry_type, entry_key)
            for entry_type, entry_key in order
        ]

        if app_state.fig is not None and app_state.fig.canvas is not None:
            app_state.fig.canvas.draw_idle()

    def _on_legend_rows_moved(self, *args):
        QTimer.singleShot(0, self._apply_legend_z_order)

    def _move_legend_item_to_top(self, entry_type, entry_key):
        if not hasattr(self, '_legend_list') or self._legend_list is None:
            return
        target_index = None
        target_item = None
        target_widget = None
        for i in range(self._legend_list.count()):
            item = self._legend_list.item(i)
            meta = item.data(Qt.UserRole)
            if not meta:
                continue
            if meta.get('type') == entry_type and meta.get('key') == entry_key:
                target_index = i
                target_item = item
                target_widget = self._legend_list.itemWidget(item)
                break
        if target_item is None or target_index is None or target_index == 0:
            return
        self._legend_list.takeItem(target_index)
        self._legend_list.insertItem(0, target_item)
        if target_widget is not None:
            self._legend_list.setItemWidget(target_item, target_widget)
        self._apply_legend_z_order()


    def _open_line_style_dialog(self, style_key, swatch):
        from ui.dialogs.line_style_dialog import open_line_style_dialog
        open_line_style_dialog(self, style_key, swatch=swatch, on_applied=self._refresh_plot)

    def _add_overlay_legend_item(self, label_key, style_key):
        item_widget = QWidget()
        item_layout = QHBoxLayout()
        item_layout.setContentsMargins(4, 2, 4, 2)
        item_layout.setSpacing(6)

        style = getattr(app_state, 'line_styles', {}).get(style_key, {}) or {}
        swatch_color = style.get('color') or '#e2e8f0'

        swatch = QPushButton()
        swatch.setFixedSize(22, 22)
        swatch.setStyleSheet(f"background-color: {swatch_color}; border: 1px solid #111827;")
        swatch.setCursor(QCursor(Qt.PointingHandCursor))
        swatch.clicked.connect(lambda checked=False, k=style_key, btn=swatch: self._open_line_style_dialog(k, btn))
        item_layout.addWidget(swatch)

        checkbox = QCheckBox()
        checkbox.setChecked(self._overlay_checked_state(style_key))
        checkbox.stateChanged.connect(lambda state, k=style_key: self._on_overlay_checkbox_change(k, state))
        checkbox.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        checkbox.setFixedWidth(18)
        item_layout.addWidget(checkbox)

        label = QLabel(translate(label_key))
        item_layout.addWidget(label, 1)
        item_layout.addStretch()

        item_widget.setLayout(item_layout)

        item = QListWidgetItem()
        item.setSizeHint(item_widget.sizeHint())
        self._set_legend_item_meta(item, 'overlay', style_key)
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled)
        self._legend_list.addItem(item)
        self._legend_list.setItemWidget(item, item_widget)

    def _overlay_checked_state(self, style_key):
        """Get checked state for overlay using OVERLAY_TOGGLE_MAP."""
        attr = OVERLAY_TOGGLE_MAP.get(style_key)
        if attr:
            return bool(getattr(app_state, attr, True))
        # Special case for isochron: also check selected_isochron_data
        if style_key == 'isochron':
            return bool(getattr(app_state, 'show_isochrons', False) or getattr(app_state, 'selected_isochron_data', None))
        return True

    def _on_overlay_checkbox_change(self, style_key, state):
        """Handle overlay checkbox change using OVERLAY_TOGGLE_MAP."""
        checked = state == Qt.Checked
        attr = OVERLAY_TOGGLE_MAP.get(style_key)
        if attr:
            setattr(app_state, attr, checked)

        # Special case: clear isochron data when unchecked
        if style_key == 'isochron' and not checked:
            app_state.selected_isochron_data = None
            app_state.isochron_results = {}

        self._sync_geochem_toggle_panels(style_key)

        # Lightweight refresh: only toggle visibility
        try:
            from visualization.plotting.style import refresh_overlay_visibility
            refresh_overlay_visibility()
        except Exception:
            self._refresh_plot()

    def _sync_geochem_toggle_panels(self, style_key):
        panel = getattr(app_state, 'control_panel_ref', None)
        data_panel = getattr(panel, 'data_panel', None) if panel is not None else None
        if data_panel is None:
            return
        try:
            if style_key == 'model_curve':
                data_panel._sync_geochem_toggle_widgets(
                    app_state.show_model_curves,
                    getattr(data_panel, 'modeling_show_model_check', None),
                    getattr(data_panel, 'show_model_check', None)
                )
            elif style_key == 'plumbotectonics_curve':
                data_panel._sync_geochem_toggle_widgets(
                    app_state.show_plumbotectonics_curves,
                    getattr(data_panel, 'modeling_show_plumbotectonics_check', None)
                )
            elif style_key == 'paleoisochron':
                data_panel._sync_geochem_toggle_widgets(
                    app_state.show_paleoisochrons,
                    getattr(data_panel, 'modeling_show_paleoisochron_check', None),
                    getattr(data_panel, 'show_paleoisochron_check', None)
                )
            elif style_key == 'model_age_line':
                data_panel._sync_geochem_toggle_widgets(
                    app_state.show_model_age_lines,
                    getattr(data_panel, 'modeling_show_model_age_check', None),
                    getattr(data_panel, 'show_model_age_check', None)
                )
            elif style_key == 'isochron':
                data_panel._sync_geochem_toggle_widgets(
                    app_state.show_isochrons,
                    getattr(data_panel, 'modeling_show_isochron_check', None),
                    getattr(data_panel, 'show_isochron_check', None)
                )
                if hasattr(data_panel, '_update_isochron_btn_text'):
                    data_panel._update_isochron_btn_text()
            elif style_key == 'growth_curve':
                data_panel._sync_geochem_toggle_widgets(
                    app_state.show_growth_curves,
                    getattr(data_panel, 'modeling_show_growth_curve_check', None)
                )
        except Exception:
            pass
    def _on_legend_item_double_clicked(self, item):
        meta = item.data(Qt.UserRole) if item is not None else None
        if not meta:
            return
        entry_type = meta.get('type')
        entry_key = meta.get('key')
        if entry_type == 'group':
            self._bring_to_front(entry_key)
        elif entry_type == 'overlay':
            self._bring_overlay_to_front(entry_key)

    def _bring_overlay_to_front(self, style_key):
        ax = getattr(app_state, 'ax', None)
        if ax is None:
            return
        overlay_map = getattr(app_state, 'overlay_artists', {}) or {}
        artists = list(overlay_map.get(style_key, []))
        if style_key == 'isochron':
            artists.extend(overlay_map.get('selected_isochron', []))
        if not artists:
            return

        max_z = 2
        try:
            for artist in ax.get_children():
                try:
                    max_z = max(max_z, artist.get_zorder())
                except Exception:
                    continue
        except Exception:
            pass

        target_z = max_z + 1
        for artist in artists:
            try:
                artist.set_zorder(target_z)
            except Exception:
                pass

        if app_state.fig is not None and app_state.fig.canvas is not None:
            app_state.fig.canvas.draw_idle()
    def _update_marker_swatch(self, group, swatch):
        color = app_state.current_palette.get(group, '#cccccc')
        marker = app_state.group_marker_map.get(group, getattr(app_state, 'plot_marker_shape', 'o'))
        icon = self._build_marker_icon(color, marker, size=16)
        swatch.setIcon(icon)
        swatch.setIconSize(QSize(16, 16))
        swatch.setStyleSheet("border: 1px solid #111827; border-radius: 3px; background: transparent;")

    def _sync_legend_panel_ui(self, refresh=False):
        panel = getattr(app_state, 'control_panel_ref', None)
        if panel is None or not hasattr(panel, 'legend_checkboxes'):
            return
        try:
            if refresh and hasattr(panel, '_update_group_list'):
                panel._update_group_list()
            elif hasattr(panel, 'sync_legend_ui'):
                panel.sync_legend_ui()
        except Exception:
            pass

    def _pick_color(self, group, swatch):
        from PyQt5.QtWidgets import QColorDialog
        current_color = app_state.current_palette.get(group, '#cccccc')
        color = QColorDialog.getColor(QColor(current_color), self, f"Color for {group}")
        if color.isValid():
            new_hex = color.name()
            app_state.current_palette[group] = new_hex
            self._update_marker_swatch(group, swatch)

            if hasattr(app_state, 'group_to_scatter') and group in app_state.group_to_scatter:
                sc = app_state.group_to_scatter[group]
                try:
                    sc.set_color(new_hex)
                    sc.set_edgecolor("#1e293b")
                    if app_state.fig:
                        app_state.fig.canvas.draw_idle()
                except Exception as exc:
                    logger.warning("Failed to update color for %s: %s", group, exc)
            self._sync_legend_panel_ui(refresh=True)

    def _set_group_shape_value(self, group, marker_value, swatch):
        self._ensure_marker_shape_map()
        marker = marker_value or getattr(app_state, 'plot_marker_shape', 'o')
        app_state.group_marker_map[group] = marker
        self._update_marker_swatch(group, swatch)
        self._sync_legend_panel_ui(refresh=True)
        self._refresh_plot()

    def _show_color_shape_menu(self, group, swatch):
        self._ensure_marker_shape_map()
        menu = QMenu(self)

        color_action = QAction(translate("Color..."), self)
        color_action.triggered.connect(lambda checked=False, g=group, btn=swatch: self._pick_color(g, btn))
        menu.addAction(color_action)

        shape_menu = menu.addMenu(translate("Shape"))
        current_marker = app_state.group_marker_map.get(group, getattr(app_state, 'plot_marker_shape', 'o'))
        for label, value in self._marker_shape_map.items():
            icon = self._build_marker_icon('#94a3b8', value, size=14)
            action = QAction(icon, "", self)
            action.setCheckable(True)
            action.setChecked(value == current_marker)
            action.triggered.connect(
                lambda checked=False, g=group, v=value, btn=swatch: self._set_group_shape_value(g, v, btn)
            )
            shape_menu.addAction(action)

        menu.exec_(QCursor.pos())

    def _on_group_checkbox_change(self, group, state):
        if not app_state.last_group_col or app_state.df_global is None:
            return

        groups = list(app_state.available_groups or app_state.df_global[app_state.last_group_col].unique())
        if app_state.visible_groups is None:
            current_visible = set(groups)
        else:
            current_visible = set(app_state.visible_groups)

        if state == Qt.Checked:
            current_visible.add(group)
        else:
            current_visible.discard(group)

        if len(current_visible) == len(groups):
            app_state.visible_groups = None
        else:
            app_state.visible_groups = sorted(current_visible)

        self._sync_legend_panel_ui()
        self._refresh_plot()

    def _bring_to_front(self, group):
        if hasattr(app_state, 'group_to_scatter') and group in app_state.group_to_scatter:
            sc = app_state.group_to_scatter[group]
            try:
                max_z = 2
                if hasattr(app_state, 'scatter_collections'):
                    for c in app_state.scatter_collections:
                        max_z = max(max_z, c.get_zorder())

                sc.set_zorder(max_z + 1)
                if app_state.fig:
                    app_state.fig.canvas.draw_idle()
            except Exception as exc:
                logger.warning("Failed to bring %s to front: %s", group, exc)
        self._move_legend_item_to_top('group', group)

    def _update_legend_panel(self, title, handles, labels):
        try:
            if not hasattr(self, '_legend_list') or self._legend_list is None:
                return
            self._apply_legend_panel_layout()
            location_key = getattr(app_state, 'legend_location', None)
            if location_key not in {'outside_left', 'outside_right'}:
                return

            if self._legend_title_label is not None:
                self._legend_title_label.setText(str(title))

            self._legend_list.clear()

            has_groups = app_state.last_group_col and app_state.df_global is not None
            groups = []
            if has_groups:
                groups = list(app_state.df_global[app_state.last_group_col].unique())
            overlay_entries = self._overlay_entries_for_legend()

            entries = []
            if has_groups:
                max_items = 100
                groups_to_show = list(groups)[:max_items]
                if len(groups) > max_items:
                    logger.warning("Showing first %d groups only.", max_items)
                for group in groups_to_show:
                    entries.append({'type': 'group', 'key': group, 'group': group})
            for label_key, style_key in overlay_entries:
                entries.append({'type': 'overlay', 'key': style_key, 'label_key': label_key})

            order_keys = getattr(app_state, 'legend_item_order', []) or []
            order_index = {key: idx for idx, key in enumerate(order_keys)}
            entries.sort(key=lambda e: order_index.get(self._legend_order_key(e['type'], e['key']), 10_000))

            if has_groups:
                self._ensure_marker_shape_map()
                visible = set(app_state.visible_groups) if app_state.visible_groups is not None else set(groups)

            for entry in entries:
                if entry['type'] == 'group':
                    group = entry['group']
                    item_widget = QWidget()
                    item_layout = QHBoxLayout()
                    item_layout.setContentsMargins(4, 2, 4, 2)
                    item_layout.setSpacing(6)

                    color_btn = QPushButton()
                    color_btn.setFixedSize(22, 22)
                    self._update_marker_swatch(group, color_btn)
                    color_btn.setCursor(QCursor(Qt.PointingHandCursor))
                    color_btn.clicked.connect(lambda checked=False, g=group, btn=color_btn: self._show_color_shape_menu(g, btn))
                    item_layout.addWidget(color_btn)

                    checkbox = QCheckBox()
                    checkbox.setChecked(group in visible)
                    checkbox.stateChanged.connect(lambda state, g=group: self._on_group_checkbox_change(g, state))
                    checkbox.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
                    checkbox.setFixedWidth(18)
                    item_layout.addWidget(checkbox)

                    label = QLabel(str(group))
                    item_layout.addWidget(label, 1)
                    item_layout.addStretch()

                    item_widget.setLayout(item_layout)

                    item = QListWidgetItem()
                    item.setSizeHint(item_widget.sizeHint())
                    self._set_legend_item_meta(item, 'group', group)
                    item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled)
                    self._legend_list.addItem(item)
                    self._legend_list.setItemWidget(item, item_widget)
                elif entry['type'] == 'overlay':
                    self._add_overlay_legend_item(entry['label_key'], entry['key'])
            self._apply_legend_z_order()
        except Exception as exc:
            import traceback
            logger.error("Legend panel update failed: %s", exc)
            traceback.print_exc()

    def _refresh_plot(self):
        self._apply_legend_panel_layout()
        try:
            from visualization.events import on_slider_change
            on_slider_change()
        except Exception:
            pass

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

        if hasattr(self, '_legend_title_label') and self._legend_title_label is not None:
            last_title = getattr(app_state, 'legend_last_title', None)
            if last_title:
                self._legend_title_label.setText(str(last_title))
            else:
                self._legend_title_label.setText(translate("Legend"))

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
            logger.warning("Failed to toggle selection tool: %s", exc)
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
                    logger.warning("Failed to refresh plot after reload: %s", exc)
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

        logger.info("Event handlers connected successfully")
