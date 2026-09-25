"""Generic background analysis worker (QThread) for heavy dialog computations.

Keeps the GUI responsive while plugins train models or run clustering:
the computation runs on a worker thread and the result (or the failure
message) is delivered back on the main thread via queued signals.

Usage::

    worker = AnalysisWorker(fn, *args, **kwargs)
    worker.finished_signal.connect(on_result)   # main thread
    worker.failed.connect(on_failed)            # main thread
    worker.start()

Owners must cancel+wait in their closeEvent so a running thread is never
destroyed while running.
"""
from __future__ import annotations

import logging
from typing import Any, Callable

from PyQt5.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class AnalysisWorker(QThread):
    """Run *fn(*args, **kwargs)* on a worker thread."""

    finished_signal = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(
        self,
        fn: Callable[..., Any],
        *args: Any,
        parent: Any = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(parent)
        self._fn = fn
        self._args = args
        self._kwargs = kwargs
        self._cancel_requested = False

    def request_cancel(self) -> None:
        self._cancel_requested = True

    def run(self) -> None:
        try:
            if self._cancel_requested:
                return
            result = self._fn(*self._args, **self._kwargs)
            if not self._cancel_requested:
                self.finished_signal.emit(result)
        except Exception as exc:
            logger.exception("Analysis worker failed: %s", exc)
            if not self._cancel_requested:
                self.failed.emit(str(exc))


def stop_analysis_worker(worker: Any, wait_ms: int = 5000) -> None:
    """Cancel, wait for, and dispose of an analysis worker (dialog close).

    When the worker does not stop within *wait_ms* it is left alive instead
    of being destroyed mid-run — destroying a running QThread crashes with
    "QThread: Destroyed while thread is still running".
    """
    if worker is None:
        return
    try:
        worker.request_cancel()
        if worker.isRunning():
            stopped = worker.wait(wait_ms)
            if not stopped:
                logger.error(
                    "Analysis worker still running after %sms; leaving it "
                    "alive to avoid destroying a running thread",
                    wait_ms,
                )
                return
        worker.deleteLater()
    except Exception as exc:
        logger.warning("Failed to stop analysis worker: %s", exc)
