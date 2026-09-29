"""录入工作簿对话框的行为测试（离屏 Qt）。

只覆盖不需要用例层的部分：控件构建、报告渲染、消息渲染回退、菜单接线。
端到端的生成/校验/导入在 `tests/test_entry_workbook_use_case.py` 里覆盖。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

import pytest
from PyQt5.QtWidgets import QAction

from ui.dialogs.entry_workbook import (
    Qt5EntryWorkbookDialog,
    _render_issue_message,
    _suggested_template_path,
)


@dataclass
class _FakeIssue:
    """与 `EntryIssue` 同形的测试替身。"""

    severity: str = "error"
    sheet: str = "1_Site"
    record_id: str = "SI-1"
    column: str = "SI1 site_name"
    message: str = "Required field 'site_name' (SI1) is empty"
    message_key: str = "Required field '{field}' ({oid}) is empty"
    params: Mapping[str, object] = field(
        default_factory=lambda: {"field": "site_name", "oid": "SI1"}
    )
    value: object | None = None


def test_suggested_template_path_is_under_data_dir():
    """建议路径落在 `数据/` 下、后缀 xlsx，且文件名与生成器缺省名一致（带档案版本号）。

    两者若不一致，同一份模板会出现两个名字，用户第二次生成时会被"是否覆盖"问得莫名其妙。
    """
    from data.metadata_profile import load_profile

    path = _suggested_template_path()
    assert path.suffix == ".xlsx"
    assert path.parent.name == "数据"
    assert path.stem == f"entry_template_TerraLID_v{load_profile().version}"


def test_render_issue_message_uses_localised_template():
    """有对应翻译时，消息按当前语言渲染并填入占位符。"""
    issue = _FakeIssue()
    rendered = _render_issue_message(issue)
    assert rendered  # 非空
    assert "site_name" in rendered and "SI1" in rendered
    # zh 环境下不应原样返回英文模板
    assert "{field}" not in rendered


def test_render_issue_message_falls_back_on_param_mismatch():
    """占位符对不上时回退到英文原文，而不是抛异常把报告吞掉。"""
    issue = _FakeIssue(message_key="Required field '{field}' ({oid}) is empty", params={})
    assert _render_issue_message(issue) == issue.message


def test_render_issue_message_falls_back_when_key_missing():
    """没有 message_key 时直接用 message。"""
    issue = _FakeIssue(message_key="", message="plain message")
    assert _render_issue_message(issue) == "plain message"


def test_dialog_builds_all_action_widgets(qapp):
    """对话框构建出三个动作按钮与只读报告区，且报告区有初始提示。"""
    dialog = Qt5EntryWorkbookDialog()
    try:
        assert "打开录入表" in dialog.open_btn.text() or dialog.open_btn.text()
        assert dialog.open_btn.isEnabled() is False  # 未选工作簿前不可点
        assert dialog.report_view.isReadOnly() is True
        assert dialog.report_view.toPlainText().strip()
        assert dialog.path_label.text() == ""
    finally:
        dialog.close()
        dialog.deleteLater()


def test_format_issues_groups_by_sheet_and_sorts(qapp):
    """问题按工作表分组、组间有序，每条含级别/记录/列/消息。"""
    dialog = Qt5EntryWorkbookDialog()
    try:
        issues = [
            _FakeIssue(sheet="5_Analysis", record_id="A-1", column="A14 analysis_lia_ratio"),
            _FakeIssue(sheet="1_Site", record_id="SI-1"),
            _FakeIssue(sheet="1_Site", record_id="SI-2", column="SI0 terralid_site_id"),
        ]
        lines = dialog._format_issues(issues)
        headers = [line for line in lines if line.startswith("[")]
        assert headers == ["[1_Site]", "[5_Analysis]"]
        site_lines = [line for line in lines if "SI-1" in line or "SI-2" in line]
        assert len(site_lines) == 2
        assert all("ERROR" in line for line in site_lines)
    finally:
        dialog.close()
        dialog.deleteLater()


def test_render_report_summarises_counts_and_backup(qapp, tmp_path):
    """报告头部含计数、档案版本、读取量，并在有备份时显示路径。"""

    @dataclass
    class _FakeReport:
        workbook: Any
        profile_version: str = "0.3.4"
        sheets_read: int = 26
        records_read: int = 12
        derived_ratios: int = 5
        error_count: int = 1
        warning_count: int = 2
        issues: tuple = ()
        backup: Any = None

    report = _FakeReport(workbook=tmp_path / "entry.xlsx", backup=tmp_path / "entry.bak.xlsx")
    report.issues = (_FakeIssue(),)

    dialog = Qt5EntryWorkbookDialog()
    try:
        dialog._render_report(report, imported=True)
        text = dialog.report_view.toPlainText()
        assert "1" in text and "2" in text          # 计数出现在头部
        assert "0.3.4" in text                       # 档案版本
        assert "26" in text and "12" in text         # 表数 / 记录数
        assert "5" in text                           # 补齐的比值条数
        assert "entry.bak.xlsx" in text              # 备份路径
        assert "[1_Site]" in text                    # 分组标题
        assert dialog.path_label.text().endswith("entry.xlsx")
    finally:
        dialog.close()
        dialog.deleteLater()


def test_render_report_without_issues_says_so(qapp, tmp_path):
    """无问题时明确显示"未发现问题"，不留下空白报告。"""

    @dataclass
    class _CleanReport:
        workbook: Any
        profile_version: str = "0.3.4"
        sheets_read: int = 1
        records_read: int = 0
        derived_ratios: int = 0
        error_count: int = 0
        warning_count: int = 0
        issues: tuple = ()
        backup: Any = None

    dialog = Qt5EntryWorkbookDialog()
    try:
        dialog._render_report(_CleanReport(workbook=tmp_path / "e.xlsx"), imported=False)
        assert dialog.report_view.toPlainText().strip()
        assert "未发现问题" in dialog.report_view.toPlainText()
    finally:
        dialog.close()
        dialog.deleteLater()


def test_file_menu_exposes_entry_action(main_window):
    """主窗口文件菜单提供录入入口，并挂上 Ctrl+N 与语言刷新登记。"""
    actions = [a for a in main_window.findChildren(QAction) if "Excel" in a.text()]
    assert len(actions) == 1, [a.text() for a in actions]
    action = actions[0]
    assert action.shortcut().toString() == "Ctrl+N"
    assert action.toolTip()
    assert "entry_workbook" in (main_window._menu_actions or {})


def test_menu_action_labels_follow_language(main_window):
    """语言切换后菜单文案随之更新（登记在 _menu_actions 里）。"""
    from core import set_language

    action = main_window._menu_actions["entry_workbook"]
    try:
        set_language("en")
        assert action.text() == "Data Entry (Excel)..."
        set_language("zh")
        assert action.text() == "数据录入（Excel）..."
    finally:
        set_language("zh")


@pytest.mark.parametrize("severity", ["error", "warning"])
def test_format_issues_renders_both_severities(qapp, severity):
    """两级严重度都能渲染为大写标记。"""
    dialog = Qt5EntryWorkbookDialog()
    try:
        lines = dialog._format_issues([_FakeIssue(severity=severity)])
        assert any(severity.upper() in line for line in lines)
    finally:
        dialog.close()
        dialog.deleteLater()
