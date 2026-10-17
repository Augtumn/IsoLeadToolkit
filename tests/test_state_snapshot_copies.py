"""Snapshots hand out copies of the values that can be changed in place.

Reported by review: current_feature_names, last_pca_variance and last_pca_components were the only three
projections that returned the internal object rather than a copy. An in-place change therefore modified both
the state and the store's authoritative snapshot, and the direct-mutation detector compared that object with
itself - it always found them equal, so the very change it exists to catch went unnoticed.
"""
from __future__ import annotations

import numpy as np
import pytest

from core import app_state
from core.state.store import StateStore


@pytest.fixture()
def snapshot():
    app_state.current_feature_names = ["a", "b"]
    app_state.last_pca_variance = np.array([1.0, 2.0])
    app_state.last_pca_components = np.array([[1.0, 0.0], [0.0, 1.0]])
    return StateStore(app_state).snapshot()


def test_the_snapshot_does_not_share_the_feature_name_list(snapshot) -> None:
    assert snapshot["current_feature_names"] is not app_state.current_feature_names
    snapshot["current_feature_names"].append("c")
    assert app_state.current_feature_names == ["a", "b"], "changing the snapshot left the state alone"


def test_the_snapshot_does_not_share_the_pca_arrays(snapshot) -> None:
    assert snapshot["last_pca_variance"] is not app_state.last_pca_variance
    assert snapshot["last_pca_components"] is not app_state.last_pca_components
    snapshot["last_pca_variance"][0] = 99.0
    assert app_state.last_pca_variance[0] == 1.0


def test_two_snapshots_do_not_share_each_other(snapshot) -> None:
    store = StateStore(app_state)
    first = store.snapshot()
    second = store.snapshot()
    assert first["current_feature_names"] is not second["current_feature_names"]
