"""Tests for visualization.plotting.core column helper heuristics."""

from __future__ import annotations

from visualization.plotting.core import _get_pb_columns


def test_get_pb_columns_prefers_exact_names() -> None:
    columns = ["206Pb/204Pb", "foo", "207Pb/204Pb", "208Pb/204Pb"]

    pb206, pb207, pb208 = _get_pb_columns(columns)

    assert pb206 == "206Pb/204Pb"
    assert pb207 == "207Pb/204Pb"
    assert pb208 == "208Pb/204Pb"


def test_get_pb_columns_uses_heuristic_when_exact_missing() -> None:
    columns = ["sample_206_204", "ratio_207_204", "value_208-204"]

    pb206, pb207, pb208 = _get_pb_columns(columns)

    assert pb206 == "sample_206_204"
    assert pb207 == "ratio_207_204"
    assert pb208 == "value_208-204"
