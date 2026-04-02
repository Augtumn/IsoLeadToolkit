"""Shared scanner helpers for generic gateway mutation guard scripts."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

from source_scan_guard import print_scan_result, scan_pattern_hits

_PATTERN = re.compile(r"\bstate_gateway\.set_attrs?\s*\(")


def scan_generic_gateway_calls(
    root: Path,
    *,
    include_file: Callable[[Path, Path], bool],
    allowlist: set[str] | None = None,
) -> dict[str, int]:
    """Scan Python files and count generic gateway mutation usages.

    Args:
        root: Repository root directory.
        include_file: Predicate deciding whether a file should be scanned.
        allowlist: Relative POSIX paths to skip even if hits are found.

    Returns:
        Mapping of relative POSIX file path to hit count.
    """
    return scan_pattern_hits(
        root,
        pattern=_PATTERN,
        include_file=include_file,
        allowlist=allowlist,
    )
