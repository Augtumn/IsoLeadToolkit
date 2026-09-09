"""Shared source scanning helpers for guard scripts."""

from __future__ import annotations

from pathlib import Path
from re import Pattern
from typing import Callable

#: Files that could not be read during a scan (reported so a scan can never
#: silently pass because everything was skipped).
SKIPPED_FILES: list[str] = []


def repo_root() -> Path:
    """Return the repository root, independent of the current directory.

    Guards used ``Path.cwd()``, so running them from a subdirectory scanned
    only that subtree and still printed ``TOTAL=0``.
    """
    return Path(__file__).resolve().parents[1]


def should_scan(path: Path, repo_root_path: Path, excluded_parts: set[str]) -> bool:
    """True when *path* is a Python file outside the excluded directories.

    Exclusion is matched against the path *relative to the repository root*:
    matching absolute parts made every file skip when the checkout itself
    lived under a directory named e.g. ``scripts`` or ``tests``.
    """
    if path.suffix != ".py":
        return False
    try:
        rel_parts = path.resolve().relative_to(repo_root_path.resolve()).parts
    except ValueError:
        rel_parts = path.parts
    return not any(part in excluded_parts for part in rel_parts)


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
    SKIPPED_FILES.clear()

    for file_path in root.rglob("*.py"):
        if not include_file(file_path, root):
            continue

        try:
            text = file_path.read_text(encoding="utf-8")
        except Exception as exc:
            try:
                rel = file_path.relative_to(root).as_posix()
            except ValueError:
                rel = str(file_path)
            SKIPPED_FILES.append(rel)
            print(f"SKIPPED\t{rel}\t{exc}")
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
    if SKIPPED_FILES:
        print(f"SKIPPED_TOTAL={len(SKIPPED_FILES)}")

    if total <= 0:
        return

    for rel, count in sorted(counts.items(), key=lambda item: item[1], reverse=True):
        print(f"{count}\t{rel}")
