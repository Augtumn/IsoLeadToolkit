"""
UI 层入口。

面板与对话框按归属组织：每段一个包（``ui.panels.<section>``），该段专属对话框
放在 ``ui.panels.<section>.dialogs``；``ui.dialogs`` 只保留跨层共享的对话框。
段注册表见 ``ui.panels.SECTIONS``，菜单对话框工厂见 ``ui.sections``。
"""

from __future__ import annotations

__all__: list[str] = []
