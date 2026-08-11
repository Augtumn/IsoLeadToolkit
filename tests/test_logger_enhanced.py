"""Tests for enhanced logging setup (error file, archive, console handler)."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest

from utils.logger import LoggerWriter, setup_logging


def _remove_new_handlers(logger: logging.Logger, baseline: list[logging.Handler]) -> None:
    for handler in list(logger.handlers):
        if handler not in baseline:
            logger.removeHandler(handler)
            try:
                handler.close()
            except Exception:
                pass


def _log_sample(root: logging.Logger) -> None:
    root.info("info-line")
    root.warning("warn-line")
    root.error("error-line")


def test_setup_logging_creates_error_file_with_only_error_records(tmp_path: Path) -> None:
    log_file = tmp_path / "app.log"
    original_stdout, original_stderr = sys.stdout, sys.stderr
    root_logger = logging.getLogger()
    app_logger = logging.getLogger("AppLogger")
    root_handlers_before = list(root_logger.handlers)
    app_handlers_before = list(app_logger.handlers)

    try:
        setup_logging(str(log_file), max_bytes=4096, backup_count=1)
        _log_sample(root_logger)
    finally:
        sys.stdout, sys.stderr = original_stdout, original_stderr
        _remove_new_handlers(root_logger, root_handlers_before)
        _remove_new_handlers(app_logger, app_handlers_before)

    main_content = log_file.read_text(encoding="utf-8")
    error_path = tmp_path / "app.error.log"
    error_content = error_path.read_text(encoding="utf-8")

    assert "info-line" in main_content
    assert "warn-line" in main_content
    assert "error-line" in main_content
    # Error file: only ERROR and above
    assert "error-line" in error_content
    assert "info-line" not in error_content
    assert "warn-line" not in error_content


def test_setup_logging_archives_previous_main_log(tmp_path: Path) -> None:
    log_file = tmp_path / "app.log"
    log_file.write_text("previous session\n", encoding="utf-8")

    original_stdout, original_stderr = sys.stdout, sys.stderr
    root_logger = logging.getLogger()
    app_logger = logging.getLogger("AppLogger")
    root_handlers_before = list(root_logger.handlers)
    app_handlers_before = list(app_logger.handlers)

    try:
        setup_logging(str(log_file), max_bytes=4096, backup_count=1, archive=True)
    finally:
        sys.stdout, sys.stderr = original_stdout, original_stderr
        _remove_new_handlers(root_logger, root_handlers_before)
        _remove_new_handlers(app_logger, app_handlers_before)

    # Previous content must have been moved to an archived timestamped file.
    archived = [p for p in tmp_path.glob("app.*.log") if "error" not in p.name]
    assert len(archived) == 1, f"expected one archive, got {[a.name for a in archived]}"
    assert "previous session" in archived[0].read_text(encoding="utf-8")
    # Fresh main log must not contain the old line.
    assert "previous session" not in log_file.read_text(encoding="utf-8")


def test_setup_logging_install_console_handler_with_level(tmp_path: Path) -> None:
    log_file = tmp_path / "app.log"
    original_stdout, original_stderr = sys.stdout, sys.stderr
    root_logger = logging.getLogger()
    app_logger = logging.getLogger("AppLogger")
    root_handlers_before = list(root_logger.handlers)
    app_handlers_before = list(app_logger.handlers)

    try:
        setup_logging(str(log_file), max_bytes=4096, backup_count=1,
                      console_level=logging.WARNING, use_color=False)
        # Console handler level applied (exclude FileHandler subclasses)
        from logging.handlers import RotatingFileHandler

        console_handler = next(
            (h for h in root_logger.handlers
             if isinstance(h, logging.StreamHandler)
             and not isinstance(h, RotatingFileHandler)),
            None,
        )
        assert console_handler is not None
        assert console_handler.level == logging.WARNING
        # Root handler count: file + error + console
        stream_handlers = [
            h for h in root_logger.handlers
            if isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler)
        ]
        file_handlers = [h for h in root_logger.handlers if isinstance(h, RotatingFileHandler)]
        assert len(file_handlers) == 2  # main + error
        assert len(stream_handlers) == 1  # console
    finally:
        sys.stdout, sys.stderr = original_stdout, original_stderr
        _remove_new_handlers(root_logger, root_handlers_before)
        _remove_new_handlers(app_logger, app_handlers_before)


def test_setup_logging_keeps_stdout_stderr_redirected(tmp_path: Path) -> None:
    """Contract: sys.stdout/stderr must remain LoggerWriter after setup."""
    log_file = tmp_path / "app.log"
    original_stdout, original_stderr = sys.stdout, sys.stderr
    root_logger = logging.getLogger()
    app_logger = logging.getLogger("AppLogger")
    root_handlers_before = list(root_logger.handlers)
    app_handlers_before = list(app_logger.handlers)

    try:
        setup_logging(str(log_file), max_bytes=4096, backup_count=1)
        assert isinstance(sys.stdout, LoggerWriter)
        assert isinstance(sys.stderr, LoggerWriter)
    finally:
        sys.stdout, sys.stderr = original_stdout, original_stderr
        _remove_new_handlers(root_logger, root_handlers_before)
        _remove_new_handlers(app_logger, app_handlers_before)
