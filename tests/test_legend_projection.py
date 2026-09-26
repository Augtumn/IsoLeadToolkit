"""The inline legend is a projection of the panel list (ordering)."""
from __future__ import annotations

import matplotlib
import pytest

matplotlib.use("Agg")

from matplotlib.figure import Figure  # noqa: E402

from visualization.plotting.rendering.common.legend import (  # noqa: E402
    apply_permutation,
    legend_order_permutation,
)


def test_entries_follow_the_panel_order() -> None:
    labels = ["B", "A", "C"]
    order = ["group:A", "group:B", "group:C"]

    permutation = legend_order_permutation(labels, order)

    assert apply_permutation(labels, permutation) == ["A", "B", "C"]


def test_unknown_labels_keep_their_relative_order_at_the_end() -> None:
    labels = ["Overlay", "A", "B"]
    order = ["group:B", "group:A"]

    permutation = legend_order_permutation(labels, order)

    assert apply_permutation(labels, permutation) == ["B", "A", "Overlay"]


def test_parent_entries_match_by_name() -> None:
    labels = ["Xinjiang", "Gansu"]
    order = ["parent:Xinjiang", "group:Gansu"]

    permutation = legend_order_permutation(labels, order)

    assert apply_permutation(labels, permutation) == ["Xinjiang", "Gansu"]


def test_an_empty_order_changes_nothing() -> None:
    labels = ["B", "A"]

    assert apply_permutation(labels, legend_order_permutation(labels, [])) == labels


def test_the_permutation_keeps_parallel_lists_aligned() -> None:
    """Handles and scatters must be reordered by the same permutation."""
    labels = ["B", "A"]
    handles = ["handle-B", "handle-A"]
    scatters = ["scatter-B", "scatter-A"]

    permutation = legend_order_permutation(labels, ["group:A", "group:B"])

    assert apply_permutation(handles, permutation) == ["handle-A", "handle-B"]
    assert apply_permutation(scatters, permutation) == ["scatter-A", "scatter-B"]


def test_a_mismatched_parallel_list_is_left_alone() -> None:
    assert apply_permutation(["only-one"], [1, 0]) == ["only-one"]
    assert apply_permutation([], [0]) == []
