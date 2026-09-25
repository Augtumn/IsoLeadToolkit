"""Tests for user config loading and merging."""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import core.config as config_module


def _write_config(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding='utf-8')


def test_load_user_config_returns_empty_when_missing() -> None:
    with patch.object(config_module, 'USER_CONFIG_PATH', Path('/nonexistent/config.json')):
        assert config_module.load_user_config() == {}


def test_load_user_config_parses_valid_json() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cfg_path = Path(tmp) / 'config.json'
        _write_config(cfg_path, {'default_language': 'en', 'point_size': 80})
        with patch.object(config_module, 'USER_CONFIG_PATH', cfg_path):
            result = config_module.load_user_config()
            assert result == {'default_language': 'en', 'point_size': 80}


def test_load_user_config_returns_empty_for_invalid_json() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cfg_path = Path(tmp) / 'config.json'
        cfg_path.write_text('not valid json', encoding='utf-8')
        with patch.object(config_module, 'USER_CONFIG_PATH', cfg_path):
            assert config_module.load_user_config() == {}


def test_load_user_config_returns_empty_when_not_dict() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cfg_path = Path(tmp) / 'config.json'
        cfg_path.write_text('[1, 2, 3]', encoding='utf-8')
        with patch.object(config_module, 'USER_CONFIG_PATH', cfg_path):
            assert config_module.load_user_config() == {}


def test_merge_config_override_scalar() -> None:
    from core.config import CONFIG

    original = CONFIG['point_size']
    assert original > 0
    try:
        config_module.merge_config({'point_size': original + 10})
        assert CONFIG['point_size'] == original + 10
    finally:
        CONFIG['point_size'] = original


def test_merge_config_shallow_merges_nested_dicts() -> None:
    from core.config import CONFIG

    original_umap = dict(CONFIG['umap_params'])
    assert 'n_neighbors' in original_umap
    try:
        config_module.merge_config({'umap_params': {'n_neighbors': 99}})
        assert CONFIG['umap_params']['n_neighbors'] == 99
        assert CONFIG['umap_params']['n_components'] == original_umap['n_components']
    finally:
        CONFIG['umap_params'] = original_umap


def test_merge_config_ignores_unknown_keys() -> None:
    config_module.merge_config({'nonexistent_key_xyz': 'value'})


def test_merge_config_uses_default_for_wrong_type() -> None:
    from core.config import CONFIG

    original = CONFIG['point_size']
    assert isinstance(original, int)
    try:
        config_module.merge_config({'point_size': 'not_an_int'})
        assert CONFIG['point_size'] == original
    finally:
        CONFIG['point_size'] = original


def test_merge_config_skips_mergeable_key_with_non_dict() -> None:
    from core.config import CONFIG

    original_umap = dict(CONFIG['umap_params'])
    try:
        config_module.merge_config({'umap_params': 'not_a_dict'})
        assert CONFIG['umap_params'] == original_umap
    finally:
        CONFIG['umap_params'] = original_umap


def test_merge_config_validates_language() -> None:
    from core.config import CONFIG

    original_lang = CONFIG['default_language']
    try:
        config_module.merge_config({'default_language': 'invalid_lang_code'})
        assert CONFIG['default_language'] == original_lang
    finally:
        CONFIG['default_language'] = original_lang


def test_merge_config_noop_with_empty_dict() -> None:
    from core.config import CONFIG

    snapshot = {k: v for k, v in CONFIG.items() if not isinstance(v, dict)}
    config_module.merge_config({})
    for k, v in snapshot.items():
        assert CONFIG[k] == v if not isinstance(v, dict) else True


def test_load_and_merge_config_end_to_end() -> None:
    from core.config import CONFIG

    with tempfile.TemporaryDirectory() as tmp:
        cfg_path = Path(tmp) / 'config.json'
        _write_config(cfg_path, {'point_size': 75, 'default_language': 'en'})
        with patch.object(config_module, 'USER_CONFIG_PATH', cfg_path):
            original_size = CONFIG['point_size']
            original_lang = CONFIG['default_language']
            try:
                config_module.load_and_merge_config()
                assert CONFIG['point_size'] == 75
                assert CONFIG['default_language'] == 'en'
            finally:
                CONFIG['point_size'] = original_size
                CONFIG['default_language'] = original_lang
