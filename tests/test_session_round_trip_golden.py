"""A session round trip carries every snapshot field.

The architecture health check named the gap: the state model has 205 snapshot keys and nothing compared a save and
a load against the state that was saved, so a change that made a field non-restorable would have passed unnoticed.
This is that net. It writes representative values, exports, changes them, imports, and compares all 205 keys with
the state that was exported.

The test starts from no dataset on purpose. A session exported with data than imported back goes through hydration,
which by design resets column selection and can report a flag - a different path from the one this test is about.
The fixture clears the dataset first and puts everything back afterwards, including the data fields: they are
excluded from the restore whitelist, as tests/test_session.py also has to work around.
"""
from __future__ import annotations

import numpy as np
import pytest

from application.use_cases import export_session, import_session
from core import state_gateway
from core.persistence import _json_safe


def _canonical(value):
    """A snapshot with every array turned into a list.

    _json_safe is what the save writes, but a nested ndarray can survive it, and comparing two of those with != is
    an ambiguous-truth-value error rather than an answer. Comparing canonical forms keeps the test about the round
    trip.
    """
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, dict):
        return {str(key): _canonical(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    return value


def _snapshot() -> dict:
    return _canonical(_json_safe(state_gateway.snapshot()))


def _restore_data(original: dict) -> None:
    state_gateway.set_dataframe_and_source(
        original["df_global"],
        file_path=original.get("file_path") or "",
        sheet_name=original.get("sheet_name"),
    )


@pytest.fixture()
def clean_state():
    """No dataset, so the round trip takes the config-only path; everything is put back afterwards."""
    original = state_gateway.snapshot()
    data = {key: original[key] for key in ("df_global", "file_path", "sheet_name") if key in original}
    state_gateway.set_dataframe_and_source(None, file_path="", sheet_name=None)
    yield
    _restore_data({**original, **data})
    state_gateway.restore_snapshot(original)


def _write(values: dict) -> None:
    state_gateway.set_render_mode(values["render_mode"])
    state_gateway.set_algorithm(values["algorithm"])
    state_gateway.set_plot_marker_size(values["plot_marker_size"])
    state_gateway.set_show_tooltip(values["show_tooltip"])
    state_gateway.set_show_marginal_kde(values["show_marginal_kde"])
    state_gateway.set_last_group_col(values["last_group_col"])
    state_gateway.set_visible_groups(list(values["visible_groups"]))


FIRST = {
    "render_mode": "PCA",
    "algorithm": "PCA",
    "plot_marker_size": 7,
    "show_tooltip": True,
    "show_marginal_kde": True,
    "last_group_col": "metal_province",
    "visible_groups": ["a", "b"],
}
SECOND = {
    "render_mode": "tSNE",
    "algorithm": "tSNE",
    "plot_marker_size": 3,
    "show_tooltip": False,
    "show_marginal_kde": False,
    "last_group_col": "other",
    "visible_groups": ["c"],
}


def test_a_session_round_trip_carries_every_snapshot_field(clean_state, tmp_path) -> None:
    archive = tmp_path / "session.isotopes"

    _write(FIRST)
    saved = _snapshot()
    assert export_session(str(archive)) is True

    _write(SECOND)
    changed = _snapshot()
    assert [key for key in saved if changed.get(key) != saved.get(key)], (
        "the values must actually differ before the import, or the comparison proves nothing"
    )

    ok, flag = import_session(str(archive))
    assert ok is True and flag is None

    loaded = _snapshot()
    lost = sorted(key for key in saved if loaded.get(key) != saved.get(key))
    assert lost == [], "the round trip lost: " + repr(lost)

