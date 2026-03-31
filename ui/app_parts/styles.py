"""Style and runtime diagnostics helpers for Qt application startup."""

import os
import sys
import traceback

from PyQt5.QtCore import QEvent, QLocale, QObject, QTranslator
from PyQt5.QtWidgets import QApplication, QStyleFactory, QWidget
from PyQt5.QtGui import QFont

from core import translate


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


class Qt5AppStyleMixin:
    """Style and diagnostics setup methods for Qt5Application."""

    def _configure_fonts(self):
        """Configure default application font."""
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
        self._style_filter = _NativeStyleFilter(self.app)
        self.app.installEventFilter(self._style_filter)

    def _install_debug_handlers(self):
        """Capture Qt and Python errors to stderr for easier debugging."""
        try:
            from PyQt5.QtCore import qInstallMessageHandler
        except Exception:
            return

        debug_enabled = os.environ.get("ISOTOPES_QT_DEBUG", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

        self._qt_message_handler = None

        def _qt_handler(msg_type, context, message):
            try:
                msg_type_int = int(msg_type)
                type_name = {
                    0: "DEBUG",
                    1: "WARN",
                    2: "CRITICAL",
                    3: "FATAL",
                    4: "INFO",
                }.get(msg_type_int, str(msg_type_int))

                if debug_enabled:
                    file_name = getattr(context, "file", "") or "<unknown>"
                    line_no = getattr(context, "line", 0) or 0
                    func_name = getattr(context, "function", "") or "<unknown>"
                    category = getattr(context, "category", "") or "qt"
                    sys.stderr.write(
                        f"[QT][{type_name}][{category}] {file_name}:{line_no} {func_name} | {message}\n"
                    )
                else:
                    sys.stderr.write(f"[QT][{type_name}] {message}\n")
                sys.stderr.flush()
            except Exception:
                pass

        self._qt_message_handler = _qt_handler
        qInstallMessageHandler(self._qt_message_handler)

        def _excepthook(exc_type, exc, tb):
            try:
                sys.stderr.write("[PY] Unhandled exception\n")
                traceback.print_exception(exc_type, exc, tb, file=sys.stderr)
                sys.stderr.flush()
            except Exception:
                pass
            sys.__excepthook__(exc_type, exc, tb)

        sys.excepthook = _excepthook

    def _setup_translator(self, language):
        """Set up Qt translation resources."""
        if self.translator:
            QApplication.removeTranslator(self.translator)

        self.translator = QTranslator()
        translations_dir = "locales"

        if self.translator.load(QLocale(language), "qt", "_", translations_dir):
            QApplication.installTranslator(self.translator)
