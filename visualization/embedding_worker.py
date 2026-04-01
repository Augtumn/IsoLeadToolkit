"""Background embedding worker for non-blocking dimensionality reduction."""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal

from .workers import compute_embedding_payload, normalize_algorithm_name

logger = logging.getLogger(__name__)


class EmbeddingWorker(QThread):
    """Compute embeddings in a background thread.

    The worker only computes numerical embeddings and never touches UI objects.
    """

    started_signal = pyqtSignal(int)
    progress = pyqtSignal(int, int, str)
    finished_signal = pyqtSignal(int, object)
    failed = pyqtSignal(int, str)
    cancelled = pyqtSignal(int)

    def __init__(
        self,
        task_token: int,
        algorithm: str,
        x_data: np.ndarray,
        params: dict[str, Any],
        feature_names: list[str],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.task_token = int(task_token)
        self.algorithm = str(algorithm)
        self.x_data = x_data
        self.params = dict(params or {})
        self.feature_names = list(feature_names or [])
        self._cancel_requested = False

    def request_cancel(self) -> None:
        self._cancel_requested = True

    def _is_cancelled(self) -> bool:
        return self._cancel_requested

    def run(self) -> None:
        self.started_signal.emit(self.task_token)
        try:
            self.progress.emit(self.task_token, 5, "prepare")
            if self._is_cancelled():
                self.cancelled.emit(self.task_token)
                return

            x = np.asarray(self.x_data)
            if x.size == 0 or x.shape[0] == 0:
                self.failed.emit(self.task_token, "No data available for embedding computation")
                return

            algorithm = normalize_algorithm_name(self.algorithm)

            result = compute_embedding_payload(
                algorithm=algorithm,
                x=x,
                params=self.params,
                feature_names=self.feature_names,
                report=lambda percent, stage: self.progress.emit(self.task_token, percent, stage),
            )
            if result is None:
                self.failed.emit(self.task_token, f"Failed to compute embedding for {algorithm}")
                return

            if self._is_cancelled():
                self.cancelled.emit(self.task_token)
                return

            payload = {
                "algorithm": algorithm,
                "embedding": result["embedding"],
                "meta": result.get("meta", {}),
            }
            self.progress.emit(self.task_token, 100, "done")
            self.finished_signal.emit(self.task_token, payload)
        except Exception as exc:
            logger.exception("Embedding worker failed: %s", exc)
            self.failed.emit(self.task_token, str(exc))
