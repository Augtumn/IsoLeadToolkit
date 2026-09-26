"""Legend search: the pure group filter behind the legend panel's search box."""
from __future__ import annotations

from ui.main_window_parts.legend_actions import filter_legend_groups

GROUPS = [f"G{i:03d}" for i in range(150)]


def test_without_a_query_every_group_is_shown() -> None:
    """The panel used to hide everything past the first 100 groups."""
    assert filter_legend_groups(GROUPS, "") == GROUPS


def test_a_query_searches_every_group() -> None:
    assert filter_legend_groups(GROUPS, "g149") == ["G149"]


def test_matching_is_case_insensitive_and_partial() -> None:
    assert filter_legend_groups(["Xinjiang", "新疆苏巴什佛寺", "Gansu"], "xin") == ["Xinjiang"]


def test_a_parent_group_name_matches_its_children() -> None:
    parents = {"新疆": {"G001", "G002"}}
    assert filter_legend_groups(["G001", "G050"], "新疆", parents) == ["G001"]


def test_a_query_without_matches_returns_nothing() -> None:
    assert filter_legend_groups(GROUPS, "zzz") == []
