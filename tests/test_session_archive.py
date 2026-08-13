"""Session archive (export/import) tests."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from application.use_cases import export_session, import_session
from application.use_cases.session_io import _DATA_CONTRACT_KEYS
from core import app_state, state_gateway
from core.persistence import SESSION_ARCHIVE_FORMAT
from core.persistence import export_session as export_archive
from core.persistence import import_session as import_archive


class _FakeStore:
    """Minimal store stand-in exposing snapshot() for archive tests."""

    def __init__(self, snapshot: dict) -> None:
        self._snap = snapshot

    def snapshot(self) -> dict:
        return dict(self._snap)


def _sample_snapshot(df: pd.DataFrame | None = None) -> dict:
    return {
        "algorithm": "tSNE",
        "render_mode": "tSNE",
        "umap_params": {"n_neighbors": 10},
        "language": "zh",
        "file_path": "D:/data/sample.xlsx",
        "df_global": df,
        "plot_marker_size": 72,
        "visible_groups": ["A", "B"],
    }


def test_export_archive_with_data(tmp_path: Path) -> None:
    df = pd.DataFrame({
        "Pb206": [1.0, 2.0, np.nan],
        "Pb207": [3.0, 4.0, 5.0],
        "Province": ["A", "B", "A"],
    })
    archive = tmp_path / "session.zip"
    assert export_archive(_FakeStore(_sample_snapshot(df)), archive) is True

    with zipfile.ZipFile(archive, "r") as zf:
        names = set(zf.namelist())
        assert {"manifest.json", "session.json", "ui_state.json", "data.csv"} <= names

        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["format"] == SESSION_ARCHIVE_FORMAT
        assert manifest["version"] == 1
        assert manifest["has_data"] is True
        assert manifest["data_file"] == "data.csv"

        session = json.loads(zf.read("session.json"))
        assert session["algorithm"] == "tSNE"
        assert session["session_version"] >= 1

        ui = json.loads(zf.read("ui_state.json"))
        assert ui["plot_marker_size"] == 72

        data = pd.read_csv(zf.open("data.csv"))
        assert list(data.columns) == ["Pb206", "Pb207", "Province"]
        assert len(data) == 3


def test_export_archive_without_data(tmp_path: Path) -> None:
    archive = tmp_path / "session.zip"
    assert export_archive(_FakeStore(_sample_snapshot(None)), archive) is True
    with zipfile.ZipFile(archive, "r") as zf:
        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["has_data"] is False
        assert "data.csv" not in zf.namelist()


def test_import_archive_roundtrip(tmp_path: Path) -> None:
    df = pd.DataFrame({"Pb206": [1.0, 2.0], "Pb207": [3.0, 4.0]})
    archive = tmp_path / "session.zip"
    assert export_archive(_FakeStore(_sample_snapshot(df)), archive) is True

    payloads = import_archive(archive)
    assert payloads is not None
    assert payloads["has_data"] is True
    assert payloads["session"]["algorithm"] == "tSNE"
    assert payloads["session"]["file_path"] == "D:/data/sample.xlsx"
    assert payloads["ui_state"]["plot_marker_size"] == 72
    restored = pd.read_csv(io.BytesIO(payloads["data_csv"].encode("utf-8")))
    assert list(restored.columns) == ["Pb206", "Pb207"]


def test_import_archive_rejects_newer_version(tmp_path: Path) -> None:
    archive = tmp_path / "future.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr(
            "manifest.json",
            json.dumps({"format": SESSION_ARCHIVE_FORMAT, "version": 99, "has_data": False}),
        )
        zf.writestr("session.json", "{}")
        zf.writestr("ui_state.json", "{}")
    assert import_archive(archive) is None


def test_import_archive_rejects_non_archive(tmp_path: Path) -> None:
    plain = tmp_path / "notes.txt"
    plain.write_text("not a session", encoding="utf-8")
    assert import_archive(plain) is None

    foreign = tmp_path / "foreign.zip"
    with zipfile.ZipFile(foreign, "w") as zf:
        zf.writestr("manifest.json", json.dumps({"format": "something-else", "version": 1}))
    assert import_archive(foreign) is None

    assert import_archive(tmp_path / "missing.zip") is None


def test_application_import_restores_config_and_data(tmp_path: Path) -> None:
    """End-to-end: export the live state, mutate it, import it back."""
    original = state_gateway.snapshot()
    archive = tmp_path / "session.zip"
    try:
        df = pd.DataFrame({
            "Pb206": [1.0, 2.0, 3.0],
            "Pb207": [4.0, 5.0, 6.0],
            "Province": ["A", "B", "A"],
        })
        state_gateway.set_dataframe_and_source(df, file_path="D:/x.xlsx", sheet_name="S1")
        state_gateway.set_group_data_columns(["Province"], ["Pb206", "Pb207"])
        state_gateway.set_render_mode("tSNE")

        assert export_session(str(archive)) is True

        # Mutate live state to prove import really restores it.
        state_gateway.set_render_mode("UMAP")
        state_gateway.set_group_data_columns([], [])
        state_gateway.set_dataframe_and_source(None, file_path="", sheet_name=None)

        ok, flag = import_session(str(archive))
        assert ok is True
        assert flag is None
        assert app_state.render_mode == "tSNE"
        assert app_state.group_cols == ["Province"]
        assert app_state.data_cols == ["Pb206", "Pb207"]
        assert app_state.df_global is not None and len(app_state.df_global) == 3
        assert app_state.file_path == "D:/x.xlsx"
        assert app_state.sheet_name == "S1"
    finally:
        # Restore the pre-test state to keep other tests isolated. df_global
        # is excluded from the restore whitelist, so restore it explicitly.
        state_gateway.set_dataframe_and_source(
            original["df_global"],
            file_path=original["file_path"],
            sheet_name=original["sheet_name"],
        )
        state_gateway.restore_snapshot(original)


def test_data_contract_keys_cover_hydration_inputs() -> None:
    """The pre-hydration contract must include every column/path field."""
    assert {"group_cols", "data_cols", "file_path", "sheet_name", "last_group_col"} <= set(
        _DATA_CONTRACT_KEYS
    )
