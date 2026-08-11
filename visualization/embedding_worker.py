"""Background embedding worker for non-blocking dimensionality reduction."""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal

from .plotting.rendering.embedding.compute_algorithms import (
    compute_pca_embedding,
    compute_robust_pca_embedding,
    compute_tsne_embedding,
    compute_umap_embedding,
)

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
        parent: Any = None,
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

            algorithm = self.algorithm.strip()
            algorithm_upper = algorithm.upper()
            if algorithm_upper == "TSNE":
                algorithm = "tSNE"
            elif algorithm_upper == "ROBUSTPCA":
                algorithm = "RobustPCA"
            else:
                algorithm = algorithm.upper() if algorithm_upper == "UMAP" else algorithm

            result = self._compute_embedding(algorithm, x)
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
                "params": dict(self.params),
            }
            self.progress.emit(self.task_token, 100, "done")
            self.finished_signal.emit(self.task_token, payload)
        except Exception as exc:
            logger.exception("Embedding worker failed: %s", exc)
            self.failed.emit(self.task_token, str(exc))

    def _compute_embedding(self, algorithm: str, x: np.ndarray) -> dict[str, Any] | None:
        if algorithm == "UMAP":
            self.progress.emit(self.task_token, 20, "umap_init")
            self.progress.emit(self.task_token, 40, "umap_fit")
            embedding = compute_umap_embedding(x, self.params)
            return {"embedding": embedding, "meta": {}}

        if algorithm == "tSNE":
            self.progress.emit(self.task_token, 20, "tsne_init")
            self.progress.emit(self.task_token, 45, "tsne_fit")
            embedding = compute_tsne_embedding(x, self.params)
            return {"embedding": embedding, "meta": {}}

        if algorithm == "PCA":
            self.progress.emit(self.task_token, 20, "pca_scale")
            self.progress.emit(self.task_token, 50, "pca_fit")
            result = compute_pca_embedding(x, self.params)
            return {
                "embedding": result["embedding"],
                "meta": {
                    "last_pca_variance": result.get("variance"),
                    "last_pca_components": result.get("components"),
                    "current_feature_names": self.feature_names,
                },
            }

        if algorithm == "RobustPCA":
            self.progress.emit(self.task_token, 20, "robust_scale")
            if x.shape[0] <= x.shape[1]:
                self.progress.emit(self.task_token, 50, "robust_fallback_pca_fit")
            else:
                self.progress.emit(self.task_token, 40, "robust_mcd_fit")
            result = compute_robust_pca_embedding(x, self.params)
            meta = {
                "last_pca_variance": result.get("variance"),
                "last_pca_components": result.get("components"),
                "current_feature_names": self.feature_names,
            }
            return {"embedding": result["embedding"], "meta": meta}

        return None
