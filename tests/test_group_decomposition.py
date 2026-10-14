"""Tests for the step-by-step legend-group decomposition.

The legend is grouped by one column and any group can be split again by another column,
inside itself. The arithmetic lives in ``visualization.plotting.decomposition`` and is
pure, so the drill-down is tested here without a window.

A group is named by its path of values, and a specification maps a path to the column
that refines it.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from visualization.plotting.decomposition import (
    EMPTY_LABEL,
    PATH_SEPARATOR,
    decompose,
    effective_labels,
    parent_child_map,
    path_key,
    path_values,
    validate_spec,
)


def _frame() -> pd.DataFrame:
    """Two sites; Tarim's rows split by phase, and one phase of Tarim split by kind."""
    return pd.DataFrame(
        {
            "Site": ["Tarim", "Tarim", "Tarim", "Tarim", "Bronze", "Bronze"],
            "Phase": ["casting", "casting", "forging", "casting", "casting", "forging"],
            "Kind": ["weapon", "tool", "tool", "weapon", "weapon", "tool"],
        }
    )


def test_a_path_key_round_trips() -> None:
    assert path_values(path_key(["Tarim", "casting"])) == ["Tarim", "casting"]
    assert path_key(["a"]) == "a"


def test_no_specification_keeps_every_row_as_it_was() -> None:
    """The falsification case: nothing decomposed means the original values, exactly."""
    frame = _frame()
    assert list(effective_labels(frame, "Site", {})) == list(frame["Site"])


def test_one_group_is_refined_by_a_second_column() -> None:
    frame = _frame()
    labels, parents = decompose(frame, "Site", {path_key(["Tarim"]): "Phase"})
    assert list(labels) == [
        "Tarim / casting",
        "Tarim / casting",
        "Tarim / forging",
        "Tarim / casting",
        "Bronze",
        "Bronze",
    ]
    assert parents == {"Tarim": ["Tarim / casting", "Tarim / forging"]}


def test_a_step_is_refined_again_inside_itself() -> None:
    """The drill-down: casting of Tarim is split by Kind, everything else is untouched."""
    frame = _frame()
    spec = {
        path_key(["Tarim"]): "Phase",
        path_key(["Tarim", "casting"]): "Kind",
    }
    labels, parents = decompose(frame, "Site", spec)
    assert list(labels) == [
        "Tarim / casting / weapon",
        "Tarim / casting / tool",
        "Tarim / forging",
        "Tarim / casting / weapon",
        "Bronze",
        "Bronze",
    ]
    # Every split node is a parent; a child that is split again is a parent too, so the flat
    # map still describes a tree.
    assert parents == {
        "Tarim": ["Tarim / casting", "Tarim / forging"],
        "Tarim / casting": ["Tarim / casting / weapon", "Tarim / casting / tool"],
    }


def test_a_third_step_keeps_going() -> None:
    """Bronze / casting is refined by Grain; the sibling branch keeps its own label."""
    frame = _frame().assign(Grain=["fine", "coarse", "fine", "coarse", "fine", "coarse"])
    spec = {
        path_key(["Bronze"]): "Phase",
        path_key(["Bronze", "casting"]): "Grain",
    }
    labels, parents = decompose(frame, "Site", spec)
    assert "Bronze / casting / fine" in list(labels)
    assert "Bronze / forging" in list(labels), "the sibling branch is untouched"
    assert parents["Bronze"] == ["Bronze / casting", "Bronze / forging"]
    assert parents["Bronze / casting"] == ["Bronze / casting / fine"]


def test_deepening_one_branch_leaves_its_siblings_alone() -> None:
    frame = _frame()
    first = {path_key(["Tarim"]): "Phase"}
    before = list(effective_labels(frame, "Site", first))
    deeper = {**first, path_key(["Tarim", "forging"]): "Kind"}
    after = list(effective_labels(frame, "Site", deeper))
    for index, (old, new) in enumerate(zip(before, after)):
        if new.startswith("Tarim / forging"):
            assert new.startswith(old) and new != old, "the deepened branch must be refined"
        else:
            assert new == old, f"row {index} was not part of the deepened branch"


def test_two_branches_can_use_different_columns() -> None:
    frame = _frame()
    spec = {
        path_key(["Tarim"]): "Phase",
        path_key(["Bronze"]): "Kind",
    }
    labels, parents = decompose(frame, "Site", spec)
    assert "Tarim / casting" in list(labels)
    assert "Bronze / weapon" in list(labels)
    assert set(parents) == {"Tarim", "Bronze"}


def test_clearing_the_specification_restores_the_original_labels() -> None:
    frame = _frame()
    spec = {path_key(["Tarim"]): "Phase", path_key(["Tarim", "casting"]): "Kind"}
    decomposed = list(effective_labels(frame, "Site", spec))
    assert decomposed != list(frame["Site"])
    assert list(effective_labels(frame, "Site", {})) == list(frame["Site"])


def test_missing_values_are_spelled_out() -> None:
    frame = pd.DataFrame({"Site": ["Tarim", "Tarim"], "Phase": [None, "casting"]})
    labels = effective_labels(frame, "Site", {path_key(["Tarim"]): "Phase"})
    assert list(labels) == [f"Tarim / {EMPTY_LABEL}", "Tarim / casting"]


def test_blank_text_is_treated_as_missing() -> None:
    frame = pd.DataFrame({"Site": ["Tarim"], "Phase": ["   "]})
    assert list(effective_labels(frame, "Site", {path_key(["Tarim"]): "Phase"})) == [
        f"Tarim / {EMPTY_LABEL}"
    ]


def test_a_nan_parent_is_still_decomposable() -> None:
    frame = pd.DataFrame({"Site": [np.nan, np.nan], "Phase": ["a", "b"]})
    labels, parents = decompose(frame, "Site", {path_key([EMPTY_LABEL]): "Phase"})
    assert list(labels) == [f"{EMPTY_LABEL} / a", f"{EMPTY_LABEL} / b"]
    assert parents == {EMPTY_LABEL: [f"{EMPTY_LABEL} / a", f"{EMPTY_LABEL} / b"]}


def test_a_value_that_is_not_in_the_data_is_an_error() -> None:
    with pytest.raises(KeyError, match="not present"):
        effective_labels(_frame(), "Site", {path_key(["Nowhere"]): "Phase"})


def test_a_column_that_is_not_in_the_data_is_an_error() -> None:
    with pytest.raises(KeyError, match="no column"):
        effective_labels(_frame(), "Site", {path_key(["Tarim"]): "Nothing"})


def test_a_column_cannot_split_the_group_it_produced() -> None:
    with pytest.raises(ValueError, match="cannot split"):
        validate_spec(_frame(), "Site", {path_key(["Tarim"]): "Site"})


def test_validate_accepts_a_specification_that_can_be_applied() -> None:
    validate_spec(_frame(), "Site", {path_key(["Tarim"]): "Phase"})


def test_validate_rejects_a_grouping_column_that_is_absent() -> None:
    with pytest.raises(KeyError, match="no grouping column"):
        validate_spec(_frame(), "Nothing", {})


def test_an_empty_path_is_rejected() -> None:
    with pytest.raises(ValueError, match="empty path"):
        effective_labels(_frame(), "Site", {"": "Phase"})


def test_parent_child_map_is_empty_for_an_empty_specification() -> None:
    frame = _frame()
    labels = effective_labels(frame, "Site", {})
    assert parent_child_map(labels, {}) == {}
    assert PATH_SEPARATOR not in "".join(str(v) for v in frame["Site"])
