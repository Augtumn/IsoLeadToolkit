"""Check direct app_state attribute assignments in Python source files."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from source_scan_guard import print_scan_result, scan_pattern_hits

PATTERN = re.compile(r"app_state\.[A-Za-z_][A-Za-z0-9_]*\s*=(?!=)")
EXCLUDED_PARTS = {".venv", "reference", ".git"}


def should_scan(path: Path, _repo_root: Path) -> bool:
    if path.suffix != ".py":
        return False
    return not any(part in EXCLUDED_PARTS for part in path.parts)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fail-on-hits", action="store_true")
    args = parser.parse_args()

    root = Path.cwd()
    counts = scan_pattern_hits(root, pattern=PATTERN, include_file=should_scan)
    total = sum(counts.values())
    print_scan_result(counts)

    if args.fail_on_hits and total > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
