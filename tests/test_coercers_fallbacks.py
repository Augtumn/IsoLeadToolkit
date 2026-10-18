"""The coercers keep a documented default instead of inventing a value.

Reported by review: a non-numeric entry in a label-spacing pair became 0.0 without a word, and the PCA component
indices could name the same component on both axes.
"""
from __future__ import annotations

import pytest

from core.state import coercers


def test_a_non_numeric_spacing_value_keeps_the_default(qapp, caplog) -> None:
    pair = coercers._normalize_adjust_text_pair(
        [5.0, "abc"], default=(2.0, 3.0), min_value=-100.0, max_value=100.0
    )
    assert pair == (5.0, 3.0), "the slot keeps the documented default, not 0.0"
    assert any("label-spacing" in record.message for record in caplog.records), "and it is said"


def test_a_numeric_spacing_value_is_used(qapp) -> None:
    pair = coercers._normalize_adjust_text_pair(
        [5.0, 7.0], default=(2.0, 3.0), min_value=-100.0, max_value=100.0
    )
    assert pair == (5.0, 7.0)


@pytest.mark.parametrize(
    ("given", "expected"),
    [([0, 1], [0, 1]), ([1], [1, 0]), ([1, 0], [1, 0]), (2, [2, 0])],
)
def test_the_two_axes_are_different_components(qapp, given, expected) -> None:
    assert coercers._normalize_pca_component_indices(given) == expected


def test_the_same_component_twice_falls_back_to_the_first_two(qapp) -> None:
    assert coercers._normalize_pca_component_indices([3, 3]) == [0, 1]
