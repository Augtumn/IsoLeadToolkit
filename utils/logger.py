"""
Logger setup for Isotopes Analysis application.

Provides:
- Rotating file handler at DEBUG level with module:line context
- Console handler at configurable level (default INFO) with color when tty
- Separate rotating error file (ERROR and above) for post-mortem triage
- stdout/stderr capture through :class:`LoggerWriter`
- On-startup archive of the previous main log (timestamped, capped)
- `ISOTOPES_LOG_LEVEL` environment override (DEBUG|INFO|WARNING|ERROR)
"""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import TextIO

DEFAULT_LOG_FILENAME = "isotopes_analyse.log"
ERROR_LOG_FILENAME = "isotopes_analyse.error.log"
DEFAULT_MAX_BYTES = 50 * 1024 * 1024
DEFAULT_BACKUP_COUNT = 2
DEFAULT_ARCHIVE_KEEP = 5

# Color palette for console handler (ANSI) — used only when stderr is a tty.
_CONSOLE_COLORS = {
    logging.DEBUG: "\033[38;5;244m",      # gray
    logging.INFO: "\033[0m",               # default
    logging.WARNING: "\033[33m",           # yellow
    logging.ERROR: "\033[31m",             # red
    logging.CRITICAL: "\033[1;31m",        # bold red
}
_RESET = "\033[0m"


class _ColorFormatter(logging.Formatter):
    """Formatter that wraps the level name in ANSI color when enabled."""

    def __init__(self, fmt: str, use_color: bool = True) -> None:
        super().__init__(fmt)
        self._use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        if not self._use_color or not _stderr_is_tty():
            return super().format(record)
        color = _CONSOLE_COLORS.get(record.levelno, _RESET)
        level = f"{color}{record.levelname:<8}{_RESET}"
        # Inject colored level into the formatted line (first %(levelname)s).
        msg = super().format(record)
        return msg.replace(record.levelname, level, 1)


def _stderr_is_tty() -> bool:
    try:
        return bool(sys.stderr.isatty())
    except Exception:
        return False


class LoggerWriter:
    """
    Custom writer that writes to both a logger (file) and the original stream (console).
    """

    def __init__(self, logger: logging.Logger, level: int, original_stream: TextIO) -> None:
        self.logger = logger
        self.level = level
        self.original_stream = original_stream
        self.linebuf = ''

    def write(self, buf: str) -> None:
        # Write to original stream (console)
        try:
            self.original_stream.write(buf)
            self.original_stream.flush()
        except Exception:
            pass

        # Buffer and write to logger
        self.linebuf += buf
        if '\n' in self.linebuf:
            lines = self.linebuf.split('\n')
            # Process all complete lines
            for line in lines[:-1]:
                line = line.rstrip()
                if line:
                    self.logger.log(self.level, line)
            # Keep the last partial line
            self.linebuf = lines[-1]

    def fileno(self) -> int:
        """Return the file descriptor of the original stream for faulthandler compatibility."""
        return self.original_stream.fileno()

    def flush(self) -> None:
        try:
            self.original_stream.flush()
        except Exception:
            pass


def _archive_previous_log(log_path: Path, keep: int = DEFAULT_ARCHIVE_KEEP) -> None:
    """Rename an existing main log to a timestamped archive, capped at *keep*.

    Called once at startup so each session gets a fresh log while history is
    retained for triage. The error log is left in place (rotating handler
    manages it).
    """
    if not log_path.exists():
        return
    try:
        import time

        stamp = time.strftime("%Y%m%d-%H%M%S")
        archived = log_path.with_name(f"{log_path.stem}.{stamp}{log_path.suffix}")
        log_path.replace(archived)
    except OSError as exc:
        logging.getLogger(__name__).warning("Failed to archive previous log: %s", exc)
        return

    # Cap archived files (oldest first, lexicographic == chronological).
    try:
        siblings = sorted(log_path.parent.glob(f"{log_path.stem}.*{log_path.suffix}"))
        for old in siblings[:-keep] if keep > 0 else siblings:
            old.unlink(missing_ok=True)
    except OSError as exc:
        logging.getLogger(__name__).warning("Failed to prune old archives: %s", exc)


def setup_logging(
    log_filename: str = DEFAULT_LOG_FILENAME,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
    *,
    archive: bool = True,
    console_level: int | None = None,
    use_color: bool = True,
) -> None:
    """
    Sets up logging to rotating files and redirects stdout/stderr to it.

    Args:
        log_filename: Path to the main log file (relative paths resolve to CWD).
        max_bytes: Max size of the main log before rotation.
        backup_count: Number of rotated backups to keep per log.
        archive: When True, rename an existing main log to a timestamped archive
            at startup.
        console_level: Log level for the console handler; defaults to INFO
            (or the ``ISOTOPES_LOG_LEVEL`` override).
        use_color: Enable ANSI colors in the console handler.
    """
    try:
        log_path = Path(log_filename)
        if archive:
            _archive_previous_log(log_path)

        log_level_name = os.environ.get('ISOTOPES_LOG_LEVEL', 'DEBUG').upper()
        log_level = getattr(logging, log_level_name, logging.DEBUG)

        file_fmt = logging.Formatter(
            '%(asctime)s [%(levelname)-8s] %(name)s:%(lineno)d: %(message)s'
        )
        console_fmt = _ColorFormatter(
            '%(asctime)s [%(levelname)-8s] %(name)s:%(lineno)d: %(message)s',
            use_color=use_color,
        )

        # ---- file handler (all records at root level) ----
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8',
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_fmt)

        # ---- error-only file handler (ERROR+) ----
        error_path = log_path.with_name(
            f"{log_path.stem}.error{log_path.suffix}"
        )
        error_handler = RotatingFileHandler(
            error_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8',
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_fmt)

        # ---- console handler (human-facing, default INFO) ----
        console_handler = logging.StreamHandler(sys.stderr)
        console_level_resolved = console_level if console_level is not None else logging.INFO
        console_handler.setLevel(console_level_resolved)
        console_handler.setFormatter(console_fmt)

        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        # Replace handlers idempotently: avoid stacking duplicates on re-entry.
        root_logger.handlers = [file_handler, error_handler, console_handler]

        # Quiet down noisy third-party logs.
        logging.getLogger('matplotlib').setLevel(logging.WARNING)
        logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)
        logging.getLogger('numba').setLevel(logging.WARNING)
        logging.getLogger('PIL').setLevel(logging.WARNING)

        # ---- stdout/stderr capture ----
        logger = logging.getLogger('AppLogger')
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        # AppLogger writes to the same file+console handlers without recursion.
        logger.handlers = [file_handler, error_handler, console_handler]

        # Redirect stdout and stderr.
        sys.stdout = LoggerWriter(logger, logging.INFO, sys.__stdout__)
        sys.stderr = LoggerWriter(logger, logging.ERROR, sys.__stderr__)

        logging.getLogger(__name__).info(
            "Logging initialized. Main log: %s | Error log: %s | Level: %s",
            os.path.abspath(log_path),
            os.path.abspath(error_path),
            logging.getLevelName(log_level),
        )
    except Exception as e:
        logging.getLogger(__name__).error("Failed to setup logging: %s", e)
