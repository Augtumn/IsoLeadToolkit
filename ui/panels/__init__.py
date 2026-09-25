"""面板模块 - 每个段落一个包：panel.py 定义公共面板类，其余模块是按职责拆分的 mixin。"""

from __future__ import annotations

from .analysis import AnalysisPanel
from .data import DataPanel
from .display import DisplayPanel
from .export import ExportPanel
from .geochemistry import GeoPanel
from .legend import LegendPanel

__all__ = [
    "AnalysisPanel",
    "DataPanel",
    "DisplayPanel",
    "ExportPanel",
    "GeoPanel",
    "LegendPanel",
]
