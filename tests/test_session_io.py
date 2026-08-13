"""Tests for core/session/io session persistence helpers."""

from __future__ import annotations

import json
from pathlib import Path

from core.config import CONFIG
from core.session.io import (
    _atomic_write_json,
    load_session_params,
    save_session_params,
)


def test_save_session_params_roundtrip(tmp_path: Path, monkeypatch) -> None:
    params_file = tmp_path / "params.json"
    monkeypatch.setitem(CONFIG, "params_temp_file", params_file)

    ok = save_session_params(
        algorithm="UMAP",
        umap_params={"n_neighbors": 12, "min_dist": 0.2},
        tsne_params={"perplexity": 25},
        point_size=80,
        group_col="Province",
        group_cols=["Province"],
        data_cols=["206Pb/204Pb"],
        file_path="C:/data/sample.xlsx",
        render_mode="UMAP",
        language="zh",
        parent_groups={"coins": ["A", "B"], "silver": []},
        parent_shape_map={"coins": "^"},
    )
    assert ok is True
    assert params_file.exists()
    # Atomic write must not leave the temp file behind.
    assert not (tmp_path / "params.json.tmp").exists()

    loaded = load_session_params()
    assert loaded is not None
    assert loaded["algorithm"] == "UMAP"
    assert loaded["umap_params"]["n_neighbors"] == 12
    assert loaded["point_size"] == 80
    assert loaded["file_path"] == "C:/data/sample.xlsx"
    assert loaded["language"] == "zh"
    assert loaded["parent_groups"] == {"coins": ["A", "B"], "silver": []}
    assert loaded["parent_shape_map"] == {"coins": "^"}


def test_save_session_params_default_parent_groups(tmp_path: Path, monkeypatch) -> None:
    params_file = tmp_path / "params.json"
    monkeypatch.setitem(CONFIG, "params_temp_file", params_file)

    ok = save_session_params(
        algorithm="UMAP",
        umap_params={},
        tsne_params={},
        point_size=60,
        group_col="Province",
    )
    assert ok is True
    loaded = load_session_params()
    assert loaded is not None
    assert loaded["parent_groups"] == {}


def test_atomic_write_json_replaces_existing_file(tmp_path: Path) -> None:
    target = tmp_path / "params.json"
    target.write_text('{"old": true}', encoding="utf-8")

    _atomic_write_json(target, {"new": 1})

    assert json.loads(target.read_text(encoding="utf-8")) == {"new": 1}
    assert not (tmp_path / "params.json.tmp").exists()
