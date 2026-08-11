# -*- coding: utf-8 -*-
"""Check direct app_state attribute assignments in Python source files.

Detects both simple (``app_state.foo = x``) and nested sub-object
(``app_state.overlay.foo = x``) assignments that bypass the StateStore.
Runtime-only targets (matplotlib objects, transient render maps) that are
rebuilt each render are excluded.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from source_scan_guard import print_scan_result

# Simple + nested assignments: app_state.foo = x  /  app_state.sub.foo = x
PATTERN = re.compile(r"app_state\.[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)?\s*=(?!=)")
EXCLUDED_PARTS = {".venv", "reference", ".git", "tests", "scripts"}

# Runtime-only matplotlib objects — not snapshot-managed.
RUNTIME_OBJECTS: tuple[str, ...] = ("app_state.annotation.", "app_state.fig.", "app_state.ax.")

# Transient render maps — rebuilt every render, cleared by clear_plot_state().
RUNTIME_MAP_FIELDS: tuple[str, ...] = (
    "sample_index_map",
    "sample_coordinates",
    "artist_to_sample",
    "group_to_scatter",
    "legend_to_scatter",
    "scatter_collections",
    "marginal_axes",
    "overlay_artists",
)


def should_scan(path: Path, _repo_root: Path) -> bool:
    if path.suffix != ".py":
        return False
    return not any(part in EXCLUDED_PARTS for part in path.parts)


def _is_runtime_target(line: str) -> bool:
    """True when the assignment writes a runtime-only object or map."""
    s = line.strip()
    for obj in RUNTIME_OBJECTS:
        if s.startswith(obj):
            return True
    for field in RUNTIME_MAP_FIELDS:
        if re.match(rf"app_state\.{field}(\s*\[|\s*=)", s):
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fail-on-hits", action="store_true")
    args = parser.parse_args()

    root = Path.cwd()
    counts: dict[str, int] = {}
    for file_path in root.rglob("*.py"):
        if not should_scan(file_path, root):
            continue
        rel = file_path.relative_to(root).as_posix()
        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue
        for line in lines:
            if PATTERN.search(line) and not _is_runtime_target(line):
                counts[rel] = counts.get(rel, 0) + 1

    total = sum(counts.values())
    print_scan_result(counts)

    if args.fail_on_hits and total > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
