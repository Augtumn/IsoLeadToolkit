"""Background embedding worker for non-blocking dimensionality reduction."""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal

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
            }
            self.progress.emit(self.task_token, 100, "done")
            self.finished_signal.emit(self.task_token, payload)
        except Exception as exc:
            logger.exception("Embedding worker failed: %s", exc)
            self.failed.emit(self.task_token, str(exc))

    def _compute_embedding(self, algorithm: str, x: np.ndarray) -> dict[str, Any] | None:
        if algorithm == "UMAP":
            self.progress.emit(self.task_token, 20, "umap_init")
            import umap

            reducer = umap.UMAP(**self.params)
            self.progress.emit(self.task_token, 40, "umap_fit")
            embedding = reducer.fit_transform(x)
            return {"embedding": embedding, "meta": {}}

        if algorithm == "tSNE":
            self.progress.emit(self.task_token, 20, "tsne_init")
            from sklearn.manifold import TSNE

            n_samples = x.shape[0]
            perplexity = float(self.params.get("perplexity", 30))
            if n_samples <= 1:
                return None
            if perplexity >= n_samples:
                perplexity = max(2, n_samples - 1)

            learning_rate = max(float(self.params.get("learning_rate", 200)), 10)
            reducer = TSNE(
                n_components=self.params.get("n_components", 2),
                perplexity=perplexity,
                learning_rate=learning_rate,
                random_state=self.params.get("random_state", 42),
                verbose=0,
                n_jobs=-1,
            )
            self.progress.emit(self.task_token, 45, "tsne_fit")
            embedding = reducer.fit_transform(x)
            return {"embedding": embedding, "meta": {}}

        if algorithm == "PCA":
            self.progress.emit(self.task_token, 20, "pca_scale")
            from sklearn.decomposition import PCA
            from sklearn.preprocessing import StandardScaler

            scaler = StandardScaler()
            try:
                x_scaled = scaler.fit_transform(x)
                if np.isnan(x_scaled).any():
                    x_scaled = np.nan_to_num(x_scaled)
            except Exception:
                x_scaled = x

            reducer = PCA(
                n_components=self.params.get("n_components", 2),
                random_state=self.params.get("random_state", 42),
            )
            self.progress.emit(self.task_token, 50, "pca_fit")
            embedding = reducer.fit_transform(x_scaled)
            return {
                "embedding": embedding,
                "meta": {
                    "last_pca_variance": reducer.explained_variance_ratio_,
                    "last_pca_components": reducer.components_,
                    "current_feature_names": self.feature_names,
                },
            }

        if algorithm == "RobustPCA":
            self.progress.emit(self.task_token, 20, "robust_scale")
            from sklearn.covariance import MinCovDet
            from sklearn.decomposition import PCA
            from sklearn.preprocessing import StandardScaler

            scaler = StandardScaler()
            try:
                x_scaled = scaler.fit_transform(x)
                if np.isnan(x_scaled).any():
                    x_scaled = np.nan_to_num(x_scaled)
            except Exception:
                x_scaled = x

            meta: dict[str, Any] = {"current_feature_names": self.feature_names}
            if x_scaled.shape[0] <= x_scaled.shape[1]:
                reducer = PCA(
                    n_components=self.params.get("n_components", 2),
                    random_state=self.params.get("random_state", 42),
                )
                self.progress.emit(self.task_token, 50, "robust_fallback_pca_fit")
                embedding = reducer.fit_transform(x_scaled)
                meta["last_pca_variance"] = reducer.explained_variance_ratio_
                meta["last_pca_components"] = reducer.components_
                return {"embedding": embedding, "meta": meta}

            support_fraction = self.params.get("support_fraction", 0.75)
            mcd = MinCovDet(
                random_state=self.params.get("random_state", 42),
                support_fraction=support_fraction,
            )
            self.progress.emit(self.task_token, 40, "robust_mcd_fit")
            mcd.fit(x_scaled)

            cov = mcd.covariance_
            mean = mcd.location_
            eigvals, eigvecs = np.linalg.eigh(cov)
            order = np.argsort(eigvals)[::-1]
            eigvecs = eigvecs[:, order]
            eigvals = eigvals[order]
            n_components = self.params.get("n_components", 2)
            components = eigvecs[:, :n_components]
            embedding = (x_scaled - mean) @ components

            if eigvals.sum() > 0:
                meta["last_pca_variance"] = eigvals[:n_components] / eigvals.sum()
            meta["last_pca_components"] = components.T
            return {"embedding": embedding, "meta": meta}

        return None
