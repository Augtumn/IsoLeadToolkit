"""
Configuration Management for Isotopes Analysis
"""
import os
import json
import sys
from pathlib import Path

# Temporary directory for storing session parameters
TEMP_DIR = Path.home() / '.isotopes_analysis'
TEMP_DIR.mkdir(exist_ok=True)
PARAMS_TEMP_FILE = TEMP_DIR / 'params.json'

# Locales directory for translations
if getattr(sys, 'frozen', False):
    # Running in a PyInstaller bundle
    BASE_DIR = Path(sys._MEIPASS)
else:
    # Running in a normal Python environment
    BASE_DIR = Path(__file__).resolve().parent

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
    'show_ellipses': False,
    'ellipse_confidence': 0.95,  # Default confidence level
    'point_size': 60,
    'figure_size': (13, 9),
    'figure_dpi': 130,
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
