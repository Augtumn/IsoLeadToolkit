"""Persistence facade tests: atomic I/O, autosave hook, restore, cache."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

import core.persistence as persistence
import core.persistence.paths as paths
from core import app_state, state_gateway
from core.cache import EmbeddingCache, build_data_signature
from core.persistence.cache import load_cache, save_cache


def _fake_state() -> SimpleNamespace:
    """Minimal app_state stand-in carrying a data signature."""
    df = pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [4.0, 5.0, 6.0]})
    return SimpleNamespace(
        df_global=df,
        file_path="tests/data/sample.xlsx",
        sheet_name="Sheet1",
        data_cols=["a", "b"],
        group_cols=["Province"],
        data_version=3,
    )


def test_save_all_writes_both_files(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(persistence, "SESSION_FILE", tmp_path / "params.json")
    monkeypatch.setattr(persistence, "UI_STATE_FILE", tmp_path / "ui_state.json")

    state_gateway.set_render_mode("tSNE")
    state_gateway.set_param_presets({"my preset": {"algorithm": "UMAP"}})
    state_gateway.set_hidden_groups({"Group A"})

    assert persistence.save_all(state_gateway) is True

    session = json.loads((tmp_path / "params.json").read_text(encoding="utf-8"))
    assert session["algorithm"] == "tSNE"
    assert session["session_version"] >= 1

    ui = json.loads((tmp_path / "ui_state.json").read_text(encoding="utf-8"))
    assert ui["param_presets"]["my preset"]["algorithm"] == "UMAP"
    # Sets must round-trip through JSON as lists (lossless via normalizers).
    assert ui["hidden_groups"] == ["Group A"]


def test_load_ui_state_and_restore_snapshot(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(persistence, "SESSION_FILE", tmp_path / "params.json")
    monkeypatch.setattr(persistence, "UI_STATE_FILE", tmp_path / "ui_state.json")

    state_gateway.set_color_scheme("retro")
    persistence.save_all(state_gateway)

    # Corrupt the file to check isolation.
    (tmp_path / "ui_state.json").write_text("{not json", encoding="utf-8")
    assert persistence.load_ui_state() is None
    corrupt_files = list(tmp_path.glob("ui_state.corrupt-*"))
    assert corrupt_files, "corrupt file must be isolated, not deleted"


def test_restore_snapshot_ignores_non_persisted_keys(caplog) -> None:
    store = app_state.state_store
    original_mode = store.snapshot()["render_mode"]
    original_df = store.snapshot()["df_global"]
    store.restore_snapshot({
        "render_mode": "PCA",
        "algorithm": "PCA",
        "df_global": "smuggled dataframe",
        "not_a_real_field": 42,
    })
    snapshot = store.snapshot()
    assert snapshot["render_mode"] == "PCA"
    assert snapshot["algorithm"] == "PCA"
    assert snapshot["df_global"] is original_df  # runtime fields untouched
    assert "not_a_real_field" not in snapshot
    store.dispatch({"type": "SET_RENDER_MODE", "render_mode": original_mode})


def test_autosave_hook_immediate_and_debounced(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(persistence, "SESSION_FILE", tmp_path / "params.json")
    monkeypatch.setattr(persistence, "UI_STATE_FILE", tmp_path / "ui_state.json")

    store = app_state.state_store
    persistence.install_autosave(store, interval=3600.0)
    try:
        # Immediate action flushes right away.
        store.dispatch({"type": "SET_PARAM_PRESETS", "presets": {"p1": {}}})
        assert (tmp_path / "params.json").exists()
        params_file = tmp_path / "params.json"
        first_mtime = params_file.stat().st_mtime_ns

        # Non-immediate dispatches inside the interval do not rewrite.
        store.dispatch({"type": "SET_COLOR_SCHEME", "scheme": "vibrant"})
        assert params_file.stat().st_mtime_ns == first_mtime

        # The dispatch-count safety net eventually saves.
        for i in range(persistence.DEFAULT_AUTOSAVE_DISPATCHES + 1):
            store.dispatch({"type": "SET_COLOR_SCHEME", "scheme": f"scheme-{i}"})
        assert params_file.stat().st_mtime_ns > first_mtime
    finally:
        store._dispatch_hook = None


def test_clean_exit_marker_roundtrip(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(persistence, "EXIT_OK_FILE", tmp_path / "last_exit_ok")
    monkeypatch.setattr(persistence, "SESSION_FILE", tmp_path / "params.json")
    monkeypatch.setattr(persistence, "UI_STATE_FILE", tmp_path / "ui_state.json")

    # No marker and no session files => first run, treated as clean.
    assert persistence.consume_exit_marker() is True
    # No marker but a previous session exists => crash detected.
    (tmp_path / "params.json").write_text("{}", encoding="utf-8")
    assert persistence.consume_exit_marker() is False
    # Marker written on clean exit is consumed exactly once.
    persistence.mark_clean_exit()
    assert persistence.consume_exit_marker() is True
    assert persistence.consume_exit_marker() is False


def test_extract_legacy_projection_presets(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(paths, "THEMES_FILE", tmp_path / "user_themes.json")
    (tmp_path / "user_themes.json").write_text(
        json.dumps({
            "My Theme": {"grid": True},
            "projection_presets": {"P1": {"algorithm": "UMAP"}},
        }),
        encoding="utf-8",
    )

    themes, presets = persistence.extract_legacy_projection_presets()
    assert presets == {"P1": {"algorithm": "UMAP"}}
    assert themes == {"My Theme": {"grid": True}}
    assert "projection_presets" not in themes

    # The cleaned container is written back, so the migration runs once.
    on_disk = json.loads((tmp_path / "user_themes.json").read_text(encoding="utf-8"))
    assert "projection_presets" not in on_disk
    themes2, presets2 = persistence.extract_legacy_projection_presets()
    assert presets2 is None
    assert themes2 == {"My Theme": {"grid": True}}


def test_restore_snapshot_normalizes_set_and_tuple_fields(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(persistence, "SESSION_FILE", tmp_path / "params.json")
    monkeypatch.setattr(persistence, "UI_STATE_FILE", tmp_path / "ui_state.json")

    state_gateway.set_hidden_groups({"A", "B"})
    state_gateway.set_legend_offset((0.1, 0.2))
    persistence.save_all(state_gateway)

    # Simulate a fresh process: wipe snapshot fields to defaults, then restore.
    store = app_state.state_store
    store._snapshot["hidden_groups"] = set()
    store._snapshot["legend_offset"] = (0.0, 0.0)
    store._sync_state()

    payload = persistence.load_ui_state()
    store.restore_snapshot(payload)
    snapshot = store.snapshot()
    assert snapshot["hidden_groups"] == {"A", "B"}
    assert snapshot["legend_offset"] == (0.1, 0.2)


def test_cache_roundtrip_with_signature_validation(tmp_path: Path) -> None:
    cache_file = tmp_path / "embedding_cache.npz"
    state = _fake_state()
    signature = build_data_signature(state)
    key = ("embed", "UMAP", '{"n_neighbors": 10}', 0, signature)

    cache = EmbeddingCache(max_entries=8)
    cache.set(key, np.arange(12.0).reshape(4, 3))

    assert save_cache(cache, cache_file) is True
    fresh = EmbeddingCache(max_entries=8)
    assert load_cache(fresh, state, cache_file) == 1
    assert fresh.get(key) is not None


def test_cache_drops_stale_signature(tmp_path: Path) -> None:
    cache_file = tmp_path / "embedding_cache.npz"
    state = _fake_state()
    current_signature = build_data_signature(state)
    stale_signature = (state.file_path, state.sheet_name, (0, 0), (), (), 0, ())
    assert stale_signature != current_signature

    cache = EmbeddingCache(max_entries=8)
    cache.set(
        ("embed", "UMAP", "{}", "all", current_signature),
        np.zeros((2, 2)),
    )
    cache.set(
        ("embed", "UMAP", "{}", "all", stale_signature),
        np.ones((2, 2)),
    )
    assert save_cache(cache, cache_file) is True

    fresh = EmbeddingCache(max_entries=8)
    assert load_cache(fresh, state, cache_file) == 1
    assert fresh.get(("embed", "UMAP", "{}", "all", stale_signature)) is None
