"""Legend search: the pure group filter behind the legend panel's search box."""
from __future__ import annotations

from ui.main_window_parts.legend_actions import filter_legend_groups

GROUPS = [f"G{i:03d}" for i in range(150)]


def test_without_a_query_the_list_is_capped_and_counts_the_hidden_entries() -> None:
    shown, hidden = filter_legend_groups(GROUPS, "")
    assert shown == GROUPS[:100]
    assert hidden == 50, "the panel must be able to tell the user what it hid"


def test_a_query_searches_every_group_including_beyond_the_cap() -> None:
    shown, hidden = filter_legend_groups(GROUPS, "g149")
    assert shown == ["G149"], "groups past the display cap must stay reachable"
    assert hidden == 0


def test_matching_is_case_insensitive_and_partial() -> None:
    shown, _ = filter_legend_groups(["Xinjiang", "新疆苏巴什佛寺", "Gansu"], "xin")
    assert shown == ["Xinjiang"]


def test_a_parent_group_name_matches_its_children() -> None:
    parents = {"新疆": {"G001", "G002"}}
    shown, _ = filter_legend_groups(["G001", "G050"], "新疆", parents)
    assert shown == ["G001"], shown


def test_an_empty_query_with_at_most_cap_items_hides_nothing() -> None:
    shown, hidden = filter_legend_groups(["A", "B"], "")
    assert shown == ["A", "B"] and hidden == 0
