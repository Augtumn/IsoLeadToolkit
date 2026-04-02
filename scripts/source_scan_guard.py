"""Shared source scanning helpers for guard scripts."""

from __future__ import annotations

from pathlib import Path
from re import Pattern
from typing import Callable


def scan_pattern_hits(
    root: Path,
    *,
    pattern: Pattern[str],
    include_file: Callable[[Path, Path], bool],
    allowlist: set[str] | None = None,
) -> dict[str, int]:
    """Scan Python files and count regex hits by relative file path."""
    allow = allowlist or set()
    counts: dict[str, int] = {}

    for file_path in root.rglob("*.py"):
        if not include_file(file_path, root):
            continue

        try:
            text = file_path.read_text(encoding="utf-8")
        except Exception:
            continue

        hits = len(pattern.findall(text))
        if hits <= 0:
            continue

        rel = file_path.relative_to(root).as_posix()
        if rel in allow:
            continue
        counts[rel] = hits

    return counts


def print_scan_result(counts: dict[str, int]) -> None:
    """Print scanner output in stable, CI-friendly format."""
    total = sum(counts.values())
    print(f"TOTAL={total}")

    if total <= 0:
        return

    for rel, count in sorted(counts.items(), key=lambda item: item[1], reverse=True):
        print(f"{count}\t{rel}")
