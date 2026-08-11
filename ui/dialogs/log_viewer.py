"""Log viewer dialog — inspect main and error logs from within the app."""
from __future__ import annotations

import logging
import os
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from core import translate

logger = logging.getLogger(__name__)

DEFAULT_LOG_FILENAME = "isotopes_analyse.log"
ERROR_LOG_FILENAME = "isotopes_analyse.error.log"

# ANSI color codes to strip from console logs if the file ever contains them.
_ANSI_RE = None


def _strip_ansi(text: str) -> str:
    global _ANSI_RE
    if _ANSI_RE is None:
        import re

        _ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
    return _ANSI_RE.sub("", text)


def _resolve_log_paths() -> tuple[Path | None, Path | None]:
    """Resolve main and error log paths (CWD-relative like setup_logging)."""
    main_path = Path(DEFAULT_LOG_FILENAME)
    error_path = Path(ERROR_LOG_FILENAME)
    return main_path if main_path.exists() else None, error_path if error_path.exists() else None


def show_log_viewer(parent=None) -> None:
    """Open the log viewer dialog."""
    dialog = Qt5LogViewerDialog(parent)
    dialog.exec_()


class Qt5LogViewerDialog(QDialog):
    """Display recent log content with refresh and file-open actions."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(translate("Log Viewer"))
        self.resize(760, 560)
        self._last_source: str | None = None
        self._setup_ui()
        self._refresh()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # ── Source selector + actions ──────────────────────────────
        top_row = QHBoxLayout()
        top_row.addWidget(QLabel(translate("Log Source:")))
        self.source_combo = QComboBox()
        main_path, error_path = _resolve_log_paths()
        if main_path is not None:
            self.source_combo.addItem(translate("Main Log"), "main")
        if error_path is not None:
            self.source_combo.addItem(translate("Error Log"), "error")
        if self.source_combo.count() == 0:
            self.source_combo.addItem(translate("Main Log"), "main")
        self.source_combo.currentIndexChanged.connect(lambda *_: self._refresh())
        top_row.addWidget(self.source_combo, 1)

        self.lines_spin_label = QLabel(translate("Lines:"))
        top_row.addWidget(self.lines_spin_label)

        from PyQt5.QtWidgets import QSpinBox

        self.lines_spin = QSpinBox()
        self.lines_spin.setRange(50, 5000)
        self.lines_spin.setValue(500)
        self.lines_spin.setSingleStep(50)
        self.lines_spin.valueChanged.connect(lambda *_: self._refresh())
        top_row.addWidget(self.lines_spin)

        refresh_btn = QPushButton(translate("Refresh"))
        refresh_btn.clicked.connect(self._refresh)
        top_row.addWidget(refresh_btn)

        open_btn = QPushButton(translate("Open File"))
        open_btn.clicked.connect(self._open_file)
        top_row.addWidget(open_btn)

        layout.addLayout(top_row)

        # ── Log content ────────────────────────────────────────────
        self.text_edit = QPlainTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setLineWrapMode(QPlainTextEdit.NoWrap)
        font = self.text_edit.font()
        font.setFamily("Consolas")
        font.setPointSize(9)
        self.text_edit.setFont(font)
        layout.addWidget(self.text_edit, 1)

        # ── Footer with path ───────────────────────────────────────
        self.path_label = QLabel("")
        self.path_label.setWordWrap(True)
        self.path_label.setStyleSheet("color: #64748b;")
        layout.addWidget(self.path_label)

    def _selected_path(self) -> Path | None:
        main_path, error_path = _resolve_log_paths()
        source = self.source_combo.currentData()
        if source == "error":
            return error_path or main_path
        return main_path or error_path

    def _refresh(self) -> None:
        path = self._selected_path()
        if path is None or not path.exists():
            self.text_edit.setPlainText(translate("No log file found."))
            self.path_label.setText("")
            return
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as err:
            self.text_edit.setPlainText(
                translate("Failed to read log: {error}").format(error=str(err))
            )
            return
        limit = self.lines_spin.value()
        tail = lines[-limit:] if limit > 0 else lines
        self.text_edit.setPlainText(_strip_ansi("\n".join(tail)))
        self.path_label.setText(str(path.resolve()))

    def _open_file(self) -> None:
        path = self._selected_path()
        if path is None or not path.exists():
            return
        try:
            os.startfile(str(path.resolve()))  # type: ignore[attr-defined]
        except Exception as err:
            logger.warning("Failed to open log file: %s", err)
