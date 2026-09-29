"""录入工作簿对话框 —— 生成 TerraLID 录入模板、校验已填工作簿并导入结果。

本对话框是"Excel 作录入面"方案的**薄启动器**：字段定义、词表、校验与比值推导都在
`data/metadata_profile/` 与 `application/use_cases/entry_workbook.py` 里，这里只负责
选文件、触发用例、把 `EntryWorkbookReport` 渲染成人能读的报告。

设计要点：

1. 校验是**只读**的，导入才写盘；导入前有确认，且写盘前由用例层自动备份原文件
   （见 `data/metadata_profile/io_xlsx.py`），所以用户填了很久的工作簿不会被静默覆盖。
2. 报告里的每条问题都带 `message_key` + `params`，用 `translate()` 渲染成当前语言；
   渲染失败（占位符对不上）时回退到用例层给的英文原文，而不是抛异常把报告吞掉。
   这些 key 是**运行时**取值的，静态扫描看不到，故在 `locales/runtime_keys.py` 登记。
3. 本地文件 IO 是毫秒级，不需要 `QThread`；但用忙碌光标标明"正在处理"，避免用户
   以为按钮没反应（`docs/dev_conventions.md` §6.1）。
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Sequence

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QGuiApplication
from PyQt5.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from core import translate

logger = logging.getLogger(__name__)

#: 打开/保存对话框的文件类型过滤（本身不是用户可见文案，故不进 locales）。
_XLSX_FILTER = "Excel Workbook (*.xlsx)"

#: 生成模板时的建议目录与文件名。
_DEFAULT_DIR = "数据"
_DEFAULT_STEM = "entry_template_TerraLID"

#: 报告区字体。
_REPORT_FONT_FAMILY = "Consolas"
_REPORT_FONT_POINT_SIZE = 9


def show_entry_workbook_dialog(parent: Any = None) -> None:
    """打开录入工作簿对话框（模态）。

    Args:
        parent: 父窗口；``None`` 时对话框独立显示。
    """
    dialog = Qt5EntryWorkbookDialog(parent)
    dialog.exec_()


def _suggested_template_path() -> Path:
    """生成模板时的建议落盘路径（用户可在保存对话框里改）。

    文件名带上档案版本号，与 `scripts/build_entry_workbook.py` 的缺省名保持一致 ——
    否则同一份模板会出现两个名字，用户第二次生成时会被"是否覆盖"问得莫名其妙。
    版本号取不到时退回不带版本的名字（只是建议值，不影响生成）。
    """
    version = ""
    try:
        from data.metadata_profile import load_profile

        version = f"_v{load_profile().version}"
    except Exception as err:  # noqa: BLE001 — 建议路径不该因版本读取失败而中断
        # 降级：退回不带版本号的名字（仍能生成，只是与生成器缺省名不再一致）。
        # 用 warning 而非 debug —— `scripts/check_silent_exceptions.py` 把"仅 logger.debug"
        # 的处理器视为静默吞异常，而这里确实是一个用户可见的降级。
        logger.warning("Cannot resolve profile version for the suggested name: %s", err)
    return Path(_DEFAULT_DIR) / f"{_DEFAULT_STEM}{version}.xlsx"


def _render_issue_message(issue: Any) -> str:
    """把一条校验问题渲染为当前语言的可读文本。

    Args:
        issue: `EntryIssue`（含 ``message_key`` / ``params`` / ``message``）。

    Returns:
        本地化后的消息；渲染失败时回退到 ``issue.message``。
    """
    message_key = str(getattr(issue, "message_key", "") or "")
    fallback = str(getattr(issue, "message", "") or message_key)
    if not message_key:
        return fallback
    template = translate(message_key)
    params = dict(getattr(issue, "params", {}) or {})
    try:
        return template.format(**params)
    except (KeyError, IndexError, ValueError) as err:
        logger.warning(
            "Cannot render validation message %r with params %r: %s",
            message_key,
            params,
            err,
        )
        return fallback


class Qt5EntryWorkbookDialog(QDialog):
    """录入工作簿的生成 / 校验 / 导入入口与报告视图。"""

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(translate("Lead Isotope Data Entry"))
        self.resize(880, 620)
        self._workbook: Path | None = None
        self._setup_ui()

    # ── UI ────────────────────────────────────────────────────────────
    def _setup_ui(self) -> None:
        """构建标题、动作按钮、报告区与底部状态。"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel(translate("Lead Isotope Data Entry"))
        title.setProperty("keepStyle", True)  # survive _NativeStyleFilter
        title.setStyleSheet("font-weight: bold;")
        layout.addWidget(title)

        hint = QLabel(
            translate(
                "Fill the generated workbook in Excel, then validate or import it here. "
                "A timestamped backup is written before anything is overwritten."
            )
        )
        hint.setWordWrap(True)
        hint.setProperty("keepStyle", True)
        hint.setStyleSheet("color: #64748b;")
        layout.addWidget(hint)

        actions = QHBoxLayout()
        self.generate_btn = QPushButton(translate("Generate Template..."))
        self.generate_btn.clicked.connect(self._on_generate)
        actions.addWidget(self.generate_btn)

        self.validate_btn = QPushButton(translate("Validate Workbook..."))
        self.validate_btn.clicked.connect(self._on_validate)
        actions.addWidget(self.validate_btn)

        self.import_btn = QPushButton(translate("Import Workbook..."))
        self.import_btn.clicked.connect(self._on_import)
        actions.addWidget(self.import_btn)

        actions.addStretch()

        self.open_btn = QPushButton(translate("Open Workbook"))
        self.open_btn.setToolTip(translate("Open the workbook in the default application"))
        self.open_btn.clicked.connect(self._on_open_workbook)
        self.open_btn.setEnabled(False)
        actions.addWidget(self.open_btn)

        layout.addLayout(actions)

        self.report_view = QPlainTextEdit()
        self.report_view.setReadOnly(True)
        self.report_view.setLineWrapMode(QPlainTextEdit.NoWrap)
        font = self.report_view.font()
        font.setFamily(_REPORT_FONT_FAMILY)
        font.setPointSize(_REPORT_FONT_POINT_SIZE)
        self.report_view.setFont(font)
        self.report_view.setPlainText(
            translate('No workbook processed yet. Start with "Generate Template...".')
        )
        layout.addWidget(self.report_view, 1)

        self.path_label = QLabel("")
        self.path_label.setWordWrap(True)
        self.path_label.setProperty("keepStyle", True)
        self.path_label.setStyleSheet("color: #64748b;")
        layout.addWidget(self.path_label)

        footer = QHBoxLayout()
        footer.addStretch()
        close_btn = QPushButton(translate("Close"))
        close_btn.clicked.connect(self.close)
        footer.addWidget(close_btn)
        layout.addLayout(footer)

    # ── helpers ───────────────────────────────────────────────────────
    def _set_workbook(self, path: Path) -> None:
        """记住当前工作簿并刷新底部路径标签。"""
        self._workbook = path
        self.path_label.setText(str(path))
        self.open_btn.setEnabled(path.exists())

    def _report_lines(self, lines: Sequence[str]) -> None:
        """把报告文本写进报告区。"""
        self.report_view.setPlainText("\n".join(lines))

    def _set_busy(self, busy: bool) -> None:
        """切换忙碌光标（本地 IO 很快，不需要进度条）。"""
        if busy:
            QGuiApplication.setOverrideCursor(Qt.WaitCursor)
        else:
            QGuiApplication.restoreOverrideCursor()

    def _warn(self, message: str, detail: str = "") -> None:
        """统一的错误提示。"""
        text = f"{message}\n\n{detail}" if detail else message
        QMessageBox.warning(self, translate("Error"), text)

    def _ask_workbook(self, title: str) -> Path | None:
        """让用户选一个已存在的工作簿。

        Args:
            title: 已本地化的对话框标题 —— 由调用方传 ``translate("...")`` 字面量，
                以便 `locales/check_untranslated.py` 能静态看到该键。
        """
        start_dir = str(self._workbook or Path(_DEFAULT_DIR))
        selected, _ = QFileDialog.getOpenFileName(self, title, start_dir, _XLSX_FILTER)
        return Path(selected) if selected else None

    # ── actions ───────────────────────────────────────────────────────
    def _on_generate(self) -> None:
        """生成录入模板（已存在时先确认再覆盖）。"""
        suggested, _ = QFileDialog.getSaveFileName(
            self,
            translate("Save Entry Template"),
            str(_suggested_template_path()),
            _XLSX_FILTER,
        )
        if not suggested:
            return
        target = Path(suggested)
        force = False
        if target.exists():
            answer = QMessageBox.question(
                self,
                translate("Overwrite?"),
                "{}\n\n{}".format(
                    translate("File already exists. Overwrite it?"), target
                ),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
            force = True

        from application.use_cases.entry_workbook import generate_template

        self._set_busy(True)
        try:
            path = Path(generate_template(target, force=force))
        except Exception as err:
            logger.warning("Failed to generate entry template %s: %s", target, err)
            self._warn(translate("Failed to generate the entry template."), str(err))
            return
        finally:
            self._set_busy(False)

        self._set_workbook(path)
        self._report_lines(
            [
                translate("Entry template generated:"),
                str(path),
                "",
                translate(
                    'Open it in Excel, fill the sheets you need, then use '
                    '"Validate Workbook..." before importing.'
                ),
            ]
        )

    def _on_validate(self) -> None:
        """校验已填工作簿（只读，不写盘）。"""
        path = self._ask_workbook(translate("Select Entry Workbook"))
        if path is None:
            return

        from application.use_cases.entry_workbook import validate_entry_workbook

        self._set_busy(True)
        try:
            report = validate_entry_workbook(path)
        except Exception as err:
            logger.warning("Failed to validate entry workbook %s: %s", path, err)
            self._warn(translate("Failed to validate the workbook."), str(err))
            return
        finally:
            self._set_busy(False)

        self._set_workbook(path)
        self._render_report(report, imported=False)

    def _on_import(self) -> None:
        """导入：补齐派生比值并回写（用例层会先备份）。"""
        path = self._ask_workbook(translate("Select Entry Workbook"))
        if path is None:
            return

        answer = QMessageBox.question(
            self,
            translate("Import Workbook?"),
            "{}\n\n{}".format(
                translate(
                    "Import will derive the missing lead isotope ratios and write the "
                    "result back into this workbook. A timestamped backup is created first."
                ),
                path,
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        from application.use_cases.entry_workbook import import_entry_workbook

        self._set_busy(True)
        try:
            report = import_entry_workbook(path)
        except Exception as err:
            logger.warning("Failed to import entry workbook %s: %s", path, err)
            self._warn(translate("Failed to import the workbook."), str(err))
            return
        finally:
            self._set_busy(False)

        self._set_workbook(path)
        self._render_report(report, imported=True)

    def _on_open_workbook(self) -> None:
        """用系统默认程序打开当前工作簿（通常就是 Excel）。"""
        if self._workbook is None or not self._workbook.exists():
            return
        try:
            os.startfile(str(self._workbook.resolve()))  # type: ignore[attr-defined]
        except OSError as err:
            logger.warning("Failed to open workbook %s: %s", self._workbook, err)
            self._warn(translate("Failed to open the workbook."), str(err))

    # ── report ────────────────────────────────────────────────────────
    def _render_report(self, report: Any, *, imported: bool) -> None:
        """把 `EntryWorkbookReport` 渲染成分组报告。"""
        error_count = int(getattr(report, "error_count", 0) or 0)
        warning_count = int(getattr(report, "warning_count", 0) or 0)

        headline = (
            translate("Import finished: {errors} error(s), {warnings} warning(s)")
            if imported
            else translate("Validation finished: {errors} error(s), {warnings} warning(s)")
        )

        lines: list[str] = [
            headline.format(errors=error_count, warnings=warning_count),
            "",
            translate("Profile version: {version}").format(
                version=getattr(report, "profile_version", "")
            ),
            translate("Sheets read: {sheets} | Records read: {records}").format(
                sheets=getattr(report, "sheets_read", 0),
                records=getattr(report, "records_read", 0),
            ),
        ]

        derived = int(getattr(report, "derived_ratios", 0) or 0)
        if derived:
            lines.append(
                translate("Derived lead isotope ratios filled in: {count}").format(
                    count=derived
                )
            )

        backup = getattr(report, "backup", None)
        if backup:
            lines.append(translate("Backup written to: {path}").format(path=backup))

        if imported and error_count:
            lines.append("")
            lines.append(
                translate(
                    "Errors were found, so the data rows were left unchanged. "
                    "Only the check report was written."
                )
            )

        issues = list(getattr(report, "issues", ()) or ())
        lines.append("")
        if not issues:
            lines.append(translate("No issues found."))
        else:
            lines.append(translate("Issues by sheet:"))
            lines.extend(self._format_issues(issues))

        self._report_lines(lines)

        workbook = Path(str(getattr(report, "workbook", "")))
        if workbook.name:
            self.path_label.setText(str(workbook))

    @staticmethod
    def _format_issues(issues: Sequence[Any]) -> list[str]:
        """按工作表分组，逐条列出问题（严重级别 / 记录 / 列 / 消息）。"""
        grouped: dict[str, list[Any]] = {}
        for issue in issues:
            grouped.setdefault(str(getattr(issue, "sheet", "") or "?"), []).append(issue)

        lines: list[str] = []
        for sheet in sorted(grouped):
            lines.append("")
            lines.append(f"[{sheet}]")
            for issue in grouped[sheet]:
                severity = str(getattr(issue, "severity", "") or "").upper()
                record_id = str(getattr(issue, "record_id", "") or "")
                column = str(getattr(issue, "column", "") or "") or str(
                    getattr(issue, "field_oid", "") or ""
                )
                location = " ".join(part for part in (record_id, column) if part)
                lines.append(
                    f"  {severity:<7} {location:<40} {_render_issue_message(issue)}"
                )
        return lines


__all__ = ["Qt5EntryWorkbookDialog", "show_entry_workbook_dialog"]
