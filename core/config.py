"""
Configuration Management for Isotopes Analysis
"""
from __future__ import annotations

import copy
import json
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Temporary directory for storing session parameters
TEMP_DIR = Path.home() / '.isotopes_analysis'
TEMP_DIR.mkdir(exist_ok=True)
PARAMS_TEMP_FILE = TEMP_DIR / 'params.json'

# Locales directory for translations
if getattr(sys, 'frozen', False):
    # Running in a PyInstaller bundle
    BASE_DIR = Path(sys._MEIPASS)
else:
    # Running in a normal Python environment - go up one level from core/
    BASE_DIR = Path(__file__).resolve().parent.parent

LOCALES_DIR = BASE_DIR / 'locales'
# Only try to create if it doesn't exist (it might be read-only in frozen app)
if not LOCALES_DIR.exists():
    try:
        LOCALES_DIR.mkdir(exist_ok=True)
    except Exception:
        pass

CONFIG = {
    'export_csv': 'selected_samples.csv',
    'algorithm_options': ['UMAP', 'tSNE', 'PCA', 'RobustPCA', 'V1V2'],
    'default_language': 'zh',
    'languages': {
        'zh': '中文',
        'en': 'English'
    },
    'temp_dir': TEMP_DIR,
    'params_temp_file': PARAMS_TEMP_FILE,
    'session_version': 2,
    'embedding_cache_size': 8,
    'locales_dir': LOCALES_DIR,
    'umap_params': {
        'n_neighbors': 10,
        'min_dist': 0.1,
        'random_state': 42,
        'n_components': 2
    },
    'tsne_params': {
        'perplexity': 30,
        'learning_rate': 200,
        'random_state': 42,
        'n_components': 2
    },
    'pca_params': {
        'random_state': 42,
        'n_components': 2
    },
    'robust_pca_params': {
        'random_state': 42,
        'n_components': 2
    },
    'ml_params': {
        'min_region_samples': 5,
        'dbscan_min_region_samples': 20,
        'dbscan_eps': 0.18,
        'dbscan_min_samples_ratio': 0.1,
        'standardize': True,
        'smote_enabled': True,
        'smote_k_neighbors': 3,
        'smote_sampling_strategy': 1.0,
        'xgb_params': {
            'n_estimators': 200,
            'max_depth': 6,
            'learning_rate': 0.1,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'objective': 'binary:logistic',
            'eval_metric': 'logloss',
            'random_state': 42,
            'n_jobs': 1,
            'tree_method': 'exact'
        },
        'predict_threshold': 0.9
    },
    'show_ellipses': False,
    'ellipse_confidence': 0.95,  # Default confidence level
    'point_size': 60,
    'figure_size': (13, 9),
    'figure_dpi': 130,
    'savefig_dpi': 400,
    'preferred_plot_fonts': [
        'Microsoft YaHei',
        'Microsoft YaHei UI',
        'SimHei',
        'SimSun',
        'NSimSun',
        'PingFang SC',
        'Source Han Sans SC',
        'Noto Sans CJK SC',
        'Arial Unicode MS'
    ]
}

# ---------------------------------------------------------------------------
# User configuration loading
# ---------------------------------------------------------------------------

USER_CONFIG_PATH = TEMP_DIR / 'config.json'

_CONFIG_SCHEMA: dict[str, tuple] = {
    'export_csv': (str, None),
    'default_language': (str, None),
    'embedding_cache_size': (int, None),
    'session_version': (int, None),
    'show_ellipses': (bool, None),
    'ellipse_confidence': (float, None),
    'point_size': (int, None),
    'figure_dpi': (int, None),
    'savefig_dpi': (int, None),
    'figure_size': ((list, tuple), 2),
}

_MERGEABLE_KEYS: frozenset[str] = frozenset({
    'umap_params', 'tsne_params', 'pca_params', 'robust_pca_params',
    'ml_params',
})


def load_user_config() -> dict[str, object]:
    """Load user configuration from the JSON file in the temp directory.

    Returns an empty dict when the file is missing, unreadable, or does not
    contain a JSON object.  Warnings are logged for recoverable errors so the
    application can continue with built-in defaults.
    """
    if not USER_CONFIG_PATH.exists():
        return {}
    try:
        with open(USER_CONFIG_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, dict):
            logger.warning(
                'User config at %s is not a JSON object; ignoring.',
                USER_CONFIG_PATH,
            )
            return {}
        return data
    except json.JSONDecodeError as exc:
        logger.warning(
            'User config at %s contains invalid JSON: %s; ignoring.',
            USER_CONFIG_PATH,
            exc,
        )
        return {}
    except OSError as exc:
        logger.warning(
            'Cannot read user config at %s: %s; ignoring.',
            USER_CONFIG_PATH,
            exc,
        )
        return {}


def _validate_config_value(key: str, value: object, default: object) -> object:
    """Validate a single user-config value against the schema.

    Returns *value* when it passes validation, otherwise the *default*.
    """
    schema = _CONFIG_SCHEMA.get(key)
    if schema is None:
        return value
    expected_type, extra = schema
    if not isinstance(value, expected_type):
        logger.debug(
            'Config key %r expected type %s, got %s; using default.',
            key, expected_type, type(value).__name__,
        )
        return default
    if isinstance(value, str) and key == 'default_language':
        if value not in CONFIG.get('languages', {}):
            logger.debug(
                'Config key %r has unsupported language %r; using default.',
                key, value,
            )
            return default
    if key == 'figure_size' and extra == 2:
        if len(value) != 2:  # type: ignore[arg-type]
            logger.debug(
                'Config key %r expected 2-element sequence; using default.',
                key,
            )
            return default
    return value


def merge_config(user_config: dict[str, object]) -> None:
    """Merge user configuration into the global CONFIG dict in-place.

    Top-level scalars are validated and replaced individually.
    Known nested sub-dicts are shallow-merged so that user overrides for a
    subset of keys do not discard other defaults.  Unknown keys are silently
    ignored.
    """
    if not user_config:
        return

    for key, value in user_config.items():
        if key not in CONFIG:
            logger.debug('Unknown config key %r; ignoring.', key)
            continue

        if key in _MERGEABLE_KEYS:
            if isinstance(value, dict) and isinstance(CONFIG[key], dict):
                merged = copy.deepcopy(CONFIG[key])
                for sub_key, sub_value in value.items():
                    if sub_key in merged:
                        merged[sub_key] = sub_value
                    else:
                        logger.debug(
                            'Unknown sub-key %r in %r config; ignoring.',
                            sub_key, key,
                        )
                CONFIG[key] = merged
                logger.info('Merged user config for %r', key)
                continue
            logger.debug(
                'Config key %r is mergeable but user value is not a dict; skipping.',
                key,
            )
            continue

        validated = _validate_config_value(key, value, CONFIG[key])
        if validated != CONFIG[key]:
            logger.info('Config override: %r = %r', key, validated)
        CONFIG[key] = validated


def load_and_merge_config() -> None:
    """Load the user config file and merge it into global CONFIG.

    Safe to call multiple times — subsequent invocations re-read the file
    and re-apply overrides.
    """
    user_cfg = load_user_config()
    if user_cfg:
        merge_config(user_cfg)
        logger.info('User configuration loaded from %s', USER_CONFIG_PATH)
    else:
        logger.debug('No user configuration found; using built-in defaults.')
