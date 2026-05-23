"""Builtin provenance classification plugin (XGBoost OvR)."""
from __future__ import annotations
from typing import Any

from plugins.api import MLClassifierPlugin, PluginMeta
from data.provenance_ml import (
    prepare_prediction_matrix,
    predict_provenance,
    run_provenance_pipeline,
)


class ProvenanceMLPlugin(MLClassifierPlugin):
    meta = PluginMeta(
        name="provenance_ml",
        version="1.0",
        api_version="1.0",
        plugin_type="classifier",
        author="IsotopesAnalyse",
        description="XGBoost OvR provenance classification with SMOTE+DBSCAN",
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

        result = run_provenance_pipeline(
            training_df,
            region_col,
            feature_cols,
            target_df=training_df,
            target_feature_cols=feature_cols,
            min_region_samples=params.get("min_region_samples", 5),
            dbscan_eps=params.get("dbscan_eps", 0.18),
            standardize=params.get("standardize", True),
            smote_enabled=params.get("smote_enabled", True),
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
            "regions": regions,
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
            "regions": regions,
        }
