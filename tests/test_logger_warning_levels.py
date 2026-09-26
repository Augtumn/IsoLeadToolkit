"""Warnings captured from stderr must not be logged as errors."""
from __future__ import annotations

import logging

import pytest

from utils.logger import LoggerWriter, enable_warning_capture, level_for_stderr_line

WARNING_LINE = (
    "d:\\Code\\IsotopesAnalyse\\application\\use_cases\\render_plot.py:92: "
    "UserWarning: constrained_layout not applied because axes sizes collapsed to zero."
)


def test_a_warning_line_is_not_an_error() -> None:
    assert level_for_stderr_line(WARNING_LINE, logging.ERROR) == logging.WARNING


@pytest.mark.parametrize(
    "line",
    [
        "d:\\app.py:12: RuntimeWarning: overflow encountered",
        "d:\\app.py:12: DeprecationWarning: old api",
        "d:\\app.py:12: MatplotlibDeprecationWarning: deprecated",
    ],
)
def test_every_warning_category_is_downgraded(line: str) -> None:
    assert level_for_stderr_line(line, logging.ERROR) == logging.WARNING


def test_an_actual_error_keeps_its_level() -> None:
    assert level_for_stderr_line("Traceback (most recent call last):", logging.ERROR) == logging.ERROR
    assert level_for_stderr_line("ValueError: bad value", logging.ERROR) == logging.ERROR


def test_stdout_lines_keep_their_own_level() -> None:
    """The helper is level-agnostic: INFO output stays INFO."""
    assert level_for_stderr_line("ordinary output", logging.INFO) == logging.INFO


class _RecordingLogger:
    def __init__(self) -> None:
        self.records: list[tuple[int, str]] = []

    def log(self, level: int, message: str) -> None:
        self.records.append((level, message))


def test_the_writer_downgrades_warning_lines() -> None:
    recorder = _RecordingLogger()
    writer = LoggerWriter(recorder, logging.ERROR, None)

    writer.write(WARNING_LINE + "\n")
    writer.write("Traceback (most recent call last):\n")

    assert [level for level, _ in recorder.records] == [logging.WARNING, logging.ERROR]


def test_warning_capture_routes_warnings_to_logging(caplog) -> None:
    import warnings

    enable_warning_capture()

    with caplog.at_level(logging.WARNING, logger="py.warnings"):
        warnings.warn("probe warning", UserWarning, stacklevel=1)

    assert any("probe warning" in record.getMessage() for record in caplog.records), caplog.records
    assert logging.getLogger("py.warnings").level == logging.WARNING
