"""Decompose legend groups step by step, one column at a time.

Grouping is a process of successive refinement: the data is grouped by one column, then
one of those groups is grouped again by a second column, and one of *those* by a third -
arbitrarily deep. Each step happens inside the group it was invoked from, so a legend
entry can be drilled into without disturbing its siblings.

A group is therefore identified by the **path** of values that leads to it
(``("Tarim",)``, ``("Tarim", "casting")``, ...), and the specification says which column
splits which path::

    {"Tarim": "Phase", "Tarim\\x1fcasting": "Kind"}

Keys are paths joined by :data:`PATH_SEPARATOR` (a unit separator, which a data value
cannot contain in practice); a path absent from the specification is a leaf and keeps the
label it already had. The whole thing is pure - no Qt, no application state - so the
arithmetic can be tested on its own.

A specification that cannot be applied - a column the frame does not have, a path whose
values are not in the data - raises instead of being skipped: this repository bans silent
fallbacks, so the caller has to be told what was wrong.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

import pandas as pd

#: Separator between the parent value and the child value in an effective label.
SEPARATOR = " / "

#: Column the decomposition materialises its labels into. To the renderer it is an ordinary grouping
#: column; to the user it is not one of their columns at all, so the places that list columns for them
#: leave it out. Defined here with the decomposition itself, so there is one name for it.
DECOMPOSED_GROUP_COLUMN = "__decomposed_group__"

#: Separator between the values that make up a path key. A unit separator: it cannot
#: realistically appear inside a data value, so paths never collide with labels.
PATH_SEPARATOR = "\x1f"

#: Label used for a missing value, in any position of a path.
EMPTY_LABEL = "(空)"


def path_key(path: Sequence[Any]) -> str:
    """Join the values of *path* into the key used by a specification."""
    return PATH_SEPARATOR.join(str(value) for value in path)


def path_values(key: Any) -> list[str]:
    """Split a specification key back into the values it names."""
    if isinstance(key, (list, tuple)):
        return [str(value) for value in key]
    return [part for part in str(key).split(PATH_SEPARATOR)]


def _cell_text(value: Any) -> str:
    """One cell as display text, with missing values spelled out rather than blank."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return EMPTY_LABEL
    text = str(value)
    return EMPTY_LABEL if text.strip() == "" else text


def _spec_by_path(spec: Mapping[Any, str]) -> dict[tuple[str, ...], str]:
    """Normalise a specification into ``{path tuple: splitting column}``."""
    by_path: dict[tuple[str, ...], str] = {}
    for key, column in spec.items():
        path = tuple(path_values(key))
        if not path or any(part == "" for part in path):
            raise ValueError(f"decomposition: empty path in specification ({key!r})")
        if not isinstance(column, str) or not column:
            raise TypeError(f"decomposition: {key!r} needs a column name")
        by_path[path] = column
    return by_path


def effective_labels(
    frame: pd.DataFrame,
    base_col: str,
    spec: Mapping[Any, str],
    *,
    separator: str = SEPARATOR,
) -> pd.Series:
    """Return the label each row belongs to after applying every step of *spec*.

    A row starts at its value of *base_col* and is refined by the split defined for the
    path it has reached, one step at a time, until no further split is defined.
    """
    if base_col not in frame.columns:
        raise KeyError(f"decomposition: no grouping column {base_col!r} in the data")
    by_path = _spec_by_path(spec)
    for path, column in by_path.items():
        if column not in frame.columns:
            raise KeyError(
                "decomposition: path "
                + separator.join(path)
                + f" is split by {column!r}, which the data has no column for"
            )

    base = frame[base_col].map(_cell_text)
    present = set(base)
    for path in by_path:
        if path[0] not in present:
            raise KeyError(
                f"decomposition: value {path[0]!r} is not present in {base_col!r}"
            )

    labels: list[str] = []
    for index in frame.index:
        parts = [base.loc[index]]
        while True:
            column = by_path.get(tuple(parts))
            if column is None:
                break
            parts.append(_cell_text(frame.at[index, column]))
            if len(parts) > len(by_path) + 1:  # a cycle can never be legitimate
                raise ValueError("decomposition: the specification refers to itself")
        labels.append(separator.join(parts))
    return pd.Series(labels, index=frame.index, dtype=object)


def parent_child_map(
    labels: pd.Series,
    spec: Mapping[Any, str],
    *,
    separator: str = SEPARATOR,
) -> dict[str, list[str]]:
    """Map every split node to its **direct** children, ready for the legend.

    Shaped for ``state_gateway.set_parent_groups``: a child appears under exactly one
    parent, and a child that is itself split also appears as a parent key, so the flat
    map still describes a tree - which is what the legend walks.
    """
    by_path = _spec_by_path(spec)
    every = [str(label) for label in labels]
    parents: dict[str, list[str]] = {}
    for path in by_path:
        parent_label = separator.join(path)
        children: list[str] = []
        prefix = f"{parent_label}{separator}"
        for label in every:
            if not label.startswith(prefix):
                continue
            remainder = label[len(prefix):]
            first = remainder.split(separator)[0]
            child = f"{prefix}{first}"
            if child not in children:
                children.append(child)
        parents[parent_label] = children
    return parents


def decompose(
    frame: pd.DataFrame,
    base_col: str,
    spec: Mapping[Any, str],
    *,
    separator: str = SEPARATOR,
) -> tuple[pd.Series, dict[str, list[str]]]:
    """Return ``(effective labels, parent -> direct children)`` for *spec*."""
    labels = effective_labels(frame, base_col, spec, separator=separator)
    return labels, parent_child_map(labels, spec, separator=separator)


def validate_spec(frame: pd.DataFrame, base_col: str, spec: Mapping[Any, str]) -> None:
    """Raise if *spec* cannot be applied to *frame*; used before anything is written."""
    if not isinstance(spec, Mapping):
        raise TypeError("decomposition: the specification must be a mapping")
    by_path = _spec_by_path(spec)
    for path, column in by_path.items():
        if base_col not in frame.columns:
            raise KeyError(f"decomposition: no grouping column {base_col!r} in the data")
        if column not in frame.columns:
            raise KeyError(f"decomposition: the data has no column {column!r}")
        # The group a step refines is produced by the base column at the first step, and by the
        # column of the step above it deeper down. Splitting a group with the column that made
        # it would not refine anything.
        parent_column = base_col if len(path) == 1 else by_path.get(path[:-1], base_col)
        if column == parent_column:
            raise ValueError(
                f"decomposition: {column!r} cannot split a group it produced itself"
            )
    effective_labels(frame, base_col, spec)
