"""
Configuration Management for Isotopes Analysis
"""
import os
import json
from pathlib import Path

# Temporary directory for storing session parameters
TEMP_DIR = Path.home() / '.isotopes_analysis'
TEMP_DIR.mkdir(exist_ok=True)
PARAMS_TEMP_FILE = TEMP_DIR / 'params.json'

# Locales directory for translations
BASE_DIR = Path(__file__).resolve().parent
LOCALES_DIR = BASE_DIR / 'locales'
LOCALES_DIR.mkdir(exist_ok=True)

CONFIG = {
    'export_csv': 'selected_samples.csv',
    'algorithm_options': ['UMAP', 'tSNE'],
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
    'point_size': 60,
    'figure_size': (13, 9),
    'figure_dpi': 130,
    'preferred_plot_fonts': [
        'Microsoft YaHei',
        'Microsoft YaHei UI',
        'SimHei',
        'PingFang SC',
        'Source Han Sans SC',
        'Noto Sans CJK SC',
        'Arial Unicode MS'
    ]
}
