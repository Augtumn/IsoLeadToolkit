"""Builtin provenance classification plugin (XGBoost OvR)."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from plugins.api import MLClassifierPlugin, PluginMeta

logger = logging.getLogger(__name__)


class ProvenanceMLError(RuntimeError):
    """Raised when the ML provenance pipeline fails or is misconfigured."""


def _validate_columns(df: pd.DataFrame, cols: List[str], label: str) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ProvenanceMLError(f"Missing {label} columns: {missing}")


def _coerce_numeric(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    for col in cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df


def _standardize_features(x: np.ndarray, standardize: bool) -> Tuple[np.ndarray, Any]:
    if not standardize:
        return x, None
    from sklearn.preprocessing import StandardScaler
    scaler = StandardScaler()
    return scaler.fit_transform(x), scaler


def prepare_training_data(
    df: pd.DataFrame,
    region_col: str,
    feature_cols: List[str],
    min_region_samples: int = 5,
    dbscan_min_region_samples: int = 20,
    dbscan_eps: float = 0.18,
    dbscan_min_samples_ratio: float = 0.1,
    standardize: bool = True,
    random_state: int = 42,
) -> Dict[str, Any]:
    if df is None:
        raise ProvenanceMLError("Training data is empty.")

    _validate_columns(df, [region_col] + feature_cols, "training")

    original_rows = int(len(df))
    work = df[[region_col] + feature_cols].copy()
    work.replace(['', 'nan', 'NaN', None], np.nan, inplace=True)
    work[region_col] = work[region_col].astype(str).str.strip()
    work = work[work[region_col].notna() & (work[region_col] != '')]
    work = _coerce_numeric(work, feature_cols)
    work = work.dropna(subset=feature_cols)
    clean_rows = int(len(work))
    if clean_rows == 0:
        raise ProvenanceMLError("No valid training rows after cleaning.")

    region_counts = work[region_col].value_counts()
    keep_regions = region_counts[region_counts >= min_region_samples].index.tolist()
    dropped_regions = [r for r in region_counts.index if r not in keep_regions]
    work = work[work[region_col].isin(keep_regions)].copy()
    if work.empty:
        raise ProvenanceMLError("No regions meet the minimum sample requirement.")

    x_raw = work[feature_cols].to_numpy(dtype=float)
    x_scaled, scaler = _standardize_features(x_raw, standardize)
    regions = work[region_col].astype(str).values

    labels = np.array([''] * len(work), dtype=object)
    outliers_removed = 0
    cluster_info: Dict[str, Dict[str, Any]] = {}

    from sklearn.cluster import DBSCAN

    for region in sorted(set(regions)):
        idx = np.where(regions == region)[0]
        n = int(len(idx))
        if n >= dbscan_min_region_samples:
            min_samples = max(2, int(np.ceil(dbscan_min_samples_ratio * n)))
            db = DBSCAN(eps=dbscan_eps, min_samples=min_samples)
            cluster_labels = db.fit_predict(x_scaled[idx])
            outliers = int(np.sum(cluster_labels == -1))
            outliers_removed += outliers
            cluster_ids = sorted({c for c in cluster_labels if c != -1})

            if not cluster_ids:
                cluster_info[region] = {
                    'clusters': 0,
                    'outliers': outliers,
                    'dbscan': True,
                    'min_samples': min_samples,
                }
                continue

            if len(cluster_ids) == 1:
                keep_idx = idx[cluster_labels != -1]
                labels[keep_idx] = region
                cluster_info[region] = {
                    'clusters': 1,
                    'outliers': outliers,
                    'dbscan': True,
                    'min_samples': min_samples,
                }
            else:
                cid_to_seq = {cid: i + 1 for i, cid in enumerate(cluster_ids)}
                for cid in cluster_ids:
                    keep_idx = idx[cluster_labels == cid]
                    labels[keep_idx] = f"{region} {cid_to_seq[cid]}"
                cluster_info[region] = {
                    'clusters': len(cluster_ids),
                    'outliers': outliers,
                    'dbscan': True,
                    'min_samples': min_samples,
                }
        else:
            labels[idx] = region
            cluster_info[region] = {
                'clusters': 1,
                'outliers': 0,
                'dbscan': False,
                'min_samples': None,
            }

    keep_mask = labels != ''
    x_final = x_scaled[keep_mask]
    y_final = labels[keep_mask]
    kept_indices = work.index.to_numpy()[keep_mask]

    if len(y_final) == 0:
        raise ProvenanceMLError("No training samples remain after DBSCAN filtering.")

    stats = {
        'input_rows': original_rows,
        'clean_rows': clean_rows,
        'rows_after_region_filter': int(len(work)),
        'rows_final': int(len(y_final)),
        'regions_initial': int(region_counts.size),
        'regions_dropped_small': dropped_regions,
        'labels_final': int(len(set(y_final))),
        'outliers_removed': int(outliers_removed),
    }

    return {
        'X': x_final,
        'y': y_final,
        'scaler': scaler,
        'feature_cols': feature_cols,
        'kept_indices': kept_indices,
        'stats': stats,
        'cluster_info': cluster_info,
        'region_counts': region_counts.to_dict(),
    }


def train_ovr_xgboost(
    x: np.ndarray,
    y: np.ndarray,
    xgb_params: Optional[Dict[str, Any]] = None,
    smote_enabled: bool = True,
    smote_k_neighbors: int = 3,
    smote_sampling_strategy: float | str = 1.0,
    random_state: int = 42,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    if x is None or len(x) == 0:
        raise ProvenanceMLError("No training features provided.")

    try:
        from xgboost import XGBClassifier
    except Exception as exc:
        raise ProvenanceMLError("xgboost is required for provenance ML.") from exc

    labels = sorted(set(y))
    models: Dict[str, Any] = {}
    model_info: Dict[str, Any] = {}

    for label in labels:
        y_bin = (y == label).astype(int)
        pos = int(np.sum(y_bin))
        neg = int(len(y_bin) - pos)

        if pos < 2 or neg < 2:
            model_info[label] = {
                'pos': pos,
                'neg': neg,
                'skipped': True,
                'reason': 'not enough samples',
            }
            continue

        x_train = x
        y_train = y_bin
        smote_info: Dict[str, Any] = {'applied': False}

        if smote_enabled:
            try:
                from imblearn.over_sampling import SMOTE
            except Exception as exc:
                smote_info = {'applied': False, 'reason': f"SMOTE unavailable: {exc}"}
            else:
                min_count = min(pos, neg)
                if min_count >= 2 and pos != neg:
                    k = min(smote_k_neighbors, min_count - 1)
                    if k >= 1:
                        smote = SMOTE(
                            random_state=random_state,
                            k_neighbors=k,
                            sampling_strategy=smote_sampling_strategy,
                        )
                        x_train, y_train = smote.fit_resample(x, y_bin)
                        smote_info = {
                            'applied': True,
                            'k_neighbors': k,
                            'sampling_strategy': smote_sampling_strategy,
                        }
                else:
                    smote_info = {'applied': False, 'reason': 'balanced or too few samples'}

        params = dict(xgb_params or {})
        params.setdefault('random_state', random_state)
        params.setdefault('n_jobs', 1)
        params.setdefault('objective', 'binary:logistic')
        params.setdefault('eval_metric', 'logloss')
        params.setdefault('tree_method', 'exact')

        model = XGBClassifier(**params)
        model.fit(x_train, y_train)
        models[label] = model
        model_info[label] = {
            'pos': pos,
            'neg': neg,
            'smote': smote_info,
            'samples_used': int(len(y_train)),
        }

    if not models:
        raise ProvenanceMLError("No models were trained. Check label counts.")

    return models, model_info


def prepare_prediction_matrix(
    df: pd.DataFrame,
    feature_cols: List[str],
) -> Tuple[np.ndarray, np.ndarray]:
    if df is None:
        raise ProvenanceMLError("Prediction data is empty.")

    _validate_columns(df, feature_cols, "prediction")
    work = df[feature_cols].copy()
    work = _coerce_numeric(work, feature_cols)
    valid_mask = ~work.isna().any(axis=1)
    x_all = work.to_numpy(dtype=float)
    return x_all, valid_mask.to_numpy()


def predict_provenance(
    models: Dict[str, Any],
    scaler: Optional[Any],
    x_raw: np.ndarray,
    threshold: float = 0.9,
) -> Tuple[List[str], np.ndarray, np.ndarray, List[str]]:
    if x_raw is None or x_raw.size == 0:
        return [], np.array([]), np.zeros((0, 0)), []

    x_scaled = scaler.transform(x_raw) if scaler is not None else x_raw
    label_order = sorted(models.keys())
    proba_list = []

    for label in label_order:
        model = models[label]
        try:
            probs = model.predict_proba(x_scaled)[:, 1]
        except Exception:
            probs = model.predict(x_scaled)
        proba_list.append(probs)

    if not proba_list:
        return [], np.array([]), np.zeros((x_scaled.shape[0], 0)), label_order

    proba = np.column_stack(proba_list)
    max_idx = np.argmax(proba, axis=1)
    max_prob = proba[np.arange(proba.shape[0]), max_idx]

    pred_labels = []
    for i, prob in enumerate(max_prob):
        if prob < threshold:
            pred_labels.append('None')
        else:
            pred_labels.append(label_order[int(max_idx[i])])

    return pred_labels, max_prob, proba, label_order


def run_provenance_pipeline(
    training_df: pd.DataFrame,
    region_col: str,
    feature_cols: List[str],
    target_df: pd.DataFrame,
    target_feature_cols: List[str],
    min_region_samples: int = 5,
    dbscan_min_region_samples: int = 20,
    dbscan_eps: float = 0.18,
    dbscan_min_samples_ratio: float = 0.1,
    standardize: bool = True,
    smote_enabled: bool = True,
    smote_k_neighbors: int = 3,
    smote_sampling_strategy: float | str = 1.0,
    xgb_params: Optional[Dict[str, Any]] = None,
    predict_threshold: float = 0.9,
    random_state: int = 42,
) -> Dict[str, Any]:
    np.random.seed(random_state)

    training = prepare_training_data(
        training_df,
        region_col,
        feature_cols,
        min_region_samples=min_region_samples,
        dbscan_min_region_samples=dbscan_min_region_samples,
        dbscan_eps=dbscan_eps,
        dbscan_min_samples_ratio=dbscan_min_samples_ratio,
        standardize=standardize,
        random_state=random_state,
    )

    models, model_info = train_ovr_xgboost(
        training['X'],
        training['y'],
        xgb_params=xgb_params,
        smote_enabled=smote_enabled,
        smote_k_neighbors=smote_k_neighbors,
        smote_sampling_strategy=smote_sampling_strategy,
        random_state=random_state,
    )

    x_all, valid_mask = prepare_prediction_matrix(target_df, target_feature_cols)
    x_valid = x_all[valid_mask]

    pred_labels, pred_probs, proba, label_order = predict_provenance(
        models,
        training['scaler'],
        x_valid,
        threshold=predict_threshold,
    )

    return {
        'training': training,
        'models': models,
        'model_info': model_info,
        'predictions': {
            'label_order': label_order,
            'labels': pred_labels,
            'max_prob': pred_probs,
            'proba': proba,
            'valid_mask': valid_mask,
        },
    }


class ProvenanceMLPlugin(MLClassifierPlugin):
    meta = PluginMeta(
        name="provenance_ml",
        version="1.0",
        api_version="1.0",
        plugin_type="classifier",
        author="IsotopesAnalyse",
        description="XGBoost OvR provenance classification with SMOTE+DBSCAN",
        source="builtin",
    )

    def __init__(self):
        self._models: dict[str, Any] = {}
        self._pipeline_result: dict[str, Any] | None = None
        self._feature_cols: list[str] = []
        self._scaler: Any = None

    def validate_environment(self) -> tuple[bool, str]:
        try:
            import xgboost  # noqa: F401
            import sklearn  # noqa: F401
            import imblearn  # noqa: F401
            return True, "ok"
        except ImportError as e:
            return False, str(e)

    def get_default_params(self) -> dict[str, Any]:
        return {
            "min_region_samples": 5,
            "dbscan_eps": 0.18,
            "standardize": True,
            "smote_enabled": True,
            "xgb_n_estimators": 200,
            "xgb_max_depth": 6,
            "predict_threshold": 0.9,
        }

    def fit(self, training_df, region_col, feature_cols, **params):
        # Build xgb_params from the plugin params dict
        xgb_params = {}
        if "xgb_n_estimators" in params:
            xgb_params["n_estimators"] = params.pop("xgb_n_estimators")
        if "xgb_max_depth" in params:
            xgb_params["max_depth"] = params.pop("xgb_max_depth")

        # Forward all supported params to run_provenance_pipeline
        result = run_provenance_pipeline(
            training_df,
            region_col,
            feature_cols,
            target_df=training_df,
            target_feature_cols=feature_cols,
            min_region_samples=params.get("min_region_samples", 5),
            dbscan_min_region_samples=params.get("dbscan_min_region_samples", 20),
            dbscan_eps=params.get("dbscan_eps", 0.18),
            dbscan_min_samples_ratio=params.get("dbscan_min_samples_ratio", 0.1),
            standardize=params.get("standardize", True),
            smote_enabled=params.get("smote_enabled", True),
            smote_k_neighbors=params.get("smote_k_neighbors", 3),
            smote_sampling_strategy=params.get("smote_sampling_strategy", 1.0),
            xgb_params=xgb_params if xgb_params else None,
            predict_threshold=params.get("predict_threshold", 0.9),
        )
        self._pipeline_result = result
        self._models = result.get("models", {})
        self._feature_cols = result["training"].get("feature_cols", [])
        self._scaler = result["training"].get("scaler")
        return {
            "regions": list(self._models.keys()),
            "pipeline_result": result,
        }

    def predict(self, df):
        if self._pipeline_result is None:
            raise RuntimeError("Model not fitted. Call fit() first.")
        x_all, valid_mask = prepare_prediction_matrix(df, self._feature_cols)
        x_valid = x_all[valid_mask]
        labels, probs, proba, regions = predict_provenance(
            self._models, self._scaler, x_valid,
            threshold=self._pipeline_result.get("predictions", {}).get(
                "predict_threshold", 0.9
            ),
        )
        return {
            "labels": labels,
            "probabilities": probs,
            "proba": proba,
            "regions": regions,
            "valid_mask": valid_mask,
        }

    def predict_proba(self, df):
        if self._pipeline_result is None:
            raise RuntimeError("Model not fitted. Call fit() first.")
        x_all, valid_mask = prepare_prediction_matrix(df, self._feature_cols)
        x_valid = x_all[valid_mask]
        _, probs, _, regions = predict_provenance(
            self._models, self._scaler, x_valid,
            threshold=0.0,  # no threshold filtering for proba
        )
        return {
            "probabilities": probs,
            "proba": None,
            "regions": regions,
            "valid_mask": valid_mask,
        }
