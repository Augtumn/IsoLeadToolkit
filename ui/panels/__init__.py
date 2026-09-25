"""面板模块 - 每段一个包：panel.py 定义公共面板类与 PANEL_META，其余模块是按职责拆分的 mixin。

``SECTIONS`` 是唯一的段落注册表（元数据来自各面板包），``ui.sections`` 据此构造菜单对话框。
"""

from __future__ import annotations

from .analysis import PANEL_META as ANALYSIS_META
from .analysis import AnalysisPanel
from .data import PANEL_META as DATA_META
from .data import DataPanel
from .display import PANEL_META as DISPLAY_META
from .display import DisplayPanel
from .export import PANEL_META as EXPORT_META
from .export import ExportPanel
from .geochemistry import PANEL_META as GEOCHEM_META
from .geochemistry import GeoPanel
from .legend import PANEL_META as LEGEND_META
from .legend import LegendPanel

#: (metadata, panel class) for every section, in navigation order.
SECTIONS = (
    (DATA_META, DataPanel),
    (DISPLAY_META, DisplayPanel),
    (ANALYSIS_META, AnalysisPanel),
    (EXPORT_META, ExportPanel),
    (LEGEND_META, LegendPanel),
    (GEOCHEM_META, GeoPanel),
)

__all__ = [
    "AnalysisPanel",
    "DataPanel",
    "DisplayPanel",
    "ExportPanel",
    "GeoPanel",
    "LegendPanel",
    "SECTIONS",
]
